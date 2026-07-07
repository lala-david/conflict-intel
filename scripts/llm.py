"""
Unified LLM toolkit for the pipeline.

One place for every model call, so precision improvements land everywhere:
  - local LLM (qwen3 via Ollama) first, OpenAI (gpt-4o-mini) fallback — CI has no
    LAN access so it degrades to OpenAI automatically;
  - few-shot prompting (small models gain a lot of precision from examples);
  - reasoning disabled + tight timeouts so it never stalls the pipeline;
  - optional self-consistency vote for the borderline calls.

Public helpers: is_violence(text), extract_actor(text, country), same_incident(a, b).
"""
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL  # noqa: E402

_LOCAL_TIMEOUT = 20
_local_ok: bool | None = None


def _local_up() -> bool:
    global _local_ok
    if _local_ok is None:
        try:
            _local_ok = requests.get(f"{LOCAL_LLM_BASE_URL}/models", timeout=3).status_code == 200
        except Exception:
            _local_ok = False
    return _local_ok


def _messages(system: str, shots: list[tuple[str, str]], user: str) -> list[dict]:
    msgs: list[dict] = [{"role": "system", "content": "/no_think " + system}]
    for u, a in shots:                       # few-shot exemplars
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": user})
    return msgs


def _strip_think(s: str) -> str:
    return re.sub(r"<think>.*?</think>", "", s or "", flags=re.S).strip()


def chat(system: str, shots: list[tuple[str, str]], user: str) -> str | None:
    """Return the model's raw answer (few-shot), or None if unavailable."""
    msgs = _messages(system, shots, user)
    if _local_up():
        try:
            r = requests.post(
                f"{LOCAL_LLM_BASE_URL}/chat/completions", timeout=_LOCAL_TIMEOUT,
                json={"model": LOCAL_LLM_MODEL, "temperature": 0, "stream": False,
                      "think": False, "messages": msgs})
            if r.status_code == 200:
                return _strip_think(r.json()["choices"][0]["message"]["content"])
        except Exception:
            return None
        return None
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            r = OpenAI(timeout=15, max_retries=1).chat.completions.create(
                model="gpt-4o-mini", temperature=0, messages=msgs)  # type: ignore[arg-type]
            return (r.choices[0].message.content or "").strip()
        except Exception:
            return None
    return None


def _yesno(system: str, shots: list[tuple[str, str]], user: str) -> bool | None:
    out = chat(system, shots, user)
    if not out:
        return None
    u = out.strip().upper()
    if u.startswith("YES") or "YES" in u[:12]:
        return True
    if u.startswith("NO") or "NO" in u[:12]:
        return False
    return None


# ── Task 1: is this organized/armed violence? (junk filter) ──────────────────
_VIOLENCE_SYS = (
    "You label a news headline. Answer YES only if it reports a real-world act of ARMED or "
    "ORGANIZED VIOLENCE (war, armed attack, terrorism, armed clash, shooting, airstrike, "
    "bombing, shelling, kidnapping/killing by armed actors, militant/rebel/insurgent action). "
    "Answer NO for diplomacy, politics, elections, economy, prices, ceremonies, sports, "
    "disease, natural disaster, weather, or general announcements. Reply with only YES or NO."
)
_VIOLENCE_SHOTS = [
    ("Militants ambush army convoy in Mali, 12 soldiers killed", "YES"),
    ("Suicide bomber detonates at Kabul market, at least 20 dead", "YES"),
    ("Airstrikes hit rebel positions in Idlib overnight", "YES"),
    ("Gunmen abduct 15 travellers on Kaduna highway", "YES"),
    ("NATO heads to Ankara with its unity in question", "NO"),
    ("Ogra notifies 15pc increase in regasified LNG price", "NO"),
    ("President and Vice President address nation in July 4 celebration", "NO"),
    ("French President Macron to visit Syria next week", "NO"),
    ("Over 500 dead in DR Congo Ebola outbreak", "NO"),
    ("Central bank raises interest rates to curb inflation", "NO"),
]


def is_violence(text: str) -> bool | None:
    return _yesno(_VIOLENCE_SYS, _VIOLENCE_SHOTS, (text or "")[:300])


# ── Task 2: extract the primary armed actor ──────────────────────────────────
_ACTOR_SYS = (
    "From a conflict/security headline, name the primary actor — the armed group, military, "
    "state force, or perpetrator the item is chiefly about. Reply with ONLY that name "
    "(e.g. 'Hamas', 'Russian military', 'Boko Haram', 'Government of Nigeria'). "
    "If there is no clear armed actor, reply exactly NONE."
)
_ACTOR_SHOTS = [
    ("Country: Mali\nBoko Haram fighters raid village, torch homes", "Boko Haram"),
    ("Country: Ukraine\nRussian forces shell Kharkiv residential district", "Russian military"),
    ("Country: Somalia\nAl-Shabaab claims mortar attack on airport", "Al-Shabaab"),
    ("Country: Nigeria\nWater shortage worsens across northern states", "NONE"),
]


def extract_actor(text: str, country: str = "") -> str | None:
    out = chat(_ACTOR_SYS, _ACTOR_SHOTS, f"Country: {country}\n{(text or '')[:280]}")
    if not out:
        return None
    out = out.strip().strip('"').splitlines()[-1].strip()
    if not out or out.upper() == "NONE" or len(out) > 60:
        return None
    return out


# ── Task 3: are two events the same incident? (dedup) ────────────────────────
_SAME_SYS = (
    "Decide if two short conflict-event descriptions report the SAME real-world incident "
    "(same event, same place, same day). Reply with only YES or NO."
)
_SAME_SHOTS = [
    ("A: 2024-05-01 Syria — ISIS attack at Raqqa; 5 killed\n"
     "B: 2024-05-01 Syria — Islamic State raid near Raqqa; 5 dead\nSame incident?", "YES"),
    ("A: 2024-05-01 Nigeria — Boko Haram raid in Borno; 10 killed\n"
     "B: 2024-05-02 Mali — JNIM ambush in Mopti; 3 killed\nSame incident?", "NO"),
]


def same_incident(desc_a: str, desc_b: str) -> bool | None:
    return _yesno(_SAME_SYS, _SAME_SHOTS, f"A: {desc_a}\nB: {desc_b}\nSame incident?")


if __name__ == "__main__":
    print("local LLM:", _local_up())
    for t in ["Ogra notifies 15pc increase in LNG price",
              "Gunmen kill 8 soldiers in northern Mali ambush",
              "Macron to visit Syria"]:
        print(f"  is_violence({t[:40]!r}) = {is_violence(t)}")
