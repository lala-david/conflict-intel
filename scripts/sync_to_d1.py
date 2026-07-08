"""
Sync the local conflict.db → Cloudflare D1 (the DB the live site reads).

  CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_API_TOKEN=... D1_DATABASE_ID=... \
      python scripts/sync_to_d1.py

Talks to the D1 HTTP query API (no wrangler CLI needed), mirroring the old
sync_to_turso.py so the daily job stays a drop-in swap.

Strategy (safe against a partial CI DB):
  - events / sanctions : append today's rows (INSERT OR IGNORE) — never destructive.
  - stats / crypto     : full replace, but ONLY if the local DB looks complete
                         (>= MIN_EVENTS). Otherwise the production snapshot is left
                         intact so a fresh/incomplete CI DB can't wipe it.

For the one-time INITIAL load of the whole DB, prefer the bulk importer instead
(much faster than the REST API):

  sqlite3 data/conflict.db .dump > /tmp/conflict.sql
  wrangler d1 import conflict-intel --remote --file=/tmp/conflict.sql

`--full` here (REST, batched) exists as a fallback when wrangler isn't available.
"""
import os
import sys
import sqlite3
from datetime import datetime

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

DB = os.path.join(os.path.dirname(__file__), "..", "data", "conflict.db")
ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
DBID = os.environ.get("D1_DATABASE_ID", "")
MIN_EVENTS = 100_000  # guard: don't full-replace stats from an incomplete DB
MAX_BODY = 90_000     # keep each /query request body under D1's request-size limit

# --dry-run emits the SQL it WOULD send to data/d1_sync_dryrun.sql (no network, no
# creds needed) so the daily payload can be inspected or applied via wrangler.
DRY = "--dry-run" in sys.argv
_DRY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "d1_sync_dryrun.sql")
_dry_lines: list[str] = []

if not DRY and not (ACCOUNT and TOKEN and DBID):
    sys.exit("CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN and D1_DATABASE_ID required.")

API = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/d1/database/{DBID}/query"
HDR = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


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


def _post(sql: str):
    if DRY:
        _dry_lines.append(sql)
        return
    r = requests.post(API, headers=HDR, json={"sql": sql}, timeout=180)
    if r.status_code >= 400:
        raise RuntimeError(f"D1 HTTP {r.status_code}: {r.text[:500]}")
    body = r.json()
    if not body.get("success", False):
        raise RuntimeError(f"D1 error: {body.get('errors')}")


def _flush(stmts):
    if stmts:
        _post("\n".join(stmts))


def _cols(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def _push(conn, table, verb="INSERT OR IGNORE", where="", replace=False):
    cols = _cols(conn, table)
    collist = ", ".join(cols)
    if replace:
        _post(f"DELETE FROM {table};")
    n, size, batch = 0, 0, []
    for row in conn.execute(f"SELECT {collist} FROM {table} {where}"):
        stmt = f"{verb} INTO {table} ({collist}) VALUES ({', '.join(_lit(v) for v in row)});"
        # flush before the batch would exceed the request-size limit
        if batch and size + len(stmt) > MAX_BODY:
            _flush(batch)
            n += len(batch)
            size, batch = 0, []
        batch.append(stmt)
        size += len(stmt) + 1
    _flush(batch)
    n += len(batch)
    return n


def main():
    full = "--full" in sys.argv
    conn = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"local DB: {n_events:,} events{' (FULL load)' if full else ''}")

    ev_where = "" if full else f"WHERE collected_at LIKE '{today}%'"
    sa_where = "" if full else f"WHERE collected_date LIKE '{today}%'"
    e = _push(conn, "events", "INSERT OR IGNORE", ev_where)
    s = _push(conn, "sanctions", "INSERT OR IGNORE", sa_where)
    print(f"  events +{e}, sanctions +{s}")

    if n_events < MIN_EVENTS:
        print(f"  SKIP stats/crypto replace — local DB incomplete ({n_events} < {MIN_EVENTS})")
    else:
        for t in ("global_stats", "country_stats", "org_stats", "category_stats", "daily_stats",
                  "crypto_addresses", "crypto_stats"):
            try:
                c = _push(conn, t, "INSERT OR REPLACE", replace=True)
                print(f"  replaced {t}: {c}")
            except Exception as ex:  # noqa: BLE001
                print(f"  {t} skipped: {ex}")
    conn.close()

    if DRY:
        with open(_DRY_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(_dry_lines) + "\n")
        print(f"DRY RUN — {len(_dry_lines)} batch(es) written to {_DRY_PATH} (no network)")
    else:
        print("DONE — D1 synced.")


if __name__ == "__main__":
    main()
