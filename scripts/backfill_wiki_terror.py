"""Backfill 2017-present terror incidents from Wikipedia lists + Wikidata SPARQL.
Bronze land + geocode (city coords) + insert into events. Idempotent (INSERT OR IGNORE).
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_terror_source import fetch_wiki_terror  # noqa: E402
from wikidata_terror_source import fetch_wikidata_terror  # noqa: E402
from database import init_db, get_conn  # noqa: E402
from pipeline import bronze  # noqa: E402
from geocoder import geocode  # noqa: E402


def main():
    init_db()
    conn = get_conn()
    countries = {r[0] for r in conn.execute("SELECT DISTINCT country FROM events WHERE country != ''")}
    name2code = {n: c for n, c in conn.execute(
        "SELECT DISTINCT country, country_code FROM events "
        "WHERE country_code IS NOT NULL AND country_code != ''")}

    run_id = datetime.now().strftime("recent-%Y%m%d-%H%M%S")
    rows = []
    print("fetching Wikipedia terror lists 2017→…", flush=True)
    try:
        w = fetch_wiki_terror(range(2017, 2027), countries)
        bronze.land("wikipedia", w, run_id)
        rows += w
        print(f"  wikipedia: {len(w):,}", flush=True)
    except Exception as ex:
        print(f"  wikipedia failed: {ex}", flush=True)
    print("fetching Wikidata terror SPARQL 2017→…", flush=True)
    try:
        wd = fetch_wikidata_terror(2017)
        bronze.land("wikidata", wd, run_id)
        rows += wd
        print(f"  wikidata: {len(wd):,}", flush=True)
    except Exception as ex:
        print(f"  wikidata failed: {ex}", flush=True)
    if not rows:
        return

    print(f"geocoding missing city coords ({sum(1 for r in rows if not r.get('latitude'))})…", flush=True)
    for i, r in enumerate(rows, 1):
        if not r.get("latitude"):
            lat, lng = geocode(r.get("location") or "", r.get("country") or "", sleep=1.0)
            r["latitude"], r["longitude"] = lat, lng
        if i % 150 == 0:
            print(f"  geocoded {i}/{len(rows)}", flush=True)

    cols = {c[1] for c in conn.execute("PRAGMA table_info(events)")}
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    field = [f for f in ["id", "source", "date", "event_type", "actor1", "actor2",
                         "country", "country_code", "location", "latitude", "longitude",
                         "fatalities", "notes", "category", "is_aggregate", "collected_at"]
             if f in cols]
    sql = f"INSERT OR IGNORE INTO events ({','.join(field)}) VALUES ({','.join(['?'] * len(field))})"
    rec_rows = [[{**r, "country_code": name2code.get(r["country"]), "is_aggregate": 0,
                  "collected_at": today}.get(f) for f in field] for r in rows]
    conn.executemany(sql, rec_rows)
    conn.commit()
    for src in ("wikipedia", "wikidata"):
        n = conn.execute("SELECT COUNT(*) FROM events WHERE source=? AND category='terrorism'", (src,)).fetchone()[0]
        coords = conn.execute("SELECT COUNT(*) FROM events WHERE source=? AND latitude IS NOT NULL AND latitude!=0", (src,)).fetchone()[0]
        print(f"  {src} terror in db: {n:,} | with coords: {coords:,}")
    conn.close()


if __name__ == "__main__":
    main()
