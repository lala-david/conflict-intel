# Manual setup — do later ⏳

Everything below is **coded and ready**; it just needs a secret/credential to turn
on. Until then each feature no-ops safely. Knock these out whenever.

## 1. Telegram alerts  →  see [ALERTS.md](./ALERTS.md)
Broadcast new notable events (terror / ≥5 killed) to a Telegram channel, 3×/day.
Also doubles as a public distribution channel.

- [ ] Create a bot with [@BotFather](https://t.me/BotFather) → get the token
- [ ] Create a channel (e.g. `@ThreatPulse`) and add the bot as **admin**
- [ ] `gh secret set TELEGRAM_BOT_TOKEN --body "<token>"`
- [ ] `gh secret set TELEGRAM_ALERT_CHAT --body "@ThreatPulse"`

## 2. CI uses the local LLM  →  see [LLM_TUNNEL.md](./LLM_TUNNEL.md)
Give the daily GitHub run the full gemma4 enrichment for free by exposing the
self-hosted model through a Cloudflare Tunnel (run on the model server).

- [ ] Run `cloudflared tunnel` → stable `https://…/` URL for `http://localhost:11434`
- [ ] `gh secret set LOCAL_LLM_BASE_URL --body "https://…/v1"`

> Without #2, the daily CI still runs — it just uses keyword cleanup + heuristic
> dedup instead of the LLM. Full LLM enrichment runs on **local** executions.
