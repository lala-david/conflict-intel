"""
NCTC (국가대테러센터) 데이터 수집 모듈

일일/주간 테러 동향 PDF를 다운로드하여 구조화 데이터로 변환.
Selenium 없이 requests + pdfminer만 사용 (경량).

데이터 구조:
- 지역별 테러 건수 (총계, 유럽, 미주, 아태, 중동, 아프리카)
- 주요 사건 목록 (날짜, 국가, 설명, 사망자, 부상자)
"""
import re
import os
import tempfile
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from logger import log

NCTC_BASE = "http://www.nctc.go.kr/nctc/information"
NCTC_DAILY_URL = f"{NCTC_BASE}/majorDailyTerrorism.do"
NCTC_WEEKLY_URL = f"{NCTC_BASE}/weeklyTerroristTrends.do"

# 한국어 테러 용어 → 영어 변환 사전
_KO_TERMS = {
    "무장괴한": "armed gunmen",
    "무장단체": "armed group",
    "무장세력": "armed forces",
    "무장조직": "armed organization",
    "총기테러": "gun attack",
    "총격": "shooting",
    "폭탄테러": "bombing",
    "자폭테러": "suicide bombing",
    "자살폭탄": "suicide bombing",
    "차량폭탄": "car bombing",
    "급조폭발물": "IED",
    "박격포": "mortar attack",
    "로켓공격": "rocket attack",
    "공습": "airstrike",
    "민간인": "civilians",
    "민간인대상": "civilian target",
    "경찰대상": "police target",
    "경찰": "police",
    "군인": "soldiers",
    "군대": "military",
    "정부군": "government forces",
    "테러": "attack",
    "공격": "attack",
    "납치": "kidnapping",
    "인질": "hostages",
    "사망": "killed",
    "부상": "wounded",
    "피해": "casualties",
    "에서": "in",
    "州": "state",
    "성": "province",
    "지역": "region",
    "도시": "city",
    "마을": "village",
    "시장": "market",
    "교회": "church",
    "사원": "mosque",
    "학교": "school",
}


def translate_korean_description(text: str) -> str:
    """한국어 설명을 영어로 변환 (단순 단어 치환)"""
    if not text:
        return text
    result = text
    # 길이 긴 것부터 치환 (부분 매칭 방지)
    for ko, en in sorted(_KO_TERMS.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    # 한국어 조사 제거
    import re
    result = re.sub(r'[가-힣]+', '', result)  # 남은 한국어 제거
    result = re.sub(r'\s+', ' ', result).strip()
    return result


# 국가명 한→영 매핑 (주요국)
_KO_TO_EN = {
    "나이지리아": "Nigeria", "파키스탄": "Pakistan", "아프가니스탄": "Afghanistan",
    "이라크": "Iraq", "시리아": "Syria", "소말리아": "Somalia", "말리": "Mali",
    "부르키나파소": "Burkina Faso", "수단": "Sudan", "콩고": "DR Congo (Zaire)",
    "이스라엘": "Israel", "팔레스타인": "Palestinian Territories",
    "예멘": "Yemen", "레바논": "Lebanon", "터키": "Turkey", "이란": "Iran",
    "이집트": "Egypt", "리비아": "Libya", "튀니지": "Tunisia",
    "모잠비크": "Mozambique", "에티오피아": "Ethiopia", "카메룬": "Cameroon",
    "차드": "Chad", "니제르": "Niger", "케냐": "Kenya",
    "인도": "India", "미얀마": "Myanmar (Burma)", "필리핀": "Philippines",
    "인도네시아": "Indonesia", "태국": "Thailand",
    "러시아": "Russia", "우크라이나": "Ukraine", "프랑스": "France",
    "영국": "United Kingdom", "독일": "Germany", "벨기에": "Belgium",
    "미국": "United States of America", "콜롬비아": "Colombia", "멕시코": "Mexico",
    "방글라데시": "Bangladesh", "스리랑카": "Sri Lanka",
}

# 국가명 한→ISO2
_KO_TO_ISO = {
    "나이지리아": "NG", "파키스탄": "PK", "아프가니스탄": "AF",
    "이라크": "IQ", "시리아": "SY", "소말리아": "SO", "말리": "ML",
    "부르키나파소": "BF", "수단": "SD", "콩고": "CD",
    "이스라엘": "IL", "팔레스타인": "PS",
    "예멘": "YE", "레바논": "LB", "터키": "TR", "이란": "IR",
    "이집트": "EG", "리비아": "LY", "튀니지": "TN",
    "모잠비크": "MZ", "에티오피아": "ET", "카메룬": "CM",
    "차드": "TD", "니제르": "NE", "케냐": "KE",
    "인도": "IN", "미얀마": "MM", "필리핀": "PH",
    "인도네시아": "ID", "태국": "TH",
    "러시아": "RU", "우크라이나": "UA", "프랑스": "FR",
    "영국": "GB", "독일": "DE", "벨기에": "BE",
    "미국": "US", "콜롬비아": "CO", "멕시코": "MX",
    "방글라데시": "BD", "스리랑카": "LK",
}


def _download_pdf(url: str) -> str:
    """PDF 다운로드 → 텍스트 추출"""
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200 or len(resp.content) < 1000:
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(resp.content)
        tmp.close()
        text = extract_text(tmp.name)
        return " ".join(text.split())  # 공백 정규화
    except Exception as e:
        log.error(f"[nctc] PDF parse failed: {e}")
        return ""
    finally:
        os.unlink(tmp.name)


def _parse_daily_pdf(text: str, year: int = None) -> dict:
    """일일 테러동향 PDF 텍스트 → 구조화 데이터"""
    if not year:
        year = datetime.now().year

    result = {"date": "", "stats": {}, "incidents": []}

    # 날짜 추출: '26. 4. 10 or '26.4.10
    dm = re.search(r"['΄']\s*(\d{2})\.\s*(\d{1,2})\.\s*(\d{1,2})", text)
    if dm:
        yr = f"20{dm.group(1)}"
        mon = dm.group(2).zfill(2)
        day = dm.group(3).zfill(2)
        result["date"] = f"{yr}-{mon}-{day}"

    # 지역별 통계: 총계(건) 유럽 미주 아태 중동 아프리카 + 숫자들
    stats_match = re.search(
        r"총계\(건\)\s*유\s*럽\s*미\s*주\s*아\s*태\s*중\s*동\s*아프리카\s*"
        r"(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])",
        text
    )
    if stats_match:
        def _parse_val(s):
            return int(s) if s not in ["-", ""] else 0

        result["stats"] = {
            "total": _parse_val(stats_match.group(1)),
            "europe": _parse_val(stats_match.group(2)),
            "americas": _parse_val(stats_match.group(3)),
            "asia_pacific": _parse_val(stats_match.group(4)),
            "middle_east": _parse_val(stats_match.group(5)),
            "africa": _parse_val(stats_match.group(6)),
        }

    # 주요 사건: ○ M.D 국가 설명(사망 N[명], 부상/납치 N[명])
    # - 날짜 뒤 trailing dot optional, "명" optional (현재 NCTC PDF는 생략)
    pattern = r"○\s*(\d{1,2}\.\d{1,2})\.?\s+(\S+)\s+(.+?)(?:\(사망\s*(\d+)명?(?:,\s*(?:부상|납치)\s*(\d+)명?)?\))"
    for m in re.finditer(pattern, text):
        date_parts = m.group(1).split(".")
        mon = date_parts[0].zfill(2)
        day = date_parts[1].zfill(2)
        incident_date = f"{year}-{mon}-{day}"

        # trailing punctuation 제거 (PDF 파싱 후 콤마/점이 붙어있는 경우)
        country_ko = m.group(2).strip(",.()[]:;")
        # 알 수 없는 매핑 = PDF 추출 실패(모지바케) 또는 단체명. 스킵.
        iso = _KO_TO_ISO.get(country_ko, "")
        if not iso:
            continue
        country_en = _KO_TO_EN.get(country_ko, country_ko)

        # 한국어 설명 → 영어 변환
        desc_ko = m.group(3).strip()
        desc_en = translate_korean_description(desc_ko)

        result["incidents"].append({
            "source": "nctc",
            "date": incident_date,
            "country": country_en,
            "country_code": iso,
            "country_ko": country_ko,
            "description": desc_en or desc_ko,  # 변환 실패 시 원본
            "description_ko": desc_ko,           # 원본 보존
            "fatalities": int(m.group(4)),
            "wounded": int(m.group(5)) if m.group(5) else 0,
        })

    # 해당 없음 체크
    if "해당 없음" in text or "해당없음" in text:
        result["no_incidents"] = True

    return result


def fetch_nctc_daily(limit: int = 5) -> list[dict]:
    """NCTC 일일 테러동향 최근 N건 수집"""
    try:
        resp = requests.get(
            NCTC_DAILY_URL,
            params={"mode": "list", "articleLimit": limit, "article.offset": 0},
            timeout=15,
        )
        if resp.status_code != 200:
            log.error(f"[nctc] HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        all_incidents = []
        all_stats = []

        for row in table.find_all("tr"):
            # PDF 다운로드 링크 찾기
            link = None
            for a in row.find_all("a", href=True):
                href = a.get("href", "")
                if "download" in href:
                    link = NCTC_DAILY_URL + href
                    break

            if not link:
                continue

            # PDF 다운로드 및 파싱
            log.info(f"  [nctc] downloading {link.split('articleNo=')[1].split('&')[0] if 'articleNo' in link else 'pdf'}...")
            text = _download_pdf(link)
            if not text:
                continue

            parsed = _parse_daily_pdf(text)

            if parsed.get("stats"):
                all_stats.append({"date": parsed["date"], **parsed["stats"]})

            for inc in parsed.get("incidents", []):
                all_incidents.append(inc)

        log.info(f"  [nctc] {len(all_incidents)} incidents, {len(all_stats)} daily stats")
        return all_incidents

    except Exception as e:
        log.error(f"[nctc] fetch failed: {e}")
        return []


# Note: weekly NCTC parsing removed as unused dead code (use daily only)
