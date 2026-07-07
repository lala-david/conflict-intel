"""One-time GTD backfill: Bronze land + insert 1970-2016 terror events into `events`.
Idempotent (INSERT OR IGNORE by id). Country codes mapped from our existing data.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gtd_source import fetch_gtd  # noqa: E402
from database import init_db, get_conn  # noqa: E402
from pipeline import bronze  # noqa: E402

# a few GTD → our canonical country-name fixups for the ISO lookup
FIX = {
    "United States": "United States of America",
    "West Germany (FRG)": "Germany", "East Germany (GDR)": "Germany",
    "Soviet Union": "Russia (Soviet Union)", "Russia": "Russia (Soviet Union)",
    "Zaire": "DR Congo (Zaire)", "Democratic Republic of the Congo": "DR Congo (Zaire)",
    "Yemen": "Yemen (North Yemen)", "Myanmar": "Myanmar (Burma)",
    "Bosnia-Herzegovina": "Bosnia-Herzegovina", "Slovak Republic": "Slovakia",
}


def main():
    init_db()
    conn = get_conn()
    name2code = {n: c for n, c in conn.execute(
        "SELECT DISTINCT country, country_code FROM events "
        "WHERE country_code IS NOT NULL AND country_code != ''")}

    def code_for(country):
        return name2code.get(country) or name2code.get(FIX.get(country, "")) or None

    print("fetching GTD…", flush=True)
    rows = fetch_gtd()
    print(f"  {len(rows):,} events", flush=True)

    run_id = datetime.now().strftime("gtd-%Y%m%d-%H%M%S")
    bronze.land("gtd", rows, run_id)

    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)")]
    have = set(cols)
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    field = ["id", "source", "date", "event_type", "actor1", "actor2", "country",
             "country_code", "location", "latitude", "longitude", "fatalities",
             "notes", "category", "is_aggregate", "collected_at"]
    field = [f for f in field if f in have]
    sql = f"INSERT OR IGNORE INTO events ({','.join(field)}) VALUES ({','.join(['?'] * len(field))})"
    batch, n = [], 0
    for r in rows:
        rec = {**r, "country_code": code_for(r["country"]), "is_aggregate": 0,
               "collected_at": today}
        batch.append([rec.get(f) for f in field])
        if len(batch) >= 2000:
            conn.executemany(sql, batch)
            n += len(batch)
            batch = []
    if batch:
        conn.executemany(sql, batch)
        n += len(batch)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    gtd = conn.execute("SELECT COUNT(*) FROM events WHERE source='gtd'").fetchone()[0]
    coded = conn.execute("SELECT COUNT(*) FROM events WHERE source='gtd' AND country_code!=''").fetchone()[0]
    conn.close()
    print(f"  inserted (new): from {n} candidates | gtd in db: {gtd:,} | with iso: {coded:,}")
    print(f"  events total now: {total:,}")


if __name__ == "__main__":
    main()
