"""설정"""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UCDP_TOKEN = os.getenv("UCDP_TOKEN", "")

# LLM (BLUF 요약 생성에만 사용)
ANALYSIS_MODEL = "gpt-5.4-mini"

# 리포트 경로
REPORTS_DIR = "reports"

# EUROPOL TE-SAT 이념 분류
IDEOLOGY_CATEGORIES = [
    "Jihadist",
    "Right-wing",
    "Left-wing / Anarchist",
    "Ethno-nationalist / Separatist",
    "Single-issue / Other",
]

# GDELT CAMEO 테러 관련 코드
GDELT_TERROR_CODES = [
    "18",   # Assault
    "181",  # Use unconventional violence
    "182",  # Use conventional military force
    "183",  # Use weapons of mass destruction
    "19",   # Fight
    "20",   # Unconventional mass violence
]

# 위협 수준 스케일
THREAT_LEVELS = {
    1: "MINIMAL",
    2: "LOW",
    3: "LOW",
    4: "GUARDED",
    5: "GUARDED",
    6: "ELEVATED",
    7: "ELEVATED",
    8: "HIGH",
    9: "HIGH",
    10: "SEVERE",
}

# RSS 피드
RSS_FEEDS = {
    # Tier 1 — 테러/분쟁 전문 (키워드 필터 면제)
    "Long War Journal": "https://www.longwarjournal.org/feed",
    "Soufan Center": "https://thesoufancenter.org/feed/",
    "CTC Sentinel": "https://ctc.westpoint.edu/feed/",
    "Jamestown Foundation": "https://jamestown.org/feed/",
    "ICG CrisisWatch": "https://www.crisisgroup.org/rss.xml",
    "Defense Post Terror": "https://thedefensepost.com/category/terrorism/feed/",
    # Tier 2 — 군사/작전 (키워드 필터 면제)
    "ISW": "https://www.iswresearch.org/feeds/posts/default",
    "AFRICOM": "https://www.africom.mil/syndication-feed/rss/press-releases",
    "CENTCOM": "https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=808&max=20",
    "Pentagon": "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=10&ContentType=1&Site=945",
    "The War Zone": "https://www.twz.com/feed",
    "Military Times": "https://www.militarytimes.com/arc/outboundfeeds/rss/?outputType=xml",
    # Tier 3 — 지역 분쟁 뉴스 (사건 보도 중심)
    "Dawn Pakistan": "https://www.dawn.com/feeds/home",
    "Premium Times NG": "https://www.premiumtimesng.com/feed",
    "Daily Star BD": "https://www.thedailystar.net/rss.xml",
    "Arab News": "https://www.arabnews.com/rss/main",
    "Anadolu Agency": "https://www.aa.com.tr/en/rss/default?cat=world",
    "France 24": "https://www.france24.com/en/rss",
    # Tier 4 — 분석/국제뉴스
    "Al-Monitor": "https://www.al-monitor.com/rss",
    "Middle East Eye": "https://www.middleeasteye.net/rss",
    "ISS Africa": "https://issafrica.org/feed",
    "RUSI": "https://www.rusi.org/rss.xml",
    "MEMRI": "https://www.memri.org/rss/all/blog",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
}

# Tier 1-2는 전문가 소스로 키워드 필터 면제
RSS_TIER1_FEEDS = {
    "Long War Journal", "Soufan Center", "CTC Sentinel", "Jamestown Foundation",
    "ICG CrisisWatch", "Defense Post Terror",
    "ISW", "AFRICOM", "CENTCOM", "Pentagon", "The War Zone", "Military Times",
}

# Google News 테러 관련 검색 쿼리
GOOGLE_NEWS_QUERIES = [
    "terrorism attack",
    "terrorist plot foiled",
    "ISIS ISIL Islamic State",
    "al-Qaeda",
    "counterterrorism operation",
    "extremist threat",
    "suicide bombing",
    "IED attack",
]
