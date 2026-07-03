"""
Turso 동기화용 SQL 생성기.

웹사이트(Cloudflare Pages)는 Turso(클라우드 SQLite)를 읽는다. 파이프라인은 로컬
conflict.db(sqlite3)에 그대로 쓰고, 이 스크립트가 "Turso에 반영할 변경분"만 SQL로 출력한다.
출력은 `turso db shell <db>` 에 파이프해서 적용한다.

  python scripts/export_for_turso.py            # 일일 증분 (오늘 수집분 + 통계 전체)
  python scripts/export_for_turso.py --full     # 전체 마이그레이션 (최초 1회)

- 통계 테이블(global_stats / country_stats / org_stats / category_stats / daily_stats)은
  매번 전체 교체(작아서 비용 무시 가능).
- events / sanctions 는 INSERT OR IGNORE 로 누적(중복 무해).
  증분 모드는 collected_at 이 오늘인 행만, full 모드는 전체.
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "conflict.db"

STATS_TABLES = ["global_stats", "country_stats", "org_stats", "category_stats", "daily_stats", "crypto_addresses"]
APPEND_TABLES = ["events", "sanctions"]


def _lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def _emit_table(conn, table, where="", insert_verb="INSERT OR REPLACE"):
    cur = conn.execute(f"SELECT * FROM {table} {where}")
    cols = [d[0] for d in cur.description]
    collist = ", ".join(cols)
    n = 0
    for row in cur:
        vals = ", ".join(_lit(v) for v in row)
        print(f"{insert_verb} INTO {table} ({collist}) VALUES ({vals});")
        n += 1
    return n


def main():
    full = "--full" in sys.argv
    conn = sqlite3.connect(str(DB_PATH))
    today = datetime.now().strftime("%Y-%m-%d")

    print("PRAGMA foreign_keys=OFF;")
    print("BEGIN;")

    # 통계 테이블: 전체 교체
    for t in STATS_TABLES:
        try:
            print(f"DELETE FROM {t};")
            _emit_table(conn, t, insert_verb="INSERT")
        except sqlite3.OperationalError:
            pass  # 테이블이 없을 수 있음

    # events / sanctions: 누적 (full=전체, 증분=오늘 수집분)
    for t in APPEND_TABLES:
        where = "" if full else f"WHERE collected_at LIKE '{today}%'"
        try:
            cnt = _emit_table(conn, t, where=where, insert_verb="INSERT OR IGNORE")
            print(f"-- {t}: {cnt} rows", file=sys.stderr)
        except sqlite3.OperationalError as e:
            print(f"-- skip {t}: {e}", file=sys.stderr)

    print("COMMIT;")
    conn.close()


if __name__ == "__main__":
    main()
