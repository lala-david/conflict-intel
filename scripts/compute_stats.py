"""
Pre-computed stats — 매일 CI에서 pipeline/run.py (report_builder.py 제공 함수 사용) 후 실행.
420K rows 실시간 scan 대신 집계 테이블 1-row lookup으로 대시보드 100x 빠르게.
"""
import sys
import math
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from database import get_conn, _ensure_columns
from logger import log


def _country_threat_score(f7, f30, f90, ev30, ev90):
    """
    Country threat score, 0-100 integer.

    Replaces the old `MIN(100, 90d_fatalities * 0.1)`, which saturated: any country
    with >= 1000 deaths in 90 days pegged at 100, so a full-scale war and a mid-size
    insurgency collapsed to the same number — with no baseline and no legend.

    This version discriminates across the high end by combining three signals and
    compressing the fatality term logarithmically (deaths have diminishing marginal
    impact, which is closer to how perceived severity actually scales):

      * Fatality load — recency-weighted deaths. The last 7 days count ~3x, the rest
        of the month ~1x, and the 8-90 day tail ~0.35x, so a fresh spike outranks the
        same body-count spread thinly over a quarter.
      * Tempo — event frequency (last 30d, with the 30-90d tail at 0.4x), so sustained
        low-lethality violence still registers even when casualty data is sparse/lagged.
      * Acceleration — the share of the quarter's deaths that landed in the last 30d;
        rewards conflicts that are escalating rather than winding down.

    Scale bands: 0-33 low · 34-66 elevated · 67-100 severe. Tuned so typical active
    conflicts spread across ~40-95 instead of all pegging 100; 100 is reserved for
    catastrophic, escalating mass-casualty situations.

    CAVEAT: this is fatality-VOLUME and tempo driven, NOT per-capita (there is no
    population data), so large active-war countries outscore small countries with
    intense but localized violence. It is a triage signal, not a normalized risk rate.
    """
    # recency-weighted death load (buckets are non-overlapping, all >= 0)
    load = f7 * 3.0 + (f30 - f7) * 1.0 + (f90 - f30) * 0.35
    tempo = ev30 * 1.0 + (ev90 - ev30) * 0.4
    raw = math.log1p(max(0.0, load)) * 10.0 + math.log1p(max(0.0, tempo)) * 3.5
    if f90 > 0:
        raw += (f30 / f90) * 7.0  # acceleration: recent share of the quarter's toll
    return max(0, min(100, int(round(raw))))


def compute():
    conn = get_conn()
    now = datetime.now().isoformat()

    # ─── 테이블 생성 ───
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS global_stats (
            id INTEGER PRIMARY KEY DEFAULT 1,
            total_events INTEGER, total_fatalities INTEGER, total_countries INTEGER,
            events_7d INTEGER, fatalities_7d INTEGER,
            events_30d INTEGER, fatalities_30d INTEGER,
            events_90d INTEGER, fatalities_90d INTEGER,
            threat_index INTEGER,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS country_stats (
            country TEXT PRIMARY KEY,
            total_events INTEGER, total_fatalities INTEGER,
            events_30d INTEGER, fatalities_30d INTEGER,
            events_90d INTEGER, fatalities_90d INTEGER,
            top_category TEXT, threat_score REAL,
            last_event_date TEXT, updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS org_stats (
            name TEXT PRIMARY KEY,
            total_events INTEGER, total_fatalities INTEGER,
            countries INTEGER, first_seen TEXT, last_seen TEXT,
            updated_at TEXT
        );
    """)

    # ─── Global stats ───
    log.info("Computing global stats...")
    g = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND dup_of IS NULL
    """).fetchone()

    countries = conn.execute("""
        SELECT COUNT(*) FROM (SELECT DISTINCT country FROM events WHERE country != '' LIMIT 300)
    """).fetchone()[0]

    w7 = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND dup_of IS NULL AND date >= date('now', '-7 days')
    """).fetchone()

    w30 = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND dup_of IS NULL AND date >= date('now', '-30 days')
    """).fetchone()

    w90 = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND dup_of IS NULL AND date >= date('now', '-90 days')
    """).fetchone()

    # Global threat index (0-100): recency-weighted, log-compressed worldwide death
    # load. Same recency buckets as the per-country score (last 7d ~3x, rest of the
    # month ~1x, 8-90d tail ~0.35x), passed through 1 - e^(-load/2500) so a busy
    # quarter doesn't instantly peg 100 and the top of the scale stays discriminating.
    # (The old form gated the whole score on 7d fatalities being > 0, which zeroed
    #  the index during quiet weeks even when the month was violent — fixed here.)
    load = w7[1] * 3.0 + (w30[1] - w7[1]) * 1.0 + (w90[1] - w30[1]) * 0.35
    threat_idx = min(100, max(0, int(round(100 * (1 - math.exp(-load / 2500.0))))))

    conn.execute("DELETE FROM global_stats")
    conn.execute("""
        INSERT INTO global_stats (id, total_events, total_fatalities, total_countries,
            events_7d, fatalities_7d, events_30d, fatalities_30d,
            events_90d, fatalities_90d, threat_index, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (g[0], g[1], countries, w7[0], w7[1], w30[0], w30[1], w90[0], w90[1], threat_idx, now))

    log.info(f"  global: {g[0]:,} events, threat={threat_idx}")

    # ─── Country stats ───
    # threat_score is computed in Python (see _country_threat_score) rather than in
    # SQL: the log/sigmoid compression isn't portable across SQLite builds. We pull
    # the raw window aggregates (incl. 7d, used only for scoring) and fold them in.
    log.info("Computing country stats...")
    conn.execute("DELETE FROM country_stats")
    agg = conn.execute("""
        SELECT
            e.country,
            COUNT(*),
            COALESCE(SUM(e.fatalities), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-7 days')  THEN e.fatalities ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-30 days') THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-30 days') THEN e.fatalities ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-90 days') THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-90 days') THEN e.fatalities ELSE 0 END), 0),
            COALESCE((
                SELECT category FROM events e2
                WHERE e2.country = e.country AND e2.is_aggregate = 0 AND e2.dup_of IS NULL AND e2.category IS NOT NULL
                GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1
            ), ''),
            MAX(e.date)
        FROM events e
        WHERE e.is_aggregate = 0 AND e.dup_of IS NULL AND e.country != ''
        GROUP BY e.country
    """).fetchall()

    country_rows = []
    for (country, total_events, total_fatalities, f7, ev30, f30,
         ev90, f90, top_category, last_event_date) in agg:
        score = _country_threat_score(f7, f30, f90, ev30, ev90)
        country_rows.append((country, total_events, total_fatalities,
                             ev30, f30, ev90, f90, top_category, score,
                             last_event_date, now))

    conn.executemany("""
        INSERT INTO country_stats (country, total_events, total_fatalities,
            events_30d, fatalities_30d, events_90d, fatalities_90d,
            top_category, threat_score, last_event_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, country_rows)

    c_count = conn.execute("SELECT COUNT(*) FROM country_stats").fetchone()[0]
    log.info(f"  countries: {c_count}")

    # ─── Org stats ───
    log.info("Computing org stats...")
    conn.execute("DELETE FROM org_stats")
    conn.execute("""
        INSERT INTO org_stats (name, total_events, total_fatalities,
            countries, first_seen, last_seen, updated_at)
        SELECT
            actor1,
            COUNT(*),
            COALESCE(SUM(fatalities), 0),
            COUNT(DISTINCT country),
            MIN(date),
            MAX(date),
            ?
        FROM events
        WHERE is_aggregate = 0 AND dup_of IS NULL AND actor1 != ''
            AND actor1 NOT LIKE 'Government of%'
            AND actor1 NOT LIKE 'XXX%'
            AND length(actor1) < 60
        GROUP BY actor1
        HAVING COUNT(*) >= 3
    """, (now,))

    o_count = conn.execute("SELECT COUNT(*) FROM org_stats").fetchone()[0]
    log.info(f"  orgs: {o_count}")

    # ─── Category stats ───
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_stats (
            category TEXT PRIMARY KEY,
            total_events INTEGER, total_fatalities INTEGER,
            updated_at TEXT
        )
    """)
    conn.execute("DELETE FROM category_stats")
    conn.execute("""
        INSERT INTO category_stats (category, total_events, total_fatalities, updated_at)
        SELECT category, COUNT(*), COALESCE(SUM(fatalities), 0), ?
        FROM events WHERE is_aggregate = 0 AND dup_of IS NULL AND category IS NOT NULL
        GROUP BY category
    """, (now,))

    # ─── Homepage serving tables ───
    # The homepage used to compute these live on every request, and three of
    # them scan most of the events table — the yearly ridgeline alone read ~500K
    # rows per run, 83% of all D1 reads (2026-09), which kept the account far
    # over D1's 5M-rows/day free tier and broke the data pages for most of each
    # day. The results only change when this pipeline runs, so they are
    # materialized here and the web reads a few hundred rows instead. The WHERE
    # clauses mirror the queries they replace so the numbers stay identical.
    log.info("Computing homepage serving tables...")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS yearly_stats (
            year INTEGER PRIMARY KEY,
            events INTEGER, fatalities INTEGER,
            fatalities_all INTEGER,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS wire_hotspots (
            rank INTEGER PRIMARY KEY,
            lat REAL, lng REAL, fatalities INTEGER,
            category TEXT, country TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS country_codes (
            country TEXT PRIMARY KEY,
            country_code TEXT
        );
        CREATE TABLE IF NOT EXISTS event_sources (
            source TEXT PRIMARY KEY,
            events INTEGER
        );
    """)

    # History ridgeline (lib/queries-history.ts): events/fatalities exclude
    # aggregates and duplicates. fatalities_all keeps duplicates in, because
    # that is what THE WIRE's year-to-date counter (lib/queries-wire.ts) sums.
    conn.execute("DELETE FROM yearly_stats")
    conn.execute("""
        INSERT INTO yearly_stats (year, events, fatalities, fatalities_all, updated_at)
        SELECT CAST(substr(date, 1, 4) AS INTEGER) AS year,
               SUM(CASE WHEN dup_of IS NULL THEN 1 ELSE 0 END),
               COALESCE(SUM(CASE WHEN dup_of IS NULL THEN fatalities END), 0),
               COALESCE(SUM(fatalities), 0),
               ?
          FROM events
         WHERE is_aggregate = 0 AND date >= '1970'
         GROUP BY year
    """, (now,))

    # THE WIRE globe: the 500 deadliest geolocated events of the last two years.
    conn.execute("DELETE FROM wire_hotspots")
    conn.execute("""
        INSERT INTO wire_hotspots (rank, lat, lng, fatalities, category, country, updated_at)
        SELECT ROW_NUMBER() OVER (ORDER BY fatalities DESC, date DESC),
               latitude, longitude, fatalities, category, country, ?
          FROM events
         WHERE is_aggregate = 0 AND dup_of IS NULL
           AND latitude IS NOT NULL AND latitude != 0
           AND longitude IS NOT NULL AND longitude != 0
           AND date >= date('now', '-730 days')
         ORDER BY fatalities DESC, date DESC
         LIMIT 500
    """, (now,))

    # Country → ISO code for the threat choropleth (lib/queries.ts), which used
    # to derive it by grouping the whole events table on every request.
    conn.execute("DELETE FROM country_codes")
    conn.execute("""
        INSERT INTO country_codes (country, country_code)
        SELECT country, country_code
          FROM events
         WHERE country_code IS NOT NULL AND country_code != ''
         GROUP BY country
    """)
    # Per-source rollup for the /events source filter (lib/queries-events.ts) and
    # /api/status freshness (app/api/status/route.ts). Both used to aggregate the
    # events table live: SELECT DISTINCT read ~600K rows per render, and the
    # status GROUP BY ~1.2M rows per call — a public endpoint where a few calls a
    # day would spend D1's whole read quota. The status columns mirror its old
    # query (discrete rows only, is_aggregate = 0).
    _ensure_columns(conn, "event_sources", [
        ("total_events", "INTEGER"),
        ("latest_event", "TEXT"),
        ("last_collected", "TEXT"),
    ])
    conn.execute("DELETE FROM event_sources")
    conn.execute("""
        INSERT INTO event_sources (source, events, total_events, latest_event, last_collected)
        SELECT source, COUNT(*),
               SUM(CASE WHEN is_aggregate = 0 THEN 1 ELSE 0 END),
               MAX(CASE WHEN is_aggregate = 0 THEN date END),
               MAX(CASE WHEN is_aggregate = 0 THEN collected_at END)
          FROM events
         WHERE source IS NOT NULL AND source != ''
         GROUP BY source
    """)
    y, w, cc, es = (conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in ("yearly_stats", "wire_hotspots", "country_codes", "event_sources"))
    log.info(f"  yearly_stats: {y}, wire_hotspots: {w}, country_codes: {cc}, event_sources: {es}")

    conn.commit()
    conn.close()

    log.info("Stats computed successfully.")


if __name__ == "__main__":
    compute()
