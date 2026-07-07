"""
Telegram alerts — broadcast the run's new notable events to a Telegram chat/channel.

Fires from the pipeline after each run. Only sends events collected this run that
are notable (terrorism / mass-atrocity, or >= 5 killed) and haven't been alerted
before (tracked in `alerted_events`). No-ops unless TELEGRAM_BOT_TOKEN and
TELEGRAM_ALERT_CHAT are set, so local/dev runs stay quiet.

  TELEGRAM_BOT_TOKEN=...  (from @BotFather)
  TELEGRAM_ALERT_CHAT=... (channel @handle or numeric chat id; bot must be admin)
"""
import os
import re
from datetime import datetime

import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT = os.getenv("TELEGRAM_ALERT_CHAT", "")
SITE = "https://conflict-intel.conflict-intel.workers.dev"


def _clean(s: str) -> str:
    s = re.sub(r"https?://\S+|t\.me/\S+", "", s or "")
    s = re.sub(r"\s*[|;]\s*", " · ", s).strip(" ·-")
    return re.sub(r"\s{2,}", " ", s)[:160]


def _send(text: str) -> bool:
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def send_alerts(conn, max_alerts: int = 8) -> int:
    """Post new notable events to Telegram. Returns how many were sent."""
    if not TOKEN or not CHAT:
        return 0
    conn.execute("CREATE TABLE IF NOT EXISTS alerted_events (id TEXT PRIMARY KEY)")
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT id, date, country, actor1, actor2, location, fatalities, category, notes
             FROM events
            WHERE collected_at LIKE ? AND dup_of IS NULL AND is_aggregate = 0
              AND country != ''
              AND (category IN ('terrorism','counterterrorism','mass_atrocity')
                   OR fatalities >= 5)
              AND id NOT IN (SELECT id FROM alerted_events)
            ORDER BY fatalities DESC
            LIMIT ?""",
        (today + "%", max_alerts)).fetchall()
    sent = 0
    for eid, date, country, a1, a2, loc, fat, cat, notes in rows:
        fat = fat or 0
        emoji = "🔴" if fat >= 10 else "🟠"
        actor = a1 or "Unknown actor"
        vs = f" vs {a2}" if a2 and a2 != "Civilians" else ""
        place = f"{loc}, {country}" if loc else country
        desc = _clean(notes)
        body = (
            f"{emoji} <b>{country}</b> · {(cat or 'armed_violence').replace('_', ' ')}\n"
            f"<b>{actor}</b>{vs} — {place}\n"
            f"{fat} killed · {date[:10]}"
            + (f"\n<i>{desc}</i>" if desc else "")
            + f"\n\n<a href=\"{SITE}/events/{eid}\">Details →</a>"
        )
        if _send(body):
            conn.execute("INSERT OR IGNORE INTO alerted_events (id) VALUES (?)", (eid,))
            sent += 1
    conn.commit()
    return sent


if __name__ == "__main__":
    import sqlite3
    print("token set:", bool(TOKEN), "| chat:", CHAT or "(none)")
    print("would send:", send_alerts(sqlite3.connect("data/conflict.db")))
