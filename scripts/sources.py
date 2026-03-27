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
import zipfile
from datetime import datetime, timedelta
from typing import Optional

from config import (
    ACLED_EMAIL, ACLED_PASSWORD,
    ACLED_TERROR_SUBTYPES, GDELT_TERROR_CODES,
    RSS_FEEDS, GOOGLE_NEWS_QUERIES,
)


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
    """테러/안보 관련성 검증"""
    text_lower = text.lower()
    return sum(1 for k in TERROR_KEYWORDS if k in text_lower) >= 1


# ─────────────────────────────────────────────
# 1. GDELT — 실시간 글로벌 이벤트 (15분 업데이트)
# ─────────────────────────────────────────────
def fetch_gdelt(target_date: datetime, limit: int = 50) -> list[dict]:
    """GDELT에서 테러 관련 이벤트 수집 (최근 24시간)"""
    date_str = target_date.strftime("%Y%m%d")

    # GDELT Events 2.0 — 일별 CSV
    url = f"http://data.gdeltproject.org/events/{date_str}.export.CSV.zip"

    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            # 당일 데이터가 아직 없으면 전날 시도
            yesterday = (target_date - timedelta(days=1)).strftime("%Y%m%d")
            url = f"http://data.gdeltproject.org/events/{yesterday}.export.CSV.zip"
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                print(f"    GDELT: HTTP {resp.status_code}")
                return []

        # ZIP 해제 → CSV 파싱
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        csv_name = z.namelist()[0]
        csv_data = z.read(csv_name).decode("utf-8", errors="replace")

        reader = csv.reader(io.StringIO(csv_data), delimiter="\t")

        events = []
        for row in reader:
            if len(row) < 58:
                continue

            event_code = row[26]  # CAMEO EventCode
            # 테러 관련 CAMEO 코드 필터
            if not any(event_code.startswith(c) for c in GDELT_TERROR_CODES):
                continue

            goldstein = float(row[30]) if row[30] else 0
            num_mentions = int(row[31]) if row[31] else 0
            num_sources = int(row[32]) if row[32] else 0
            num_articles = int(row[33]) if row[33] else 0
            avg_tone = float(row[34]) if row[34] else 0

            actor1 = row[6] if len(row) > 6 else ""   # Actor1Name
            actor2 = row[16] if len(row) > 16 else ""  # Actor2Name
            country = row[37] if len(row) > 37 else ""  # ActionGeo_CountryCode
            location = row[40] if len(row) > 40 else ""  # ActionGeo_FullName
            lat = row[39] if len(row) > 39 else ""
            lon = row[38] if len(row) > 38 else ""  # Note: GDELT has Lat at 39
            source_url = row[57] if len(row) > 57 else ""

            events.append({
                "source": "gdelt",
                "event_code": event_code,
                "actor1": actor1,
                "actor2": actor2,
                "country_code": country,
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "goldstein_scale": goldstein,
                "num_mentions": num_mentions,
                "num_sources": num_sources,
                "num_articles": num_articles,
                "avg_tone": avg_tone,
                "source_url": source_url,
                "date": date_str,
            })

        # 중요도순 정렬 (mentions + sources)
        events.sort(key=lambda x: x["num_mentions"] + x["num_sources"], reverse=True)
        return events[:limit]

    except Exception as e:
        print(f"    [gdelt] 수집 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 2. ACLED — 코딩된 정치폭력 사건
# ─────────────────────────────────────────────
def _get_acled_token() -> str:
    """ACLED OAuth 토큰 발급"""
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
        print(f"    [acled] OAuth 실패: {resp.status_code} {resp.text[:200]}")
        return ""


def fetch_acled(target_date: datetime, limit: int = 100) -> list[dict]:
    """ACLED에서 테러 관련 사건 수집 (최근 14일, OAuth 인증)"""
    if not ACLED_EMAIL or not ACLED_PASSWORD:
        print("    [acled] 인증 정보 없음 — 스킵 (ACLED_EMAIL, ACLED_PASSWORD 필요)")
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
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"    [acled] HTTP {resp.status_code}: {resp.text[:200]}")
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
# 3. OpenSanctions — 제재 목록 변동
# ─────────────────────────────────────────────
def fetch_sanctions_updates(limit: int = 20) -> list[dict]:
    """OpenSanctions에서 최근 제재 목록 변동 수집"""
    try:
        # 테러 관련 데이터셋 목록
        datasets = [
            "un_sc_sanctions",   # UN 안보리
            "us_ofac_sdn",       # 미국 OFAC
            "eu_sanctions",      # EU 제재
        ]

        results = []
        for ds in datasets:
            resp = requests.get(
                f"https://data.opensanctions.org/datasets/latest/{ds}/entities.ftm.json",
                timeout=30,
                stream=True,
            )
            if resp.status_code != 200:
                continue

            # 스트리밍으로 처음 몇 줄만 읽기
            count = 0
            for line in resp.iter_lines():
                if count >= 10:
                    break
                if not line:
                    continue
                try:
                    import json
                    entity = json.loads(line)
                    props = entity.get("properties", {})
                    name = props.get("name", ["Unknown"])[0] if props.get("name") else "Unknown"
                    topics = props.get("topics", [])

                    # 테러 관련만
                    if any(t in str(topics).lower() for t in ["terror", "sanction"]):
                        results.append({
                            "source": f"opensanctions/{ds}",
                            "entity_id": entity.get("id", ""),
                            "name": name,
                            "schema": entity.get("schema", ""),
                            "datasets": ds,
                            "topics": topics,
                        })
                        count += 1
                except Exception:
                    continue

        return results[:limit]

    except Exception as e:
        print(f"    [sanctions] 수집 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 4. Google News — 테러 관련 뉴스
# ─────────────────────────────────────────────
def fetch_google_news(limit: int = 30) -> list[dict]:
    """Google News RSS에서 테러 관련 뉴스 수집"""
    articles = []
    seen_titles = set()

    for query in GOOGLE_NEWS_QUERIES:
        try:
            url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            for entry in feed.entries[:8]:
                title = entry.title
                # 중복 제거
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # 관련성 검증
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

            time.sleep(0.5)  # rate limit
        except Exception as e:
            print(f"    [google_news:{query}] 수집 실패: {e}")
            continue

    return articles[:limit]


# ─────────────────────────────────────────────
# 5. RSS — 전문 분석 기관
# ─────────────────────────────────────────────
def fetch_expert_rss(limit: int = 30) -> list[dict]:
    """테러/안보 전문 기관 RSS 수집"""
    articles = []

    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.title
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:400]
                text = title + " " + summary

                # Tier 1 소스는 필터 없이 전부 포함
                tier1 = ["Long War Journal", "Soufan Center", "CTC Sentinel", "Jamestown Foundation"]
                if name not in tier1 and not _is_terror_relevant(text):
                    continue

                articles.append({
                    "source": f"rss/{name}",
                    "title": title,
                    "url": entry.link,
                    "summary": summary,
                    "date": entry.get("published", ""),
                    "feed_name": name,
                })
        except Exception as e:
            print(f"    [{name}] 수집 실패: {e}")
            continue

    return articles[:limit]


# ─────────────────────────────────────────────
# 6. OFAC SDN — 미국 제재 대상 최신 변동
# ─────────────────────────────────────────────
def fetch_ofac_recent(limit: int = 15) -> list[dict]:
    """OFAC SDN 리스트에서 최근 변동 확인"""
    try:
        # OFAC recent actions RSS
        resp = requests.get(
            "https://ofac.treasury.gov/recent-actions",
            timeout=15,
            headers={"User-Agent": "terror-researcher/1.0"},
        )
        if resp.status_code != 200:
            return []

        # 간단한 HTML 파싱으로 최근 액션 추출
        text = resp.text
        # OFAC 페이지에서 링크 + 텍스트 추출
        import re
        links = re.findall(r'<a[^>]+href="(/recent-actions/[^"]+)"[^>]*>([^<]+)</a>', text)

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
    """모든 소스에서 데이터 수집"""
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
