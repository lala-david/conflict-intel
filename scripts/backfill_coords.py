"""Backfill latitude/longitude for events already in the DB that lack coords
(text sources: wikidata/wikipedia/gtd/telegram rows that arrived without lat/lon).
Uses the shared geocoder (Nominatim + on-disk cache, country-centroid fallback).
Idempotent: only rows with null/zero/empty coords are touched. Junk locations that
fail to geocode are left null and simply retried on the next run."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geocoder import geocode  # noqa: E402

# Historical / alternate country strings Nominatim can't resolve → a geocodable
# equivalent, so the country-centroid fallback still lands the event on the map.
COUNTRY_ALIAS = {
    "West Germany (FRG)": "Germany",
    "West Bank and Gaza Strip": "Palestine",
    "People's Republic of the Congo": "Republic of the Congo",
}


def main():
    conn = sqlite3.connect("data/conflict.db", timeout=60)
    rows = conn.execute(
        "SELECT id, location, country FROM events "
        "WHERE dup_of IS NULL AND (latitude IS NULL OR latitude=0 OR latitude='') "
        "AND (country!='' OR location!='')"
    ).fetchall()
    print(f"geocoding {len(rows)} events missing coords…", flush=True)
    filled = 0
    for i, (eid, loc, ctry) in enumerate(rows, 1):
        lat, lon = geocode(loc, COUNTRY_ALIAS.get(ctry, ctry), sleep=1.0)
        if lat is not None:
            conn.execute("UPDATE events SET latitude=?, longitude=? WHERE id=?", (lat, lon, eid))
            filled += 1
        if i % 10 == 0:
            conn.commit()
            print(f"  {i}/{len(rows)} (filled {filled})", flush=True)
    conn.commit()
    conn.close()
    print(f"done: filled {filled}/{len(rows)} events")


if __name__ == "__main__":
    main()
