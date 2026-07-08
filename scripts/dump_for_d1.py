"""
Generate a full SQL dump of the local conflict.db for the ONE-TIME initial load
into Cloudflare D1 (schema + indexes + every row). Daily increments go through
scripts/sync_to_d1.py instead — this is only for seeding a fresh D1.

  python scripts/dump_for_d1.py                 # → data/conflict_d1.sql
  python scripts/dump_for_d1.py out.sql          # → custom path

Then load it (wrangler batches large files natively):

  cd web && npx wrangler d1 execute conflict-intel --remote --yes --file=../<out.sql>
  cd web && npx wrangler d1 execute conflict-intel --remote --yes --file=../scripts/d1_waitlist_schema.sql

BEGIN/COMMIT/PRAGMA lines are stripped because wrangler wraps its own transaction.
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "conflict.db"


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "conflict_d1.sql"
    conn = sqlite3.connect(str(DB_PATH))
    kept = skipped = 0
    with open(out, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            s = line.strip()
            if s in ("BEGIN TRANSACTION;", "COMMIT;") or s.startswith("PRAGMA"):
                skipped += 1
                continue
            f.write(line + "\n")
            kept += 1
    conn.close()
    mb = out.stat().st_size / 1e6
    print(f"wrote {kept:,} statements ({skipped} control lines skipped) → {out} ({mb:.0f} MB)")


if __name__ == "__main__":
    main()
