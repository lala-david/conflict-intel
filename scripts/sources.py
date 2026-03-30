"""
Terror Intelligence 데이터 소스 수집 모듈
- GDELT (실시간 이벤트), ACLED (코딩된 사건), OpenSanctions (제재)
- RSS (전문 기관), Google News (뉴스)
"""
import requests
import feedparser
import re
import csv
import io
import time
import json
import zipfile
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from config import (
    ACLED_EMAIL, ACLED_PASSWORD,
    ACLED_TERROR_SUBTYPES, GDELT_TERROR_CODES,
    RSS_FEEDS, GOOGLE_NEWS_QUERIES,
)
from fips_to_iso import fips_to_iso

ROOT = Path(__file__).resolve().parent.parent

# 테러 관련 키워드 (2차 필터링용)
TERROR_KEYWORDS = [
    "terror", "terrorism", "terrorist", "extremis", "militant",
    "bomb", "bombing", "suicide attack", "ied", "explosive",
    "isis", "isil", "islamic state", "al-qaeda", "al qaeda",
    "boko haram", "al-shabaab", "taliban", "hezbollah", "hamas",
    "jihadist", "jihad", "radicali", "extremist",
    "counterterror", "counter-terror", "antiterror",
    "insurgent", "insurgency", "guerrilla",
    "hostage", "kidnap", "assassination", "ambush",
    "lone wolf", "mass shooting", "mass casualty",
    "chemical attack", "bioterror", "cyberterror",
    "right-wing extrem", "far-right", "neo-nazi", "white supremac",
    "left-wing extrem", "anarchist",
    "separatist", "liberation front",
    "sanctions", "designated", "ofac", "blacklist",
    "threat level", "security alert", "travel warning",
]


def _is_terror_relevant(text: str) -> bool:
    text_lower = text.lower()
    return sum(1 for k in TERROR_KEYWORDS if k in text_lower) >= 1


def _similar(a: str, b: str) -> float:
    """두 문자열 유사도 (0~1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ─────────────────────────────────────────────
# 1. GDELT — 글로벌 이벤트 (#1 좌표 수정, #2 3일 폴백)
# ─────────────────────────────────────────────
def fetch_gdelt(target_date: datetime, limit: int = 50) -> list[dict]:
    """GDELT에서 테러 관련 이벤트 수집 (3일 폴백)"""

    # #2: 3일 전까지 역순 시도
    for days_back in range(0, 4):
        check_date = target_date - timedelta(days=days_back)
        date_str = check_date.strftime("%Y%m%d")
        url = f"http://data.gdeltproject.org/events/{date_str}.export.CSV.zip"

        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 1000:
                print(f"    GDELT: using {date_str} ({days_back}d ago)")
                break
        except Exception:
            continue
    else:
        print("    GDELT: no data found (0~3 days)")
        return []

    try:
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        csv_name = z.namelist()[0]
        csv_data = z.read(csv_name).decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(csv_data), delimiter="\t")

        events = []
        for row in reader:
            if len(row) < 58:
                continue

            event_code = row[26]  # CAMEO EventCode
            if not any(event_code.startswith(c) for c in GDELT_TERROR_CODES):
                continue

            goldstein = float(row[30]) if row[30] else 0
            num_mentions = int(row[31]) if row[31] else 0
            num_sources = int(row[32]) if row[32] else 0
            num_articles = int(row[33]) if row[33] else 0
            avg_tone = float(row[34]) if row[34] else 0

            actor1 = row[6] if row[6] else ""
            actor2 = row[16] if row[16] else ""

            # #1: 좌표 매핑 수정 — ActionGeo 우선, 없으면 Actor1Geo
            action_lat = row[39] if row[39] else ""
            action_lon = row[40] if row[40] else ""
            action_country = row[37] if row[37] else ""
            action_location = ""

            # ActionGeo_FullName은 GDELT V1에서 별도 컬럼이 아닐 수 있음
            # ADM1Code에서 추출
            action_adm1 = row[38] if row[38] else ""

            # ActionGeo가 비어있으면 Actor1Geo 사용 (row[42~46])
            if not action_lat and len(row) > 46:
                action_lat = row[46] if row[46] else ""  # Actor1Geo_Lat
                action_lon = row[47] if len(row) > 47 and row[47] else ""  # Actor1Geo_Long
                action_country = row[44] if len(row) > 44 and row[44] else ""  # Actor1Geo_CountryCode

            # 위치명 구성
            if action_adm1:
                action_location = action_adm1
            if action_country:
                action_location = f"{action_location}, {action_country}".strip(", ")

            source_url = row[57] if len(row) > 57 else ""

            # #1: FIPS → ISO 변환
            iso_country = fips_to_iso(action_country) if action_country else ""

            events.append({
                "source": "gdelt",
                "event_code": event_code,
                "actor1": actor1,
                "actor2": actor2,
                "country_code": iso_country,
                "location": action_location,
                "latitude": action_lat,
                "longitude": action_lon,
                "goldstein_scale": goldstein,
                "num_mentions": num_mentions,
                "num_sources": num_sources,
                "num_articles": num_articles,
                "avg_tone": avg_tone,
                "source_url": source_url,
                "date": date_str,
            })

        events.sort(key=lambda x: x["num_mentions"] + x["num_sources"], reverse=True)
        return events[:limit]

    except Exception as e:
        print(f"    [gdelt] 파싱 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 2. ACLED — 코딩된 정치폭력 사건
# ─────────────────────────────────────────────
def _get_acled_token() -> str:
    resp = requests.post(
        "https://acleddata.com/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": ACLED_EMAIL,
            "password": ACLED_PASSWORD,
            "grant_type": "password",
            "client_id": "acled",
        },
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    else:
        print(f"    [acled] OAuth 실패: {resp.status_code}")
        return ""


def fetch_acled(target_date: datetime, limit: int = 100) -> list[dict]:
    if not ACLED_EMAIL or not ACLED_PASSWORD:
        print("    [acled] 인증 정보 없음 — 스킵")
        return []

    token = _get_acled_token()
    if not token:
        return []

    since = (target_date - timedelta(days=14)).strftime("%Y-%m-%d")
    until = target_date.strftime("%Y-%m-%d")
    sub_types = "|".join(ACLED_TERROR_SUBTYPES)

    try:
        resp = requests.get(
            "https://acleddata.com/api/acled/read",
            params={
                "_format": "json",
                "sub_event_type": sub_types,
                "event_date": f"{since}|{until}",
                "event_date_where": "BETWEEN",
                "limit": limit,
                "fields": "event_id_cnty|event_date|event_type|sub_event_type|actor1|actor2|country|admin1|location|latitude|longitude|fatalities|notes|source",
            },
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"    [acled] HTTP {resp.status_code}")
            return []

        data = resp.json()
        events = []
        for item in data.get("data", []):
            events.append({
                "source": "acled",
                "event_id": item.get("event_id_cnty", ""),
                "date": item.get("event_date", ""),
                "event_type": item.get("event_type", ""),
                "sub_event_type": item.get("sub_event_type", ""),
                "actor1": item.get("actor1", ""),
                "actor2": item.get("actor2", ""),
                "country": item.get("country", ""),
                "admin1": item.get("admin1", ""),
                "location": item.get("location", ""),
                "latitude": item.get("latitude", ""),
                "longitude": item.get("longitude", ""),
                "fatalities": int(item.get("fatalities", 0) or 0),
                "notes": (item.get("notes", "") or "")[:500],
                "source_text": item.get("source", ""),
            })

        events.sort(key=lambda x: x["fatalities"], reverse=True)
        return events

    except Exception as e:
        print(f"    [acled] 수집 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 3. OpenSanctions — 제재 목록 (#12 변동 감지)
# ─────────────────────────────────────────────
def _load_previous_sanctions() -> set:
    """이전 수집된 제재 엔티티 ID 로드"""
    cache = ROOT / "data" / ".sanctions_cache.json"
    if cache.exists():
        try:
            return set(json.loads(cache.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_sanctions_cache(entity_ids: list):
    """현재 제재 엔티티 ID 저장"""
    cache = ROOT / "data" / ".sanctions_cache.json"
    cache.write_text(json.dumps(entity_ids, ensure_ascii=False), encoding="utf-8")


def fetch_sanctions_updates(limit: int = 30) -> list[dict]:
    """OpenSanctions에서 제재 목록 변동 수집 (diff 방식)"""
    previous_ids = _load_previous_sanctions()

    try:
        datasets = ["un_sc_sanctions", "us_ofac_sdn", "eu_sanctions"]
        results = []
        current_ids = []

        for ds in datasets:
            resp = requests.get(
                f"https://data.opensanctions.org/datasets/latest/{ds}/entities.ftm.json",
                timeout=30,
                stream=True,
            )
            if resp.status_code != 200:
                continue

            count = 0
            for line in resp.iter_lines():
                if count >= 50:
                    break
                if not line:
                    continue
                try:
                    entity = json.loads(line)
                    props = entity.get("properties", {})
                    name = props.get("name", ["Unknown"])[0] if props.get("name") else "Unknown"
                    entity_id = entity.get("id", "")
                    schema = entity.get("schema", "")
                    topics = props.get("topics", [])

                    if schema in ("Organization", "LegalEntity", "Person"):
                        current_ids.append(entity_id)
                        is_new = entity_id not in previous_ids
                        results.append({
                            "source": f"opensanctions/{ds}",
                            "entity_id": entity_id,
                            "name": name,
                            "schema": schema,
                            "datasets": ds,
                            "topics": topics,
                            "is_new": is_new,  # #12: 변동 감지
                        })
                        count += 1
                except Exception:
                    continue

        # 캐시 업데이트
        _save_sanctions_cache(current_ids)

        # 신규 엔티티 우선 정렬
        results.sort(key=lambda x: (not x["is_new"], x["name"]))
        new_count = sum(1 for r in results if r["is_new"])
        if new_count > 0:
            print(f"    NEW sanctions entities: {new_count}")

        return results[:limit]

    except Exception as e:
        print(f"    [sanctions] 수집 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 4. Google News — 테러 관련 뉴스 (#4 클러스터링)
# ─────────────────────────────────────────────
def fetch_google_news(limit: int = 30) -> list[dict]:
    """Google News RSS — 중복 클러스터링 적용"""
    articles = []
    seen_titles = set()

    for query in GOOGLE_NEWS_QUERIES:
        try:
            url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            for entry in feed.entries[:8]:
                title = entry.title
                if title in seen_titles:
                    continue

                # #4: 제목 유사도 기반 클러스터링 (70% 이상 유사하면 중복)
                is_duplicate = False
                for seen in seen_titles:
                    if _similar(title, seen) > 0.7:
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue

                seen_titles.add(title)

                text = title + " " + entry.get("summary", "")
                if not _is_terror_relevant(text):
                    continue

                articles.append({
                    "source": "google_news",
                    "query": query,
                    "title": title,
                    "url": entry.link,
                    "summary": re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:300],
                    "date": entry.get("published", ""),
                })

            time.sleep(0.5)
        except Exception as e:
            print(f"    [google_news:{query}] 실패: {e}")
            continue

    return articles[:limit]


# ─────────────────────────────────────────────
# 5. RSS — 전문 분석 기관 (#5 48시간 필터)
# ─────────────────────────────────────────────
def _parse_rss_date(date_str: str) -> datetime:
    """RSS 날짜 파싱 시도"""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
    return datetime.min


def fetch_expert_rss(limit: int = 30) -> list[dict]:
    """테러/안보 전문 기관 RSS — 48시간 필터 적용"""
    articles = []
    cutoff = datetime.now() - timedelta(hours=48)
    tier1 = ["Long War Journal", "Soufan Center", "CTC Sentinel", "Jamestown Foundation"]

    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                # #5: 48시간 필터
                pub_date = entry.get("published", "")
                if pub_date:
                    parsed = _parse_rss_date(pub_date)
                    if parsed != datetime.min and parsed < cutoff:
                        continue

                title = entry.title
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:400]
                text = title + " " + summary

                if name not in tier1 and not _is_terror_relevant(text):
                    continue

                articles.append({
                    "source": f"rss/{name}",
                    "title": title,
                    "url": entry.link,
                    "summary": summary,
                    "date": pub_date,
                    "feed_name": name,
                })
        except Exception as e:
            print(f"    [{name}] 실패: {e}")
            continue

    return articles[:limit]


# ─────────────────────────────────────────────
# 6. OFAC SDN — 미국 제재 대상
# ─────────────────────────────────────────────
def fetch_ofac_recent(limit: int = 15) -> list[dict]:
    try:
        resp = requests.get(
            "https://ofac.treasury.gov/recent-actions",
            timeout=15,
            headers={"User-Agent": "terror-researcher/1.0"},
        )
        if resp.status_code != 200:
            return []

        links = re.findall(r'<a[^>]+href="(/recent-actions/[^"]+)"[^>]*>([^<]+)</a>', resp.text)
        results = []
        for href, title in links[:limit]:
            results.append({
                "source": "ofac",
                "title": title.strip(),
                "url": f"https://ofac.treasury.gov{href}",
            })
        return results
    except Exception as e:
        print(f"    [ofac] 수집 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 통합 수집
# ─────────────────────────────────────────────
def collect_all(target_date: datetime) -> dict:
    print("=" * 55)
    print("  Terror Intelligence — Data Collection")
    print("=" * 55)

    print("\n  [1/6] GDELT (global events)...")
    gdelt = fetch_gdelt(target_date)
    print(f"         {len(gdelt)} events")

    print("  [2/6] ACLED (coded incidents)...")
    acled = fetch_acled(target_date)
    print(f"         {len(acled)} incidents")

    print("  [3/6] Google News...")
    news = fetch_google_news()
    print(f"         {len(news)} articles")

    print("  [4/6] Expert RSS feeds...")
    expert = fetch_expert_rss()
    print(f"         {len(expert)} articles")

    print("  [5/6] OpenSanctions...")
    sanctions = fetch_sanctions_updates()
    print(f"         {len(sanctions)} entities")

    print("  [6/6] OFAC recent actions...")
    ofac = fetch_ofac_recent()
    print(f"         {len(ofac)} actions")

    total = len(gdelt) + len(acled) + len(news) + len(expert) + len(sanctions) + len(ofac)
    print(f"\n  Total: {total} items")

    return {
        "gdelt": gdelt,
        "acled": acled,
        "google_news": news,
        "expert_rss": expert,
        "sanctions": sanctions,
        "ofac": ofac,
        "collected_at": datetime.now().isoformat(),
    }
