"""
Sync the local conflict.db → Turso (the DB the live site reads).

  TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... python scripts/sync_to_turso.py

Strategy (safe against a partial CI DB):
  - events / sanctions : append today's rows (INSERT OR IGNORE) — never destructive.
  - stats / crypto     : full replace, but ONLY if the local DB looks complete
                         (>= MIN_EVENTS). Otherwise the production snapshot is left
                         intact so a fresh/incomplete CI DB can't wipe it.
"""
import os
import sys
import sqlite3
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), "..", "data", "conflict.db")
URL = os.environ.get("TURSO_DATABASE_URL", "")
TOK = os.environ.get("TURSO_AUTH_TOKEN", "")
MIN_EVENTS = 100_000  # guard: don't full-replace stats from an incomplete DB

if not URL or not TOK:
    sys.exit("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN required.")

import requests  # noqa: E402

PIPE = URL.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline"
HDR = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}


def _arg(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, bytes):
        return {"type": "text", "value": v.decode("utf-8", "replace")}
    return {"type": "text", "value": str(v)}


def _post(stmts):
    r = requests.post(PIPE, headers=HDR, json={"requests": stmts}, timeout=180)
    r.raise_for_status()
    for res in r.json().get("results", []):
        if res.get("type") == "error":
            raise RuntimeError(res["error"]["message"])


def _cols(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def _push(conn, table, verb="INSERT OR REPLACE", where="", replace=False):
    cols = _cols(conn, table)
    rows = conn.execute(f"SELECT {', '.join(cols)} FROM {table} {where}").fetchall()
    sql = f"{verb} INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})"
    if replace:
        _post([{"type": "execute", "stmt": {"sql": f"DELETE FROM {table}"}}, {"type": "close"}])
    n = 0
    batch = []
    for row in rows:
        batch.append({"type": "execute", "stmt": {"sql": sql, "args": [_arg(v) for v in row]}})
        if len(batch) >= 200:
            _post([{"type": "execute", "stmt": {"sql": "BEGIN"}}] + batch
                  + [{"type": "execute", "stmt": {"sql": "COMMIT"}}, {"type": "close"}])
            n += len(batch)
            batch = []
    if batch:
        _post([{"type": "execute", "stmt": {"sql": "BEGIN"}}] + batch
              + [{"type": "execute", "stmt": {"sql": "COMMIT"}}, {"type": "close"}])
        n += len(batch)
    return n


def main():
    conn = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"local DB: {n_events:,} events")

    # always safe — append today's new rows
    e = _push(conn, "events", "INSERT OR IGNORE", f"WHERE collected_at LIKE '{today}%'")
    s = _push(conn, "sanctions", "INSERT OR IGNORE", f"WHERE collected_date LIKE '{today}%'")
    print(f"  appended: events +{e}, sanctions +{s}")

    if n_events < MIN_EVENTS:
        print(f"  SKIP stats/crypto replace — local DB incomplete ({n_events} < {MIN_EVENTS})")
        return

    for t in ("global_stats", "country_stats", "org_stats", "category_stats", "daily_stats",
              "crypto_addresses", "crypto_stats"):
        try:
            c = _push(conn, t, "INSERT OR REPLACE", replace=True)
            print(f"  replaced {t}: {c}")
        except Exception as ex:  # noqa: BLE001
            print(f"  {t} skipped: {ex}")
    conn.close()
    print("DONE — Turso synced.")


if __name__ == "__main__":
    main()
