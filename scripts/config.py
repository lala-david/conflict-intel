"""설정"""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UCDP_TOKEN = os.getenv("UCDP_TOKEN", "")

# LLM (BLUF 요약 생성에만 사용)
ANALYSIS_MODEL = "gpt-5.4-mini"

# 로컬 LLM (사내 Ollama, OpenAI 호환) — 교차소스 중복제거 판단에 사용.
# 비용 0 + 데이터 로컬. 도달 불가 시 dedup는 휴리스틱만으로 폴백.
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://192.168.150.225:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen3:8b")

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
GDELT_CONFLICT_CODES = [
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
    "GNET": "https://gnet-research.org/feed/",
    "Militant Wire": "https://www.militantwire.com/feed",
    "Hedayah": "https://hedayahcenter.org/feed/",
    "Homeland Security Today": "https://www.hstoday.us/feed/",
    # Tier 2 — 군사/작전 (키워드 필터 면제)
    "ISW": "https://www.iswresearch.org/feeds/posts/default",
    "AFRICOM": "https://www.africom.mil/syndication-feed/rss/press-releases",
    "CENTCOM": "https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=808&max=20",
    "Pentagon": "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=10&ContentType=1&Site=945",
    "The War Zone": "https://www.twz.com/feed",
    "Military Times": "https://www.militarytimes.com/arc/outboundfeeds/rss/?outputType=xml",
    "War on the Rocks": "https://warontherocks.com/feed/",
    # Tier 3 — 지역 분쟁 뉴스 (사건 보도 중심)
    "Dawn Pakistan": "https://www.dawn.com/feeds/home",
    "Premium Times NG": "https://www.premiumtimesng.com/feed",
    "Daily Star BD": "https://www.thedailystar.net/rss.xml",
    "Arab News": "https://www.arabnews.com/rss/main",
    "France 24": "https://www.france24.com/en/rss",
    # Tier 4 — 분석/국제뉴스
    "Al-Monitor": "https://www.al-monitor.com/rss",
    "Middle East Eye": "https://www.middleeasteye.net/rss",
    "ISS Africa": "https://issafrica.org/feed",
    "RUSI": "https://www.rusi.org/rss.xml",
    "MEMRI": "https://www.memri.org/rss/all/blog",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    # Tier 5 — OSINT / 싱크탱크 / 인권
    "Bellingcat": "https://www.bellingcat.com/feed/",
    "HRW": "https://www.hrw.org/rss/news",
    "Oryx Blog": "https://www.oryxspioenkop.com/feeds/posts/default",
    "ReliefWeb": "https://reliefweb.int/updates/rss.xml",
    "Atlantic Council": "https://www.atlanticcouncil.org/feed/",
    "Global Initiative": "https://globalinitiative.net/feed/",
    # Tier 6 — 일반 뉴스 (키워드 필터 적용)
    "CEP": "https://www.counterextremism.com/rss.xml",
    "Fox News World": "https://feeds.foxnews.com/foxnews/world",
    "CBS News": "https://www.cbsnews.com/latest/rss/main",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "ABC News International": "https://abcnews.go.com/abcnews/internationalheadlines",
    "UN Peace and Security": "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml",
    # Tier 7 — 확장: 검증된 지역 분쟁 뉴스 + 싱크탱크 (서브에이전트 조사로 확인)
    "AFP": "https://www.afp.com/en/rss.xml",
    "DW News": "https://rss.dw.com/rdf/rss-en-all",
    "RFE/RL": "https://www.rferl.org/api/zrqiteuuir",
    "VOA News": "https://www.voanews.com/api/epiqq",
    "Kyiv Independent": "https://kyivindependent.com/news-archive/rss/",
    "Ukrainska Pravda": "https://www.pravda.com.ua/eng/rss/",
    "Meduza": "https://meduza.io/rss/en/all",
    "Moscow Times": "https://www.themoscowtimes.com/rss/news",
    "Haaretz": "https://www.haaretz.com/srv/all-headlines-rss",
    "InSight Crime": "https://insightcrime.org/feed/",
    "HumAngle": "https://humangle.org/feed/",
    "CSIS": "https://www.csis.org/rss.xml",
    "SIPRI": "https://www.sipri.org/rss/combined.xml",
    "ECFR": "https://ecfr.eu/feed/",
    "ICCT": "https://icct.nl/rss.xml",
}

# Tier 1-2는 전문가 소스로 키워드 필터 면제
# 신규: Bellingcat, HRW, Oryx, ReliefWeb, Atlantic Council, Global Initiative도 전문 소스로 면제
RSS_TIER1_FEEDS = {
    # 테러/분쟁 전문
    "Long War Journal", "Soufan Center", "CTC Sentinel", "Jamestown Foundation",
    "ICG CrisisWatch", "Defense Post Terror",
    "GNET", "Militant Wire", "Hedayah", "Homeland Security Today",
    # 군사/작전
    "ISW", "AFRICOM", "CENTCOM", "Pentagon", "The War Zone", "Military Times",
    "War on the Rocks",
    # OSINT / 싱크탱크 / 인권 / 유엔
    "Bellingcat",           # OSINT 조사 (러-우, 시리아)
    "HRW",                  # Human Rights Watch (분쟁 중 인권침해)
    "Oryx Blog",            # 러-우 장비 손실 검증
    "ReliefWeb",            # 유엔 인도적 위기
    "Atlantic Council",     # 지정학 싱크탱크
    "Global Initiative",    # 조직범죄/violence 싱크탱크
    "CEP",                  # Counter Extremism Project
    "UN Peace and Security",
    # 확장: 분쟁 특화 (키워드 필터 면제)
    "Kyiv Independent", "Ukrainska Pravda", "Meduza",
    "InSight Crime", "HumAngle", "CSIS", "SIPRI", "ECFR", "ICCT",
}

# Tier 6: 일반 뉴스 (키워드 필터는 적용)
# Fox, CBS, NYT, ABC, Homeland Sec Newswire는 일반 뉴스라 테러 키워드 필터 거침

# Telegram OSINT 공개 채널 (t.me/s/<channel> 스크래핑, 인증 불필요)
# 실제 살아있는(공개 프리뷰 제공) 분쟁/전쟁 모니터 채널만 등록.
TELEGRAM_CHANNELS = [
    # 글로벌 분쟁/안보 속보
    "intelslava", "worldsource24", "Faytuks", "spectatorindex",
    "insiderpaper", "clashreport", "warmonitors", "auroraintel",
    "osinttechnical",
    # 러-우 전황
    "war_monitor", "ukraine_watch", "RVvoenkor",
    "militarysummary", "new_militarycolumnist",
]

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
