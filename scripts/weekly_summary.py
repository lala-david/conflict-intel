"""
주간 요약 리포트 생성 (LLM 없이 코드 기반)
- SQLite에 쌓인 데이터를 기반으로 주간 통계 + 트렌드 분석
"""
import sys
import io
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import REPORTS_DIR

DB_PATH = ROOT / "data" / "terror.db"


def get_weekly_data(end_date: datetime) -> dict:
    """최근 7일 데이터 집계"""
    start = (end_date - timedelta(days=6)).strftime("%Y-%m-%d")
    end = end_date.strftime("%Y-%m-%d")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        daily = conn.execute(
            "SELECT date, gdelt_count, acled_count, news_count, total_fatalities, sanctions_new, top_countries, top_actors "
            "FROM daily_stats WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, end),
        ).fetchall()

        country_events = conn.execute(
            "SELECT COALESCE(NULLIF(country,''), country_code) as c, COUNT(*) as cnt "
            "FROM events WHERE collected_at >= ? GROUP BY c ORDER BY cnt DESC LIMIT 15",
            (start,),
        ).fetchall()

        source_events = conn.execute(
            "SELECT source, COUNT(*) FROM events WHERE collected_at >= ? GROUP BY source",
            (start,),
        ).fetchall()

        total_events = conn.execute(
            "SELECT COUNT(*) FROM events WHERE collected_at >= ?", (start,)
        ).fetchone()[0]

        new_sanctions = conn.execute(
            "SELECT name, dataset, schema_type FROM sanctions WHERE is_new=1 AND collected_date BETWEEN ? AND ?",
            (start, end),
        ).fetchall()
    finally:
        conn.close()

    return {
        "period": f"{start} ~ {end}",
        "daily_stats": [
            {"date": r[0], "gdelt": r[1], "ucdp": r[2], "news": r[3], "fatalities": r[4], "new_sanctions": r[5],
             "top_countries": r[6], "top_actors": r[7]}
            for r in daily
        ],
        "country_ranking": [{"country": r[0], "events": r[1]} for r in country_events],
        "source_breakdown": [{"source": r[0], "count": r[1]} for r in source_events],
        "total_events": total_events,
        "new_sanctions": [{"name": r[0], "dataset": r[1], "type": r[2]} for r in new_sanctions],
    }


def build_weekly_report(data: dict, end_date: datetime) -> str:
    """주간 요약을 코드로 생성 (LLM 없음)"""
    week_num = end_date.isocalendar()[1]
    weekday = ["월", "화", "수", "목", "금", "토", "일"][end_date.weekday()]
    date_display = f"{end_date.strftime('%Y년 %m월 %d일')} ({weekday})"

    lines = []
    lines.append(f"# Weekly Intelligence Summary \u2014 Week {week_num} ({data['period']})")
    lines.append("")

    # 주간 통계 테이블
    lines.append("## 주간 통계")
    lines.append("")
    lines.append("| 날짜 | GDELT | UCDP | 뉴스 | 사망자 | 신규제재 |")
    lines.append("|------|-------|------|------|--------|----------|")

    total_gdelt = total_ucdp = total_news = total_fat = total_sanctions = 0
    for d in data["daily_stats"]:
        lines.append(f"| {d['date']} | {d['gdelt']} | {d['ucdp']} | {d['news']} | {d['fatalities']} | {d['new_sanctions']} |")
        total_gdelt += d["gdelt"]
        total_ucdp += d["ucdp"]
        total_news += d["news"]
        total_fat += d["fatalities"]
        total_sanctions += d["new_sanctions"]

    lines.append(f"| **합계** | **{total_gdelt}** | **{total_ucdp}** | **{total_news}** | **{total_fat}** | **{total_sanctions}** |")
    lines.append("")

    # 국가별 순위
    if data["country_ranking"]:
        lines.append("## 국가별 활동 순위")
        lines.append("")
        lines.append("| 순위 | 국가 | 이벤트 수 |")
        lines.append("|------|------|-----------|")
        for i, cr in enumerate(data["country_ranking"][:10], 1):
            lines.append(f"| {i} | {cr['country']} | {cr['events']} |")
        lines.append("")

    # 소스별 분포
    if data["source_breakdown"]:
        lines.append("## 소스별 분포")
        lines.append("")
        for sb in data["source_breakdown"]:
            lines.append(f"- {sb['source']}: {sb['count']}건")
        lines.append("")

    # 신규 제재
    if data["new_sanctions"]:
        lines.append("## 신규 제재 엔티티")
        lines.append("")
        for ns in data["new_sanctions"]:
            lines.append(f"- [{ns['dataset']}] {ns['name']} ({ns['type']})")
        lines.append("")

    lines.append("---")
    lines.append(f"*Weekly Summary | Generated: {date_display}*")

    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        end_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    else:
        end_date = datetime.now()

    week_num = end_date.isocalendar()[1]
    print(f"\n  Weekly Summary \u2014 Week {week_num}\n")

    data = get_weekly_data(end_date)
    if not data["daily_stats"]:
        print("  No data for this week.")
        return

    print(f"  Period: {data['period']}")
    print(f"  Days with data: {len(data['daily_stats'])}")
    print(f"  Total events: {data['total_events']}")

    report = build_weekly_report(data, end_date)

    year = end_date.strftime("%Y")
    month = end_date.strftime("%m")
    week = f"week-{week_num:02d}"
    report_dir = ROOT / REPORTS_DIR / year / month / week
    report_dir.mkdir(parents=True, exist_ok=True)

    path = report_dir / f"week-{week_num:02d}_summary.md"
    path.write_text(report, encoding="utf-8")
    print(f"  -> {path.relative_to(ROOT)} ({len(report):,} chars)")


if __name__ == "__main__":
    main()
