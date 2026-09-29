"""
Sync the local conflict.db → Cloudflare D1 (the DB the live site reads).

  python scripts/sync_to_d1.py                    # normal run
  python scripts/sync_to_d1.py --since 2026-08-03 # (re)start the events cursor there
  python scripts/sync_to_d1.py --max-writes 50000 # cap this run's D1 writes
  python scripts/sync_to_d1.py --dry-run          # read D1, write the SQL to a file instead
  python scripts/sync_to_d1.py --twin path.db     # diff against a local SQLite file (tests)
  python scripts/sync_to_d1.py --db other.db      # sync from a DB other than data/conflict.db

Credentials: CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN / D1_DATABASE_ID (CI secrets).
Locally, anything missing falls back to wrangler's own login (the OAuth token in its
config file, the one account that token sees, and database_id from web/wrangler.jsonc),
so after `wrangler login` this runs with no extra setup.

Built around D1's free-tier quotas — 5M rows read and 100K rows WRITTEN per day, where
every index entry touched counts as a written row. Replacing tables wholesale does not
fit: crypto_addresses alone (17K rows x 6 index entries, deleted then re-inserted) came
to ~200K writes per sync. So each step writes only what actually differs:

  1. stats / gold / crypto tables: read D1's copy, compare by primary key, upsert the
     changed rows and delete vanished ones. Bookkeeping columns that change on every
     run (updated_at, collected_date) are ignored in the comparison, except on
     global_stats, whose updated_at is the site's "Updated X ago".
  2. dup_of: reconcile duplicate marks on events already on D1. INSERT OR IGNORE never
     updates an existing row, so a mark set after the row was first synced — e.g. by
     the laptop's LLM dedup — would otherwise never reach the site.
  3. events: append everything past a cursor ("collected_at|id") kept on D1 in
     sync_state, so it survives across machines and resumes where the last run
     stopped. INSERT OR IGNORE, so re-sending a row costs a read, not a write.

Writes are metered against --max-writes (default 80K, leaving headroom for the site's
own writes) using the rows_written D1 reports back. When the budget runs out the run
stops cleanly; the next run carries on from the cursor.

Guard: tables are only reconciled when the local DB looks complete (>= MIN_EVENTS),
so a fresh or partial CI DB can't delete production rows.

One sync writer at a time: the events cursor assumes rows are appended in collected_at
order by the machine that syncs. If CI and the laptop both collect, seed one from the
other (db-latest) rather than syncing both.
"""
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import requests

from country_canonical import CANONICAL_COUNTRY

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
MIN_EVENTS = 100_000   # guard: don't reconcile tables from an incomplete DB
MAX_BODY = 90_000      # keep each /query request body under D1's request-size limit
PROBE = 25             # first batch of a costed run: measures the real per-row write cost

# Mirrored by primary-key diff, homepage tables first so a tight budget still
# leaves the front page consistent.
TABLES = ("global_stats", "yearly_stats", "wire_hotspots", "country_codes", "event_sources",
          "country_stats", "category_stats", "daily_stats", "org_stats",
          "crypto_stats", "event_reviews", "crypto_addresses")
VOLATILE = {"updated_at", "collected_date"}   # change every run, mean nothing new
VOLATILE_KEPT = {"global_stats"}              # ...except where the site shows it
CURSOR_KEY = "events_cursor"


def _arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


DB = _arg("--db", str(ROOT / "data" / "conflict.db"))
DRY = "--dry-run" in sys.argv
TWIN = _arg("--twin")
SINCE = _arg("--since")
MAX_WRITES = int(_arg("--max-writes", "80000"))
DRY_PATH = str(ROOT / "data" / "d1_sync_dryrun.sql")


def _lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    return "'" + str(v).replace("'", "''") + "'"


def _norm(v):
    # D1 hands rows back as JSON, so compare on JSON's terms.
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


# ── backends: query() -> (rows, rows_read); execute() -> (rows_written, rows_read) ──

class D1:
    """Cloudflare D1 over its HTTP query API."""

    def __init__(self):
        token = os.environ.get("CLOUDFLARE_API_TOKEN") or _wrangler_token()
        if not token:
            sys.exit("No CLOUDFLARE_API_TOKEN and no wrangler login found — run `wrangler login`.")
        self.hdr = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or self._only_account()
        dbid = os.environ.get("D1_DATABASE_ID") or _wrangler_database_id()
        if not dbid:
            sys.exit("No D1_DATABASE_ID, and none found in web/wrangler.jsonc.")
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{account}/d1/database/{dbid}/query"

    def _only_account(self):
        r = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=self.hdr, timeout=30)
        accts = r.json().get("result") or []
        if len(accts) != 1:
            sys.exit(f"Set CLOUDFLARE_ACCOUNT_ID — the token sees {len(accts)} accounts.")
        return accts[0]["id"]

    def _call(self, sql):
        r = requests.post(self.url, headers=self.hdr, json={"sql": sql}, timeout=180)
        if r.status_code >= 400:
            raise RuntimeError(f"D1 HTTP {r.status_code}: {r.text[:500]}")
        body = r.json()
        if not body.get("success", False):
            raise RuntimeError(f"D1 error: {body.get('errors')}")
        return body["result"]

    def query(self, sql):
        res = self._call(sql)[0]
        return res.get("results") or [], res.get("meta", {}).get("rows_read", 0)

    def execute(self, sql, table=None):
        res = self._call(sql)
        return (sum(r.get("meta", {}).get("rows_written", 0) for r in res),
                sum(r.get("meta", {}).get("rows_read", 0) for r in res))


class Twin:
    """A local SQLite file standing in for D1 — tests and offline dry-runs.
    rows_written is estimated the way D1 counts it: each changed row x (1 + indexes)."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def query(self, sql):
        rows = [dict(r) for r in self.conn.execute(sql)]
        return rows, len(rows)

    def execute(self, sql, table=None):
        before = self.conn.total_changes
        self.conn.executescript(sql)
        changed = self.conn.total_changes - before
        n_idx = self.conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=?", (table,)
        ).fetchone()[0] if table else 0
        return changed * (1 + n_idx), 0


def _wrangler_token():
    for base in (os.environ.get("APPDATA", ""), os.path.expanduser("~")):
        for sub in ("xdg.config/.wrangler", ".wrangler", ".config/.wrangler"):
            p = Path(base) / sub / "config" / "default.toml"
            if p.exists():
                m = re.search(r'^oauth_token\s*=\s*"([^"]+)"', p.read_text(encoding="utf-8"), re.M)
                if m:
                    return m.group(1)
    return None


def _wrangler_database_id():
    p = ROOT / "web" / "wrangler.jsonc"
    if p.exists():
        m = re.search(r'"database_id"\s*:\s*"([^"]+)"', p.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return None


# ── metered writer ────────────────────────────────────────────────────────

class OutOfBudget(Exception):
    pass


class Writer:
    """Sends statements in request-sized batches and meters rows_written against
    the run's budget. Each batch is checked *before* sending with a per-statement
    cost estimate, so the budget is never overshot; the tally uses D1's actuals."""

    def __init__(self, backend, budget):
        self.b, self.budget = backend, budget
        self.written = self.read = self.learned = 0
        self.exhausted = False
        self.dry: list[str] = []
        self._idx: dict[str, int] = {}

    def left(self):
        return self.budget - self.written

    def query(self, sql):
        rows, n = self.b.query(sql)
        self.read += n
        return rows

    def remote_indexes(self, table):
        """Index count on D1's copy of `table` — what a written row really costs there."""
        if table not in self._idx:
            rows = self.query("SELECT COUNT(*) AS n FROM sqlite_master "
                              f"WHERE type='index' AND tbl_name={_lit(table)}")
            self._idx[table] = rows[0]["n"] if rows else 0
        return self._idx[table]

    def send(self, stmts, table=None, cost=0):
        """One request. Raises OutOfBudget instead of sending if it could overshoot.
        Returns the rows actually written."""
        if not stmts:
            return 0
        if cost and cost > self.left():
            raise OutOfBudget
        sql = "\n".join(stmts)
        if DRY:
            self.dry.append(sql)
            self.written += cost
            return cost
        w, r = self.b.execute(sql, table)
        self.written += w
        self.read += r
        return w

    def run(self, stmts, table=None, cost_each=0):
        """Send `stmts` in as many requests as the body limit needs; return how many
        went out. Stops early (setting .exhausted) when the next batch wouldn't fit
        the budget. The per-statement cost starts as an estimate and is raised to
        what D1 actually reported after every batch; the first batch is a small
        probe, so a bad guess can overshoot by at most PROBE statements."""
        sent, batch, size = 0, [], 0
        cap = PROBE if cost_each else None
        for s in stmts:
            if batch and (size + len(s) > MAX_BODY or (cap and len(batch) >= cap)
                          or cost_each * (len(batch) + 1) > self.left()):
                if not self._batch(batch, table, cost_each):
                    return sent
                sent += len(batch)
                cost_each, cap, batch, size = self.learned, None, [], 0
            batch.append(s)
            size += len(s) + 1
        if batch and self._batch(batch, table, cost_each):
            sent += len(batch)
        return sent

    def _batch(self, batch, table, cost_each):
        try:
            written = self.send(batch, table, cost_each * len(batch))
        except OutOfBudget:
            self.exhausted = True
            return False
        self.learned = max(cost_each, -(-written // len(batch))) if cost_each else 0
        return True


# ── sync steps ────────────────────────────────────────────────────────────

def _cols(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def _pk(conn, table):
    return [r[1] for r in sorted(conn.execute(f"PRAGMA table_info({table})"), key=lambda r: r[5]) if r[5]]


def ensure_table(conn, w, table):
    """Create `table` on D1 from the local schema if it isn't there yet, so a new
    gold table ships with the next sync instead of failing as 'no such table'."""
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if sql and sql[0]:
        w.send([sql[0].replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1) + ";"])


def mirror_table(conn, w, table):
    """Make D1's `table` equal the local one, writing only the rows that differ."""
    ensure_table(conn, w, table)
    cols, pk = _cols(conn, table), _pk(conn, table)
    ignore = set() if table in VOLATILE_KEPT else VOLATILE
    cmp_cols = [c for c in cols if c not in ignore]

    local = {tuple(_norm(r[c]) for c in pk): r
             for r in (dict(zip(cols, row)) for row in conn.execute(f"SELECT {', '.join(cols)} FROM {table}"))}
    remote = {tuple(_norm(r[c]) for c in pk): tuple(_norm(r[c]) for c in cmp_cols)
              for r in w.query(f"SELECT {', '.join(cols)} FROM {table}")}

    upserts = [r for k, r in local.items() if remote.get(k) != tuple(_norm(r[c]) for c in cmp_cols)]
    deletes = [k for k in remote if k not in local]
    per_row = 1 + w.remote_indexes(table)
    up = w.run([f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) "
                f"VALUES ({', '.join(_lit(r[c]) for c in cols)});" for r in upserts],
               table, 2 * per_row)   # REPLACE = delete + insert, each touching every index
    dl = 0 if w.exhausted else w.run(
        [f"DELETE FROM {table} WHERE " + " AND ".join(f"{c} = {_lit(v)}" for c, v in zip(pk, k)) + ";"
         for k in deletes], table, per_row)
    return f"upserted {up:,}/{len(upserts):,}, deleted {dl:,}/{len(deletes):,}", len(local)


def normalize_countries(w):
    """Fold historical/variant country names on the D1 side (events append is
    INSERT OR IGNORE, so already-synced rows keep their old name until renamed
    here). Idempotent — mirrors scripts/normalize_countries.py. Once applied these
    match nothing, so they cost index reads only."""
    w.run([f"UPDATE events SET country = {_lit(canon)} WHERE country = {_lit(alias)};"
           for alias, canon in CANONICAL_COUNTRY.items() if alias != canon], "events")


def get_cursor(w):
    rows = w.query(f"SELECT value FROM sync_state WHERE key = {_lit(CURSOR_KEY)}")
    return rows[0]["value"] if rows else None


def _split(cursor):
    at, _, last_id = cursor.partition("|")
    return at, last_id


def reconcile_dup_of(conn, w, cursor):
    """Bring dup_of on D1 in line with the local DB for events already pushed
    (those at or before the cursor). Later rows carry their mark when inserted."""
    at, last_id = _split(cursor)
    # `dup_of > ''` rather than IS NOT NULL: same rows, but it can use
    # idx_events_dup instead of scanning all ~600K events on D1.
    remote = {r["id"]: r["dup_of"] for r in w.query("SELECT id, dup_of FROM events WHERE dup_of > ''")}
    local = dict(conn.execute(
        "SELECT id, dup_of FROM events WHERE dup_of > '' AND (collected_at, id) <= (?, ?)", (at, last_id)))
    sets = [(i, d) for i, d in local.items() if remote.get(i) != d]
    # D1 marks the local DB has since cleared. Local is authoritative, but only
    # for rows it actually holds — an id it doesn't know is left alone.
    gone = [i for i in remote if i not in local]
    cleared = []
    for k in range(0, len(gone), 500):
        chunk = gone[k:k + 500]
        cleared += [r[0] for r in conn.execute(
            f"SELECT id FROM events WHERE id IN ({', '.join('?' * len(chunk))}) "
            "AND (dup_of IS NULL OR dup_of = '')", chunk)]
    stmts = ([f"UPDATE events SET dup_of = {_lit(d)} WHERE id = {_lit(i)};" for i, d in sets] +
             [f"UPDATE events SET dup_of = NULL WHERE id = {_lit(i)};" for i in cleared])
    # Estimated at the row plus its idx_events_dup entry; Writer.run corrects that
    # from D1's own count after the first small batch.
    return len(sets), len(cleared), w.run(stmts, "events", 2)


def push_events(conn, w, cursor):
    """Append local events past the cursor, oldest first. Each request carries its
    batch plus the cursor move, so stopping at any point loses nothing."""
    at, last_id = _split(cursor)
    cols = _cols(conn, "events")
    i_at, i_id = cols.index("collected_at"), cols.index("id")
    where = "WHERE (collected_at, id) > (?, ?)"
    pending = conn.execute(f"SELECT COUNT(*) FROM events {where}", (at, last_id)).fetchone()[0]
    per_row = 1 + w.remote_indexes("events")

    pushed, batch, size, cur, sent = 0, [], 0, cursor, cursor

    def flush():
        # Returns the per-row cost D1 actually charged, so later batches are sized
        # on facts rather than on the index-count estimate.
        written = w.send(batch + [f"INSERT OR REPLACE INTO sync_state (key, value) "
                                  f"VALUES ({_lit(CURSOR_KEY)}, {_lit(cur)});"],
                         "events", per_row * len(batch) + 2)
        return max(per_row, -(-written // len(batch)))

    try:
        for r in conn.execute(f"SELECT {', '.join(cols)} FROM events {where} "
                              "ORDER BY collected_at, id", (at, last_id)):
            stmt = f"INSERT OR IGNORE INTO events ({', '.join(cols)}) VALUES ({', '.join(_lit(v) for v in r)});"
            if batch and (size + len(stmt) > MAX_BODY - 300 or per_row * (len(batch) + 1) + 2 > w.left()):
                per_row = flush()
                pushed, sent = pushed + len(batch), cur
                batch, size = [], 0
                if per_row + 2 > w.left():
                    raise OutOfBudget
            batch.append(stmt)
            size += len(stmt) + 1
            cur = f"{r[i_at]}|{r[i_id]}"
        if batch:
            flush()
            pushed, sent = pushed + len(batch), cur
    except OutOfBudget:
        w.exhausted = True
    return pushed, pending, sent


def main():
    w = Writer(Twin(TWIN) if TWIN else D1(), MAX_WRITES)
    conn = sqlite3.connect(DB)
    n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"local DB: {n_events:,} events | write budget {MAX_WRITES:,}{' | DRY RUN' if DRY else ''}")

    try:
        w.send(["CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT);"])
        if SINCE:
            # Persist it now: if the budget runs out before any event is pushed,
            # the next run must still know where to start.
            w.send([f"INSERT OR REPLACE INTO sync_state (key, value) "
                    f"VALUES ({_lit(CURSOR_KEY)}, {_lit(SINCE + '|')});"])
        normalize_countries(w)

        if n_events < MIN_EVENTS:
            print(f"  SKIP tables — local DB incomplete ({n_events} < {MIN_EVENTS})")
        else:
            for t in TABLES:
                if w.exhausted:
                    break
                if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone():
                    print(f"  {t:17} not in the local DB yet — run compute_stats.py first; skipped")
                    continue
                result, n = mirror_table(conn, w, t)
                print(f"  {t:17} {n:6,} rows | {result}")

        today = datetime.now().strftime("%Y-%m-%d")
        sa_cols = _cols(conn, "sanctions")
        sa = [f"INSERT OR IGNORE INTO sanctions ({', '.join(sa_cols)}) VALUES ({', '.join(_lit(v) for v in r)});"
              for r in conn.execute(f"SELECT {', '.join(sa_cols)} FROM sanctions "
                                    "WHERE collected_date LIKE ?", (f"{today}%",))]
        if not w.exhausted:
            print(f"  sanctions         +{w.run(sa, 'sanctions', 1 + w.remote_indexes('sanctions'))}/{len(sa)}")

        cursor = f"{SINCE}|" if SINCE else get_cursor(w)   # (a dry run never stored it)
        if not cursor:
            print("  events: no cursor on D1 yet — run once with --since YYYY-MM-DD to set where to start")
        elif not w.exhausted:
            s, c, done = reconcile_dup_of(conn, w, cursor)
            print(f"  dup_of            {s:,} to set, {c:,} to clear — sent {done:,}")
            if not w.exhausted:
                pushed, pending, cursor = push_events(conn, w, cursor)
                print(f"  events            {pushed:,} of {pending:,} pending sent | cursor {cursor}")
    except OutOfBudget:
        w.exhausted = True
    finally:
        conn.close()
    if w.exhausted:
        print("  write budget exhausted — the next run continues from here")

    print(f"D1 rows written {w.written:,} / {MAX_WRITES:,} | rows read {w.read:,}")
    if DRY:
        Path(DRY_PATH).write_text("\n".join(w.dry) + "\n", encoding="utf-8")
        print(f"DRY RUN — {len(w.dry)} request(s) written to {DRY_PATH}")


if __name__ == "__main__":
    main()
