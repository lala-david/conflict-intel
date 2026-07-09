"""
NCTC (국가대테러센터) 데이터 수집 모듈

일일 테러동향 PDF를 다운로드하여 구조화 데이터로 변환.
Selenium 없이 requests + pdfminer만 사용 (경량).

수집 정책 (2026-07 개편):
- 하루 한 번: 파이프라인이 17:00 KST 실행에서만 NCTC를 포함한다(registry의 RUN_NCTC 게이트).
- 최신 N개(기본 5) 글을 훑어 놓친 날을 백필한다 (INSERT OR IGNORE 로 중복 무해).
- 사건 날짜는 게시일이 아니라 PDF 안 각 사건의 실제 발생일(○ M.D)을 쓴다.
- 국가 매핑을 크게 확장했고, 매핑에 없는 토큰(단체명·파편)은 버리고 로그만 남긴다.
"""
import re
import os
import tempfile
import requests
from datetime import datetime
from bs4 import BeautifulSoup, Tag
from pdfminer.high_level import extract_text
from logger import log

NCTC_BASE = "http://www.nctc.go.kr/nctc/information"
NCTC_DAILY_URL = f"{NCTC_BASE}/majorDailyTerrorism.do"

# 한국어 테러 용어 → 영어 (설명 번역용)
_KO_TERMS = {
    "무장괴한": "armed gunmen", "무장단체": "armed group", "무장세력": "armed forces",
    "무장조직": "armed organization", "총기테러": "gun attack", "총격": "shooting",
    "폭탄테러": "bombing", "자폭테러": "suicide bombing", "자살폭탄": "suicide bombing",
    "차량폭탄": "car bombing", "급조폭발물": "IED", "박격포": "mortar attack",
    "로켓공격": "rocket attack", "공습": "airstrike", "민간인": "civilians",
    "경찰": "police", "군인": "soldiers", "군대": "military", "정부군": "government forces",
    "테러": "attack", "공격": "attack", "납치": "kidnapping", "인질": "hostages",
    "사망": "killed", "부상": "wounded", "피해": "casualties",
    "시장": "market", "교회": "church", "사원": "mosque", "학교": "school",
}


def translate_korean_description(text: str) -> str:
    """한국어 설명을 영어로 변환 (단순 단어 치환). 남은 한글·군더더기는 정리."""
    if not text:
        return text
    result = text
    for ko, en in sorted(_KO_TERMS.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, f" {en} ")
    result = re.sub(r"[가-힣]+", " ", result)         # 남은 한글 제거
    result = re.sub(r"[一-鿿]+", " ", result)  # 남은 한자(州·省 등) 제거
    result = re.sub(r"[·∘ㆍ]", " ", result)
    result = re.sub(r"\s*,\s*", ", ", result)
    result = re.sub(r"\s{2,}", " ", result).strip(" ,")
    return result


# 국가명 한글 → (ISO2, 영문). 대폭 확장 — 매핑에 없으면 버리지 않고 한글명으로 보존한다.
_KO_COUNTRY: dict[str, tuple[str, str]] = {
    # 중동·북아프리카
    "이라크": ("IQ", "Iraq"), "시리아": ("SY", "Syria"), "예멘": ("YE", "Yemen"),
    "레바논": ("LB", "Lebanon"), "이스라엘": ("IL", "Israel"),
    "팔레스타인": ("PS", "Palestinian Territories"), "요르단": ("JO", "Jordan"),
    "사우디아라비아": ("SA", "Saudi Arabia"), "사우디": ("SA", "Saudi Arabia"),
    "이란": ("IR", "Iran"), "터키": ("TR", "Turkey"), "튀르키예": ("TR", "Turkey"),
    "쿠웨이트": ("KW", "Kuwait"), "카타르": ("QA", "Qatar"),
    "아랍에미리트": ("AE", "United Arab Emirates"), "바레인": ("BH", "Bahrain"),
    "오만": ("OM", "Oman"), "이집트": ("EG", "Egypt"), "리비아": ("LY", "Libya"),
    "튀니지": ("TN", "Tunisia"), "알제리": ("DZ", "Algeria"), "모로코": ("MA", "Morocco"),
    "모리타니": ("MR", "Mauritania"),
    # 사하라 이남 아프리카
    "나이지리아": ("NG", "Nigeria"), "말리": ("ML", "Mali"),
    "부르키나파소": ("BF", "Burkina Faso"), "니제르": ("NE", "Niger"),
    "차드": ("TD", "Chad"), "카메룬": ("CM", "Cameroon"), "소말리아": ("SO", "Somalia"),
    "케냐": ("KE", "Kenya"), "에티오피아": ("ET", "Ethiopia"), "수단": ("SD", "Sudan"),
    "남수단": ("SS", "South Sudan"), "콩고": ("CD", "DR Congo (Zaire)"),
    "콩고민주공화국": ("CD", "DR Congo (Zaire)"), "콩고공화국": ("CG", "Republic of the Congo"),
    "중앙아프리카공화국": ("CF", "Central African Republic"),
    "중아공": ("CF", "Central African Republic"), "모잠비크": ("MZ", "Mozambique"),
    "우간다": ("UG", "Uganda"), "탄자니아": ("TZ", "Tanzania"), "르완다": ("RW", "Rwanda"),
    "부룬디": ("BI", "Burundi"), "앙골라": ("AO", "Angola"), "짐바브웨": ("ZW", "Zimbabwe"),
    "남아프리카공화국": ("ZA", "South Africa"), "남아공": ("ZA", "South Africa"),
    "세네갈": ("SN", "Senegal"), "기니": ("GN", "Guinea"), "코트디부아르": ("CI", "Cote d'Ivoire"),
    "가나": ("GH", "Ghana"), "토고": ("TG", "Togo"), "베냉": ("BJ", "Benin"),
    "가봉": ("GA", "Gabon"), "에리트레아": ("ER", "Eritrea"), "지부티": ("DJ", "Djibouti"),
    "마다가스카르": ("MG", "Madagascar"), "잠비아": ("ZM", "Zambia"),
    # 남·중앙 아시아
    "아프가니스탄": ("AF", "Afghanistan"), "파키스탄": ("PK", "Pakistan"), "인도": ("IN", "India"),
    "방글라데시": ("BD", "Bangladesh"), "스리랑카": ("LK", "Sri Lanka"), "네팔": ("NP", "Nepal"),
    "미얀마": ("MM", "Myanmar (Burma)"), "카자흐스탄": ("KZ", "Kazakhstan"),
    "우즈베키스탄": ("UZ", "Uzbekistan"), "타지키스탄": ("TJ", "Tajikistan"),
    "키르기스스탄": ("KG", "Kyrgyzstan"), "투르크메니스탄": ("TM", "Turkmenistan"),
    # 동·동남 아시아
    "중국": ("CN", "China"), "태국": ("TH", "Thailand"), "필리핀": ("PH", "Philippines"),
    "인도네시아": ("ID", "Indonesia"), "말레이시아": ("MY", "Malaysia"),
    "베트남": ("VN", "Vietnam"), "캄보디아": ("KH", "Cambodia"),
    # 유럽·러시아
    "러시아": ("RU", "Russia"), "우크라이나": ("UA", "Ukraine"), "프랑스": ("FR", "France"),
    "영국": ("GB", "United Kingdom"), "독일": ("DE", "Germany"), "벨기에": ("BE", "Belgium"),
    "스페인": ("ES", "Spain"), "이탈리아": ("IT", "Italy"), "그리스": ("GR", "Greece"),
    "스웨덴": ("SE", "Sweden"), "노르웨이": ("NO", "Norway"), "네덜란드": ("NL", "Netherlands"),
    "오스트리아": ("AT", "Austria"), "세르비아": ("RS", "Serbia"), "코소보": ("XK", "Kosovo"),
    "폴란드": ("PL", "Poland"),
    # 아메리카
    "미국": ("US", "United States of America"), "멕시코": ("MX", "Mexico"),
    "콜롬비아": ("CO", "Colombia"), "브라질": ("BR", "Brazil"), "베네수엘라": ("VE", "Venezuela"),
    "페루": ("PE", "Peru"), "칠레": ("CL", "Chile"), "아르헨티나": ("AR", "Argentina"),
    "에콰도르": ("EC", "Ecuador"), "볼리비아": ("BO", "Bolivia"), "아이티": ("HT", "Haiti"),
    "온두라스": ("HN", "Honduras"), "과테말라": ("GT", "Guatemala"),
    "엘살바도르": ("SV", "El Salvador"), "니카라과": ("NI", "Nicaragua"),
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
        return " ".join(extract_text(tmp.name).split())
    except Exception as e:  # noqa: BLE001
        log.error(f"[nctc] PDF parse failed: {e}")
        return ""
    finally:
        os.unlink(tmp.name)


def _parse_daily_pdf(text: str) -> dict:
    """일일 테러동향 PDF 텍스트 → 구조화 데이터. 사건 연도는 PDF 자체 발행연도를 쓴다."""
    result = {"date": "", "stats": {}, "incidents": []}

    # PDF 발행일: '26. 4. 10  → 사건 연도의 기준
    pub_year = datetime.now().year
    pub_month = None
    dm = re.search(r"['΄'’]\s*(\d{2})\.\s*(\d{1,2})\.\s*(\d{1,2})", text)
    if dm:
        pub_year = int(f"20{dm.group(1)}")
        pub_month = int(dm.group(2))
        result["date"] = f"{pub_year}-{dm.group(2).zfill(2)}-{dm.group(3).zfill(2)}"

    # 지역별 통계
    stats_match = re.search(
        r"총계\(건\)\s*유\s*럽\s*미\s*주\s*아\s*태\s*중\s*동\s*아프리카\s*"
        r"(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])\s+(\d+|[-])",
        text,
    )
    if stats_match:
        def _v(s):
            return int(s) if s not in ["-", ""] else 0
        result["stats"] = {
            "total": _v(stats_match.group(1)), "europe": _v(stats_match.group(2)),
            "americas": _v(stats_match.group(3)), "asia_pacific": _v(stats_match.group(4)),
            "middle_east": _v(stats_match.group(5)), "africa": _v(stats_match.group(6)),
        }

    # 주요 사건: ○ M.D 국가 설명(사망 N[명], 부상/납치 N[명])
    pattern = r"○\s*(\d{1,2})\.(\d{1,2})\.?\s+(\S+)\s+(.+?)(?:\(사망\s*(\d+)명?(?:,\s*(?:부상|납치)\s*(\d+)명?)?\))"
    for m in re.finditer(pattern, text):
        mon = int(m.group(1))
        day = int(m.group(2))
        # 연도 롤오버: 발행월보다 사건월이 크면 전년도 (예: 1월 발행 PDF의 12월 사건)
        yr = pub_year - 1 if (pub_month and mon > pub_month) else pub_year
        incident_date = f"{yr}-{str(mon).zfill(2)}-{str(day).zfill(2)}"

        country_ko = m.group(3).strip(",.()[]:;·")
        # 모지바케(깨진 추출)나 빈 토큰은 스킵, 그 외엔 매핑 없어도 보존한다.
        if not country_ko or not re.search(r"[가-힣]", country_ko):
            continue
        iso, country_en = _KO_COUNTRY.get(country_ko, ("", country_ko))

        desc_ko = m.group(4).strip()
        desc_en = translate_korean_description(desc_ko)
        result["incidents"].append({
            "source": "nctc",
            "date": incident_date,
            "country": country_en,
            "country_code": iso,
            "country_ko": country_ko,
            "description": desc_en or desc_ko,
            "description_ko": desc_ko,
            "fatalities": int(m.group(5)),
            "wounded": int(m.group(6)) if m.group(6) else 0,
        })

    if "해당 없음" in text or "해당없음" in text:
        result["no_incidents"] = True
    return result


def _article_no(href: str) -> int:
    m = re.search(r"articleNo=(\d+)", href)
    return int(m.group(1)) if m else 0


def fetch_nctc_daily(limit: int = 5) -> list[dict]:
    """NCTC 일일 테러동향 최신 `limit`개 글을 파싱해 사건 목록을 반환한다. 하루 한 번(17:00
    KST)만 호출되도록 스케줄에서 게이트하며, limit>1 로 놓친 날을 백필한다(INSERT OR IGNORE)."""
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
        if not isinstance(table, Tag):
            return []

        # 다운로드 링크(글번호 순) 수집
        links: list[tuple[int, str]] = []
        for row in table.find_all("tr"):
            for a in row.find_all("a", href=True):
                if "mode=download" in a["href"]:
                    links.append((_article_no(a["href"]), NCTC_DAILY_URL + a["href"]))
                    break
        if not links:
            return []

        all_incidents = []
        unmapped: set[str] = set()
        for art_no, link in sorted(links, reverse=True):
            log.info(f"  [nctc] downloading article {art_no}...")
            text = _download_pdf(link)
            if not text:
                continue
            for inc in _parse_daily_pdf(text).get("incidents", []):
                # 매핑 안 된 토큰은 대개 단체명(예: 알샤바브)·파편이라 버리고 로그만 남긴다.
                if not inc["country_code"]:
                    unmapped.add(inc["country_ko"])
                    continue
                all_incidents.append(inc)

        if unmapped:
            log.info(f"  [nctc] unmapped tokens (dropped, extend _KO_COUNTRY if a real country): {sorted(unmapped)}")
        log.info(f"  [nctc] {len(all_incidents)} incidents from {len(links)} article(s)")
        return all_incidents

    except Exception as e:  # noqa: BLE001
        log.error(f"[nctc] fetch failed: {e}")
        return []
