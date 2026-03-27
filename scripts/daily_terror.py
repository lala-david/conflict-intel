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
from config import ANALYSIS_MODEL, TEMPERATURE, MAX_TOKENS, REPORTS_DIR

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
mapper = TerrorMapper()


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
            for e in geo_events[:15]:
                lines.append(
                    f"  - [{e['latitude']}, {e['longitude']}] {e['country']}, {e['location']} | "
                    f"{e['sub_event_type']} | {e['actor1']} | "
                    f"Fatalities: {e['fatalities']} | {e['date']}"
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
            for e in geo_gdelt[:10]:
                lines.append(
                    f"  - [{e['latitude']}, {e['longitude']}] {e['location']} ({e['country_code']}) | "
                    f"Code: {e['event_code']} | Mentions: {e['num_mentions']} | "
                    f"Tone: {e['avg_tone']:.1f}"
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


def build_raw_context(data: dict) -> str:
    """수집 데이터를 LLM 컨텍스트로 변환"""
    sections = []

    # 통계 대시보드를 맨 앞에 배치
    stats = compute_statistics(data)
    if stats:
        sections.append(stats)

    if data.get("gdelt"):
        sections.append("\n## GDELT Events (Global Conflict/Terror)")
        for e in data["gdelt"][:20]:
            enr = e.get("_enrichment", {})
            zone_info = ""
            if enr.get("conflict_zone"):
                z = enr["conflict_zone"]
                zone_info = f"\n  CONFLICT ZONE: {z['zone_name']} | Intensity: {z['intensity']} | Trend: {z['trend']}"
            country_info = ""
            if enr.get("country"):
                c = enr["country"]
                country_info = f"\n  COUNTRY THREAT: {c['name']} | Level: {c['threat_level']} | Region: {c['region']}"
            org_info = ""
            if enr.get("actor1_org"):
                o = enr["actor1_org"]
                org_info = f"\n  DESIGNATED ORG: {o['matched_name']} ({o['designation']}) [{o['match_type']}]"

            sections.append(
                f"- EventCode: {e['event_code']} | Actor1: {e['actor1']} | Actor2: {e['actor2']}\n"
                f"  Location: {e['location']} ({e['country_code']}) | Coords: [{e['latitude']}, {e['longitude']}]\n"
                f"  Mentions: {e['num_mentions']} | Sources: {e['num_sources']} | Tone: {e['avg_tone']:.1f}\n"
                f"  URL: {e['source_url']}"
                f"{zone_info}{country_info}{org_info}"
            )

    if data.get("acled"):
        sections.append("\n## ACLED Incidents (Coded Political Violence)")
        for e in data["acled"][:25]:
            enr = e.get("_enrichment", {})
            zone_info = ""
            if enr.get("conflict_zone"):
                z = enr["conflict_zone"]
                zone_info = f"\n  CONFLICT ZONE: {z['zone_name']} | Intensity: {z['intensity']} | Trend: {z['trend']} | Pop at risk: {z.get('population_at_risk', 'N/A'):,}"
            country_info = ""
            if enr.get("country"):
                c = enr["country"]
                country_info = f"\n  COUNTRY THREAT: {c['name']} | Level: {c['threat_level']} | Active groups: {', '.join(c['active_groups'][:3])}"
            org_info = ""
            if enr.get("actor1_org"):
                o = enr["actor1_org"]
                org_info = f"\n  DESIGNATED ORG (Actor1): {o['matched_name']} ({o['designation']})"
            if enr.get("actor2_org"):
                o = enr["actor2_org"]
                org_info += f"\n  DESIGNATED ORG (Actor2): {o['matched_name']} ({o['designation']})"
            attack_info = ""
            if enr.get("attack_classification"):
                a = enr["attack_classification"]
                attack_info = f"\n  ATTACK TYPE: {a['category_name']}"

            sections.append(
                f"- {e['date']} | {e['sub_event_type']} | {e['country']} ({e['admin1']}, {e['location']})\n"
                f"  Coords: [{e['latitude']}, {e['longitude']}]\n"
                f"  Actor1: {e['actor1']} | Actor2: {e['actor2']}\n"
                f"  Fatalities: {e['fatalities']}\n"
                f"  Notes: {e['notes'][:250]}"
                f"{zone_info}{country_info}{org_info}{attack_info}"
            )

    if data.get("google_news"):
        sections.append("\n## Google News (Terror-Related)")
        for a in data["google_news"][:20]:
            sections.append(f"- {a['title']}\n  URL: {a['url']}\n  {a['summary'][:150]}")

    if data.get("expert_rss"):
        sections.append("\n## Expert Analysis (RSS)")
        for a in data["expert_rss"][:20]:
            sections.append(f"- [{a['feed_name']}] {a['title']}\n  URL: {a['url']}\n  {a['summary'][:200]}")

    if data.get("sanctions"):
        sections.append("\n## Sanctions Updates")
        for s in data["sanctions"][:15]:
            sections.append(f"- [{s['datasets']}] {s['name']} | Schema: {s['schema']} | Topics: {s['topics']}")

    if data.get("ofac"):
        sections.append("\n## OFAC Recent Actions")
        for o in data["ofac"][:10]:
            sections.append(f"- {o['title']}\n  URL: {o['url']}")

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
7. NEVER speculate beyond what the data supports."""


def generate_report(data: dict, date: datetime, lang: str) -> str:
    """LLM으로 인텔리전스 리포트 생성"""
    raw = build_raw_context(data)
    date_str = date.strftime("%Y-%m-%d")

    # 통계 요약
    acled_count = len(data.get("acled", []))
    acled_fatalities = sum(e.get("fatalities", 0) for e in data.get("acled", []))
    gdelt_count = len(data.get("gdelt", []))
    news_count = len(data.get("google_news", []))

    stats_block = f"""
## Collection Stats:
- ACLED incidents: {acled_count} (total fatalities: {acled_fatalities})
- GDELT events: {gdelt_count}
- News articles: {news_count}
- Expert analyses: {len(data.get('expert_rss', []))}
- Sanctions updates: {len(data.get('sanctions', []))}
"""

    if lang == "ko":
        weekday = ["월", "화", "수", "목", "금", "토", "일"][date.weekday()]
        date_display = f"{date.strftime('%Y년 %m월 %d일')} ({weekday})"
        prompt = f"""아래 수집 데이터를 분석하여 한국어 테러 인텔리전스 데일리 브리프를 작성하라.

## 날짜: {date_display}
{stats_block}
## 수집 데이터:
{raw}

## 작성 규칙:
1. BLUF 원칙: 가장 중요한 판단을 최상단에 배치한다
2. 각 항목을 3~4줄의 분석문으로 작성한다
3. 문장은 "~이다/~하다/~한다/~으로 판단된다"로 종결한다
4. 신뢰도 등급을 명시한다 (높은 확신 / 중간 확신 / 낮은 확신)
5. 출처는 마크다운 링크로 표기한다
6. 수집 데이터에 없는 사건은 절대 작성하지 않는다
7. 해당 섹션에 데이터가 없으면 "보고된 주요 활동 없음"으로 표기한다

## 출력 형식:

# Terror Intelligence Brief — {date_display}

> CLASSIFICATION: UNCLASSIFIED // FOR OFFICIAL USE ONLY

---

## BLUF (Bottom Line Up Front)

> (오늘 가장 중요한 위협 판단 2~3문장. URL 없이 핵심만 서술한다)

---

## 1. 위협 수준 평가

| 지역 | 수준 | 근거 |
|------|------|------|
(수집 데이터 기반으로 주요 지역별 위협 수준을 평가한다)

## 2. 통계 대시보드

(수집 데이터의 STATISTICS DASHBOARD를 기반으로 아래 테이블을 작성한다)

### 사건 개요
| 지표 | 수치 |
|------|------|
| 총 사건 수 | (ACLED + GDELT) |
| 총 사망자 | (ACLED fatalities 합계) |
| 가장 활발한 국가 | (상위 5개국) |
| 가장 활발한 조직 | (상위 5개) |

### 공격 유형 분포
| 유형 | 건수 |
|------|------|
(데이터의 By Attack Type에서 추출)

## 3. 주요 사건 상세

| 날짜 | 위치 | 좌표 | 유형 | 조직/행위자 | 사상자 | 출처 |
|------|------|------|------|-------------|--------|------|
(ACLED + GDELT 데이터에서 좌표 포함하여 주요 사건을 테이블로 정리한다. 좌표는 [lat, lon] 형식)

## 4. 지역별 분석

### 중동 / 북아프리카
### 사하라 이남 아프리카
### 남아시아 / 동남아시아
### 유럽 / 북미
### 기타 지역

(각 지역별로 주요 동향을 분석한다. 좌표 데이터가 있으면 [lat, lon]을 포함한다. 데이터가 없는 지역은 "보고된 주요 활동 없음")

## 5. 조직 동향

(통계 대시보드의 By Actor 데이터를 기반으로 활동이 확인된 조직의 사건 수, 지역, 공격 유형을 분석한다)

## 6. 제재 / 정책 변동

(OFAC, UN, EU 제재 목록 변동 및 대테러 정책 변화를 분석한다)

## 7. 전문가 분석 요약

(Long War Journal, Soufan Center 등 전문 기관의 분석을 요약한다)

## 8. 트렌드 & 패턴

(통계 대시보드 데이터를 기반으로 관찰되는 패턴을 분석한다. 미디어 톤, 언급량 변화도 포함)

## 9. 실무 시사점

> (구체적 액션 아이템. 번호로 나열한다)

---

*Sources: ACLED, GDELT, Google News, Long War Journal, Soufan Center, CTC Sentinel, Jamestown, OpenSanctions, OFAC*
*Generated: {date_display} | Model: {ANALYSIS_MODEL} | UNCLASSIFIED*
"""
    else:
        weekday = date.strftime("%A")
        date_display = f"{date_str} ({weekday})"
        prompt = f"""Analyze the collected data and produce an English daily terror intelligence brief.

## Date: {date_display}
{stats_block}
## Collected Data:
{raw}

## Rules:
1. BLUF principle: Lead with the most critical assessment
2. Each item: 3-4 line analytical paragraph
3. Use estimative language with confidence levels (HIGH/MODERATE/LOW CONFIDENCE)
4. Source as markdown link: [text](URL)
5. NEVER fabricate. Only use provided data.
6. Empty sections: "No significant activity reported"

## Output format:

# Terror Intelligence Brief — {date_display}

> CLASSIFICATION: UNCLASSIFIED // FOR OFFICIAL USE ONLY

---

## BLUF (Bottom Line Up Front)

> (2-3 sentences. Most critical threat assessment. No URLs.)

---

## 1. Threat Level Assessment

| Region | Level | Basis |
|--------|-------|-------|

## 2. Statistics Dashboard

### Incident Overview
| Metric | Value |
|--------|-------|
(Use STATISTICS DASHBOARD data)

### Attack Type Distribution
| Type | Count |
|------|-------|

## 3. Key Incidents Detail

| Date | Location | Coords | Type | Actor | Casualties | Source |
|------|----------|--------|------|-------|------------|--------|
(Include [lat, lon] coordinates from data)

## 4. Regional Analysis

### Middle East / North Africa
### Sub-Saharan Africa
### South / Southeast Asia
### Europe / North America
### Other Regions

(Include coordinates where available)

## 5. Threat Group Activity

(Use By Actor statistics for incident counts per group)

## 6. Sanctions & Policy Updates

## 7. Expert Analysis Summary

## 8. Trends & Patterns

(Include media tone analysis and mention volume from GDELT)

## 9. Actionable Takeaways

> (Numbered action items)

---

*Sources: ACLED, GDELT, Google News, Long War Journal, Soufan Center, CTC Sentinel, Jamestown, OpenSanctions, OFAC*
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

    # 3. 리포트 디렉토리
    report_dir = get_report_dir(target_date)

    # 4. 한글 리포트
    print("\n  [KO] Generating...")
    ko = generate_report(data, target_date, "ko")
    ko_path = report_dir / f"{date_str}_ko.md"
    ko_path.write_text(ko, encoding="utf-8")
    print(f"   -> {ko_path.relative_to(ROOT)}")

    # 5. 영문 리포트
    print("\n  [EN] Generating...")
    en = generate_report(data, target_date, "en")
    en_path = report_dir / f"{date_str}_en.md"
    en_path.write_text(en, encoding="utf-8")
    print(f"   -> {en_path.relative_to(ROOT)}")

    # 6. README
    update_week_readme(report_dir, target_date)
    update_month_readme(report_dir, target_date)

    # 7. Raw JSON
    raw_path = report_dir / f"{date_str}_raw.json"
    raw_out = {k: v for k, v in data.items() if k != "collected_at"}
    raw_out["meta"] = {"collected_at": data.get("collected_at", ""), "total": total}
    raw_path.write_text(json.dumps(raw_out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"\n{'='*55}")
    print(f"  DONE | KO: {ko_path.name} / EN: {en_path.name}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
