"""
AI VERIFICATION PASS — LLM cross-check of high-value events (local LLM only).

For the top-N canonical events worth reviewing (recent + high fatalities, plus any
with 2+ corroborating sources) this assembles the distinct corroborating sources
that already live in the data — the event's own record plus every source record
clustered onto it via `dup_of` (source, source_url, notes, reported fatalities) —
and asks the self-hosted local LLM (scripts/llm.py) to cross-check them and emit a
STRICT-JSON verification note + a proposed grade. Results are upserted into a small
`event_reviews` table and shown on the site as an "AI-reviewed" panel. A human
console confirms forensic grade later; this is only the automatable bridge.

Cost-0 / graceful-degrade policy: uses the existing local LLM client (no new
dependency). If the LLM is unreachable or a response won't parse, the event is
skipped and logged — the pass NEVER crashes the pipeline. Safe to run in CI after
the pipeline with LOCAL_LLM_BASE_URL pointing at the model server.

  python scripts/ai_verify.py                 # review up to N=200 (default)
  python scripts/ai_verify.py --limit 50      # cap the batch
  python scripts/ai_verify.py --force         # re-review already-reviewed events
  AI_VERIFY_LIMIT=500 python scripts/ai_verify.py
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL  # noqa: E402
from llm import chat  # noqa: E402

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "conflict.db"

# selection window / defaults
RECENT_DAYS = 120
DEFAULT_LIMIT = int(os.getenv("AI_VERIFY_LIMIT", "200"))

# allowed enum values — anything outside these is treated as a parse failure
_CONSISTENCY = {"consistent", "partial", "conflicting"}
_TOLL = {"agree", "dispute", "single-source"}
_GEO = {"high", "medium", "low"}
_GRADE = {"verified", "corroborated", "reported", "machine-coded", "unclear"}


# ── LLM prompt (strict JSON) ────────────────────────────────────────────────
_SYS = (
    "You are a conflict-intelligence VERIFICATION analyst. You are given ONE incident "
    "and its corroborating source records (each: source, reported fatalities, and a note). "
    "Cross-check the sources against each other and judge how well they corroborate the "
    "same real-world incident. Return ONLY a compact JSON object — no prose, no markdown. "
    "Fields:\n"
    '  "consistency": "consistent" if the sources describe the same incident without '
    'contradiction, "partial" if they broadly agree but differ on some detail, '
    '"conflicting" if they contradict each other.\n'
    '  "toll_agreement": "agree" if the reported fatality figures are close/consistent, '
    '"dispute" if they differ materially, "single-source" if only one source reports a toll.\n'
    '  "geo_confidence": "high" | "medium" | "low" — how confidently the location is pinned '
    "from the sources.\n"
    '  "summary": a <=280 character plain-text note on what the sources agree and disagree on.\n'
    '  "proposed_grade": one of "verified", "corroborated", "reported", "machine-coded", '
    '"unclear" — the reliability grade the corroboration supports.'
)
_SHOTS = [
    (
        "Incident: 2026-05-01 · Syria · Raqqa\nReported fatalities (event): 5\n"
        "Sources (3):\n"
        "- ucdp | toll=5 | ISIS raid near Raqqa, 5 killed in overnight assault\n"
        "- wikipedia | toll=5 | Islamic State attack at Raqqa leaves five dead\n"
        "- google_news | toll=6 | Six reported killed in Raqqa militant raid",
        '{"consistency": "consistent", "toll_agreement": "agree", "geo_confidence": "high", '
        '"summary": "Three sources agree on an ISIS raid near Raqqa on the same day; tolls '
        'cluster at 5-6 killed. Location well pinned.", "proposed_grade": "verified"}',
    ),
    (
        "Incident: 2026-05-02 · Nigeria · (no location)\nReported fatalities (event): 12\n"
        "Sources (1):\n"
        "- gdelt | toll=0 | Machine-coded armed clash event, no casualty figure",
        '{"consistency": "consistent", "toll_agreement": "single-source", "geo_confidence": '
        '"low", "summary": "Only a single machine-coded GDELT record; no location and no '
        'corroborating human source. Toll unverified.", "proposed_grade": "machine-coded"}',
    ),
    (
        "Incident: 2026-05-03 · Sudan · Nyala\nReported fatalities (event): 40\n"
        "Sources (2):\n"
        "- google_news | toll=40 | Dozens killed in RSF shelling of Nyala market\n"
        "- expert_rss | toll=15 | At least 15 dead after clashes in Nyala",
        '{"consistency": "partial", "toll_agreement": "dispute", "geo_confidence": "high", '
        '"summary": "Two sources place clashes in Nyala but tolls diverge sharply (40 vs 15). '
        'Same location, disputed casualty count.", "proposed_grade": "corroborated"}',
    ),
]


def _llm_reachable() -> bool:
    """One up-front probe so an unreachable LLM skips fast instead of N timeouts."""
    try:
        return requests.get(f"{LOCAL_LLM_BASE_URL}/models", timeout=3).status_code == 200
    except Exception:
        return False


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS event_reviews (
            event_id       TEXT PRIMARY KEY,
            ai_grade       TEXT,
            consistency    TEXT,
            toll_agreement TEXT,
            geo_confidence TEXT,
            summary        TEXT,
            model          TEXT,
            reviewed_at    TEXT
        )
        """
    )
    conn.commit()


def _select_candidates(conn, limit: int, force: bool) -> list:
    """Canonical events worth reviewing: recent + high fatalities, plus any recent
    canonical event with 2+ corroborating sources (canonical row + >=1 dup)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")

    # Top-N recent canonical by fatalities.
    top = conn.execute(
        """
        SELECT id FROM events
         WHERE dup_of IS NULL AND date >= ?
         ORDER BY COALESCE(fatalities, 0) DESC
         LIMIT ?
        """,
        (cutoff, limit),
    ).fetchall()

    # Recent canonical events that already have >=1 corroborating dup (=> 2+ sources).
    corroborated = conn.execute(
        """
        SELECT e.id FROM events e
         WHERE e.dup_of IS NULL AND e.date >= ?
           AND EXISTS (SELECT 1 FROM events d WHERE d.dup_of = e.id)
        """,
        (cutoff,),
    ).fetchall()

    seen: set[str] = set()
    ids: list[str] = []
    for (eid,) in list(top) + list(corroborated):
        if eid and eid not in seen:
            seen.add(eid)
            ids.append(eid)

    if force:
        return ids

    reviewed = {r[0] for r in conn.execute("SELECT event_id FROM event_reviews").fetchall()}
    return [eid for eid in ids if eid not in reviewed]


def _gather_sources(conn, event_id: str) -> tuple[dict, list[dict]]:
    """The canonical event's headline fields + its distinct corroborating sources
    (own record + every dup), each as {source, source_url, notes, fatalities}."""
    ev = conn.execute(
        "SELECT id, date, country, location, fatalities FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    event = {
        "id": ev[0] if ev else event_id,
        "date": (ev[1] if ev else "") or "",
        "country": (ev[2] if ev else "") or "",
        "location": (ev[3] if ev else "") or "",
        "fatalities": (ev[4] if ev else 0) or 0,
    }

    rows = conn.execute(
        """
        SELECT source, source_url, notes, fatalities FROM events
         WHERE id = ? OR dup_of = ?
        """,
        (event_id, event_id),
    ).fetchall()

    # Collapse to distinct (source, note) so we don't feed the model duplicates.
    seen: set[tuple] = set()
    sources: list[dict] = []
    for source, url, notes, fat in rows:
        note = (notes or "").strip()
        key = ((source or "").lower(), note[:120].lower())
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "source": source or "unknown",
            "source_url": url or "",
            "notes": note,
            "fatalities": fat or 0,
        })
    return event, sources


def _build_user_prompt(event: dict, sources: list[dict]) -> str:
    loc = event["location"] or "(no location)"
    lines = [
        f"Incident: {event['date']} · {event['country']} · {loc}",
        f"Reported fatalities (event): {event['fatalities']}",
        f"Sources ({len(sources)}):",
    ]
    for s in sources:
        note = (s["notes"] or "(no description)").replace("\n", " ")[:220]
        lines.append(f"- {s['source']} | toll={s['fatalities']} | {note}")
    return "\n".join(lines)


def _parse_review(raw: str | None) -> dict | None:
    """Defensively parse the model's STRICT-JSON answer. Returns None on any
    failure or if an enum value is out of range."""
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None

    consistency = str(d.get("consistency", "")).strip().lower()
    toll = str(d.get("toll_agreement", "")).strip().lower()
    geo = str(d.get("geo_confidence", "")).strip().lower()
    grade = str(d.get("proposed_grade", "")).strip().lower()
    summary = str(d.get("summary", "")).strip()

    if consistency not in _CONSISTENCY:
        return None
    if toll not in _TOLL:
        return None
    if geo not in _GEO:
        return None
    if grade not in _GRADE:
        return None
    if not summary:
        return None

    return {
        "consistency": consistency,
        "toll_agreement": toll,
        "geo_confidence": geo,
        "proposed_grade": grade,
        "summary": summary[:280],
    }


def _upsert(conn, event_id: str, review: dict) -> None:
    conn.execute(
        """
        INSERT INTO event_reviews
            (event_id, ai_grade, consistency, toll_agreement, geo_confidence, summary, model, reviewed_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(event_id) DO UPDATE SET
            ai_grade       = excluded.ai_grade,
            consistency    = excluded.consistency,
            toll_agreement = excluded.toll_agreement,
            geo_confidence = excluded.geo_confidence,
            summary        = excluded.summary,
            model          = excluded.model,
            reviewed_at    = excluded.reviewed_at
        """,
        (
            event_id,
            review["proposed_grade"],
            review["consistency"],
            review["toll_agreement"],
            review["geo_confidence"],
            review["summary"],
            LOCAL_LLM_MODEL,
            _iso_now(),
        ),
    )
    conn.commit()


def _arg_limit(default: int) -> int:
    if "--limit" in sys.argv:
        try:
            return max(1, int(sys.argv[sys.argv.index("--limit") + 1]))
        except (IndexError, ValueError):
            pass
    return default


def main() -> int:
    import sqlite3

    force = "--force" in sys.argv
    limit = _arg_limit(DEFAULT_LIMIT)

    if not DB_PATH.exists():
        print(f"[ai_verify] DB not found at {DB_PATH} — nothing to do.")
        return 0

    if not _llm_reachable():
        print(f"[ai_verify] local LLM unreachable at {LOCAL_LLM_BASE_URL} — skipping "
              "(graceful no-op, e.g. CI without LAN access).")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    reviewed = skipped = errors = 0
    try:
        _ensure_table(conn)
        candidates = _select_candidates(conn, limit, force)
        print(f"[ai_verify] {len(candidates)} candidate event(s) to review "
              f"(limit={limit}, force={force}, model={LOCAL_LLM_MODEL}).")

        for event_id in candidates:
            try:
                event, sources = _gather_sources(conn, event_id)
                if not sources:
                    skipped += 1
                    continue
                user = _build_user_prompt(event, sources)
                raw = chat(_SYS, _SHOTS, user)  # None if LLM unreachable/failed
                review = _parse_review(raw)
                if review is None:
                    skipped += 1
                    print(f"  skip {event_id}: no parseable review")
                    continue
                _upsert(conn, event_id, review)
                reviewed += 1
                print(f"  ok   {event_id}: {review['proposed_grade']} "
                      f"({review['consistency']}/{review['toll_agreement']}/{review['geo_confidence']})")
            except Exception as exc:  # noqa: BLE001 — one bad event must not crash the pass
                errors += 1
                print(f"  ERR  {event_id}: {exc}")
                continue
    finally:
        conn.close()

    print(f"[ai_verify] done — reviewed={reviewed}, skipped={skipped}, errors={errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
