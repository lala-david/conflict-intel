"""
Terror Intelligence 데이터 소스 수집 모듈
- GDELT (실시간 이벤트), UCDP (분쟁 사건+사상자), OpenSanctions (제재)
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
import concurrent.futures
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from config import (
    UCDP_TOKEN, GDELT_TERROR_CODES,
    RSS_FEEDS, RSS_TIER1_FEEDS, GOOGLE_NEWS_QUERIES,
)
from fips_to_iso import fips_to_iso
from database import get_known_ucdp_ids

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

        # D2: Only keep events whose SQLDATE is within 2 days of target_date
        target_ymd = target_date.strftime("%Y%m%d")
        min_date = (target_date - timedelta(days=2)).strftime("%Y%m%d")

        # D3: Actor skip list — generic/non-terror actors
        _ACTOR_SKIP = {
            "POLICE", "DOCTOR", "SUPREME COURT", "JUDGE", "NAVY",
            "BATTALION", "MALE", "FEMALE", "BRITISH", "CITIZEN",
            "ACTOR", "FIREFIGHTER", "PROSECUTOR", "HOSPITAL", "WORKER",
            "PENNSYLVANIA", "PHOENIX", "LOS ANGELES", "COLORADO",
            "CHANDIGARH", "ABU DHABI", "TELEVISION", "NEWSPAPER",
            "INTELLIGENCE", "NATIONALS", "CAMBODIA",
        }
        # D3: URL domains/keywords that indicate non-terror content
        _URL_NOISE = {
            "gas-price", "bike", "newborn", "ww2", "world-war",
            "recipe", "sport", "weather", "zoo", "reunion",
            "celebrity", "entertainment", "kanye", "schitts",
            "iheart.com", "aol.co.uk", "aol.com",
            "mix106", "mymagic", "kfbx", "q106",
            "perthnow.com.au",
        }
        # D3: Minimum Goldstein hostility — skip events with weak conflict signal
        _MIN_GOLDSTEIN = -5.0

        events = []
        for row in reader:
            if len(row) < 58:
                continue

            # D2: Filter by SQLDATE (column 1, YYYYMMDD) — within 2 days of target
            sql_date = row[1] if row[1] else ""
            if sql_date < min_date or sql_date > target_ymd:
                continue

            event_code = row[26]  # CAMEO EventCode
            if not any(event_code.startswith(c) for c in GDELT_TERROR_CODES):
                continue

            try:
                goldstein = float(row[30]) if row[30] else 0
                num_mentions = int(row[31]) if row[31] else 0
                num_sources = int(row[32]) if row[32] else 0
                num_articles = int(row[33]) if row[33] else 0
                avg_tone = float(row[34]) if row[34] else 0
            except (ValueError, IndexError):
                continue  # skip rows with unparseable numeric fields

            actor1 = row[6] if row[6] else ""
            actor2 = row[16] if row[16] else ""

            # D3: Goldstein filter — skip events with weak conflict signal
            if goldstein > _MIN_GOLDSTEIN:
                continue

            # D3: Actor relevance filter — skip generic/non-terror actors
            actor1_upper = actor1.upper().strip()
            actor2_upper = actor2.upper().strip()
            if actor1_upper in _ACTOR_SKIP or actor2_upper in _ACTOR_SKIP:
                continue

            # #1: 좌표 매핑 수정 — ActionGeo 우선, 없으면 Actor1Geo
            # GDELT V1 export columns:
            #   ActionGeo: CountryCode=51, ADM1Code=52, Lat=53, Long=54
            #   Actor1Geo: CountryCode=37, ADM1Code=38, Lat=39, Long=40
            try:
                action_lat = row[53] if len(row) > 53 and row[53] else ""
                action_lon = row[54] if len(row) > 54 and row[54] else ""
                action_country = row[51] if len(row) > 51 and row[51] else ""
                action_adm1 = row[52] if len(row) > 52 and row[52] else ""
            except IndexError:
                action_lat = action_lon = action_country = action_adm1 = ""
            action_location = ""

            # ActionGeo가 비어있으면 Actor1Geo 폴백 (columns 37-40)
            if not action_lat:
                try:
                    action_lat = row[39] if len(row) > 39 and row[39] else ""
                    action_lon = row[40] if len(row) > 40 and row[40] else ""
                    action_country = row[37] if len(row) > 37 and row[37] else ""
                    action_adm1 = row[38] if len(row) > 38 and row[38] else ""
                except IndexError:
                    pass

            # Safety check: validate lat/lon are actually numeric
            try:
                if action_lat:
                    float(action_lat)
                if action_lon:
                    float(action_lon)
            except ValueError:
                action_lat = action_lon = ""

            # 위치명 구성
            if action_adm1:
                action_location = action_adm1
            if action_country:
                action_location = f"{action_location}, {action_country}".strip(", ")

            source_url = row[57] if len(row) > 57 else ""

            # D3: URL keyword filter — skip obvious non-terror content
            url_lower = source_url.lower()
            if any(noise in url_lower for noise in _URL_NOISE):
                continue

            # #1: FIPS → ISO 변환
            iso_country = fips_to_iso(action_country) if action_country else ""

            # D2: Format SQLDATE "20260329" → "2026-03-29"
            formatted_date = f"{sql_date[:4]}-{sql_date[4:6]}-{sql_date[6:8]}" if len(sql_date) == 8 else sql_date

            events.append({
                "source": "gdelt",
                "event_code": event_code,
                "actor1": actor1,
                "actor2": actor2,
                "country_code": iso_country,
                "country": iso_country,  # D4: populated with ISO code, enrichment resolves full name
                "location": action_location,
                "latitude": action_lat,
                "longitude": action_lon,
                "goldstein_scale": goldstein,
                "num_mentions": num_mentions,
                "num_sources": num_sources,
                "num_articles": num_articles,
                "avg_tone": avg_tone,
                "source_url": source_url,
                "date": formatted_date,
            })

        # D18: Regional diversity — top 30 by mentions + fill from unseen countries
        events.sort(key=lambda x: x["num_mentions"] + x["num_sources"], reverse=True)
        top_events = events[:30]
        seen_countries = {e.get("country_code") for e in top_events}
        diverse = []
        for e in events[30:]:
            cc = e.get("country_code", "")
            if cc and cc not in seen_countries:
                diverse.append(e)
                seen_countries.add(cc)
            if len(diverse) >= 20:
                break
        return (top_events + diverse)[:limit]

    except Exception as e:
        print(f"    [gdelt] 파싱 실패: {e}")
        return []


# ─────────────────────────────────────────────
# 2. UCDP — 분쟁 사건 + 사상자 데이터
# ─────────────────────────────────────────────
def fetch_ucdp(target_date: datetime, limit: int = 100) -> list[dict]:
    """UCDP GED Candidate API — 분쟁 사건 수집 (사상자 포함)"""
    if not UCDP_TOKEN:
        print("    [ucdp] 토큰 없음 — 스킵 (.env에 UCDP_TOKEN 설정 필요)")
        return []

    # 최근 90일 범위 (UCDP Candidate는 월 1회 일괄 업데이트, ~2개월 지연)
    since = (target_date - timedelta(days=90)).strftime("%Y-%m-%d")
    until = target_date.strftime("%Y-%m-%d")
    known_ids = get_known_ucdp_ids()

    try:
        events = []
        page = 0
        while len(events) < limit:
            resp = requests.get(
                "https://ucdpapi.pcr.uu.se/api/gedevents/26.0.2",
                params={
                    "pagesize": min(100, limit - len(events)),
                    "page": page,
                    "StartDate": since,
                    "EndDate": until,
                },
                headers={"x-ucdp-access-token": UCDP_TOKEN},
                timeout=30,
            )

            if resp.status_code == 401:
                print("    [ucdp] 토큰 만료 또는 유효하지 않음")
                break
            if resp.status_code != 200:
                print(f"    [ucdp] HTTP {resp.status_code}")
                break

            data = resp.json()
            results = data.get("Result", [])
            if not results:
                break

            for item in results:
                best_deaths = int(item.get("best", 0) or 0)
                ucdp_country = item.get("country", "")
                event_id = str(item.get("id", ""))
                events.append({
                    "source": "ucdp",
                    "event_id": event_id,
                    "is_new": event_id not in known_ids,
                    "date": item.get("date_start", ""),
                    "event_type": f"type_{item.get('type_of_violence', '')}",
                    "sub_event_type": item.get("conflict_name", ""),
                    "actor1": item.get("side_a", ""),
                    "actor2": item.get("side_b", ""),
                    "country": ucdp_country,
                    "country_code": ucdp_country,
                    "admin1": item.get("adm_1", ""),
                    "location": item.get("where_coordinates", ""),
                    "latitude": str(item.get("latitude", "")),
                    "longitude": str(item.get("longitude", "")),
                    "fatalities": best_deaths,
                    "deaths_a": int(item.get("deaths_a", 0) or 0),
                    "deaths_b": int(item.get("deaths_b", 0) or 0),
                    "deaths_civilians": int(item.get("deaths_civilians", 0) or 0),
                    "fatalities_low": int(item.get("low", 0) or 0),
                    "fatalities_high": int(item.get("high", 0) or 0),
                    "notes": (item.get("source_headline", "") or "")[:500],
                    "source_text": (item.get("source_article", "") or "")[:300],
                    "conflict_name": item.get("conflict_name", ""),
                    "dyad_name": item.get("dyad_name", ""),
                })

            total_pages = data.get("TotalPages", 0)
            page += 1
            if page >= total_pages:
                break

        events.sort(key=lambda x: x["fatalities"], reverse=True)
        return events[:limit]

    except Exception as e:
        print(f"    [ucdp] 수집 실패: {e}")
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

        # 캐시 업데이트: merge new IDs into existing cache (union) so it accumulates
        merged_ids = list(previous_ids | set(current_ids))
        _save_sanctions_cache(merged_ids)

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
            rss_resp = requests.get(url, timeout=15)
            feed = feedparser.parse(rss_resp.content)

            # D19: Skip articles older than 3 days
            staleness_cutoff = datetime.now() - timedelta(days=3)
            # D19: URL domains that indicate non-news (encyclopedias, etc.)
            _GNEWS_URL_NOISE = ("britannica.com", "wikipedia.org", "aol.com/", "dictionary.com")

            for entry in feed.entries[:8]:
                # D19: Date staleness filter — skip articles older than 3 days
                pub_parsed = entry.get("published_parsed")
                if pub_parsed:
                    try:
                        pub_dt = datetime(*pub_parsed[:6])
                        if pub_dt < staleness_cutoff:
                            continue
                    except (TypeError, ValueError):
                        pass

                title = entry.title
                link = entry.link or ""

                # D19: URL-based noise filter — skip encyclopedias & non-news
                link_lower = link.lower()
                if any(domain in link_lower for domain in _GNEWS_URL_NOISE):
                    continue

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
                    "url": link,
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
    tier1 = RSS_TIER1_FEEDS

    for name, url in RSS_FEEDS.items():
        try:
            rss_resp = requests.get(url, timeout=15)
            feed = feedparser.parse(rss_resp.content)
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
# 7. Wikipedia — 연도별 테러 사건 목록
# ─────────────────────────────────────────────
def fetch_wikipedia_incidents(limit: int = 50) -> list[dict]:
    """Fetch terrorist incidents from Wikipedia's 'List of terrorist incidents in YYYY' page.

    Uses the MediaWiki API to get wikitext, then parses wiki-table markup.
    No BeautifulSoup needed — pure regex/string parsing.
    """
    year = datetime.now().year
    cutoff = datetime.now() - timedelta(days=30)
    page_title = f"List_of_terrorist_incidents_in_{year}"
    api_url = (
        "https://en.wikipedia.org/w/api.php"
        f"?action=parse&page={page_title}&prop=wikitext&format=json"
    )
    wiki_page_url = f"https://en.wikipedia.org/wiki/{page_title}"

    try:
        resp = requests.get(api_url, timeout=20, headers={"User-Agent": "terror-researcher/1.0"})
        if resp.status_code != 200:
            print(f"    [wikipedia] HTTP {resp.status_code}")
            return []

        data = resp.json()
        if "error" in data:
            print(f"    [wikipedia] 페이지 없음: {data['error'].get('info', '')}")
            return []

        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        if not wikitext:
            return []

        results = _parse_wiki_terror_table(wikitext, cutoff, wiki_page_url)
        return results[:limit]

    except Exception as e:
        print(f"    [wikipedia] 수집 실패: {e}")
        return []


def _parse_wiki_terror_table(wikitext: str, cutoff: datetime, page_url: str) -> list[dict]:
    """Parse the 2026 Wikipedia terror incidents table.

    Actual format (each cell on its own line):
        |-
        |{{dts|19 January}}
        |[[Suicide bombing]]
        | style="..." |7 (+1)
        | style="..." |13
        |[[Kabul]], Afghanistan
        |[[2026 Kabul restaurant bombing]]
        |A suicide bomber...
        |{{Flag icon|IS}} [[IS-KP]]
        |[[Islamic State-Taliban conflict]]

    Columns: Date, Type, Dead, Injured, Location, Article, Details, Perpetrator, Part of
    """
    results = []
    year = datetime.now().year

    # Find the main table
    table_match = re.search(r'\{\|[^\n]*wikitable.*?\|\}', wikitext, re.DOTALL)
    if not table_match:
        return []

    table = table_match.group()
    # Split into rows by |-
    rows = re.split(r'\n\|\-[^\n]*', table)

    for row in rows:
        lines = [l.strip() for l in row.strip().split('\n') if l.strip().startswith('|') and not l.strip().startswith('|}')]
        if len(lines) < 5:
            continue

        # Clean each cell
        cells = [_clean_wiki_cell(l) for l in lines]
        if len(cells) < 5:
            continue

        # Column order: Date, Type, Dead, Injured, Location, Article, Details, Perpetrator, Part of
        try:
            date_raw = cells[0]
            attack_type = cells[1] if len(cells) > 1 else ""
            dead_raw = cells[2] if len(cells) > 2 else "0"
            injured_raw = cells[3] if len(cells) > 3 else "0"
            location_raw = cells[4] if len(cells) > 4 else ""
            notes = cells[6] if len(cells) > 6 else ""
            perpetrator = cells[7] if len(cells) > 7 else ""

            # Parse date
            date_parsed = _parse_wiki_date(date_raw, year)
            if not date_parsed:
                continue
            if date_parsed < cutoff:
                continue

            # Parse fatalities (handle "7 (+1)", "'''32'''", "162-200+", "0")
            fatalities = _parse_wiki_number(dead_raw)
            wounded = _parse_wiki_number(injured_raw)

            # Parse location → country
            country = _guess_country(location_raw)

            results.append({
                "source": "wikipedia",
                "event_id": f"wiki-{date_parsed.strftime('%Y%m%d')}-{location_raw[:30]}",
                "date": date_parsed.strftime("%Y-%m-%d"),
                "event_type": attack_type,
                "sub_event_type": "",
                "actor1": perpetrator[:100],
                "actor2": "",
                "country": country,
                "country_code": "",
                "location": location_raw[:100],
                "latitude": "",
                "longitude": "",
                "fatalities": fatalities,
                "wounded": wounded,
                "notes": notes[:500],
                "url": page_url,
            })
        except (IndexError, ValueError):
            continue

    return results


def _clean_wiki_cell(cell: str) -> str:
    """Strip wiki markup from a cell value."""
    text = cell.strip()
    # Remove leading | and style attributes
    text = re.sub(r'^\|(?:\s*style="[^"]*"\s*\|)?', '', text).strip()
    # Extract date from {{dts|...}} template
    dts = re.search(r'\{\{dts\|([^}]+)\}\}', text)
    if dts:
        text = dts.group(1)
    # Extract from {{Flag icon|...}} [[Name]]
    text = re.sub(r'\{\{[Ff]lag\s+icon\|[^}]*\}\}\s*', '', text)
    # Remove [[ ]] wiki links, keep display text
    text = re.sub(r'\[\[[^\]]*\|([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    # Remove remaining {{ }} templates
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Remove external links
    text = re.sub(r'\[https?://\S+\s*([^\]]*)\]', r'\1', text)
    # Remove ref tags
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^/]*/>', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove bold/italic markup
    text = re.sub(r"'{2,}", '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_wiki_number(s: str) -> int:
    """Parse casualty numbers from wiki format: '7 (+1)', '32', '162-200+', 'Unknown'"""
    s = re.sub(r"'{2,}", '', s)  # remove bold markup
    s = s.strip()
    if not s or s.lower() in ('unknown', 'none', 'n/a', '?', ''):
        return 0
    # Take the first number found
    m = re.search(r'(\d+)', s)
    return int(m.group(1)) if m else 0


def _parse_wiki_date(date_str: str | None, default_year: int) -> datetime | None:
    """Parse common date formats found in Wikipedia tables."""
    if not date_str:
        return None

    # "1 January 2026" or "12 March 2026"
    m = re.search(
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|'
        r'September|October|November|December)\s+(\d{4})', date_str
    )
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y")
        except ValueError:
            pass

    # "2026-03-15"
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # "19 January" or "January 1" (no year) — assume default_year
    m = re.search(
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|'
        r'September|October|November|December)', date_str
    )
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {default_year}", "%d %B %Y")
        except ValueError:
            pass

    m = re.search(
        r'(January|February|March|April|May|June|July|August|'
        r'September|October|November|December)\s+(\d{1,2})', date_str
    )
    if m:
        try:
            return datetime.strptime(f"{m.group(2)} {m.group(1)} {default_year}", "%d %B %Y")
        except ValueError:
            pass

    return None


def _guess_country(location: str) -> str:
    """Extract a likely country name from a location string.

    Very basic heuristic: take the last comma-separated part, or the whole string
    if there's no comma.
    """
    if not location:
        return ""
    parts = [p.strip() for p in location.split(",")]
    return parts[-1] if parts else location


# ─────────────────────────────────────────────
# 통합 수집
# ─────────────────────────────────────────────
def _safe_fetch(name, fn, *args, **kwargs):
    """Run a fetch function with error isolation so one source failure doesn't kill others."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"    [{name}] failed: {e}")
        return []


def collect_all(target_date: datetime) -> dict:
    print("=" * 55)
    print("  Terror Intelligence — Data Collection")
    print("=" * 55)

    # Fetch all 7 sources in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        future_gdelt = executor.submit(_safe_fetch, "gdelt", fetch_gdelt, target_date)
        future_ucdp = executor.submit(_safe_fetch, "ucdp", fetch_ucdp, target_date)
        future_news = executor.submit(_safe_fetch, "google_news", fetch_google_news)
        future_expert = executor.submit(_safe_fetch, "expert_rss", fetch_expert_rss)
        future_sanctions = executor.submit(_safe_fetch, "sanctions", fetch_sanctions_updates)
        future_ofac = executor.submit(_safe_fetch, "ofac", fetch_ofac_recent)
        future_wiki = executor.submit(_safe_fetch, "wikipedia", fetch_wikipedia_incidents)

    gdelt = future_gdelt.result()
    ucdp = future_ucdp.result()
    news = future_news.result()
    expert = future_expert.result()
    sanctions = future_sanctions.result()
    ofac = future_ofac.result()
    wikipedia = future_wiki.result()

    print(f"\n  [1/7] GDELT:          {len(gdelt)} events")
    print(f"  [2/7] UCDP:           {len(ucdp)} incidents")
    print(f"  [3/7] Google News:    {len(news)} articles")
    print(f"  [4/7] Expert RSS:     {len(expert)} articles")
    print(f"  [5/7] OpenSanctions:  {len(sanctions)} entities")
    print(f"  [6/7] OFAC:           {len(ofac)} actions")
    print(f"  [7/7] Wikipedia:      {len(wikipedia)} incidents")

    total = len(gdelt) + len(ucdp) + len(news) + len(expert) + len(sanctions) + len(ofac) + len(wikipedia)
    print(f"\n  Total: {total} items")

    return {
        "gdelt": gdelt,
        "ucdp": ucdp,
        "google_news": news,
        "expert_rss": expert,
        "sanctions": sanctions,
        "ofac": ofac,
        "wikipedia": wikipedia,
        "collected_at": datetime.now().isoformat(),
    }
