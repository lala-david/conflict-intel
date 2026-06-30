"""
위협 수준 자동 계산 엔진
#1: 이벤트수 + 톤 + 분쟁강도 + 사상자 기반 수치화
#2: 전일 대비 비교
#4: 조직별 활동 트래커
#5: 지역 밀도 분석
"""
import json
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "terror.db"


def _get_conn():
    return sqlite3.connect(str(DB_PATH))


# ─────────────────────────────────────
# #1: 위협 수준 자동 계산
# ─────────────────────────────────────
THREAT_SCALE = {
    (0, 2): {"level": 1, "label": "MINIMAL", "color": "🟢"},
    (2, 4): {"level": 2, "label": "LOW", "color": "🟡"},
    (4, 6): {"level": 3, "label": "ELEVATED", "color": "🟠"},
    (6, 8): {"level": 4, "label": "HIGH", "color": "🔴"},
    (8, 10): {"level": 5, "label": "SEVERE", "color": "⚫"},
}


def _score_to_threat(score: float) -> dict:
    clamped = max(0, min(10, score))
    for (low, high), info in THREAT_SCALE.items():
        if low <= clamped < high:
            return {**info, "score": round(clamped, 1)}
    return {"level": 5, "label": "SEVERE", "color": "⚫", "score": round(clamped, 1)}


def compute_threat_levels(data: dict, zones_db: list) -> dict:
    """
    국가별 위협 수준을 데이터 기반으로 계산

    산출 공식:
    score = (이벤트수 × 1.5) + (사상자 × 2.0) + (미디어톤 × 0.5) + (분쟁강도 × 1.0) + (클러스터뉴스 × 0.3)
    → 0~10 스케일로 정규화
    """
    country_stats = defaultdict(lambda: {
        "events": 0, "fatalities": 0, "tone_sum": 0, "tone_count": 0,
        "news_mentions": 0, "zone_intensity": 0,
    })

    # GDELT 이벤트 집계
    for e in data.get("gdelt", []):
        c = e.get("country_code", "")
        if not c:
            continue
        country_stats[c]["events"] += 1
        tone = e.get("avg_tone", 0)
        country_stats[c]["tone_sum"] += abs(tone)  # 절대값 (부정이 클수록 위험)
        country_stats[c]["tone_count"] += 1

    # ACLED 사건 집계
    for e in data.get("ucdp", []):
        c = e.get("country", "")
        if not c:
            continue
        # ISO 2자리로 변환 시도
        enr = e.get("_enrichment", {}).get("country", {})
        iso = enr.get("iso", "")
        if not iso:
            continue
        country_stats[iso]["events"] += 1
        country_stats[iso]["fatalities"] += int(e.get("fatalities", 0) or 0)

    # 뉴스 클러스터 국가 집계
    for cluster in data.get("event_clusters", []):
        for c in cluster.get("countries", []):
            country_stats[c]["news_mentions"] += cluster.get("cluster_size", 1)

    # 분쟁 지역 강도 매핑
    intensity_map = {"High": 3, "Medium": 2, "Low": 1}
    zone_countries = defaultdict(int)
    for zone in zones_db:
        iso = zone.get("iso_code", "")
        intensity = zone.get("intensity", "Low")
        zone_countries[iso] = max(zone_countries[iso], intensity_map.get(intensity, 0))

    for c, val in zone_countries.items():
        if c in country_stats:
            country_stats[c]["zone_intensity"] = val

    # 점수 계산
    results = {}
    for country, s in country_stats.items():
        if not country:
            continue

        raw = (
            s["events"] * 1.5
            + s["fatalities"] * 2.0
            + (s["tone_sum"] / max(s["tone_count"], 1)) * 0.5
            + s["zone_intensity"] * 1.0
            + s["news_mentions"] * 0.3
        )

        # 0~10 정규화 (sigmoid-like)
        normalized = 10 * (1 - math.exp(-raw / 15))

        threat = _score_to_threat(normalized)
        threat["raw_score"] = round(raw, 2)
        threat["events"] = s["events"]
        threat["fatalities"] = s["fatalities"]
        threat["news_mentions"] = s["news_mentions"]
        results[country] = threat

    # 점수순 정렬
    sorted_results = dict(sorted(results.items(), key=lambda x: x[1]["score"], reverse=True))
    return sorted_results


# ─────────────────────────────────────
# #2: 전일 대비 비교
# ─────────────────────────────────────
def compute_daily_diff(date_str: str) -> dict:
    """어제 vs 오늘 통계 비교"""
    conn = _get_conn()
    try:
        today = conn.execute(
            "SELECT gdelt_count, ucdp_count, news_count, total_fatalities, sanctions_new, top_countries, top_actors "
            "FROM daily_stats WHERE date = ?", (date_str,)
        ).fetchone()

        # 어제 찾기 (데이터가 있는 가장 최근 날)
        yesterday = conn.execute(
            "SELECT date, gdelt_count, ucdp_count, news_count, total_fatalities, sanctions_new, top_countries, top_actors "
            "FROM daily_stats WHERE date < ? ORDER BY date DESC LIMIT 1", (date_str,)
        ).fetchone()
    finally:
        conn.close()

    if not today:
        return {"available": False}

    result = {
        "available": True,
        "today": {
            "gdelt": today[0], "ucdp": today[1], "news": today[2],
            "fatalities": today[3], "new_sanctions": today[4],
        },
    }

    if yesterday:
        prev = {
            "date": yesterday[0],
            "gdelt": yesterday[1], "ucdp": yesterday[2], "news": yesterday[3],
            "fatalities": yesterday[4], "new_sanctions": yesterday[5],
        }
        result["previous"] = prev
        result["diff"] = {
            "gdelt": today[0] - yesterday[1],
            "ucdp": today[1] - yesterday[2],
            "news": today[2] - yesterday[3],
            "fatalities": today[3] - yesterday[4],
        }

        def _trend(diff):
            if diff > 0:
                return f"▲ +{diff}"
            elif diff < 0:
                return f"▼ {diff}"
            return "— 0"

        result["trend_text"] = {
            "gdelt": _trend(today[0] - yesterday[1]),
            "ucdp": _trend(today[1] - yesterday[2]),
            "fatalities": _trend(today[3] - yesterday[4]),
        }
    else:
        result["previous"] = None
        result["diff"] = None
        result["trend_text"] = None

    return result


# ─────────────────────────────────────
# #4: 조직별 활동 트래커
# ─────────────────────────────────────
def track_org_activity(data: dict, days: int = 7) -> list[dict]:
    """조직별 활동 집계 (현재 수집 데이터 + DB 이력)"""
    org_activity = defaultdict(lambda: {
        "events_today": 0, "fatalities_today": 0,
        "countries": set(), "attack_types": set(),
        "designation": "",
    })

    # 오늘 데이터 — 모든 이벤트성 소스 커버
    for source_key in ["ucdp", "gdelt", "wikipedia", "expert_rss", "google_news", "nctc"]:
        for e in data.get(source_key, []):
            enr = e.get("_enrichment", {})

            for actor_key in ["actor1_org", "actor2_org"]:
                org = enr.get(actor_key)
                if not org:
                    continue

                name = org.get("matched_name", "")
                if not name:
                    continue

                org_activity[name]["events_today"] += 1
                fat = int(e.get("fatalities", 0) or e.get("fatalities_estimated", 0) or 0)
                org_activity[name]["fatalities_today"] += fat
                org_activity[name]["designation"] = org.get("designation", "")

                country = e.get("country", "") or e.get("country_code", "")
                if country:
                    org_activity[name]["countries"].add(country)

                attack = enr.get("attack_classification", {}).get("category_name", "")
                if attack:
                    org_activity[name]["attack_types"].add(attack)

    # DB에서 최근 N일 이력 — Government/aggregate 제외 (compute_stats와 일관)
    conn = _get_conn()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT actor1, COUNT(*), SUM(fatalities) FROM events "
            "WHERE date >= ? AND actor1 != '' "
            "  AND actor1 NOT LIKE 'Government of%' "
            "  AND is_aggregate = 0 "
            "GROUP BY actor1 ORDER BY COUNT(*) DESC LIMIT 20",
            (cutoff,)
        ).fetchall()

        db_activity = {r[0]: {"events_7d": r[1], "fatalities_7d": r[2] or 0} for r in rows}
    except Exception:
        db_activity = {}
    finally:
        conn.close()

    # 병합
    results = []
    for name, stats in org_activity.items():
        db = db_activity.get(name, {})
        results.append({
            "name": name,
            "designation": stats["designation"],
            "events_today": stats["events_today"],
            "fatalities_today": stats["fatalities_today"],
            "events_7d": db.get("events_7d", stats["events_today"]),
            "fatalities_7d": db.get("fatalities_7d", stats["fatalities_today"]),
            "countries": list(stats["countries"]),
            "attack_types": list(stats["attack_types"]),
        })

    results.sort(key=lambda x: x["events_today"], reverse=True)
    return results


# ─────────────────────────────────────
# #5: 지역 밀도 분석 (핫스팟 탐지)
# ─────────────────────────────────────
def detect_hotspots(data: dict, grid_size: float = 2.0) -> list[dict]:
    """
    좌표 그리드 기반 핫스팟 탐지
    grid_size: 위/경도 그리드 크기 (2도 ≈ 약 220km)
    """
    grid = defaultdict(lambda: {
        "events": 0, "fatalities": 0, "lats": [], "lons": [],
        "countries": set(), "actors": set(), "types": set(),
    })

    for source_key in ["gdelt", "ucdp", "wikipedia", "expert_rss", "google_news", "nctc"]:
        for e in data.get(source_key, []):
            lat = e.get("latitude", "")
            lon = e.get("longitude", "")
            if lat is None or lon is None:
                continue
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (ValueError, TypeError):
                continue

            # 그리드 셀 계산
            grid_lat = round(lat_f / grid_size) * grid_size
            grid_lon = round(lon_f / grid_size) * grid_size
            key = (grid_lat, grid_lon)

            grid[key]["events"] += 1
            grid[key]["fatalities"] += int(e.get("fatalities", 0) or 0)
            grid[key]["lats"].append(lat_f)
            grid[key]["lons"].append(lon_f)

            country = e.get("country", "") or e.get("country_code", "")
            if country:
                grid[key]["countries"].add(country)
            actor = e.get("actor1", "")
            if actor:
                grid[key]["actors"].add(actor)

            etype = e.get("sub_event_type", "") or e.get("event_code", "")
            if etype:
                grid[key]["types"].add(etype)

    # 핫스팟 = 이벤트 2건 이상인 그리드
    hotspots = []
    for (glat, glon), stats in grid.items():
        if stats["events"] < 2:
            continue

        center_lat = sum(stats["lats"]) / len(stats["lats"])
        center_lon = sum(stats["lons"]) / len(stats["lons"])

        hotspots.append({
            "center": [round(center_lat, 2), round(center_lon, 2)],
            "grid": [glat, glon],
            "events": stats["events"],
            "fatalities": stats["fatalities"],
            "countries": list(stats["countries"]),
            "actors": list(stats["actors"])[:5],
            "event_types": list(stats["types"])[:5],
            "density_score": stats["events"] + stats["fatalities"] * 2,
        })

    hotspots.sort(key=lambda x: x["density_score"], reverse=True)
    return hotspots[:10]


# ─────────────────────────────────────
# 통합: 전체 분석 실행
# ─────────────────────────────────────
def run_analysis(data: dict, date_str: str) -> dict:
    """모든 분석을 실행하고 결과 반환"""

    # 분쟁 지역 DB 로드
    zones_path = ROOT / "data" / "conflict_zones.json"
    zones_db = []
    if zones_path.exists():
        zones_data = json.loads(zones_path.read_text(encoding="utf-8"))
        zones_db = zones_data.get("conflict_zones", [])

    # #1: 위협 수준
    threat_levels = compute_threat_levels(data, zones_db)

    # #2: 전일 비교
    daily_diff = compute_daily_diff(date_str)

    # #4: 조직 트래커
    org_tracker = track_org_activity(data)

    # #5: 핫스팟
    hotspots = detect_hotspots(data)

    return {
        "threat_levels": threat_levels,
        "daily_diff": daily_diff,
        "org_tracker": org_tracker,
        "hotspots": hotspots,
    }
