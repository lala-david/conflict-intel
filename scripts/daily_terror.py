"""
Terror Intelligence Daily Report — 데일리 인텔리전스 자동 생성

사용법:
    python scripts/daily_terror.py              # 오늘 날짜
    python scripts/daily_terror.py 2026-03-27   # 특정 날짜
"""
import os
import sys
import io
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
load_dotenv(ROOT / ".env")

from sources import collect_all
from mapper import TerrorMapper
from event_linker import link_events
from threat_scorer import run_analysis
from database import save_events, save_daily_stats
from config import ANALYSIS_MODEL, TEMPERATURE, MAX_TOKENS, REPORTS_DIR

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
mapper = TerrorMapper()


def generate_with_retry(fn, *args, max_retries=2):
    """#11: LLM 응답이 빈 경우 재시도"""
    result = ""
    for attempt in range(max_retries + 1):
        result = fn(*args)
        if result and len(result.strip()) > 100:
            return result
        print(f"   WARNING: empty response (attempt {attempt + 1}/{max_retries + 1}), retrying...")
    return result or "Report generation failed."


def get_week_number(date: datetime) -> int:
    return date.isocalendar()[1]


def get_report_dir(date: datetime) -> Path:
    year = date.strftime("%Y")
    month = date.strftime("%m")
    week = f"week-{get_week_number(date):02d}"
    d = ROOT / REPORTS_DIR / year / month / week
    d.mkdir(parents=True, exist_ok=True)
    return d


def compute_statistics(data: dict) -> str:
    """수집 데이터에서 통계 대시보드 생성"""
    lines = ["## STATISTICS DASHBOARD\n"]

    # ACLED 통계
    acled = data.get("acled", [])
    if acled:
        total_fatalities = sum(e.get("fatalities", 0) for e in acled)
        # 국가별 사건 수
        country_counts = {}
        for e in acled:
            c = e.get("country", "Unknown")
            country_counts[c] = country_counts.get(c, 0) + 1
        top_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # 공격 유형별
        type_counts = {}
        for e in acled:
            t = e.get("sub_event_type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:8]

        # 조직별
        actor_counts = {}
        for e in acled:
            a = e.get("actor1", "").strip()
            if a and a != "Unknown":
                actor_counts[a] = actor_counts.get(a, 0) + 1
        top_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # 좌표 데이터 (사상자 있는 사건 우선)
        geo_events = [e for e in acled if e.get("latitude") and e.get("longitude")]
        geo_events.sort(key=lambda x: x.get("fatalities", 0), reverse=True)

        lines.append(f"### ACLED Summary (last 14 days)")
        lines.append(f"- Total incidents: {len(acled)}")
        lines.append(f"- Total fatalities: {total_fatalities}")
        lines.append(f"\n**By Country:**")
        for c, n in top_countries:
            lines.append(f"  - {c}: {n} incidents")
        lines.append(f"\n**By Attack Type:**")
        for t, n in top_types:
            lines.append(f"  - {t}: {n} incidents")
        lines.append(f"\n**By Actor (top 10):**")
        for a, n in top_actors:
            lines.append(f"  - {a}: {n} incidents")

        if geo_events:
            lines.append(f"\n**Georeferenced Incidents (top by fatalities):**")
            for e in geo_events[:8]:
                lines.append(
                    f"  - [{e.get('latitude', '')}, {e.get('longitude', '')}] {e.get('country', 'Unknown')}, {e.get('location', 'Unknown')} | "
                    f"{e.get('sub_event_type', 'Unknown')} | {e.get('actor1', 'Unknown')} | "
                    f"Fatalities: {e.get('fatalities', 0)} | {e.get('date', '')}"
                )

    # GDELT 통계
    gdelt = data.get("gdelt", [])
    if gdelt:
        gdelt_countries = {}
        for e in gdelt:
            c = e.get("country_code", "??")
            gdelt_countries[c] = gdelt_countries.get(c, 0) + 1
        top_gdelt = sorted(gdelt_countries.items(), key=lambda x: x[1], reverse=True)[:10]

        total_mentions = sum(e.get("num_mentions", 0) for e in gdelt)
        avg_tone_all = sum(e.get("avg_tone", 0) for e in gdelt) / len(gdelt) if gdelt else 0

        lines.append(f"\n### GDELT Summary")
        lines.append(f"- Total events: {len(gdelt)}")
        lines.append(f"- Total mentions across media: {total_mentions:,}")
        lines.append(f"- Average media tone: {avg_tone_all:.2f} (negative = hostile)")
        lines.append(f"\n**By Country Code:**")
        for c, n in top_gdelt:
            lines.append(f"  - {c}: {n} events")

        # GDELT 좌표 데이터
        geo_gdelt = [e for e in gdelt if e.get("latitude") and e.get("longitude")]
        if geo_gdelt:
            lines.append(f"\n**Georeferenced Events (top by mentions):**")
            for e in geo_gdelt[:5]:
                tone = e.get('avg_tone', 0)
                lines.append(
                    f"  - [{e.get('latitude', '')}, {e.get('longitude', '')}] {e.get('location', 'Unknown')} ({e.get('country_code', '??')}) | "
                    f"Code: {e.get('event_code', '')} | Mentions: {e.get('num_mentions', 0)} | "
                    f"Tone: {tone:.1f}"
                )

    # News 통계
    news = data.get("google_news", [])
    expert = data.get("expert_rss", [])
    if news or expert:
        lines.append(f"\n### Media Coverage")
        lines.append(f"- Google News articles: {len(news)}")
        lines.append(f"- Expert analyses: {len(expert)}")
        if expert:
            feed_counts = {}
            for a in expert:
                f = a.get("feed_name", "Unknown")
                feed_counts[f] = feed_counts.get(f, 0) + 1
            lines.append("**By Source:**")
            for f, n in sorted(feed_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  - {f}: {n} articles")

    # Sanctions 통계
    sanctions = data.get("sanctions", [])
    ofac = data.get("ofac", [])
    if sanctions or ofac:
        lines.append(f"\n### Sanctions")
        lines.append(f"- OpenSanctions entities: {len(sanctions)}")
        lines.append(f"- OFAC recent actions: {len(ofac)}")

    return "\n".join(lines)


def cluster_news(articles: list[dict]) -> list[dict]:
    """#2: 같은 사건 뉴스를 클러스터링하여 대표 기사 + 소스 수로 압축"""
    from difflib import SequenceMatcher

    clusters = []
    used = set()

    for i, article in enumerate(articles):
        if i in used:
            continue

        cluster = [article]
        used.add(i)
        title_i = article.get("title", "").lower()

        for j in range(i + 1, len(articles)):
            if j in used:
                continue
            title_j = articles[j].get("title", "").lower()
            if SequenceMatcher(None, title_i, title_j).ratio() > 0.5:
                cluster.append(articles[j])
                used.add(j)

        # 대표 기사 = 가장 긴 요약을 가진 것
        representative = max(cluster, key=lambda x: len(x.get("summary", "")))
        clusters.append({
            **representative,
            "cluster_size": len(cluster),
            "sources": list(set(a.get("source", "") for a in cluster)),
        })

    return clusters


def build_raw_context(data: dict) -> str:
    """수집 데이터를 LLM 컨텍스트로 변환"""
    sections = []

    # 통계 대시보드를 맨 앞에 배치
    stats = compute_statistics(data)
    if stats:
        sections.append(stats)

    if data.get("gdelt"):
        sections.append(f"\n## GDELT Events (Top 10 of {len(data['gdelt'])})")
        for e in data["gdelt"][:10]:
            enr = e.get("_enrichment", {})
            extras = []
            if enr.get("conflict_zone"):
                z = enr["conflict_zone"]
                extras.append(f"Zone: {z['zone_name']}({z['intensity']})")
            if enr.get("actor1_org"):
                o = enr["actor1_org"]
                extras.append(f"Org: {o['matched_name']}")
            extra_str = " | " + " | ".join(extras) if extras else ""

            tone = e.get('avg_tone', 0)
            sections.append(
                f"- Date:{e.get('date', '')} | Code:{e.get('event_code', '')} | {e.get('actor1', 'Unknown')} vs {e.get('actor2', 'Unknown')} | "
                f"{e.get('location', 'Unknown')}({e.get('country_code', '??')}) [{e.get('latitude', '')},{e.get('longitude', '')}] | "
                f"Mentions:{e.get('num_mentions', 0)} Tone:{tone:.1f}{extra_str}\n"
                f"  URL: {e.get('source_url', '')}"
            )

    if data.get("acled"):
        sections.append(f"\n## ACLED Incidents (Top 15 of {len(data['acled'])})")
        for e in data["acled"][:15]:
            enr = e.get("_enrichment", {})
            extras = []
            if enr.get("conflict_zone"):
                extras.append(f"Zone: {enr['conflict_zone']['zone_name']}")
            if enr.get("actor1_org"):
                extras.append(f"Org: {enr['actor1_org']['matched_name']}")
            if enr.get("attack_classification"):
                extras.append(enr["attack_classification"]["category_name"])
            extra_str = " | " + " | ".join(extras) if extras else ""

            notes = e.get('notes', '')
            sections.append(
                f"- {e.get('date', '')} | {e.get('sub_event_type', 'Unknown')} | {e.get('country', 'Unknown')}({e.get('admin1', '')},{e.get('location', 'Unknown')}) "
                f"[{e.get('latitude', '')},{e.get('longitude', '')}] | "
                f"{e.get('actor1', 'Unknown')} vs {e.get('actor2', 'Unknown')} | Fatal:{e.get('fatalities', 0)}{extra_str}\n"
                f"  {notes[:150]}"
            )

    # 이벤트 클러스터 (교차 매칭 결과)
    if data.get("event_clusters"):
        clusters = data["event_clusters"]
        sections.append(f"\n## EVENT CLUSTERS — {len(clusters)} events")
        for c in clusters[:10]:
            countries = ", ".join(c.get("countries", []))
            summary = c.get('summary', '')
            sections.append(
                f"- [Score:{c.get('importance_score',0)} News:{c.get('cluster_size',1)} GDELT:{c.get('gdelt_count',0)} RSS:{c.get('rss_count',0)}] "
                f"{c.get('title', 'Untitled')}\n  {c.get('url', '')}\n  Countries: {countries} | {summary[:120]}"
            )

    # 클러스터에 안 묶인 RSS
    if data.get("expert_rss"):
        matched_rss_titles = set()
        for c in data.get("event_clusters", []):
            matched_rss_titles.update(c.get("matched_rss", []))

        unmatched = [a for a in data["expert_rss"] if a.get("title", "") not in matched_rss_titles]
        if unmatched:
            sections.append(f"\n## Expert Analysis (Standalone)")
            for a in unmatched[:5]:
                a_summary = a.get('summary', '')
                sections.append(f"- [{a.get('feed_name', 'Unknown')}] {a.get('title', 'Untitled')}\n  {a.get('url', '')}\n  {a_summary[:120]}")

    if data.get("sanctions"):
        sections.append(f"\n## Sanctions Updates ({len(data['sanctions'])} entities)")
        for s in data["sanctions"][:10]:
            sections.append(f"- [{s.get('datasets', '')}] {s.get('name', 'Unknown')} ({s.get('schema', '')})")

    if data.get("ofac"):
        sections.append(f"\n## OFAC Recent Actions ({len(data['ofac'])})")
        for o in data["ofac"][:5]:
            sections.append(f"- {o.get('title', 'Untitled')} | {o.get('url', '')}")

    # ─── 심층 분석 결과 (#1 위협수준, #2 전일비교, #4 조직, #5 핫스팟) ───
    analysis = data.get("_analysis", {})

    # #1: 위협 수준 (자동 계산)
    threat = analysis.get("threat_levels", {})
    if threat:
        sections.append("\n## COMPUTED THREAT LEVELS (Data-Driven)")
        sections.append("| Country | Score | Level | Events | Fatalities | News |")
        sections.append("|---------|-------|-------|--------|------------|------|")
        for country, t in list(threat.items())[:10]:
            sections.append(
                f"| {country} | {t['score']}/10 | {t['label']} | {t['events']} | {t['fatalities']} | {t['news_mentions']} |"
            )

    # #2: 전일 대비
    diff = analysis.get("daily_diff", {})
    if diff.get("diff"):
        sections.append("\n## DAILY COMPARISON (vs Previous)")
        prev = diff["previous"]
        sections.append(f"Previous date: {prev['date']}")
        sections.append(f"GDELT: {diff['trend_text']['gdelt']}")
        sections.append(f"Fatalities: {diff['trend_text']['fatalities']}")

    # #4: 조직별 활동
    orgs = analysis.get("org_tracker", [])
    if orgs:
        sections.append("\n## ORGANIZATION ACTIVITY TRACKER")
        sections.append("| Organization | Designation | Events Today | Fatalities | Countries | Attack Types |")
        sections.append("|-------------|-------------|-------------|------------|-----------|-------------|")
        for o in orgs[:7]:
            name = o["name"][:30].replace("|", "/").replace('"', "'")
            countries = ", ".join(str(c) for c in o["countries"][:3])
            attacks = ", ".join(str(a) for a in o["attack_types"][:3])
            sections.append(
                f"| {name} | {o['designation']} | {o['events_today']} | {o['fatalities_today']} | {countries} | {attacks} |"
            )

    # #5: 핫스팟
    hotspots = analysis.get("hotspots", [])
    if hotspots:
        sections.append("\n## GEOGRAPHIC HOTSPOTS (Density Analysis)")
        for i, h in enumerate(hotspots[:5]):
            countries = ", ".join(str(c) for c in h["countries"])
            actors = ", ".join(str(a).replace('"', "'")[:25] for a in h["actors"][:3])
            sections.append(
                f"- HOTSPOT #{i+1}: [{h['center'][0]}, {h['center'][1]}] | "
                f"Events: {h['events']} | Fatalities: {h['fatalities']} | "
                f"Countries: {countries} | Actors: {actors}"
            )

    return "\n".join(sections)


SYSTEM_PROMPT = """You are a senior counterterrorism intelligence analyst producing a daily intelligence brief.

ABSOLUTE RULES:
1. Use ONLY facts from the provided data. NEVER fabricate events, casualties, groups, or locations.
2. Every claim MUST reference its source. Use markdown links: [text](URL)
3. If a section has no data, write "No significant activity reported" (EN) or "보고된 주요 활동 없음" (KO).
4. Use estimative language with confidence levels:
   - "We assess with HIGH CONFIDENCE" = multiple corroborating sources
   - "We assess with MODERATE CONFIDENCE" = credible but not fully verified
   - "We assess with LOW CONFIDENCE" = limited or fragmentary reporting
5. BLUF (Bottom Line Up Front): Lead with the most critical assessment.
6. For Korean: 문장은 "~이다", "~하다", "~한다", "~으로 판단된다", "~으로 평가된다"로 종결한다.
7. NEVER speculate beyond what the data supports.
8. Source links MUST use actual URLs from the provided data. NEVER use '#' placeholder links like [text](#). Every incident in the report MUST include [description](actual-url-from-data). This is a CRITICAL integrity requirement.
9. Use the ACTUAL event date from the data (the Date field), NOT the report generation date. If GDELT shows Date:2026-03-29, report that date, not today's date."""


def generate_report_ko(data: dict, date: datetime) -> str:
    """LLM으로 한국어 인텔리전스 리포트 생성"""
    raw = build_raw_context(data)

    acled_count = len(data.get("acled", []))
    acled_fatalities = sum(e.get("fatalities", 0) for e in data.get("acled", []))
    gdelt_count = len(data.get("gdelt", []))

    stats_block = (
        f"- ACLED: {acled_count}건 (사망 {acled_fatalities}) | GDELT: {gdelt_count}건 | "
        f"뉴스: {len(data.get('google_news', []))}건 | 전문가: {len(data.get('expert_rss', []))}건 | "
        f"제재: {len(data.get('sanctions', []))}건"
    )

    weekday = ["월", "화", "수", "목", "금", "토", "일"][date.weekday()]
    date_display = f"{date.strftime('%Y년 %m월 %d일')} ({weekday})"
    rules = (
        "1. BLUF 원칙: 가장 중요한 판단을 최상단에 배치\n"
        "2. 각 항목 3~4줄 분석문. ~이다/~하다/~한다/~으로 판단된다 로 종결\n"
        "3. 신뢰도 등급 명시 (높은 확신/중간 확신/낮은 확신). 출처는 마크다운 링크\n"
        "4. 데이터에 없는 사건 절대 작성 금지. 데이터 없는 섹션은 '보고된 주요 활동 없음'\n"
        "5. 출처 링크는 수집 데이터에 포함된 실제 URL을 사용한다. '#' 플레이스홀더를 절대 사용하지 않는다."
    )

    template = (
        "## BLUF (Bottom Line Up Front)\n"
        "> (핵심 위협 판단 2~3문장)\n\n---\n\n"
        "## 1. 위협 수준 평가\n| 지역 | 수준 | 근거 |\n|------|------|------|\n\n"
        "## 2. 통계 대시보드\n### 사건 개요\n| 지표 | 수치 |\n|------|------|\n\n"
        "### 공격 유형 분포\n| 유형 | 건수 |\n|------|------|\n\n"
        "## 3. 주요 사건 상세\n| 날짜 | 위치 | 좌표 | 유형 | 조직/행위자 | 사상자 | 출처 |\n"
        "|------|------|------|------|-------------|--------|------|\n\n"
        "## 4. 지역별 분석\n### 중동/북아프리카\n### 사하라 이남 아프리카\n### 남아시아/동남아시아\n### 유럽/북미\n### 기타\n\n"
        "## 5. 조직 동향\n## 6. 제재/정책 변동\n## 7. 전문가 분석 요약\n## 8. 트렌드 & 패턴\n"
        "## 9. 실무 시사점\n> (번호 나열)"
    )

    prompt = f"""아래 수집 데이터를 분석하여 한국어 테러 인텔리전스 데일리 브리프를 작성하라.

## 날짜: {date_display}
## 수집 통계: {stats_block}
## 수집 데이터:
{raw}

## 작성 규칙:
{rules}

## 출력 형식:

# Terror Intelligence Brief — {date_display}

> CLASSIFICATION: UNCLASSIFIED // FOR OFFICIAL USE ONLY

---

{template}

---
*Sources: ACLED, GDELT, Google News, LWJ, Soufan, CTC, Jamestown, OpenSanctions, OFAC*
*Generated: {date_display} | Model: {ANALYSIS_MODEL} | UNCLASSIFIED*
"""

    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_TOKENS,
    )

    content = response.choices[0].message.content or ""
    usage = response.usage
    if usage:
        print(f"   tokens: in={usage.prompt_tokens:,} out={usage.completion_tokens:,} total={usage.total_tokens:,}")
    return content


def translate_to_en(ko_report: str, date: datetime) -> str:
    """한국어 보고서를 영문으로 번역 (컨텍스트 재전송 없이)"""
    weekday = date.strftime("%A")
    date_display = f"{date.strftime('%Y-%m-%d')} ({weekday})"

    emdash = "\u2014"
    arrow = "\u2192"
    translate_rules = (
        "- Preserve all markdown formatting, tables, links, and structure exactly\n"
        f"- Replace Korean date header with: Terror Intelligence Brief {emdash} {date_display}\n"
        "- Use professional intelligence language (HIGH/MODERATE/LOW CONFIDENCE)\n"
        f'- Replace "높은 확신" {arrow} "HIGH CONFIDENCE", "중간 확신" {arrow} "MODERATE CONFIDENCE", "낮은 확신" {arrow} "LOW CONFIDENCE"\n'
        "- Keep all URLs, coordinates, and numbers unchanged\n"
        "- Replace footer date with English equivalent"
    )
    prompt = f"""Translate the following Korean intelligence brief into English.

Rules:
{translate_rules}

Korean report:
{ko_report}"""

    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional translator specializing in intelligence and security documents. Translate accurately without adding or removing information."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_completion_tokens=MAX_TOKENS,
    )

    content = response.choices[0].message.content or ""
    usage = response.usage
    if usage:
        print(f"   tokens: in={usage.prompt_tokens:,} out={usage.completion_tokens:,} total={usage.total_tokens:,}")
    return content


def update_week_readme(report_dir: Path, date: datetime):
    readme = report_dir / "README.md"
    week_num = get_week_number(date)
    year = date.strftime("%Y")
    month = date.strftime("%m월")

    ko_reports = sorted(report_dir.glob("*_ko.md"))
    rows = []
    for r in ko_reports:
        date_part = r.stem.replace("_ko", "")
        en_file = r.parent / f"{date_part}_en.md"
        en_link = f" / [EN]({en_file.name})" if en_file.exists() else ""
        rows.append(f"| {date_part} | [KO]({r.name}){en_link} |")

    table = "\n".join(rows) if rows else "| - | - |"
    content = f"""# Week {week_num} — {year}년 {month}

| Date | Report |
|------|--------|
{table}
"""
    readme.write_text(content, encoding="utf-8")


def update_month_readme(report_dir: Path, date: datetime):
    month_dir = report_dir.parent
    readme = month_dir / "README.md"
    year = date.strftime("%Y")
    month = date.strftime("%m월")

    weeks = sorted(d for d in month_dir.iterdir() if d.is_dir() and d.name.startswith("week-"))
    rows = []
    for w in weeks:
        count = len(list(w.glob("*_ko.md")))
        rows.append(f"| [{w.name}]({w.name}/README.md) | {count} |")
    table = "\n".join(rows) if rows else "| - | 0 |"

    content = f"""# {year}년 {month} Terror Intelligence

| Week | Reports |
|------|---------|
{table}
"""
    readme.write_text(content, encoding="utf-8")


def main():
    if len(sys.argv) > 1:
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    else:
        target_date = datetime.now()

    date_str = target_date.strftime("%Y-%m-%d")
    print(f"\n{'='*55}")
    print(f"  Terror Intelligence Brief — {date_str}")
    print(f"{'='*55}\n")

    # 1. 수집
    data = collect_all(target_date)
    total = sum(len(v) for v in data.values() if isinstance(v, list))
    if total == 0:
        print("No data collected.")
        return

    # 2. 기반 데이터 매핑
    print("\n  Enriching with foundation data...")
    data = mapper.enrich_all(data)
    stats = data.get("_enrichment_stats", {})
    print(f"   enriched: {stats.get('total_enriched', 0)} events")
    print(f"   org matches: {stats.get('org_matches', 0)}")
    print(f"   country matches: {stats.get('country_matches', 0)}")
    print(f"   zone matches: {stats.get('zone_matches', 0)}")

    # 3. 이벤트 링킹 (멀티소스 교차 매칭)
    print("\n  Linking events across sources...")
    data = link_events(data)
    cl_stats = data.get("_cluster_stats", {})
    print(f"   clusters: {cl_stats.get('total_clusters', 0)} (from {cl_stats.get('total_articles', 0)} articles)")
    print(f"   GDELT linked: {cl_stats.get('gdelt_linked', 0)}")
    print(f"   RSS linked: {cl_stats.get('rss_linked', 0)}")
    if cl_stats.get("top_event"):
        print(f"   TOP: {cl_stats['top_event'][:70]} (score: {cl_stats['top_event_score']})")

    # 4. 심층 분석 (위협 수준, 전일 비교, 조직 트래커, 핫스팟)
    print("\n  Running deep analysis...")
    analysis = run_analysis(data, date_str)
    data["_analysis"] = analysis

    threat_top = list(analysis["threat_levels"].items())[:5]
    threat_str = ", ".join(f"{c}={t['label']}({t['score']})" for c, t in threat_top)
    print(f"   Threat levels: {threat_str}")

    diff = analysis["daily_diff"]
    if diff.get("diff"):
        print(f"   vs previous: GDELT {diff['trend_text']['gdelt']}, fatalities {diff['trend_text']['fatalities']}")

    orgs = analysis["org_tracker"]
    if orgs:
        print(f"   Active orgs: {len(orgs)} ({', '.join(o['name'][:20] for o in orgs[:3])})")

    spots = analysis["hotspots"]
    if spots:
        spots_str = ", ".join(str(h["countries"]) for h in spots[:3])
        print(f"   Hotspots: {len(spots)} ({spots_str})")

    # 5. 리포트 디렉토리
    report_dir = get_report_dir(target_date)

    # 6. DB 저장
    print("\n  Saving to database...")
    save_events(data, date_str)
    save_daily_stats(date_str, data, stats)
    print("   -> terror.db updated")

    # 7. 한글 리포트 (#11 재시도)
    print("\n  [KO] Generating...")
    ko = generate_with_retry(generate_report_ko, data, target_date)
    if ko.startswith("Report generation failed"):
        print(f"   ERROR: KO report generation failed.")
        sys.exit(1)
    ko_path = report_dir / f"{date_str}_ko.md"
    ko_path.write_text(ko, encoding="utf-8")
    print(f"   -> {ko_path.relative_to(ROOT)} ({len(ko):,} chars)")

    # 8. 영문 리포트 (KO 번역)
    print("\n  [EN] Translating from KO...")
    en = generate_with_retry(translate_to_en, ko, target_date)
    if en.startswith("Report generation failed"):
        print(f"   ERROR: EN report generation failed.")
        sys.exit(1)
    en_path = report_dir / f"{date_str}_en.md"
    en_path.write_text(en, encoding="utf-8")
    print(f"   -> {en_path.relative_to(ROOT)} ({len(en):,} chars)")

    # 7. README
    update_week_readme(report_dir, target_date)
    update_month_readme(report_dir, target_date)

    # 8. Raw JSON
    raw_path = report_dir / f"{date_str}_raw.json"
    raw_out = {k: v for k, v in data.items() if k != "collected_at" and k != "_enrichment_stats"}
    raw_out["meta"] = {"collected_at": data.get("collected_at", ""), "total": total, "enrichment": stats}
    raw_path.write_text(json.dumps(raw_out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"\n{'='*55}")
    print(f"  DONE | KO: {ko_path.name} / EN: {en_path.name}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
