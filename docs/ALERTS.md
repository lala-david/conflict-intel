# Telegram alerts

After every pipeline run, `scripts/alerts.py` pushes the run's **new notable
events** (terrorism / mass-atrocity, or ≥ 5 killed) to a Telegram chat or channel.
Each event is sent once (tracked in the `alerted_events` table). It no-ops unless
both secrets are set, so local runs stay silent.

## Setup (5 min)

1. **Create a bot** — DM [@BotFather](https://t.me/BotFather) → `/newbot` → copy the
   token (`123456:ABC...`).

2. **Create a channel** (e.g. `@ThreatPulse`) and **add the bot as an admin** so it
   can post. (For a private chat instead, get the numeric chat id from
   `https://api.telegram.org/bot<token>/getUpdates` after messaging the bot.)

3. **Add the two secrets:**
   ```
   gh secret set TELEGRAM_BOT_TOKEN --body "123456:ABC..."
   gh secret set TELEGRAM_ALERT_CHAT --body "@ThreatPulse"
   ```

Done. The daily job (3×/day) now posts new notable events to the channel — which
also doubles as a public distribution channel people can follow.

## Message format
```
🔴 Nigeria · terrorism
Boko Haram — Maiduguri, Nigeria
14 killed · 2026-07-07
Gunmen raided a village overnight …
Details →
```
`🔴` = ≥ 10 killed, `🟠` = notable. Tune the threshold/limit in `send_alerts()`.
