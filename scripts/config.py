"""설정"""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACLED_EMAIL = os.getenv("ACLED_EMAIL")
ACLED_PASSWORD = os.getenv("ACLED_PASSWORD")

# LLM
ANALYSIS_MODEL = "gpt-5.4-mini"
TEMPERATURE = 0.12  # 인텔리전스 분석은 더 보수적으로
MAX_TOKENS = 6000

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

# ACLED 테러 프록시 이벤트 타입
ACLED_TERROR_SUBTYPES = [
    "Suicide bomb",
    "Remote explosive/landmine/IED",
    "Attack",
    "Armed assault",
    "Grenade",
    "Chemical weapon",
    "Air/drone strike",
    "Shelling/artillery/missile attack",
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
    # Tier 1 — 테러 전문
    "Long War Journal": "https://www.longwarjournal.org/feed",
    "Soufan Center": "https://thesoufancenter.org/feed/",
    "CTC Sentinel": "https://ctc.westpoint.edu/feed/",
    "Jamestown Foundation": "https://jamestown.org/feed/",
    # Tier 2 — 분쟁/안보
    "ICG CrisisWatch": "https://www.crisisgroup.org/rss.xml",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
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
