"""
ONE-TIME bulk deduplication over the ENTIRE events DB.

Multi-LLM ensemble cross-validation (local Ollama models) confirms whether two
similar events are the same real-world incident; a majority vote marks the
lower-priority record's `dup_of` → the canonical one.

Strategy (keeps the LLM workload bounded on 400k+ rows):
  - block by (country, ±1 day),
  - cheap lexical similarity prefilter,
  - `sim >= AUTO_SIM`  → duplicate without asking any LLM,
  - `MIN_SIM <= sim < AUTO_SIM` → ensemble vote (majority = duplicate),
  - resumable: already-marked rows are skipped on re-run.

Usage:
  python scripts/pipeline/bulk_dedup.py estimate      # count candidate pairs (no LLM)
  python scripts/pipeline/bulk_dedup.py run [limit]   # run the ensemble dedup
"""
import re
import sys
import time
import requests
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database import get_conn  # noqa: E402
from config import LOCAL_LLM_BASE_URL  # noqa: E402

ENSEMBLE = ["qwen3:8b", "gemma4-12b-obliterated:q8", "gpt-oss:20b"]
MIN_SIM = 0.45
AUTO_SIM = 0.90

_PRIORITY = {"ucdp": 90, "wikipedia": 70, "nctc": 68, "gdelt": 50, "ofac": 40,
             "expert_rss": 35, "google_news": 30, "telegram": 20}


def _prio(src: str) -> int:
    for k, v in _PRIORITY.items():
        if src.startswith(k):
            return v
    return 10


def _family(src: str) -> str:
    return src.split("-")[0]


def _blob(e: dict) -> str:
    return f"{e['actor1']} {e['actor2']} {e['location']} {e['notes']}".lower()[:220]


_STOP = {"government", "forces", "unknown", "civilians", "military", "police",
         "state", "attack", "killed", "people", "group", "armed", "against", "near"}


def _tokens(e: dict) -> set[str]:
    txt = f"{e['actor1']} {e['actor2']} {e['location']} {e['notes']}".lower()
    return {w for w in re.findall(r"[a-z]{4,}", txt) if w not in _STOP}


def _desc(e: dict) -> str:
    a2 = f" vs {e['actor2']}" if e["actor2"] else ""
    return f"{e['date'][:10]} {e['country']} — {e['actor1']}{a2} at {e['location'] or e['country']}; {e['fatalities']} killed. {e['notes'][:130]}"


def _ask(model: str, a: dict, b: dict) -> bool | None:
    try:
        r = requests.post(
            f"{LOCAL_LLM_BASE_URL}/chat/completions", timeout=90,
            json={"model": model, "temperature": 0, "stream": False, "messages": [
                {"role": "system", "content": "Decide if two short conflict-event descriptions report the SAME real-world incident (same event, place, day). Reply exactly YES or NO."},
                {"role": "user", "content": f"A: {_desc(a)}\nB: {_desc(b)}\nSame incident?"}]})
        if r.status_code == 200:
            ans = r.json()["choices"][0]["message"]["content"].upper()
            return "YES" in ans and "NO" not in ans.replace("KNOW", "")
    except Exception:
        return None
    return None


def _vote(a: dict, b: dict, models: list[str]) -> bool:
    yes = 0
    votes = 0
    for m in models:
        v = _ask(m, a, b)
        if v is None:
            continue
        votes += 1
        yes += 1 if v else 0
    return votes > 0 and yes * 2 > votes  # strict majority


def _load() -> list[dict]:
    conn = get_conn()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
        if "dup_of" not in cols:
            conn.execute("ALTER TABLE events ADD COLUMN dup_of TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_dup ON events(dup_of)")
            conn.commit()
        rows = conn.execute(
            """SELECT id, source, date, country, actor1, actor2, location, notes, fatalities
                 FROM events WHERE is_aggregate = 0 AND dup_of IS NULL AND country != ''
                 AND date LIKE '____-__-__' ORDER BY country, date"""
        ).fetchall()
    finally:
        conn.close()
    k = ["id", "source", "date", "country", "actor1", "actor2", "location", "notes", "fatalities"]
    return [dict(zip(k, [x if x is not None else "" for x in r])) for r in rows]


def _candidate_pairs(events: list[dict], block_cap: int = 500):
    """Only cross-source pairs that share a distinctive token, blocked by country+day.

    Single-source historical UCDP blocks (which UCDP already de-duplicated) are
    skipped entirely — cross-source overlap is where real duplicates live.
    """
    blocks = defaultdict(list)
    for e in events:
        blocks[(e["country"], e["date"][:10])].append(e)  # country + DAY
    for grp in blocks.values():
        if len(grp) < 2 or len(grp) > block_cap:
            continue
        if len({_family(e["source"]) for e in grp}) < 2:
            continue  # need ≥2 source families for a cross-source duplicate
        toks = [_tokens(e) for e in grp]
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                a, b = grp[i], grp[j]
                if _family(a["source"]) == _family(b["source"]):
                    continue  # only cross-source pairs
                if not (toks[i] & toks[j]):
                    continue  # must share a distinctive token
                yield a, b, SequenceMatcher(None, _blob(a), _blob(b)).ratio()


def estimate():
    events = _load()
    auto = cross = same = 0
    for a, b, sim in _candidate_pairs(events):
        if sim >= AUTO_SIM:
            auto += 1
        elif _family(a["source"]) != _family(b["source"]):
            cross += 1
        else:
            same += 1
    llm = cross + same
    print(f"  events considered:   {len(events):,}")
    print(f"  auto-dup (sim>={AUTO_SIM}): {auto:,}  (no LLM)")
    print(f"  LLM pairs (ensemble x{len(ENSEMBLE)}): {llm:,}  (~cross {cross:,} / same {same:,})")
    print(f"  est. LLM calls: {llm*len(ENSEMBLE):,}  → rough time @6s: {llm*len(ENSEMBLE)*6/3600:.1f} h")


def run(limit: int | None = None):
    events = _load()
    conn = get_conn()
    marked = auto = llm = 0
    dropped: set[str] = set()
    t0 = time.time()
    try:
        for a, b, sim in _candidate_pairs(events):
            if limit and llm >= limit:
                break
            if a["id"] in dropped or b["id"] in dropped:
                continue
            if sim >= AUTO_SIM:
                same = True
                auto += 1
            else:
                same = _vote(a, b, ENSEMBLE)
                llm += 1
            if same:
                keep, drop = ((a, b) if (_prio(a["source"]), a["fatalities"]) >= (_prio(b["source"]), b["fatalities"]) else (b, a))
                conn.execute("UPDATE events SET dup_of=? WHERE id=? AND dup_of IS NULL", (keep["id"], drop["id"]))
                dropped.add(drop["id"])
                marked += 1
            if marked and marked % 25 == 0:
                conn.commit()
            if llm and llm % 50 == 0:
                print(f"    …{llm} LLM votes, {marked} dups, {time.time()-t0:.0f}s")
        conn.commit()
    finally:
        conn.close()
    print(f"  [bulk_dedup] {marked} duplicates marked ({auto} auto, {llm} ensemble votes) in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "estimate"
    if cmd == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        estimate()
