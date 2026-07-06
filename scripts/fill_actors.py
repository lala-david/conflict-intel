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


def main() -> None:
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        f"SELECT id, country, notes FROM events WHERE {NO_ACTOR} AND {HAS_TEXT}").fetchall()
    print(f"[fill-actors] {len(rows)} events to enrich", flush=True)
    filled = 0
    for i, (eid, country, notes) in enumerate(rows, 1):
        actor = _extract(notes[:300], country or "")
        if actor:
            conn.execute("UPDATE events SET actor1 = ? WHERE id = ?", (actor, eid))
            filled += 1
        if i % 25 == 0:
            conn.commit()
            print(f"  …{i}/{len(rows)} filled={filled}", flush=True)
    conn.commit()
    conn.close()
    print(f"[fill-actors] DONE — filled {filled}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
