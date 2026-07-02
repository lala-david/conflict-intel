"""
Cross-source deduplication (Silver).

The same real-world incident often arrives from several sources (UCDP + a news
wire + a Telegram post). We:
  1. block candidate events by country + a ±1 day window (recent events only),
  2. prefilter pairs by cheap text similarity,
  3. confirm ambiguous pairs with a LOCAL LLM (Ollama, free & private),
  4. mark the lower-priority duplicate's `dup_of` → the canonical event id.

Canonical = most authoritative source (structured > news), fatalities as tiebreak.
The web serves `dup_of IS NULL` for a de-duplicated view.
"""
import sys
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database import get_conn  # noqa: E402
from config import LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL  # noqa: E402

# Higher = more authoritative → kept as the canonical record.
_PRIORITY = {
    "ucdp": 90, "wikipedia": 70, "nctc": 68, "gdelt": 50, "ofac": 40,
    "expert_rss": 35, "google_news": 30, "telegram": 20,
}


def _prio(src: str) -> int:
    for k, v in _PRIORITY.items():
        if src.startswith(k):
            return v
    return 10


def _desc(e: dict) -> str:
    a2 = f" vs {e['actor2']}" if e["actor2"] else ""
    place = e["location"] or e["country"]
    return f"{e['date'][:10]} {e['country']} — {e['actor1']}{a2} at {place}; {e['fatalities']} killed. {e['notes'][:140]}".strip()


def _llm_up() -> bool:
    """Fast health check — is the local LLM reachable? (Avoids per-pair timeouts in CI.)"""
    try:
        return requests.get(f"{LOCAL_LLM_BASE_URL}/models", timeout=3).status_code == 200
    except Exception:
        return False


def _llm_same(a: dict, b: dict) -> bool | None:
    """Ask the local LLM if two events are the same incident. None = unknown (LLM down)."""
    try:
        r = requests.post(
            f"{LOCAL_LLM_BASE_URL}/chat/completions",
            timeout=25,
            json={
                "model": LOCAL_LLM_MODEL,
                "temperature": 0,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You decide if two short conflict-event descriptions report the SAME real-world incident (same event, same place, same day). Reply with exactly one word: YES or NO."},
                    {"role": "user", "content": f"A: {_desc(a)}\nB: {_desc(b)}\nSame incident?"},
                ],
            },
        )
        if r.status_code == 200:
            ans = r.json()["choices"][0]["message"]["content"].strip().upper()
            return ans.startswith("YES") or ans[:6].find("YES") >= 0
    except Exception:
        return None
    return None


def deduplicate(days: int = 7) -> int:
    """Mark cross-source duplicates among events dated within the last `days`."""
    conn = get_conn()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
        if "dup_of" not in cols:
            conn.execute("ALTER TABLE events ADD COLUMN dup_of TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_dup ON events(dup_of)")
            conn.commit()

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT id, source, date, country, actor1, actor2, location, notes, fatalities
                 FROM events
                WHERE date >= ? AND is_aggregate = 0 AND dup_of IS NULL AND country != ''
                ORDER BY country, date""",
            (cutoff,),
        ).fetchall()
        keys = ["id", "source", "date", "country", "actor1", "actor2", "location", "notes", "fatalities"]
        events = [dict(zip(keys, [x if x is not None else "" for x in r])) for r in rows]

        by_country = defaultdict(list)
        for e in events:
            by_country[e["country"]].append(e)

        llm_ok = _llm_up()  # decide once — no per-pair timeouts when the LLM is unreachable (e.g. CI)
        marked = 0
        llm_calls = 0
        dropped: set[str] = set()
        for grp in by_country.values():
            if len(grp) < 2:
                continue
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    a, b = grp[i], grp[j]
                    if a["id"] in dropped or b["id"] in dropped:
                        continue
                    # ±1 day window
                    try:
                        da = datetime.strptime(a["date"][:10], "%Y-%m-%d")
                        db = datetime.strptime(b["date"][:10], "%Y-%m-%d")
                        if abs((da - db).days) > 1:
                            continue
                    except ValueError:
                        continue
                    sim = SequenceMatcher(
                        None,
                        f"{a['actor1']} {a['actor2']} {a['location']} {a['notes']}".lower()[:200],
                        f"{b['actor1']} {b['actor2']} {b['location']} {b['notes']}".lower()[:200],
                    ).ratio()
                    if sim < 0.35:
                        continue
                    if sim >= 0.85:
                        same = True
                    elif llm_ok:
                        same = _llm_same(a, b)
                        llm_calls += 1
                        if same is None:  # transient LLM error → skip this pair
                            continue
                    else:
                        continue  # no LLM (e.g. CI) → trust only strong similarity
                    if same:
                        keep, drop = (
                            (a, b)
                            if (_prio(a["source"]), a["fatalities"]) >= (_prio(b["source"]), b["fatalities"])
                            else (b, a)
                        )
                        conn.execute(
                            "UPDATE events SET dup_of = ? WHERE id = ? AND dup_of IS NULL",
                            (keep["id"], drop["id"]),
                        )
                        dropped.add(drop["id"])
                        marked += 1
        conn.commit()
        print(f"  [dedup] {marked} duplicates marked across sources ({llm_calls} local-LLM judgments)")
        return marked
    finally:
        conn.close()


if __name__ == "__main__":
    deduplicate()
