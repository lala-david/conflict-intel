"""
일회성 DB 정리 스크립트 — 잘못된 데이터 보정

1. NCTC country_code 채움 (한→ISO2)
2. NULL country 이벤트 백필 (notes/actor 텍스트 → ISO 추정)
3. 중복 source_url 제거 (가장 오래된 것 유지)
4. 기존 wiki/rss/news 이벤트에 enrichment 채움 (mapper)
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from database import get_conn
from mapper import ConflictMapper
from event_linker import extract_countries_from_text
from nctc_source import _KO_TO_EN, _KO_TO_ISO


def fix_nctc_country_code(conn, mapper):
    """NCTC 이벤트의 country_code 채우기."""
    rows = conn.execute(
        "SELECT id, country FROM events WHERE source='nctc' AND (country_code IS NULL OR country_code='')"
    ).fetchall()
    fixed = 0
    for eid, country in rows:
        if not country:
            continue
        cd = mapper.match_country(country)
        iso = cd.get("iso") if cd else ""
        # 국가명을 ISO로 못 찾으면 한국어 매핑 시도
        if not iso:
            for ko, en in _KO_TO_EN.items():
                if en == country:
                    iso = _KO_TO_ISO.get(ko, "")
                    break
        if iso:
            conn.execute("UPDATE events SET country_code=? WHERE id=?", (iso, eid))
            fixed += 1
    print(f"  NCTC country_code filled: {fixed}/{len(rows)}")


def backfill_null_country(conn):
    """country=NULL 이벤트에 텍스트 기반 국가 추정."""
    rows = conn.execute(
        "SELECT id, source, actor1, actor2, notes, source_url FROM events WHERE country IS NULL OR country=''"
    ).fetchall()
    fixed = 0
    skipped = 0
    for eid, src, a1, a2, notes, url in rows:
        text = " ".join(filter(None, [a1, a2, notes, url])).strip()
        if not text:
            skipped += 1
            continue
        codes = extract_countries_from_text(text)
        if codes:
            iso = codes[0]
            conn.execute(
                "UPDATE events SET country=?, country_code=? WHERE id=?",
                (iso, iso, eid),
            )
            fixed += 1
        else:
            skipped += 1
    print(f"  NULL country backfilled: {fixed} (unmatched: {skipped})")


def dedupe_source_urls(conn):
    """중복 source_url 제거 — 가장 오래된 row(=가장 작은 created_at) 1개만 유지."""
    dups = conn.execute("""
        SELECT source_url, COUNT(*) c
        FROM events
        WHERE source_url IS NOT NULL AND source_url != ''
        GROUP BY source_url
        HAVING c > 1
    """).fetchall()
    removed = 0
    for url, _ in dups:
        ids = [r[0] for r in conn.execute(
            "SELECT id FROM events WHERE source_url=? ORDER BY created_at ASC, id ASC",
            (url,)
        ).fetchall()]
        for eid in ids[1:]:
            conn.execute("DELETE FROM events WHERE id=?", (eid,))
            removed += 1
    print(f"  duplicate source_urls cleaned: {removed} rows removed across {len(dups)} URLs")


def enrich_existing(conn, mapper):
    """기존 wiki/expert_rss/google_news/ofac 이벤트에 enrichment 채움."""
    sources = ("wikipedia", "expert_rss", "google_news", "ofac")
    placeholders = ",".join("?" * len(sources))
    rows = conn.execute(
        f"SELECT id, source, actor1, actor2, country, country_code, location, "
        f"latitude, longitude, event_type, sub_event_type, notes "
        f"FROM events WHERE source IN ({placeholders}) "
        f"AND (enrichment IS NULL OR enrichment='' OR enrichment='{{}}')",
        sources,
    ).fetchall()
    enriched_count = 0
    for r in rows:
        eid = r[0]
        ev = {
            "actor1": r[2], "actor2": r[3],
            "country": r[4], "country_code": r[5],
            "location": r[6],
            "latitude": r[7], "longitude": r[8],
            "event_type": r[9], "sub_event_type": r[10],
        }
        e = mapper.enrich_event(ev)
        en = e.get("_enrichment", {})
        if en:
            conn.execute(
                "UPDATE events SET enrichment=? WHERE id=?",
                (json.dumps(en, ensure_ascii=False), eid),
            )
            enriched_count += 1
    print(f"  existing rows enriched: {enriched_count}/{len(rows)}")


def main():
    mapper = ConflictMapper()
    conn = get_conn()
    try:
        print("[1/4] NCTC country_code")
        fix_nctc_country_code(conn, mapper)

        print("[2/4] NULL country backfill")
        backfill_null_country(conn)

        print("[3/4] dedupe source_url")
        dedupe_source_urls(conn)

        print("[4/4] enrich wiki/rss/news/ofac")
        enrich_existing(conn, mapper)

        conn.commit()
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
