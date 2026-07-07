"""
Unified LLM toolkit for the pipeline — LOCAL LLM ONLY (cost-0 policy).

One place for every model call, so precision improvements land everywhere:
  - self-hosted Ollama model (config.LOCAL_LLM_MODEL, default gemma4:26b) over the
    OpenAI-compatible API. NO paid fallback: if the local LLM is unreachable
    (e.g. GitHub CI can't see the LAN), every helper returns None and callers fall
    back to their keyword/heuristic path. The full LLM enrichment therefore runs on
    local executions (a machine on the same network as the model server);
  - few-shot prompting for precision; reasoning disabled + tight timeouts so it
    never stalls the pipeline.

Public helpers: is_violence(text), extract_actor(text, country),
same_incident(a, b), analyze_event(text, country).
"""
import json
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
    return None  # local LLM only — no paid fallback (cost-0 policy)


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


# ── Agentic: read a raw news item and return a STRUCTURED understanding ──────
CATEGORIES = {"war", "civil_war", "insurgency", "terrorism", "counterterrorism",
              "state_violence", "communal_violence", "cartel_violence", "armed_violence",
              "mass_atrocity"}

_ANALYZE_SYS = (
    "You are a conflict-intelligence analyst. Read one news item and return ONLY a compact "
    "JSON object — no prose. Fields:\n"
    '  "conflict": true if it reports an act of ARMED or ORGANIZED VIOLENCE (war, armed '
    "attack, terrorism, armed clash, shooting, airstrike, bombing, shelling, militant/rebel/"
    "insurgent action, armed kidnapping); false for politics, elections, economy, prices, "
    "diplomacy, disease, natural disaster, weather, sports, ceremonies, announcements.\n"
    '  "category": one of [war, civil_war, insurgency, terrorism, counterterrorism, '
    "state_violence, communal_violence, cartel_violence, armed_violence, mass_atrocity], "
    "or null if conflict is false.\n"
    '  "actor": the primary armed perpetrator (group/military/state), or null.\n'
    '  "target": who was attacked (e.g. Civilians, Military, a named group), or null.\n'
    '  "location": the city/town/place, or null.\n'
    '  "fatalities": integer deaths if clearly stated, else null.\n'
    '  "confidence": 0.0-1.0.'
)
_ANALYZE_SHOTS = [
    ("Country: Mali\nBoko Haram fighters raided a village near Mopti, killing 12 civilians and torching homes",
     '{"conflict": true, "category": "terrorism", "actor": "Boko Haram", "target": "Civilians", '
     '"location": "Mopti", "fatalities": 12, "confidence": 0.92}'),
    ("Country: Ukraine\nRussian forces shelled a residential district of Kharkiv overnight; 3 dead",
     '{"conflict": true, "category": "war", "actor": "Russian military", "target": "Civilians", '
     '"location": "Kharkiv", "fatalities": 3, "confidence": 0.9}'),
    ("Country: Pakistan\nOgra notifies 15pc increase in regasified LNG price",
     '{"conflict": false, "category": null, "actor": null, "target": null, "location": null, '
     '"fatalities": null, "confidence": 0.96}'),
]


def analyze_event(text: str, country: str = "") -> dict | None:
    """Agentic structured read of a raw news item → normalized event fields."""
    out = chat(_ANALYZE_SYS, _ANALYZE_SHOTS, f"Country: {country}\n{(text or '')[:400]}")
    if not out:
        return None
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(d, dict) or "conflict" not in d:
        return None
    # normalize / validate
    d["conflict"] = bool(d.get("conflict"))
    cat = (d.get("category") or "").strip().lower() if d.get("category") else None
    d["category"] = cat if cat in CATEGORIES else None
    for k in ("actor", "target", "location"):
        v = d.get(k)
        d[k] = v.strip() if isinstance(v, str) and v.strip() and v.strip().lower() != "null" else None
    fat = d.get("fatalities")
    d["fatalities"] = fat if isinstance(fat, int) and fat >= 0 else None
    try:
        d["confidence"] = max(0.0, min(1.0, float(d.get("confidence", 0.5))))
    except Exception:
        d["confidence"] = 0.5
    return d


if __name__ == "__main__":
    print("local LLM:", _local_up())
    import json as _j
    for t in ["Gunmen kill 8 soldiers in a dawn ambush near Gao, northern Mali",
              "Ogra notifies 15pc increase in LNG price",
              "Israel government says it will defy Supreme Court ruling"]:
        print(f"  analyze({t[:38]!r}) = {_j.dumps(analyze_event(t), ensure_ascii=False)}")
    for t in ["Ogra notifies 15pc increase in LNG price",
              "Gunmen kill 8 soldiers in northern Mali ambush",
              "Macron to visit Syria"]:
        print(f"  is_violence({t[:40]!r}) = {is_violence(t)}")
