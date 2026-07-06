"""
Fill a missing actor from the event's own text using the local LLM.

Events without an extracted actor but WITH a headline/notes (mostly news/RSS) get
their `actor1` inferred from that text. Truly text-less events are left for the
empty-shell cleanup instead. Uses the local LLM (qwen3, reasoning disabled).
"""
import re
import sys
import sqlite3
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "data" / "conflict.db"
NO_ACTOR = "(actor1 IS NULL OR TRIM(actor1)='' OR actor1='Unknown' OR actor1=UPPER(country))"
HAS_TEXT = "(notes IS NOT NULL AND TRIM(notes)!='')"

SYS = ("/no_think You extract the primary actor from a conflict/security news headline: "
       "the armed group, military, state, or perpetrator the item is chiefly about. "
       "Reply with ONLY that actor's name (e.g. 'Hamas', 'Russian military', "
       "'Government of Nigeria', 'ISIS'). If there is no clear actor, reply exactly NONE.")


def _extract(text: str, country: str) -> str | None:
    try:
        r = requests.post(
            f"{LOCAL_LLM_BASE_URL}/chat/completions", timeout=30,
            json={"model": LOCAL_LLM_MODEL, "temperature": 0, "stream": False, "think": False,
                  "messages": [{"role": "system", "content": SYS},
                               {"role": "user", "content": f"Country: {country}\nHeadline: {text}"}]})
        if r.status_code != 200:
            return None
        out = r.json()["choices"][0]["message"]["content"] or ""
        out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip().strip('"').strip()
        out = out.splitlines()[-1].strip() if out else ""
        if not out or out.upper() == "NONE" or len(out) > 60:
            return None
        return out
    except Exception:
        return None


# actor missing AND no headline AND no place AND no deaths → a contentless shell
NO_TEXT = "(notes IS NULL OR TRIM(notes)='')"
NO_LOC = "(location IS NULL OR TRIM(location)='' OR location='None')"
NO_FAT = "(fatalities IS NULL OR fatalities=0)"
SHELL = f"{NO_ACTOR} AND {NO_TEXT} AND {NO_LOC} AND {NO_FAT}"


def _llm_reachable() -> bool:
    try:
        return requests.get(f"{LOCAL_LLM_BASE_URL}/models", timeout=3).status_code == 200
    except Exception:
        return False


def fill_missing_actors(conn: sqlite3.Connection, limit: int = 500) -> int:
    """LLM-infer actor1 for actor-less events that still have a headline.
    No-op when the local LLM is unreachable (e.g. GitHub CI) — avoids per-row timeouts."""
    if not _llm_reachable():
        return 0
    rows = conn.execute(
        f"SELECT id, country, notes FROM events WHERE {NO_ACTOR} AND {HAS_TEXT} LIMIT ?",
        (limit,)).fetchall()
    filled = 0
    for eid, country, notes in rows:
        actor = _extract((notes or "")[:300], country or "")
        if actor:
            conn.execute("UPDATE events SET actor1 = ? WHERE id = ?", (actor, eid))
            filled += 1
    conn.commit()
    return filled


def drop_empty_shells(conn: sqlite3.Connection) -> int:
    """Delete contentless events (no actor, no headline, no place, no deaths)."""
    n = conn.execute(f"SELECT COUNT(*) FROM events WHERE {SHELL}").fetchone()[0]
    conn.execute(f"DELETE FROM events WHERE {SHELL}")
    conn.commit()
    return n


def main() -> None:
    conn = sqlite3.connect(DB)
    total = conn.execute(f"SELECT COUNT(*) FROM events WHERE {NO_ACTOR} AND {HAS_TEXT}").fetchone()[0]
    print(f"[fill-actors] {total} events to enrich", flush=True)
    filled = fill_missing_actors(conn, limit=total or 1)
    dropped = drop_empty_shells(conn)
    conn.close()
    print(f"[fill-actors] DONE — filled {filled}, dropped {dropped} shells", flush=True)


if __name__ == "__main__":
    main()
