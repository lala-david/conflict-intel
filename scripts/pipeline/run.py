"""
Medallion pipeline orchestrator: Bronze → Silver → Gold.

  BRONZE  extract each source connector → land raw Parquet → record health
  SILVER  enrich (casualties, entities) → link → analyze → load into `events`
  GOLD    recompute serving aggregates + write the daily brief

Reuses the proven transform/load modules; adds immutable raw capture and
per-source observability on top. Run: `python -m pipeline.run [YYYY-MM-DD]`.
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from pipeline import bronze, health
from pipeline.registry import build_registry
from pipeline.dedup import deduplicate

from casualty_extractor import enrich_articles_with_casualties
from mapper import ConflictMapper
from event_linker import link_events
from threat_scorer import run_analysis
from database import (
    save_events, save_daily_stats, init_db, cleanup_db, save_known_ucdp_ids,
)
from compute_stats import compute as compute_stats
from report_builder import (
    build_report, get_report_dir, update_week_readme, update_month_readme,
)

TEXT_SOURCES = ("google_news", "expert_rss", "telegram")


def run(target_date: datetime | None = None) -> None:
    target_date = target_date or datetime.now()
    date_str = target_date.strftime("%Y-%m-%d")
    run_id = target_date.strftime("%Y%m%d") + "-" + datetime.now().strftime("%H%M%S")

    print(f"\n{'='*60}\n  Medallion pipeline — {date_str}  (run {run_id})\n{'='*60}")
    init_db()
    cleanup_db()

    # ── BRONZE: extract + immutable raw landing + health ──
    print("\n[BRONZE] extract → raw Parquet")
    data: dict = {}
    results = []
    for conn in build_registry(target_date):
        res = conn.run()
        results.append(res)
        data[conn.name] = res.records
        if res.records:
            bronze.land(conn.name, res.records, run_id)
        flag = "ok " if res.ok else "ERR"
        print(f"  [{flag}] {conn.name:14} {len(res.records):>5}  {res.error[:60]}")
    health.record(run_id, results)
    data["collected_at"] = datetime.now().isoformat()

    total = sum(len(v) for v in data.values() if isinstance(v, list))
    if total == 0:
        print("No data collected. Aborting.")
        return

    # ── SILVER: transform → normalized events ──
    print("\n[SILVER] enrich → link → analyze → load")
    for key in TEXT_SOURCES:
        if data.get(key):
            data[key] = enrich_articles_with_casualties(data[key])

    mapper = ConflictMapper()
    data = mapper.enrich_all(data)

    # geocode text-source events that arrive without coordinates (news/RSS/telegram)
    from geocoder import enrich_missing_coords
    geo_n = enrich_missing_coords(data)
    print(f"  geocoded {geo_n} events missing coordinates")

    stats = data.get("_enrichment_stats", {})
    data = link_events(data)
    data["_analysis"] = run_analysis(data, date_str)

    save_events(data, date_str)
    save_daily_stats(date_str, data, stats)
    save_known_ucdp_ids([e.get("event_id") for e in data.get("ucdp", []) if e.get("event_id")])

    # fill actors from headlines (local LLM), then drop contentless empty shells
    try:
        from fill_actors import drop_empty_shells, drop_junk_events, agentic_enrich
        from database import get_conn
        _c = get_conn()
        _sh = drop_empty_shells(_c)
        _kj = drop_junk_events(_c)                 # cheap keyword pre-filter
        _drop, _enr = agentic_enrich(_c)           # LLM agent: understand → fill + drop
        _c.close()
        print(f"  cleanup: shells {_sh}, keyword-junk {_kj}, "
              f"agent-dropped {_drop}, agent-enriched {_enr}")
    except Exception as e:  # noqa: BLE001
        print(f"  cleanup skipped: {e}")

    # cross-source dedup via local LLM (free/private); heuristic fallback if unreachable
    try:
        deduplicate(days=7)
    except Exception as e:  # noqa: BLE001
        print(f"  dedup skipped: {e}")

    # crypto threat-finance — its own bronze → silver → gold medallion
    try:
        from pipeline import crypto as crypto_pipeline
        crypto_pipeline.run(run_id)
    except Exception as e:  # noqa: BLE001
        print(f"  crypto skipped: {e}")

    # ── GOLD: aggregates + brief ──
    print("\n[GOLD] aggregate + brief")
    report_dir = get_report_dir(target_date)
    (report_dir / f"{date_str}.md").write_text(build_report(data, target_date, mapper), encoding="utf-8")
    update_week_readme(report_dir, target_date)
    update_month_readme(report_dir, target_date)
    try:
        compute_stats()
    except Exception as e:  # noqa: BLE001
        print(f"  gold aggregate failed: {e}")

    raw_out = {k: v for k, v in data.items() if not k.startswith("_")}
    (report_dir / f"{date_str}_raw.json").write_text(
        json.dumps(raw_out, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    print(f"\n{'='*60}\n  DONE — {total} records | bronze+silver+gold complete\n{'='*60}")
    for h in health.latest():
        mark = "✓" if h["ok"] and h["count"] else ("·" if h["ok"] else "✗")
        print(f"   {mark} {h['source']:14} {h['count']:>5}")


def main() -> None:
    target = datetime.strptime(sys.argv[1], "%Y-%m-%d") if len(sys.argv) > 1 else datetime.now()
    run(target)


if __name__ == "__main__":
    main()
