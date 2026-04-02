"""
SQLite 데이터베이스 — 수집 데이터 누적 저장
- events: GDELT + ACLED 이벤트
- sanctions: 제재 엔티티 변동
- daily_stats: 일일 통계
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "terror.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """테이블 생성"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                date TEXT,
                event_type TEXT,
                sub_event_type TEXT,
                actor1 TEXT,
                actor2 TEXT,
                country TEXT,
                country_code TEXT,
                location TEXT,
                latitude REAL,
                longitude REAL,
                fatalities INTEGER DEFAULT 0,
                notes TEXT,
                source_url TEXT,
                enrichment TEXT,
                collected_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sanctions (
                entity_id TEXT,
                name TEXT,
                schema_type TEXT,
                dataset TEXT,
                topics TEXT,
                is_new INTEGER DEFAULT 0,
                collected_date TEXT,
                PRIMARY KEY (entity_id, collected_date)
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                gdelt_count INTEGER DEFAULT 0,
                acled_count INTEGER DEFAULT 0,
                news_count INTEGER DEFAULT 0,
                expert_count INTEGER DEFAULT 0,
                sanctions_count INTEGER DEFAULT 0,
                sanctions_new INTEGER DEFAULT 0,
                total_fatalities INTEGER DEFAULT 0,
                org_matches INTEGER DEFAULT 0,
                country_matches INTEGER DEFAULT 0,
                zone_matches INTEGER DEFAULT 0,
                top_countries TEXT,
                top_actors TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
            CREATE INDEX IF NOT EXISTS idx_events_country ON events(country);
            CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
            CREATE INDEX IF NOT EXISTS idx_sanctions_date ON sanctions(collected_date);
        """)
        conn.commit()
    finally:
        conn.close()


def save_events(data: dict, date_str: str):
    """수집된 이벤트를 DB에 저장"""
    conn = get_conn()
    try:
        now = datetime.now().isoformat()

        # GDELT 이벤트
        for e in data.get("gdelt", []):
            event_id = f"gdelt-{e.get('date', '')}-{e.get('event_code', '')}-{e.get('source_url', '')[:50]}"
            enrichment = json.dumps(e.get("_enrichment", {}), ensure_ascii=False)
            # D4: Use country field if present, fall back to country_code
            country_val = e.get("country", "") or e.get("country_code", "")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events (id, source, date, event_type, sub_event_type, actor1, actor2, country, country_code, location, latitude, longitude, fatalities, source_url, enrichment, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id, "gdelt", e.get("date", ""), e.get("event_code", ""), "",
                     e.get("actor1", ""), e.get("actor2", ""),
                     country_val, e.get("country_code", ""),
                     e.get("location", ""),
                     float(e["latitude"]) if e.get("latitude") else None,
                     float(e["longitude"]) if e.get("longitude") else None,
                     0,  # D5: GDELT does not provide fatality counts; default to 0
                     e.get("source_url", ""), enrichment, now),
                )
            except Exception as e:
                print(f"   WARN: skipped event: {e}")
                continue

        # ACLED 이벤트
        for e in data.get("acled", []):
            event_id = e.get("event_id", f"acled-{e.get('date', '')}-{e.get('location', '')}")
            enrichment = json.dumps(e.get("_enrichment", {}), ensure_ascii=False)
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events (id, source, date, event_type, sub_event_type, actor1, actor2, country, location, latitude, longitude, fatalities, notes, enrichment, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id, "acled", e.get("date", ""), e.get("event_type", ""),
                     e.get("sub_event_type", ""), e.get("actor1", ""), e.get("actor2", ""),
                     e.get("country", ""), e.get("location", ""),
                     float(e["latitude"]) if e.get("latitude") else None,
                     float(e["longitude"]) if e.get("longitude") else None,
                     e.get("fatalities", 0), e.get("notes", ""), enrichment, now),
                )
            except Exception as e:
                print(f"   WARN: skipped event: {e}")
                continue

        # 제재
        for s in data.get("sanctions", []):
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO sanctions (entity_id, name, schema_type, dataset, topics, is_new, collected_date) VALUES (?,?,?,?,?,?,?)",
                    (s.get("entity_id", ""), s.get("name", ""), s.get("schema", ""),
                     s.get("datasets", ""), json.dumps(s.get("topics", [])),
                     1 if s.get("is_new") else 0, date_str),
                )
            except Exception as e:
                print(f"   WARN: skipped event: {e}")
                continue

        conn.commit()
    finally:
        conn.close()


def save_daily_stats(date_str: str, data: dict, enrichment_stats: dict):
    """일일 통계 저장"""
    conn = get_conn()

    # 국가별, 조직별 집계
    country_counts = {}
    actor_counts = {}
    total_fat = 0

    for source_key in ["acled", "gdelt"]:
        for e in data.get(source_key, []):
            c = e.get("country", "") or e.get("country_code", "")
            if c:
                country_counts[c] = country_counts.get(c, 0) + 1
            a = e.get("actor1", "")
            if a:
                actor_counts[a] = actor_counts.get(a, 0) + 1
            total_fat += e.get("fatalities", 0)

    top_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    sanctions_new = sum(1 for s in data.get("sanctions", []) if s.get("is_new"))

    try:
        conn.execute(
            """INSERT INTO daily_stats (date, gdelt_count, acled_count, news_count, expert_count,
               sanctions_count, sanctions_new, total_fatalities, org_matches,
               country_matches, zone_matches, top_countries, top_actors)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
                 gdelt_count=excluded.gdelt_count,
                 acled_count=excluded.acled_count,
                 news_count=excluded.news_count,
                 expert_count=excluded.expert_count,
                 sanctions_count=excluded.sanctions_count,
                 sanctions_new=excluded.sanctions_new,
                 total_fatalities=excluded.total_fatalities,
                 org_matches=excluded.org_matches,
                 country_matches=excluded.country_matches,
                 zone_matches=excluded.zone_matches,
                 top_countries=excluded.top_countries,
                 top_actors=excluded.top_actors""",
            (date_str,
             len(data.get("gdelt", [])),
             len(data.get("acled", [])),
             len(data.get("google_news", [])),
             len(data.get("expert_rss", [])),
             len(data.get("sanctions", [])),
             sanctions_new,
             total_fat,
             enrichment_stats.get("org_matches", 0),
             enrichment_stats.get("country_matches", 0),
             enrichment_stats.get("zone_matches", 0),
             json.dumps(top_countries, ensure_ascii=False),
             json.dumps(top_actors, ensure_ascii=False)),
        )
        conn.commit()
    except Exception as e:
        print(f"  [db] stats 저장 실패: {e}")
    finally:
        conn.close()


def get_weekly_trend(date_str: str) -> dict:
    """최근 7일 통계 트렌드"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT date, gdelt_count, acled_count, total_fatalities, sanctions_new FROM daily_stats ORDER BY date DESC LIMIT 7"
        ).fetchall()
        return {
            "days": [{"date": r[0], "gdelt": r[1], "acled": r[2], "fatalities": r[3], "new_sanctions": r[4]} for r in rows]
        }
    except Exception:
        return {"days": []}
    finally:
        conn.close()


# 모듈 로드 시 DB 초기화
try:
    init_db()
except Exception as e:
    print(f"  [db] init_db failed (will retry on first use): {e}")
