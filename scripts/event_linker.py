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


# 주요 도시/지역 → 국가 매핑 (상위 200개)
CITY_TO_COUNTRY = {
    # 중동
    "paris": "FR", "baghdad": "IQ", "mosul": "IQ", "basra": "IQ", "erbil": "IQ",
    "kabul": "AF", "kandahar": "AF", "jalalabad": "AF", "nangarhar": "AF",
    "damascus": "SY", "aleppo": "SY", "idlib": "SY", "raqqa": "SY", "deir ez-zor": "SY",
    "tehran": "IR", "isfahan": "IR", "beirut": "LB", "tripoli": "LB",
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
    "congo": "CD", "kinshasa": "CD", "goma": "CD",
    "cameroon": "CM", "chad": "TD", "sahel": "ML",
    # 남아시아
    "islamabad": "PK", "karachi": "PK", "peshawar": "PK", "quetta": "PK",
    "balochistan": "PK", "waziristan": "PK", "lahore": "PK",
    "mumbai": "IN", "kashmir": "IN", "delhi": "IN", "new delhi": "IN",
    "colombo": "LK", "dhaka": "BD",
    # 동남아
    "manila": "PH", "mindanao": "PH", "marawi": "PH",
    "jakarta": "ID", "myanmar": "MM", "yangon": "MM", "rakhine": "MM",
    "bangkok": "TH",
    # 유럽
    "london": "GB", "manchester": "GB", "brussels": "BE", "berlin": "DE",
    "madrid": "ES", "barcelona": "ES", "rome": "IT", "moscow": "RU",
    "vienna": "AT", "stockholm": "SE", "copenhagen": "DK", "oslo": "NO",
    "amsterdam": "NL", "zurich": "CH", "kyiv": "UA", "ukraine": "UA",
    # 북미/중남미
    "washington": "US", "new york": "US", "bogota": "CO", "colombia": "CO",
    "mexico city": "MX", "caracas": "VE",
    # 국가명 직접 매핑
    "france": "FR", "germany": "DE", "britain": "GB", "uk": "GB", "united kingdom": "GB",
    "israel": "IL", "iran": "IR", "iraq": "IQ", "syria": "SY", "turkey": "TR",
    "afghanistan": "AF", "pakistan": "PK", "india": "IN", "china": "CN",
    "russia": "RU", "saudi arabia": "SA", "egypt": "EG", "lebanon": "LB",
    "nigeria": "NG", "kenya": "KE", "philippines": "PH", "indonesia": "ID",
    "palestine": "PS", "palestinian": "PS", "sri lanka": "LK",
    "united states": "US", "america": "US", "american": "US",
}

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
        if city in text_lower:
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
            if SequenceMatcher(None, title_i, title_j).ratio() > 0.4:
                cluster_articles.append(google_news[j])
                used.add(j)

        # RSS도 매칭 시도
        matched_rss = []
        for rss in expert_rss:
            rss_title = rss.get("title", "").lower()
            if SequenceMatcher(None, title_i, rss_title).ratio() > 0.35:
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

            if country_match and text_sim > 0.15:
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
