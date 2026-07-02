"""
Pre-computed stats — 매일 CI에서 pipeline/run.py (report_builder.py 제공 함수 사용) 후 실행.
420K rows 실시간 scan 대신 집계 테이블 1-row lookup으로 대시보드 100x 빠르게.
"""
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from database import get_conn
from logger import log


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
        FROM events WHERE is_aggregate = 0
    """).fetchone()

    countries = conn.execute("""
        SELECT COUNT(*) FROM (SELECT DISTINCT country FROM events WHERE country != '' LIMIT 300)
    """).fetchone()[0]

    w7 = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND date >= date('now', '-7 days')
    """).fetchone()

    w30 = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND date >= date('now', '-30 days')
    """).fetchone()

    w90 = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(fatalities), 0)
        FROM events WHERE is_aggregate = 0 AND date >= date('now', '-90 days')
    """).fetchone()

    # Threat index: weighted score from 7d, 30d, 90d fatalities (sigmoid-like)
    # 7d has highest weight (recent), 90d anchors baseline
    import math
    raw = (w7[1] * 0.5 + w30[1] * 0.1 + w90[1] * 0.02) if w7[1] else 0
    threat_idx = min(100, max(0, int(100 * (1 - math.exp(-raw / 500)))))

    conn.execute("DELETE FROM global_stats")
    conn.execute("""
        INSERT INTO global_stats (id, total_events, total_fatalities, total_countries,
            events_7d, fatalities_7d, events_30d, fatalities_30d,
            events_90d, fatalities_90d, threat_index, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (g[0], g[1], countries, w7[0], w7[1], w30[0], w30[1], w90[0], w90[1], threat_idx, now))

    log.info(f"  global: {g[0]:,} events, threat={threat_idx}")

    # ─── Country stats ───
    log.info("Computing country stats...")
    conn.execute("DELETE FROM country_stats")
    conn.execute("""
        INSERT INTO country_stats (country, total_events, total_fatalities,
            events_30d, fatalities_30d, events_90d, fatalities_90d,
            top_category, threat_score, last_event_date, updated_at)
        SELECT
            e.country,
            COUNT(*),
            COALESCE(SUM(e.fatalities), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-30 days') THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-30 days') THEN e.fatalities ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-90 days') THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN e.date >= date('now', '-90 days') THEN e.fatalities ELSE 0 END), 0),
            COALESCE((
                SELECT category FROM events e2
                WHERE e2.country = e.country AND e2.is_aggregate = 0 AND e2.category IS NOT NULL
                GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1
            ), ''),
            MIN(100, COALESCE(SUM(CASE WHEN e.date >= date('now', '-90 days') THEN e.fatalities ELSE 0 END), 0) * 0.1),
            MAX(e.date),
            ?
        FROM events e
        WHERE e.is_aggregate = 0 AND e.country != ''
        GROUP BY e.country
    """, (now,))

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
        WHERE is_aggregate = 0 AND actor1 != ''
            AND actor1 NOT LIKE 'Government of%'
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
        FROM events WHERE is_aggregate = 0 AND category IS NOT NULL
        GROUP BY category
    """, (now,))

    conn.commit()
    conn.close()

    log.info("Stats computed successfully.")


if __name__ == "__main__":
    compute()
