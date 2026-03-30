"""
주간 요약 리포트 생성
- SQLite에 쌓인 데이터를 기반으로 주간 통계 + 트렌드 분석
"""
import os
import sys
import io
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
load_dotenv(ROOT / ".env")

from config import ANALYSIS_MODEL, TEMPERATURE, REPORTS_DIR

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_PATH = ROOT / "data" / "terror.db"


def get_weekly_data(end_date: datetime) -> dict:
    """최근 7일 데이터 집계"""
    start = (end_date - timedelta(days=7)).strftime("%Y-%m-%d")
    end = end_date.strftime("%Y-%m-%d")

    conn = sqlite3.connect(str(DB_PATH))

    # 일일 통계
    daily = conn.execute(
        "SELECT date, gdelt_count, acled_count, news_count, total_fatalities, sanctions_new, top_countries, top_actors "
        "FROM daily_stats WHERE date BETWEEN ? AND ? ORDER BY date",
        (start, end),
    ).fetchall()

    # 이벤트 국가별
    country_events = conn.execute(
        "SELECT COALESCE(NULLIF(country,''), country_code) as c, COUNT(*) as cnt "
        "FROM events WHERE collected_at >= ? GROUP BY c ORDER BY cnt DESC LIMIT 15",
        (start,),
    ).fetchall()

    # 이벤트 소스별
    source_events = conn.execute(
        "SELECT source, COUNT(*) FROM events WHERE collected_at >= ? GROUP BY source",
        (start,),
    ).fetchall()

    # 총 이벤트
    total_events = conn.execute(
        "SELECT COUNT(*) FROM events WHERE collected_at >= ?", (start,)
    ).fetchone()[0]

    # 제재 변동
    new_sanctions = conn.execute(
        "SELECT name, dataset, schema_type FROM sanctions WHERE is_new=1 AND collected_date BETWEEN ? AND ?",
        (start, end),
    ).fetchall()

    conn.close()

    return {
        "period": f"{start} ~ {end}",
        "daily_stats": [
            {"date": r[0], "gdelt": r[1], "acled": r[2], "news": r[3], "fatalities": r[4], "new_sanctions": r[5],
             "top_countries": r[6], "top_actors": r[7]}
            for r in daily
        ],
        "country_ranking": [{"country": r[0], "events": r[1]} for r in country_events],
        "source_breakdown": [{"source": r[0], "count": r[1]} for r in source_events],
        "total_events": total_events,
        "new_sanctions": [{"name": r[0], "dataset": r[1], "type": r[2]} for r in new_sanctions],
    }


def generate_weekly(data: dict, end_date: datetime) -> str:
    """주간 요약 리포트 생성"""
    weekday = ["월", "화", "수", "목", "금", "토", "일"][end_date.weekday()]
    date_display = f"{end_date.strftime('%Y년 %m월 %d일')} ({weekday})"
    week_num = end_date.isocalendar()[1]

    context = json.dumps(data, ensure_ascii=False, indent=2, default=str)

    prompt = f"""아래 주간 수집 데이터를 분석하여 한국어 주간 인텔리전스 요약을 작성하라.

## 기간: {data['period']} (Week {week_num})

## 수집 데이터:
{context}

## 작성 규칙:
1. 문장은 "~이다/~하다/~한다"로 종결한다
2. 출처는 마크다운 링크로 표기한다
3. 수집 데이터에 없는 내용은 절대 작성하지 않는다
4. 주간 트렌드(증가/감소/안정)를 명확히 서술한다

## 출력 형식:

# Weekly Intelligence Summary — Week {week_num} ({data['period']})

## 주간 핵심 요약
> (이번 주 가장 중요한 3가지를 서술한다)

## 주간 통계

| 날짜 | GDELT | ACLED | 뉴스 | 사망자 | 신규제재 |
|------|-------|-------|------|--------|----------|
(일별 데이터를 테이블로 정리한다)

## 국가별 활동 순위

| 순위 | 국가 | 이벤트 수 | 트렌드 |
|------|------|-----------|--------|

## 주간 트렌드 분석
(전주 대비 변화, 패턴, 이상 징후를 분석한다)

## 제재 변동
(이번 주 신규 제재 엔티티를 정리한다)

## 다음 주 전망
> (다음 주 주목해야 할 포인트)

---
*Weekly Summary | Generated: {date_display}*
"""

    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": "Senior counterterrorism analyst producing weekly intelligence summary. Use ONLY provided data."},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_completion_tokens=4000,
    )

    return response.choices[0].message.content or ""


def main():
    if len(sys.argv) > 1:
        end_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    else:
        end_date = datetime.now()

    week_num = end_date.isocalendar()[1]
    print(f"\n  Weekly Summary — Week {week_num}\n")

    # 데이터 집계
    data = get_weekly_data(end_date)
    if not data["daily_stats"]:
        print("  No data for this week.")
        return

    print(f"  Period: {data['period']}")
    print(f"  Days with data: {len(data['daily_stats'])}")
    print(f"  Total events: {data['total_events']}")

    # 리포트 생성
    print("\n  Generating weekly summary...")
    report = generate_weekly(data, end_date)

    # 저장
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
