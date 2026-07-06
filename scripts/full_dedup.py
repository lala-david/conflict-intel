"""
One-time FULL-history deduplication (local-LLM assisted).

The daily path (pipeline.dedup.deduplicate) only covers a 7-day window. This
sweeps the entire events table once:

  - skip UCDP-internal pairs      : UCDP-GED is academically pre-deduped (distinct
                                    events by design); comparing them is noise.
  - exact structural key          : same date + actor1 + location + fatalities across
                                    sources → mark as duplicate (no LLM, 100% reliable).
  - textful ambiguous pairs       : both have real notes/location and 0.35 ≤ sim < 0.9
                                    → ask the LOCAL LLM if they are the same incident.
  - sparse-text pairs             : skipped — their similarity is meaningless (empty
                                    notes give false 1.0 matches), the exact key already
                                    caught the reliable ones.

Sliding ±1-day window over date-sorted, country-grouped events → scales to the
full 420k without O(n²) blowup. Marks `dup_of`; never hard-deletes.
"""
import sys
import time
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.dedup import _llm_same, _llm_up, _openai_same, _prio  # noqa: E402
from database import get_conn  # noqa: E402

KEYS = ["id", "source", "date", "country", "actor1", "actor2", "location", "notes", "fatalities"]


def _textful(e: dict) -> bool:
    return bool((e["notes"] or "").strip()) or bool((e["location"] or "").strip())


def _exact_key(e: dict) -> tuple:
    return (e["date"][:10], (e["actor1"] or "").lower().strip(),
            (e["location"] or "").lower().strip(), e["fatalities"])


def main() -> None:
    conn = get_conn()
    llm_ok = _llm_up()
    import os
    openai_ok = (not llm_ok) and bool(os.getenv("OPENAI_API_KEY"))
    mode = "local-llm" if llm_ok else ("openai" if openai_ok else "heuristic-only")
    print(f"[full-dedup] confirmer: {mode}", flush=True)

    rows = conn.execute(
        """SELECT id, source, date, country, actor1, actor2, location, notes, fatalities
             FROM events
            WHERE is_aggregate = 0 AND dup_of IS NULL AND country != ''
            ORDER BY country, date""").fetchall()
    events = [dict(zip(KEYS, [x if x is not None else "" for x in r])) for r in rows]
    print(f"[full-dedup] scanning {len(events):,} events", flush=True)

    by_country: dict[str, list] = defaultdict(list)
    for e in events:
        by_country[e["country"]].append(e)

    dropped: set[str] = set()
    marked_exact = marked_llm = llm_calls = 0
    t0 = time.time()

    def _mark(a: dict, b: dict) -> None:
        nonlocal dropped
        keep, drop = ((a, b) if (_prio(a["source"]), a["fatalities"])
                      >= (_prio(b["source"]), b["fatalities"]) else (b, a))
        conn.execute("UPDATE events SET dup_of = ? WHERE id = ? AND dup_of IS NULL",
                     (keep["id"], drop["id"]))
        dropped.add(drop["id"])

    for ci, grp in enumerate(by_country.values()):
        if len(grp) < 2:
            continue
        for i in range(len(grp)):
            a = grp[i]
            if a["id"] in dropped:
                continue
            try:
                da = datetime.strptime(a["date"][:10], "%Y-%m-%d")
            except ValueError:
                continue
            a_ucdp = a["source"].startswith("ucdp")
            a_key = _exact_key(a)
            a_textful = _textful(a)
            for j in range(i + 1, len(grp)):
                b = grp[j]
                if b["id"] in dropped:
                    continue
                try:
                    db = datetime.strptime(b["date"][:10], "%Y-%m-%d")
                except ValueError:
                    continue
                if (db - da).days > 1:
                    break
                if a_ucdp and b["source"].startswith("ucdp"):
                    continue
                # 1) exact structural key → reliable duplicate, no LLM
                if a_key == _exact_key(b):
                    _mark(a, b)
                    marked_exact += 1
                    continue
                # 2) textful ambiguous → local-LLM judgment
                if not (a_textful and _textful(b)):
                    continue
                sim = SequenceMatcher(
                    None,
                    f"{a['actor1']} {a['actor2']} {a['location']} {a['notes']}".lower()[:200],
                    f"{b['actor1']} {b['actor2']} {b['location']} {b['notes']}".lower()[:200],
                ).ratio()
                if sim < 0.35 or sim >= 0.9:
                    if sim >= 0.9:
                        _mark(a, b)
                        marked_llm += 1
                    continue
                same = _llm_same(a, b) if llm_ok else (_openai_same(a, b) if openai_ok else None)
                llm_calls += 1
                if same:
                    _mark(a, b)
                    marked_llm += 1
        if ci % 20 == 0:
            conn.commit()
            print(f"  …country {ci}: exact={marked_exact} llm_marked={marked_llm} "
                  f"llm_calls={llm_calls} ({time.time()-t0:.0f}s)", flush=True)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM events WHERE dup_of IS NOT NULL").fetchone()[0]
    conn.close()
    print(f"[full-dedup] DONE — exact={marked_exact}, llm_marked={marked_llm}, "
          f"llm_calls={llm_calls}, total dup_of now {total} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
