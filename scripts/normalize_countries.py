"""Fold historical / variant country names in the events table onto their modern
canonical name (see country_canonical.py).

Idempotent and cheap (indexed UPDATE over a handful of alias names) — the daily
pipeline runs it before compute_stats so country_stats aggregates one row per
country, the choropleth colors it (feature names match), and country pages route
by the modern name. Also safe to run by hand:

    python scripts/normalize_countries.py
"""
import sys

from country_canonical import CANONICAL_COUNTRY
from database import get_conn
from logger import log


def normalize(conn) -> int:
    """Rename aliased country rows in-place. Returns rows changed."""
    total = 0
    for alias, canon in CANONICAL_COUNTRY.items():
        if alias == canon:
            continue
        cur = conn.execute(
            "UPDATE events SET country = ? WHERE country = ?", (canon, alias)
        )
        if cur.rowcount:
            total += cur.rowcount
            log.info(f"  {alias!r} → {canon!r}: {cur.rowcount:,}")
    conn.commit()
    return total


def main() -> int:
    conn = get_conn()
    changed = normalize(conn)
    remaining = conn.execute(
        "SELECT COUNT(*) FROM events WHERE country LIKE '%(%'"
    ).fetchone()[0]
    conn.close()
    log.info(f"normalize_countries: {changed:,} rows renamed; "
             f"{remaining:,} parenthetical names remain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
