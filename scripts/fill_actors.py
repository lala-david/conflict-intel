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
from config import LOCAL_LLM_BASE_URL  # noqa: E402
from llm import is_violence, extract_actor, analyze_event  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "data" / "conflict.db"
NO_ACTOR = "(actor1 IS NULL OR TRIM(actor1)='' OR actor1='Unknown' OR actor1=UPPER(country))"
HAS_TEXT = "(notes IS NOT NULL AND TRIM(notes)!='')"

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
        actor = extract_actor(notes or "", country or "")
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


_DISASTER = re.compile(r"\b(ebola|outbreak|cholera|pandemic|covid|earthquake|flood|"
                       r"hurricane|cyclone|wildfire|drought|famine|measles)\b", re.I)
# attack-specific signals (deliberately NOT 'dead/kill' — disease/disaster news
# also "kills", so those generic words would keep genuine junk).
_VIOLENCE = re.compile(r"\b(attack|clash|strike|shell|bomb|militant|rebel|fighter|soldier|"
                       r"troop|gunmen|gunman|assault|raid|offensive|abduct|massacre|insurgent|"
                       r"armed|shoot|explos|drone|missile|siege|ambush|airstrike|jihad|terror)\b", re.I)


def drop_junk_events(conn: sqlite3.Connection) -> int:
    """Drop scraped news that isn't organized violence — natural-disaster / disease
    posts (from Telegram/Google News) with no violence signal in the text."""
    rows = conn.execute(
        "SELECT id, notes FROM events WHERE source IN ('telegram','google_news') "
        "AND dup_of IS NULL AND notes IS NOT NULL").fetchall()
    junk = [eid for eid, notes in rows
            if _DISASTER.search(notes or "") and not _VIOLENCE.search(notes or "")]
    for jid in junk:
        conn.execute("DELETE FROM events WHERE id = ?", (jid,))
    conn.commit()
    return len(junk)


def agentic_enrich(conn: sqlite3.Connection, budget: int = 100) -> tuple[int, int]:
    """Agentic pass over raw scraped text events: the LLM reads each item, drops
    non-conflict, and fills any missing actor / target / category / location /
    fatalities from its structured analysis. Fills gaps only — never overwrites
    existing values. Bounded by `budget` events/run."""
    rows = conn.execute(
        "SELECT id, notes, actor1, actor2, country, category, fatalities, location "
        "FROM events WHERE source IN ('telegram','google_news','expert_rss') "
        "AND dup_of IS NULL AND notes IS NOT NULL LIMIT ?", (budget,)).fetchall()
    dropped = enriched = 0
    for eid, notes, actor1, actor2, country, cat, fat, loc in rows:
        a = analyze_event(notes or "", country or "")
        if a is None:
            continue
        if not a["conflict"]:
            conn.execute("DELETE FROM events WHERE id = ?", (eid,))
            dropped += 1
            continue
        sets, vals = [], []
        blank = lambda v: not v or str(v).strip() in ("", "Unknown", "None")  # noqa: E731
        if blank(actor1) and a["actor"]:
            sets.append("actor1 = ?"); vals.append(a["actor"])
        if blank(actor2) and a["target"]:
            sets.append("actor2 = ?"); vals.append(a["target"])
        if blank(cat) and a["category"]:
            sets.append("category = ?"); vals.append(a["category"])
        if blank(loc) and a["location"]:
            sets.append("location = ?"); vals.append(a["location"])
        if (not fat or fat == 0) and a["fatalities"]:
            sets.append("fatalities = ?"); vals.append(a["fatalities"])
        if sets:
            conn.execute(f"UPDATE events SET {', '.join(sets)} WHERE id = ?", vals + [eid])
            enriched += 1
    conn.commit()
    return dropped, enriched


def drop_junk_llm(conn: sqlite3.Connection, budget: int = 80) -> int:
    """LLM pass over ambiguous scraped news (no clear attack keyword) — drops the
    ones the model says aren't armed violence. Bounded by `budget` calls/run."""
    rows = conn.execute(
        "SELECT id, notes FROM events WHERE source IN ('telegram','google_news') "
        "AND dup_of IS NULL AND notes IS NOT NULL").fetchall()
    ambiguous = [(i, n) for i, n in rows if not _VIOLENCE.search(n or "")][:budget]
    dropped = 0
    for eid, notes in ambiguous:
        if is_violence(notes or "") is False:
            conn.execute("DELETE FROM events WHERE id = ?", (eid,))
            dropped += 1
    conn.commit()
    return dropped


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
