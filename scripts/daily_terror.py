"""
Terror Intelligence Daily Report — 데일리 인텔리전스 자동 생성
- 보고서는 코드로 자동 생성, LLM은 BLUF 요약(3~5줄)만 담당

사용법:
    python scripts/daily_terror.py              # 오늘 날짜
    python scripts/daily_terror.py 2026-03-27   # 특정 날짜
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
load_dotenv(ROOT / ".env")

from sources import collect_all
from mapper import TerrorMapper
from event_linker import link_events
from threat_scorer import run_analysis
from database import save_events, save_daily_stats, init_db, cleanup_db, save_known_ucdp_ids
from casualty_extractor import enrich_articles_with_casualties
from compute_stats import compute as compute_stats
from config import ANALYSIS_MODEL, REPORTS_DIR

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
mapper = TerrorMapper()


# ─── 유틸리티 ─────────────────────────────────

def get_week_number(date: datetime) -> int:
    return date.isocalendar()[1]


def get_report_dir(date: datetime) -> Path:
    year = date.strftime("%Y")
    month = date.strftime("%m")
    week = f"week-{get_week_number(date):02d}"
    d = ROOT / REPORTS_DIR / year / month / week
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── BLUF 생성 (유일한 LLM 호출) ──────────────

def generate_bluf(summary_text: str) -> str:
    """정제된 데이터 요약을 받아 BLUF 3~5줄 생성 (유일한 LLM 호출)"""
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a senior counterterrorism analyst. "
                    "Write a 3-5 line executive summary (BLUF) in Korean. "
                    "Use only the provided data. Never fabricate. "
                    "End sentences with ~이다/~하다/~한다/~으로 판단된다."
                )},
                {"role": "user", "content": f"아래 데이터를 기반으로 오늘의 핵심 위협 판단을 3~5줄로 작성하라.\n\n{summary_text}"},
            ],
            temperature=0.1,
            max_completion_tokens=300,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        if usage:
            print(f"   BLUF tokens: in={usage.prompt_tokens:,} out={usage.completion_tokens:,}")
        return content.strip()
    except Exception as e:
        print(f"   BLUF generation failed: {e}")
        return "BLUF 생성 실패 — 아래 데이터를 직접 참고하시오."


# ─── 보고서 자동 생성 (코드 기반) ──────────────

def _resolve_country(mapper, code: str) -> str:
    """ISO 코드를 '국가명' 형식으로 변환 (이미 국가명이면 그대로)"""
    if not code or len(code) > 3:
        return code  # 이미 국가명이면 그대로 반환
    country_info = mapper.match_country(code)
    if country_info and country_info.get("name"):
        return country_info["name"]
    return code


def build_report(data: dict, date: datetime, mapper=None) -> str:
    """정제된 데이터로 보고서를 코드로 생성 (LLM 없이 구조화)"""
    weekday = ["월", "화", "수", "목", "금", "토", "일"][date.weekday()]
    date_display = f"{date.strftime('%Y-%m-%d')} ({weekday})"
    analysis = data.get("_analysis", {})

    gdelt = data.get("gdelt", [])
    ucdp = data.get("ucdp", [])
    news = data.get("google_news", [])
    expert = data.get("expert_rss", [])
    sanctions = data.get("sanctions", [])
    ofac = data.get("ofac", [])
    clusters = data.get("event_clusters", [])

    total_fatalities = sum(int(e.get("fatalities", 0) or 0) for e in ucdp)
    ucdp_new = [e for e in ucdp if e.get("is_new", False)]
    ucdp_old = [e for e in ucdp if not e.get("is_new", False)]
    new_fatalities = sum(int(e.get("fatalities", 0) or 0) for e in ucdp_new)

    lines = []
    lines.append(f"# Terror Intelligence Brief \u2014 {date_display}")
    lines.append("")
    lines.append("> CLASSIFICATION: UNCLASSIFIED // FOR OFFICIAL USE ONLY")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── BLUF (LLM 생성) ───
    bluf_context = _build_bluf_context(data, analysis)
    bluf = generate_bluf(bluf_context)
    lines.append("## BLUF (Bottom Line Up Front)")
    lines.append("")
    lines.append(f"> {bluf}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── 1. 수집 통계 ───
    lines.append("## 1. 수집 통계")
    lines.append("")
    lines.append("| 소스 | 건수 |")
    lines.append("|------|------|")
    lines.append(f"| GDELT 이벤트 | {len(gdelt)} |")
    lines.append(f"| UCDP 분쟁 사건 (신규/전체) | **{len(ucdp_new)}** / {len(ucdp)} |")
    lines.append(f"| Google News | {len(news)} |")
    lines.append(f"| 전문가 RSS | {len(expert)} |")
    lines.append(f"| 제재 엔티티 | {len(sanctions)} |")
    lines.append(f"| OFAC 조치 | {len(ofac)} |")
    lines.append(f"| **UCDP 사망자 (신규/누적)** | **{new_fatalities}** / {total_fatalities} |")
    # 뉴스 기반 사상자 추정
    news_est = sum(a.get("fatalities_estimated", 0) for a in news)
    rss_est = sum(a.get("fatalities_estimated", 0) for a in expert)
    total_est = news_est + rss_est
    if total_est > 0:
        lines.append(f"| **오늘 뉴스 추정 사망자** | **~{total_est}** (뉴스 {news_est} + RSS {rss_est}) |")
    lines.append("")

    # ─── 2. 위협 수준 ───
    threat = analysis.get("threat_levels", {})
    if threat:
        lines.append("## 2. 위협 수준 평가")
        lines.append("")
        lines.append("| 국가 | 점수 | 등급 | 사건 수 | 사망자 |")
        lines.append("|------|------|------|---------|--------|")
        for country, t in list(threat.items())[:10]:
            display_name = _resolve_country(mapper, country) if mapper else country
            lines.append(f"| {display_name} | {t['score']}/10 | {t['label']} | {t['events']} | {t['fatalities']} |")
        lines.append("")

        # ─── 지역별 요약 ───
        if mapper:
            regions = {}
            for country, t in threat.items():
                country_info = mapper.match_country(country)
                region = country_info.get("region", "기타") if country_info else "기타"
                if region not in regions:
                    regions[region] = []
                regions[region].append((country, t, country_info))

            lines.append("### 지역별 요약")
            lines.append("")
            for region, items in sorted(regions.items()):
                lines.append(f"### {region}")
                for country, t, info in items:
                    name = info['name'] if info else country
                    lines.append(f"- **{name}**: {t['label']}({t['score']}/10) | 사건 {t['events']} | 사망 {t['fatalities']}")
            lines.append("")

    # ─── 3. 전일 비교 ───
    diff = analysis.get("daily_diff", {})
    if diff.get("diff"):
        lines.append("## 3. 전일 대비 변동")
        lines.append("")
        lines.append(f"- GDELT: {diff['trend_text'].get('gdelt', 'N/A')}")
        lines.append(f"- 사망자: {diff['trend_text'].get('fatalities', 'N/A')}")
        lines.append("")

    # ─── 4. UCDP 분쟁 사건 ───
    if ucdp:
        # 4a. 신규 사건 (이번에 처음 감지된 것)
        if ucdp_new:
            lines.append(f"## 4. 신규 분쟁 사건 ({len(ucdp_new)}건, 사망 {new_fatalities}명)")
            lines.append("")
            lines.append("| 날짜 | 국가 | 위치 | 행위자A | 행위자B | 사망자 | 좌표 |")
            lines.append("|------|------|------|---------|---------|--------|------|")
            for e in ucdp_new[:15]:
                lat = e.get("latitude", "")
                lon = e.get("longitude", "")
                coord = f"[{lat},{lon}]" if lat and lon else ""
                lines.append(
                    f"| {e.get('date', '')} | {e.get('country', '')} | {e.get('location', '')} "
                    f"| {e.get('actor1', '')[:25]} | {e.get('actor2', '')[:25]} "
                    f"| {e.get('fatalities', 0)} | {coord} |"
                )
            lines.append("")
        else:
            lines.append("## 4. 신규 분쟁 사건")
            lines.append("")
            lines.append("UCDP 신규 사건 없음 (월간 업데이트 대기 중)")
            lines.append("")

        # 4b. 월간 누적 통계 (요약만)
        country_fat = {}
        for e in ucdp:
            c = e.get("country", "Unknown")
            country_fat[c] = country_fat.get(c, 0) + int(e.get("fatalities", 0) or 0)
        top_countries = sorted(country_fat.items(), key=lambda x: x[1], reverse=True)[:8]

        lines.append(f"### UCDP 누적 현황 ({len(ucdp)}건, 사망 {total_fatalities}명)")
        lines.append("")
        lines.append("| 국가 | 사망자 |")
        lines.append("|------|--------|")
        for c, f in top_countries:
            lines.append(f"| {c} | {f} |")
        lines.append("")

    # ─── 5. GDELT 주요 이벤트 ───
    if gdelt:
        lines.append(f"## 5. GDELT 미디어 이벤트 (상위 {min(10, len(gdelt))}건)")
        lines.append("")
        lines.append("| 날짜 | 코드 | Actor1 | Actor2 | 국가 | 언급수 | 톤 | 출처 |")
        lines.append("|------|------|--------|--------|------|--------|-----|------|")
        for e in gdelt[:10]:
            tone = e.get('avg_tone', 0)
            tone_str = f"{tone:.1f}" if isinstance(tone, (int, float)) else str(tone)
            url = e.get('source_url', '')
            link = f"[link]({url})" if url else ""
            lines.append(
                f"| {e.get('date', '')} | {e.get('event_code', '')} "
                f"| {e.get('actor1', '')[:20]} | {e.get('actor2', '')[:20]} "
                f"| {e.get('country_code', '')} | {e.get('num_mentions', 0)} "
                f"| {tone_str} | {link} |"
            )
        lines.append("")

    # ─── 6. 이벤트 클러스터 ───
    if clusters:
        lines.append(f"## 6. 뉴스 클러스터 (교차매칭, {len(clusters)}건)")
        lines.append("")
        for i, c in enumerate(clusters[:8], 1):
            score = c.get("importance_score", 0)
            title = c.get("title", "Untitled")
            url = c.get("url", "")
            countries = ", ".join(c.get("countries", []))
            est_dead = c.get("fatalities_estimated", 0)
            casualty_tag = f" | ~{est_dead} killed" if est_dead > 0 else ""
            link = f"[{title[:60]}]({url})" if url else title[:60]
            lines.append(f"{i}. **[Score:{score}]** {link}{casualty_tag}")
            if countries:
                lines.append(f"   - 관련 국가: {countries}")
        lines.append("")

    # ─── 7. 조직 동향 ───
    orgs = analysis.get("org_tracker", [])
    if orgs:
        lines.append("## 7. 조직 활동")
        lines.append("")
        lines.append("| 조직 | 지정 | 금일 사건 | 사망자 | 활동 국가 |")
        lines.append("|------|------|-----------|--------|-----------|")
        for o in orgs[:7]:
            countries = ", ".join(
                _resolve_country(mapper, str(c)) if mapper else str(c)
                for c in o.get("countries", [])[:3]
            )
            lines.append(
                f"| {o['name'][:30]} | {o.get('designation', '')} "
                f"| {o.get('events_today', 0)} | {o.get('fatalities_today', 0)} | {countries} |"
            )
        lines.append("")

    # ─── 8. 핫스팟 ───
    hotspots = analysis.get("hotspots", [])
    if hotspots:
        lines.append("## 8. 지리적 핫스팟")
        lines.append("")
        for i, h in enumerate(hotspots[:5], 1):
            resolved = dict.fromkeys(
                _resolve_country(mapper, str(c)) if mapper else str(c)
                for c in h.get("countries", [])
            )
            countries = ", ".join(resolved)
            lines.append(
                f"{i}. [{h['center'][0]}, {h['center'][1]}] "
                f"| 사건: {h['events']} | 사망: {h['fatalities']} | 국가: {countries}"
            )
        lines.append("")

    # ─── 9. 제재/OFAC ───
    new_sanctions = [s for s in sanctions if s.get("is_new")]
    if new_sanctions or ofac:
        lines.append("## 9. 제재 동향")
        lines.append("")
        if new_sanctions:
            lines.append(f"**신규 제재 엔티티: {len(new_sanctions)}건**")
            for s in new_sanctions[:5]:
                lines.append(f"- [{s.get('datasets', '')}] {s.get('name', '')} ({s.get('schema', '')})")
        else:
            lines.append("신규 제재 엔티티 없음")
        if ofac:
            lines.append(f"\n**OFAC 최근 조치: {len(ofac)}건**")
            for o in ofac[:3]:
                url = o.get('url', '')
                link = f"[{o.get('title', '')[:50]}]({url})" if url else o.get('title', '')[:50]
                lines.append(f"- {link}")
        lines.append("")

    # ─── 10. 전문가 분석 ───
    if expert:
        lines.append("## 10. 전문가 분석")
        lines.append("")
        for a in expert[:8]:
            url = a.get('url', '')
            link = f"[{a.get('title', '')[:60]}]({url})" if url else a.get('title', '')[:60]
            lines.append(f"- **{a.get('feed_name', '')}**: {link}")
        lines.append("")

    # ─── Footer ───
    lines.append("---")
    lines.append(f"*Sources: GDELT, UCDP, Google News, OpenSanctions, OFAC + {len(data.get('expert_rss', []))} expert RSS feeds*")
    lines.append(f"*Generated: {date_display} | UNCLASSIFIED*")

    return "\n".join(lines)


def _build_bluf_context(data: dict, analysis: dict) -> str:
    """BLUF 생성을 위한 최소 컨텍스트 (~1000 토큰)"""
    parts = []

    # 위협 상위 5국
    threat = analysis.get("threat_levels", {})
    if threat:
        top5 = list(threat.items())[:5]
        parts.append("위협 상위 국가: " + ", ".join(f"{c}({t['label']},{t['score']}/10,사건{t['events']},사망{t['fatalities']})" for c, t in top5))

    # UCDP 사상자 (신규 우선)
    ucdp = data.get("ucdp", [])
    if ucdp:
        ucdp_new = [e for e in ucdp if e.get("is_new", False)]
        total_dead = sum(int(e.get("fatalities", 0) or 0) for e in ucdp)
        new_dead = sum(int(e.get("fatalities", 0) or 0) for e in ucdp_new)
        parts.append(f"UCDP 전체 {len(ucdp)}건(사망{total_dead}), 신규 {len(ucdp_new)}건(사망{new_dead})")
        # 신규 사건 우선, 없으면 전체에서
        top_incidents = (ucdp_new or ucdp)[:5]
        for e in top_incidents:
            tag = "[신규] " if e.get("is_new") else ""
            parts.append(f"  - {tag}{e.get('country','')} {e.get('location','')}: {e.get('actor1','')} vs {e.get('actor2','')}, 사망 {e.get('fatalities',0)}")

    # GDELT 요약
    gdelt = data.get("gdelt", [])
    if gdelt:
        parts.append(f"GDELT {len(gdelt)}건, 총 언급 {sum(e.get('num_mentions',0) for e in gdelt):,}")

    # 핫스팟
    hotspots = analysis.get("hotspots", [])
    if hotspots:
        parts.append("핫스팟: " + ", ".join(f"{','.join(str(c) for c in h['countries'])}(사건{h['events']},사망{h['fatalities']})" for h in hotspots[:3]))

    # 전일 비교
    diff = analysis.get("daily_diff", {})
    if diff.get("trend_text"):
        parts.append(f"전일비교: GDELT {diff['trend_text'].get('gdelt','')}, 사망 {diff['trend_text'].get('fatalities','')}")

    # 조직
    orgs = analysis.get("org_tracker", [])
    if orgs:
        parts.append("활동 조직: " + ", ".join(f"{o['name'][:20]}(사건{o['events_today']},사망{o['fatalities_today']})" for o in orgs[:5]))

    return "\n".join(parts)


# ─── README 업데이트 ───

def update_week_readme(report_dir: Path, date: datetime):
    readme = report_dir / "README.md"
    week_num = get_week_number(date)
    year = date.strftime("%Y")
    month = date.strftime("%m월")

    reports = sorted(report_dir.glob("*.md"))
    rows = []
    for r in reports:
        if r.name == "README.md" or r.name.endswith("_summary.md"):
            continue
        rows.append(f"| {r.stem} | [{r.name}]({r.name}) |")

    table = "\n".join(rows) if rows else "| - | - |"
    content = f"""# Week {week_num} \u2014 {year}년 {month}

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
        count = len([f for f in w.glob("*.md") if f.name != "README.md"])
        rows.append(f"| [{w.name}]({w.name}/README.md) | {count} |")
    table = "\n".join(rows) if rows else "| - | 0 |"

    content = f"""# {year}년 {month} Terror Intelligence

| Week | Reports |
|------|---------|
{table}
"""
    readme.write_text(content, encoding="utf-8")


# ─── 메인 파이프라인 ───

def main():
    if len(sys.argv) > 1:
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    else:
        target_date = datetime.now()

    date_str = target_date.strftime("%Y-%m-%d")
    print(f"\n{'='*55}")
    print(f"  Terror Intelligence Brief \u2014 {date_str}")
    print(f"{'='*55}\n")

    # 0. DB 초기화 + 마이그레이션 (명시적 호출)
    init_db()
    cleanup_db()

    # 1. 수집
    data = collect_all(target_date)
    total = sum(len(v) for v in data.values() if isinstance(v, list))
    if total == 0:
        print("No data collected.")
        return

    # 2. 뉴스 사상자 추출 (NLP)
    print("\n  Extracting casualties from news text...")
    for key in ["google_news", "expert_rss"]:
        articles = data.get(key, [])
        if articles:
            data[key] = enrich_articles_with_casualties(articles)
    news_fatalities = sum(a.get("fatalities_estimated", 0) for a in data.get("google_news", []))
    rss_fatalities = sum(a.get("fatalities_estimated", 0) for a in data.get("expert_rss", []))
    print(f"   news: {news_fatalities} estimated killed | rss: {rss_fatalities} estimated killed")

    # 3. 기반 데이터 매핑
    print("\n  Enriching with foundation data...")
    data = mapper.enrich_all(data)
    stats = data.get("_enrichment_stats", {})
    print(f"   enriched: {stats.get('total_enriched', 0)} events")

    # 4. 이벤트 링킹
    print("\n  Linking events across sources...")
    data = link_events(data)

    # 5. 심층 분석
    print("\n  Running deep analysis...")
    analysis = run_analysis(data, date_str)
    data["_analysis"] = analysis

    # 6. DB 저장
    report_dir = get_report_dir(target_date)
    print("\n  Saving to database...")
    save_events(data, date_str)
    save_daily_stats(date_str, data, stats)
    ucdp_ids = [e.get("event_id") for e in data.get("ucdp", []) if e.get("event_id")]
    total_known = save_known_ucdp_ids(ucdp_ids)
    print(f"   -> terror.db updated | known UCDP ids: {total_known}")

    # 6. 보고서 생성 (코드 기반 + LLM BLUF만)
    print("\n  Building report...")
    report = build_report(data, target_date, mapper)
    report_path = report_dir / f"{date_str}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"   -> {report_path.relative_to(ROOT)} ({len(report):,} chars)")

    # 7. README
    update_week_readme(report_dir, target_date)
    update_month_readme(report_dir, target_date)

    # 8. 집계 테이블 갱신 (global_stats, country_stats, org_stats)
    print("\n  Recomputing aggregate stats...")
    try:
        compute_stats()
        print("   -> stats tables updated")
    except Exception as e:
        print(f"   -> stats update failed: {e}")

    # 9. Raw JSON
    raw_path = report_dir / f"{date_str}_raw.json"
    raw_out = {k: v for k, v in data.items() if not k.startswith("_")}
    raw_out["meta"] = {"collected_at": data.get("collected_at", ""), "total": total, "enrichment": stats}
    raw_path.write_text(json.dumps(raw_out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"\n{'='*55}")
    print(f"  DONE | {report_path.name}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
