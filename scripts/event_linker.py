"""
이벤트 링커 — 멀티소스 교차 매칭 엔진
#1: GDELT ↔ 뉴스 ↔ RSS 사건 연결
#2: 뉴스 볼륨 가중치
#3: GDELT 톤 분석
#4: 뉴스 지명 추출 → 국가 매핑
"""
import re
from difflib import SequenceMatcher
from typing import Optional


# 주요 도시/지역/형용사/별칭 → 국가 매핑
CITY_TO_COUNTRY = {
    # 중동
    "baghdad": "IQ", "mosul": "IQ", "basra": "IQ", "erbil": "IQ",
    "kabul": "AF", "kandahar": "AF", "jalalabad": "AF", "nangarhar": "AF",
    "damascus": "SY", "aleppo": "SY", "idlib": "SY", "raqqa": "SY", "deir ez-zor": "SY",
    "tehran": "IR", "isfahan": "IR", "beirut": "LB", "tripoli lebanon": "LB",
    "riyadh": "SA", "jeddah": "SA", "yemen": "YE", "sanaa": "YE", "aden": "YE",
    "gaza": "PS", "west bank": "PS", "jerusalem": "IL", "tel aviv": "IL",
    "istanbul": "TR", "ankara": "TR", "kuwait": "KW", "doha": "QA", "dubai": "AE",
    "amman": "JO", "cairo": "EG", "sinai": "EG",
    # 아프리카
    "mogadishu": "SO", "somalia": "SO", "borno": "NG", "maiduguri": "NG", "lagos": "NG",
    "abuja": "NG", "nairobi": "KE", "bamako": "ML", "mali": "ML", "niger": "NE",
    "niamey": "NE", "burkina faso": "BF", "ouagadougou": "BF",
    "tripoli": "LY", "benghazi": "LY", "libya": "LY",
    "khartoum": "SD", "sudan": "SD", "darfur": "SD",
    "addis ababa": "ET", "ethiopia": "ET", "tigray": "ET",
    "mozambique": "MZ", "cabo delgado": "MZ",
    "kinshasa": "CD", "goma": "CD", "dr congo": "CD", "drc": "CD", "zaire": "CD",
    "cameroon": "CM", "chad": "TD", "sahel": "ML",
    # 남아시아
    "islamabad": "PK", "karachi": "PK", "peshawar": "PK", "quetta": "PK",
    "balochistan": "PK", "waziristan": "PK", "lahore": "PK",
    "mumbai": "IN", "kashmir": "IN", "delhi": "IN", "new delhi": "IN",
    "colombo": "LK", "dhaka": "BD",
    # 동남아
    "manila": "PH", "mindanao": "PH", "marawi": "PH",
    "jakarta": "ID", "myanmar": "MM", "burma": "MM", "yangon": "MM", "rakhine": "MM",
    "bangkok": "TH",
    # 유럽
    "paris": "FR",
    "london": "GB", "manchester": "GB", "brussels": "BE", "berlin": "DE",
    "madrid": "ES", "barcelona": "ES", "rome": "IT", "moscow": "RU",
    "vienna": "AT", "stockholm": "SE", "copenhagen": "DK", "oslo": "NO",
    "amsterdam": "NL", "zurich": "CH", "kyiv": "UA", "ukraine": "UA",
    "georgia": "GE", "tbilisi": "GE",
    "hungary": "HU", "budapest": "HU",
    "belarus": "BY", "minsk": "BY",
    "poland": "PL", "warsaw": "PL",
    "caucasus": "GE", "south caucasus": "GE",
    # 북미/중남미
    "washington": "US", "new york": "US", "bogota": "CO", "colombia": "CO",
    "mexico city": "MX", "caracas": "VE", "venezuela": "VE",
    "haiti": "HT", "port-au-prince": "HT",
    "brazil": "BR", "brasilia": "BR", "rio de janeiro": "BR", "sao paulo": "BR",
    # 동아시아
    "beijing": "CN", "shanghai": "CN", "hong kong": "CN",
    "seoul": "KR", "south korea": "KR",
    "pyongyang": "KP", "north korea": "KP",
    "tokyo": "JP", "japan": "JP",
    "taipei": "TW", "taiwan": "TW",
    "uzbekistan": "UZ", "tashkent": "UZ",
    "central asia": "KZ",  # 모호하면 카자흐스탄 default
    "kazakhstan": "KZ", "kyrgyzstan": "KG", "tajikistan": "TJ", "turkmenistan": "TM",
    # 국가명 직접 매핑
    "france": "FR", "germany": "DE", "britain": "GB", "uk": "GB", "united kingdom": "GB",
    "israel": "IL", "iran": "IR", "iraq": "IQ", "syria": "SY", "turkey": "TR",
    "afghanistan": "AF", "pakistan": "PK", "india": "IN", "china": "CN",
    "russia": "RU", "saudi arabia": "SA", "egypt": "EG", "lebanon": "LB",
    "nigeria": "NG", "kenya": "KE", "philippines": "PH", "indonesia": "ID",
    "palestine": "PS", "sri lanka": "LK",
    "united states": "US", "america": "US",
    "spain": "ES", "italy": "IT", "netherlands": "NL", "belgium": "BE",
    "switzerland": "CH", "austria": "AT", "sweden": "SE", "norway": "NO",
    "denmark": "DK", "finland": "FI", "ireland": "IE", "portugal": "PT",
    "greece": "GR", "romania": "RO", "bulgaria": "BG", "czech": "CZ",
    "slovakia": "SK", "croatia": "HR", "slovenia": "SI", "albania": "AL",
    # 형용사 (보통 본문에 자주 등장 — 강력한 시그널)
    "iranian": "IR", "iraqi": "IQ", "syrian": "SY", "afghan": "AF", "pakistani": "PK",
    "indian": "IN", "chinese": "CN", "russian": "RU", "ukrainian": "UA",
    "israeli": "IL", "palestinian": "PS", "lebanese": "LB", "saudi": "SA",
    "yemeni": "YE", "egyptian": "EG", "turkish": "TR", "kurdish": "IQ",
    "nigerian": "NG", "kenyan": "KE", "somali": "SO", "ethiopian": "ET",
    "sudanese": "SD", "libyan": "LY", "malian": "ML", "burkinabe": "BF",
    "filipino": "PH", "indonesian": "ID", "myanmar military": "MM", "burmese": "MM",
    "thai": "TH", "vietnamese": "VN", "cambodian": "KH",
    "british": "GB", "french": "FR", "german": "DE", "italian": "IT", "spanish": "ES",
    "georgian": "GE", "hungarian": "HU", "belarusian": "BY", "polish": "PL",
    "american": "US", "mexican": "MX", "colombian": "CO", "venezuelan": "VE", "brazilian": "BR",
    "japanese": "JP", "korean": "KR", "north korean": "KP", "south korean": "KR",
    "prc": "CN", "soviet": "RU",
}

# 뉴스 도메인 → 국가 (도메인 TLD 또는 알려진 매체)
DOMAIN_TO_COUNTRY = {
    "israelnationalnews.com": "IL", "haaretz.com": "IL", "timesofisrael.com": "IL",
    "aljazeera.com": "QA", "dawn.com": "PK", "thedailystar.net": "BD",
    "thehindu.com": "IN", "indiatimes.com": "IN", "ndtv.com": "IN",
    "rferl.org": "RU", "tass.com": "RU", "rt.com": "RU",
    "premiumtimesng.com": "NG", "vanguardngr.com": "NG", "dailytrust.com": "NG",
    "alarabiya.net": "SA", "arabnews.com": "SA",
    "presstv.ir": "IR", "tehrantimes.com": "IR",
    "anadolu agency": "TR", "aa.com.tr": "TR", "trtworld.com": "TR",
    "kyivindependent.com": "UA", "kyivpost.com": "UA",
    "scmp.com": "HK", "globaltimes.cn": "CN",
}


def _domain_country(url: str) -> str:
    """URL의 도메인에서 국가 코드 추출."""
    if not url:
        return ""
    import re as _re
    m = _re.search(r'https?://([^/]+)/', url + "/")
    if not m:
        return ""
    host = m.group(1).lower()
    # 정확 일치
    for d, iso in DOMAIN_TO_COUNTRY.items():
        if d in host:
            return iso
    # 국가 코드 TLD (.kr, .jp, .uk, .pk 등) — 단 .com/.org/.net 제외
    tld = host.rsplit('.', 1)[-1] if '.' in host else ''
    cctld_map = {
        'kr':'KR','jp':'JP','cn':'CN','hk':'HK','tw':'TW','sg':'SG','my':'MY',
        'pk':'PK','in':'IN','bd':'BD','lk':'LK','np':'NP',
        'ru':'RU','ua':'UA','de':'DE','fr':'FR','it':'IT','es':'ES','nl':'NL','pl':'PL',
        'gr':'GR','ie':'IE','pt':'PT','tr':'TR','il':'IL','sa':'SA','ae':'AE',
        'eg':'EG','ng':'NG','ke':'KE','za':'ZA','et':'ET','sd':'SD','ly':'LY','ma':'MA',
        'au':'AU','nz':'NZ','ca':'CA','mx':'MX','br':'BR','ar':'AR','co':'CO','ve':'VE',
    }
    return cctld_map.get(tld, "")

# 톤 해석
TONE_LABELS = {
    (-15, -5): "매우 적대적 (Strongly Hostile)",
    (-5, -2): "부정적 (Negative)",
    (-2, 2): "중립 (Neutral)",
    (2, 5): "긍정적 (Positive)",
    (5, 15): "매우 긍정적 (Strongly Positive)",
}


def extract_countries_from_text(text: str) -> list[str]:
    """#4: 텍스트에서 국가/도시명 추출 → ISO 코드 반환"""
    text_lower = text.lower()
    found = set()
    for city, iso in CITY_TO_COUNTRY.items():
        if len(city) <= 2:
            continue
        if re.search(r'\b' + re.escape(city) + r'\b', text_lower):
            found.add(iso)
    return list(found)


def interpret_tone(avg_tone: float) -> str:
    """#3: GDELT avg_tone → 해석"""
    for (low, high), label in TONE_LABELS.items():
        if low <= avg_tone < high:
            return label
    return "알 수 없음"


def link_events(data: dict) -> dict:
    """
    멀티소스 교차 매칭:
    1. 뉴스를 사건 클러스터로 묶기 (유사도 40%)
    2. GDELT 이벤트와 뉴스 클러스터 연결
    3. RSS 분석과 연결
    4. 볼륨 + 톤 가중치 계산
    """
    google_news = data.get("google_news", [])
    expert_rss = data.get("expert_rss", [])
    gdelt = data.get("gdelt", [])

    # ─── Step 1: 뉴스 클러스터링 (유사도 40%) ───
    clusters = []
    used = set()

    for i, article in enumerate(google_news):
        if i in used:
            continue
        cluster_articles = [article]
        used.add(i)
        title_i = article.get("title", "").lower()

        for j in range(i + 1, len(google_news)):
            if j in used:
                continue
            title_j = google_news[j].get("title", "").lower()
            if SequenceMatcher(None, title_i, title_j).ratio() > 0.5:
                cluster_articles.append(google_news[j])
                used.add(j)

        # RSS도 매칭 시도
        matched_rss = []
        for rss in expert_rss:
            rss_title = rss.get("title", "").lower()
            if SequenceMatcher(None, title_i, rss_title).ratio() > 0.45:
                matched_rss.append(rss)

        # 대표 기사
        representative = max(cluster_articles, key=lambda x: len(x.get("summary", "")))

        # #4: 국가 추출
        all_text = " ".join(a.get("title", "") + " " + a.get("summary", "") for a in cluster_articles)
        countries = extract_countries_from_text(all_text)

        cluster = {
            **representative,
            "cluster_size": len(cluster_articles),
            "articles": [a.get("title", "") for a in cluster_articles],
            "matched_rss": [r.get("title", "") for r in matched_rss],
            "rss_count": len(matched_rss),
            "countries": countries,
            "total_sources": len(cluster_articles) + len(matched_rss),
        }
        clusters.append(cluster)

    # ─── Step 2: GDELT ↔ 클러스터 연결 ───
    for cluster in clusters:
        cluster_title = cluster.get("title", "").lower()
        cluster_countries = set(cluster.get("countries", []))
        linked_gdelt = []

        for event in gdelt:
            # 국가 매칭
            event_country = event.get("country_code", "")
            country_match = event_country in cluster_countries

            # 텍스트 매칭 (actor + source_url)
            event_text = f"{event.get('actor1', '')} {event.get('actor2', '')} {event.get('source_url', '')}".lower()
            text_sim = SequenceMatcher(None, cluster_title[:50], event_text[:50]).ratio()

            if country_match and text_sim > 0.25:
                linked_gdelt.append({
                    "event_code": event.get("event_code", ""),
                    "country": event_country,
                    "location": event.get("location", ""),
                    "coords": [event.get("latitude", ""), event.get("longitude", "")],
                    "mentions": event.get("num_mentions", 0),
                    "tone": event.get("avg_tone", 0),
                    "tone_label": interpret_tone(event.get("avg_tone", 0)),
                })

        cluster["linked_gdelt"] = linked_gdelt
        cluster["gdelt_count"] = len(linked_gdelt)

        # #3: 평균 톤 계산
        if linked_gdelt:
            avg = sum(g["tone"] for g in linked_gdelt) / len(linked_gdelt)
            cluster["avg_media_tone"] = round(avg, 2)
            cluster["tone_label"] = interpret_tone(avg)
        else:
            cluster["avg_media_tone"] = None
            cluster["tone_label"] = None

    # ─── Step 3: 볼륨 가중치로 정렬 ───
    for c in clusters:
        c["importance_score"] = (
            c["cluster_size"] * 3          # 뉴스 수
            + c["rss_count"] * 5           # 전문가 분석은 가중치 높음
            + c["gdelt_count"] * 2         # GDELT 교차 확인
            + len(c["countries"]) * 1      # 다국가 연관
        )

    clusters.sort(key=lambda x: x["importance_score"], reverse=True)

    # ─── Step 4: 결과 저장 ───
    data["event_clusters"] = clusters
    data["_cluster_stats"] = {
        "total_clusters": len(clusters),
        "total_articles": len(google_news),
        "duplicates_removed": len(google_news) - len(clusters),
        "gdelt_linked": sum(1 for c in clusters if c["gdelt_count"] > 0),
        "rss_linked": sum(1 for c in clusters if c["rss_count"] > 0),
        "multi_source": sum(1 for c in clusters if c["total_sources"] > 1),
        "top_event": clusters[0]["title"] if clusters else "",
        "top_event_score": clusters[0]["importance_score"] if clusters else 0,
    }

    return data
