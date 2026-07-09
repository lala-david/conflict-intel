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

from database import get_conn
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

    conn.commit()
    conn.close()

    log.info("Stats computed successfully.")


if __name__ == "__main__":
    compute()
