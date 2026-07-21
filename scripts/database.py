"""
SQLite 데이터베이스 — 수집 데이터 누적 저장
- events: GDELT + ACLED 이벤트
- sanctions: 제재 엔티티 변동
- daily_stats: 일일 통계
"""
import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path

from country_canonical import canonical_country

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "conflict.db"


# ── 국가명 정규화 ─────────────────────────────
# GDELT/뉴스가 ISO-2 코드(예: "IL", "NG")를 country로 넣으면 정식명("Israel")과
# 분리 집계되어 국가 수가 부풀려진다. 저장 시점에 항상 정식명으로 변환한다.
def _load_iso2name() -> dict:
    m = {}
    try:
        cj = json.loads((ROOT / "data" / "countries.json").read_text(encoding="utf-8"))
        for rd in cj.get("regions", {}).values():
            for co in rd.get("countries", []):
                iso = (co.get("iso_alpha2", "") or "").upper()
                name = co.get("name", "")
                if iso and name:
                    m[iso] = name
    except Exception:
        pass
    # 누락 보강 + 모던 정식명으로 통일 (Natural Earth 지도 라벨과 일치시켜 분리·미표시 방지)
    m.update({
        "CN": "China", "JP": "Japan", "MH": "Marshall Islands", "VA": "Vatican",
        "RU": "Russia", "US": "United States of America",
        "MM": "Myanmar", "EE": "Estonia", "LV": "Latvia",
        "IT": "Italy", "NZ": "New Zealand", "OM": "Oman",
    })
    return m


_ISO2NAME = _load_iso2name()


def _canon_country(val: str) -> str:
    """country 값을 모던 정식명으로 정규화.

    2글자 ISO 코드는 정식명으로 펼치고, 역사적/변형 국가명("Russia (Soviet Union)"
    등)은 canonical_country로 모던명에 접는다. 지도(topojson)·통계·라우팅이 같은
    이름을 쓰도록 하는 단일 진입점.
    """
    v = (val or "").strip()
    if len(v) == 2 and v.isupper() and v.isalpha():
        v = _ISO2NAME.get(v, v)
    return canonical_country(v) or ""


def _normalize_date(raw: str) -> str:
    """다양한 날짜 포맷을 YYYY-MM-DD로 정규화. 실패 시 오늘 날짜."""
    if not raw:
        return datetime.now().strftime("%Y-%m-%d")
    s = raw.strip()
    # 이미 ISO 형식
    m = re.match(r'(\d{4}-\d{2}-\d{2})', s)
    if m:
        return m.group(1)
    # RSS: "Sun, 26 Apr 2026 12:34:56 +0000"
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return datetime.now().strftime("%Y-%m-%d")


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

            CREATE TABLE IF NOT EXISTS crypto_addresses (
                address TEXT PRIMARY KEY,
                chain TEXT,
                entity_name TEXT,
                category TEXT,
                topics TEXT,
                is_terror INTEGER DEFAULT 0,
                org TEXT,
                source TEXT,
                collected_date TEXT
            );

            CREATE TABLE IF NOT EXISTS crypto_stats (
                scope TEXT,
                key TEXT,
                n INTEGER DEFAULT 0,
                chains INTEGER DEFAULT 0,
                PRIMARY KEY (scope, key)
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                gdelt_count INTEGER DEFAULT 0,
                ucdp_count INTEGER DEFAULT 0,
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
            CREATE INDEX IF NOT EXISTS idx_events_actor1 ON events(actor1);
            CREATE INDEX IF NOT EXISTS idx_events_source_url ON events(source_url);
            -- composite indexes: speed up per-country / per-actor GROUP BY aggregations
            CREATE INDEX IF NOT EXISTS idx_ev_country_date ON events(country, date);
            CREATE INDEX IF NOT EXISTS idx_ev_country_actor ON events(country, actor1);
            CREATE INDEX IF NOT EXISTS idx_ev_actor_date ON events(actor1, date);
            CREATE INDEX IF NOT EXISTS idx_sanctions_date ON sanctions(collected_date);
            CREATE INDEX IF NOT EXISTS idx_crypto_entity ON crypto_addresses(entity_name);
            CREATE INDEX IF NOT EXISTS idx_crypto_org ON crypto_addresses(org);
            CREATE INDEX IF NOT EXISTS idx_crypto_terror ON crypto_addresses(is_terror);
            CREATE INDEX IF NOT EXISTS idx_crypto_category ON crypto_addresses(category);
        """)

        # Additive column migrations (idempotent).
        # These are needed by compute_stats.py and the web dashboard but were
        # dropped from the initial schema during an earlier simplification.
        _ensure_columns(conn, "events", [
            ("admin1", "TEXT"),
            ("deaths_a", "INTEGER"),
            ("deaths_b", "INTEGER"),
            ("deaths_civilians", "INTEGER"),
            ("fatalities_low", "INTEGER"),
            ("fatalities_high", "INTEGER"),
            ("conflict_name", "TEXT"),
            ("category", "TEXT"),
            ("category_confidence", "TEXT"),
            ("is_aggregate", "INTEGER DEFAULT 0"),
            ("dup_of", "TEXT"),
        ])

        # is_aggregate 컬럼이 보장된 뒤에 인덱스 생성 (fresh DB에서 컬럼보다
        # 먼저 만들면 'no such column: is_aggregate'로 init이 깨짐).
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events(is_aggregate)")
        # category is also added via _ensure_columns, so its index must come after too.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)")

        conn.commit()
    finally:
        conn.close()


def _ensure_columns(conn, table: str, columns: list[tuple[str, str]]):
    """Add columns via ALTER TABLE if missing. Idempotent."""
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, sql_type in columns:
        if name not in existing:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
            except Exception as e:
                print(f"  [db] failed to add column {table}.{name}: {e}")


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
            country_val = _canon_country(e.get("country", "") or e.get("country_code", ""))
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

        # UCDP 이벤트
        for e in data.get("ucdp", []):
            event_id = e.get("event_id", f"ucdp-{e.get('date', '')}-{e.get('location', '')}")
            enrichment = json.dumps(e.get("_enrichment", {}), ensure_ascii=False)
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events (id, source, date, event_type, sub_event_type, actor1, actor2, country, location, latitude, longitude, fatalities, notes, enrichment, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id, "ucdp", e.get("date", ""), e.get("event_type", ""),
                     e.get("sub_event_type", ""), e.get("actor1", ""), e.get("actor2", ""),
                     _canon_country(e.get("country", "")), e.get("location", ""),
                     float(e["latitude"]) if e.get("latitude") else None,
                     float(e["longitude"]) if e.get("longitude") else None,
                     e.get("fatalities", 0), e.get("notes", ""), enrichment, now),
                )
            except Exception as e:
                print(f"   WARN: skipped event: {e}")
                continue

        # NCTC 사건 — source='nctc' → 항상 terrorism 분류
        for e in data.get("nctc", []):
            nctc_id = f"nctc-{e.get('date', '')}-{e.get('country', '')[:20]}-{e.get('fatalities', 0)}"
            desc = e.get("description", "") or e.get("description_ko", "")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events (id, source, date, country, country_code, actor1, fatalities, notes, category, category_confidence, is_aggregate, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (nctc_id, "nctc", e.get("date", ""), _canon_country(e.get("country", "")),
                     e.get("country_code", ""),
                     desc[:80],
                     int(e.get("fatalities", 0) or 0),
                     desc[:500],
                     "terrorism", "high", 0, now),
                )
            except Exception as exc:
                print(f"   WARN: skipped nctc event {nctc_id}: {exc}")
                continue

        # Wikipedia 사건
        for e in data.get("wikipedia", []):
            wiki_id = e.get("event_id") or f"wiki-{e.get('date','')}-{(e.get('location','') or '')[:30]}"
            enrichment = json.dumps(e.get("_enrichment", {}), ensure_ascii=False)
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events (id, source, date, event_type, actor1, country, country_code, location, fatalities, notes, source_url, enrichment, category, category_confidence, is_aggregate, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (wiki_id, "wikipedia", e.get("date", ""), e.get("event_type", ""),
                     e.get("actor1", ""), _canon_country(e.get("country", "")), e.get("country_code", ""),
                     (e.get("location", "") or "")[:100],
                     int(e.get("fatalities", 0) or 0),
                     (e.get("notes", "") or "")[:500],
                     e.get("url", ""), enrichment,
                     "terrorism", "medium", 0, now),
                )
            except Exception as exc:
                print(f"   WARN: skipped wikipedia event {wiki_id}: {exc}")
                continue

        # Expert RSS / Google News — 텍스트 기반, casualty_extractor가 fatalities_estimated 채움
        # NOTE: 피드명은 sub_event_type에 저장 (web의 getTodayAnalysis가 이 필드 참조).
        for source_key in ("expert_rss", "google_news", "telegram"):
            for e in data.get(source_key, []):
                title = e.get("title", "") or ""
                url = e.get("url", "") or ""
                ev_date = _normalize_date(e.get("date", ""))
                news_country = _canon_country(e.get("country", ""))
                # D-clean: 국가 미상 + 사망자 0 인 비분쟁 뉴스는 DB 노이즈로 저장 제외
                # (NASA·동문·항모추적 등 Tier-1 피드 비분쟁 기사가 country=NULL로 적재되던 문제 방지)
                if not news_country and not int(e.get("fatalities_estimated", 0) or 0):
                    continue
                # ID에는 title 사용 (URL은 utm 등으로 동일 기사가 다른 URL을 갖는 케이스 회피)
                event_id = f"{source_key}-{ev_date}-{title[:80]}" if title else f"{source_key}-{ev_date}-{url[:80]}"
                enrichment = json.dumps(e.get("_enrichment", {}), ensure_ascii=False)
                feed_name = (e.get("feed_name") or "")[:60]
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO events (id, source, date, sub_event_type, country, country_code, location, fatalities, notes, source_url, enrichment, category, category_confidence, is_aggregate, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (event_id, source_key, ev_date,
                         feed_name,
                         news_country, e.get("country_code", ""),
                         "",
                         int(e.get("fatalities_estimated", 0) or 0),
                         (title + " | " + (e.get("summary", "") or ""))[:500],
                         url, enrichment,
                         "terrorism" if e.get("fatalities_estimated", 0) else None,
                         e.get("casualty_confidence", "").lower() if e.get("fatalities_estimated", 0) else None,
                         0, now),
                    )
                except Exception as exc:
                    print(f"   WARN: skipped {source_key} event {event_id}: {exc}")
                    continue

        # OFAC 조치
        for e in data.get("ofac", []):
            title = e.get("title", "") or ""
            url = e.get("url", "") or ""
            ofac_id = f"ofac-{url[:120]}" if url else f"ofac-{title[:80]}"
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events (id, source, date, actor1, country, fatalities, notes, source_url, category, category_confidence, is_aggregate, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ofac_id, "ofac",
                     datetime.now().strftime("%Y-%m-%d"),
                     "OFAC",
                     "United States of America",
                     0,
                     title[:500],
                     url,
                     "counterterrorism", "high", 0, now),
                )
            except Exception as exc:
                print(f"   WARN: skipped ofac event {ofac_id}: {exc}")
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

    for source_key in ["ucdp", "gdelt"]:
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

    # wiki_count 컬럼 확보 (idempotent)
    _ensure_columns(conn, "daily_stats", [("wiki_count", "INTEGER DEFAULT 0")])

    try:
        conn.execute(
            """INSERT INTO daily_stats (date, gdelt_count, ucdp_count, news_count, expert_count,
               sanctions_count, sanctions_new, total_fatalities, org_matches,
               country_matches, zone_matches, top_countries, top_actors, wiki_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
                 gdelt_count=excluded.gdelt_count,
                 ucdp_count=excluded.ucdp_count,
                 news_count=excluded.news_count,
                 expert_count=excluded.expert_count,
                 sanctions_count=excluded.sanctions_count,
                 sanctions_new=excluded.sanctions_new,
                 total_fatalities=excluded.total_fatalities,
                 org_matches=excluded.org_matches,
                 country_matches=excluded.country_matches,
                 zone_matches=excluded.zone_matches,
                 top_countries=excluded.top_countries,
                 top_actors=excluded.top_actors,
                 wiki_count=excluded.wiki_count""",
            (date_str,
             len(data.get("gdelt", [])),
             len(data.get("ucdp", [])),
             len(data.get("google_news", [])),
             len(data.get("expert_rss", [])),
             len(data.get("sanctions", [])),
             sanctions_new,
             total_fat,
             enrichment_stats.get("org_matches", 0),
             enrichment_stats.get("country_matches", 0),
             enrichment_stats.get("zone_matches", 0),
             json.dumps(top_countries, ensure_ascii=False),
             json.dumps(top_actors, ensure_ascii=False),
             len(data.get("wikipedia", []))),
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
            "SELECT date, gdelt_count, ucdp_count, total_fatalities, sanctions_new FROM daily_stats ORDER BY date DESC LIMIT 7"
        ).fetchall()
        return {
            "days": [{"date": r[0], "gdelt": r[1], "ucdp": r[2], "fatalities": r[3], "new_sanctions": r[4]} for r in rows]
        }
    except Exception:
        return {"days": []}
    finally:
        conn.close()


KNOWN_UCDP_IDS_FILE = Path(__file__).resolve().parent.parent / "data" / "known_ucdp_ids.json"


def get_known_ucdp_ids() -> set:
    """committed JSON + DB union. JSON이 CI 실행 간 영속 상태를 담당."""
    ids: set[str] = set()
    try:
        if KNOWN_UCDP_IDS_FILE.exists():
            ids.update(str(x) for x in json.loads(KNOWN_UCDP_IDS_FILE.read_text(encoding="utf-8")))
    except Exception as e:
        print(f"  [db] known_ucdp_ids.json load failed: {e}")
    conn = get_conn()
    try:
        rows = conn.execute("SELECT id FROM events WHERE source='ucdp'").fetchall()
        ids.update(str(r[0]) for r in rows)
    except Exception:
        pass
    finally:
        conn.close()
    return ids


def save_known_ucdp_ids(fetched_ids) -> int:
    """이번 수집에서 본 UCDP ID를 영속 JSON에 union 저장. 반환: 파일의 총 ID 수."""
    existing = get_known_ucdp_ids()
    merged = existing | {str(x) for x in fetched_ids if x}
    KNOWN_UCDP_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KNOWN_UCDP_IDS_FILE.write_text(
        json.dumps(sorted(merged), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(merged)


def cleanup_db():
    """Clean legacy data + migrate schema.

    Safe to call repeatedly: uses IF NOT EXISTS, bounded UPDATE/DELETE targets.
    All mutations are scoped to GDELT noise + old date formats only.
    Does NOT drop columns or tables.
    """
    conn = get_conn()
    try:
        # --- 마이그레이션: acled_count → ucdp_count ---
        cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_stats)").fetchall()]
        if "acled_count" in cols and "ucdp_count" not in cols:
            print("  [db] migrating daily_stats: acled_count → ucdp_count")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS daily_stats_new (
                    date TEXT PRIMARY KEY,
                    gdelt_count INTEGER DEFAULT 0,
                    ucdp_count INTEGER DEFAULT 0,
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
                INSERT OR IGNORE INTO daily_stats_new
                    SELECT date, gdelt_count, acled_count, news_count, expert_count,
                           sanctions_count, sanctions_new, total_fatalities,
                           org_matches, country_matches, zone_matches,
                           top_countries, top_actors, created_at
                    FROM daily_stats;
                DROP TABLE daily_stats;
                ALTER TABLE daily_stats_new RENAME TO daily_stats;
            """)
            print("  [db] migration complete")

        # --- 구형식 날짜 변환 (YYYYMMDD -> YYYY-MM-DD) ---
        fixed_dates = conn.execute("""
            UPDATE events
            SET date = substr(date,1,4) || '-' || substr(date,5,2) || '-' || substr(date,7,2)
            WHERE source='gdelt' AND length(date)=8 AND date NOT LIKE '____-__-__'
        """).rowcount
        if fixed_dates:
            print(f"  [db] fixed {fixed_dates} old date formats")

        # --- 노이즈 GDELT 이벤트 삭제 ---
        noise_actors = ('POLICE', 'DOCTOR', 'FIREFIGHTER', 'SUPREME COURT', 'JUDGE',
                       'BATTALION', 'MALE', 'FEMALE', 'ACTOR', 'PROSECUTOR', 'HOSPITAL',
                       'WORKER', 'ABU DHABI', 'TELEVISION', 'NEWSPAPER', 'PRINCE',
                       'VICTORIA', 'AUTHORITIES', 'CAMBODIA')
        placeholders = ','.join('?' * len(noise_actors))
        deleted = conn.execute(
            f"DELETE FROM events WHERE source='gdelt' AND (actor1 IN ({placeholders}) OR actor2 IN ({placeholders}))",
            noise_actors + noise_actors
        ).rowcount
        if deleted:
            print(f"  [db] cleaned {deleted} noise GDELT events")

        # --- 빈 country 채우기 ---
        updated = conn.execute(
            "UPDATE events SET country = country_code WHERE source='gdelt' AND (country IS NULL OR country = '') AND country_code != ''"
        ).rowcount
        if updated:
            print(f"  [db] filled {updated} empty GDELT country fields")

        conn.commit()
    except Exception as e:
        print(f"  [db] cleanup failed: {e}")
    finally:
        conn.close()


# Module-level auto-init removed — was running on every import
# (including read-only scripts), which caused spurious cleanup passes.
# Callers should invoke init_db() and cleanup_db() explicitly when needed.
#
# pipeline/run.py (report_builder.py 제공 함수 사용): explicitly calls init_db() + cleanup_db() before collection
# compute_stats.py, read-only tools: skip init; just use get_conn()
