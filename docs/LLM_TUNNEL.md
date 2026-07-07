# Give CI the local LLM (Cloudflare Tunnel)

The daily GitHub Actions run can't reach the LLM on your LAN
(`192.168.150.225:11434`), so by default its LLM steps skip. To get the full
gemma4 enrichment in CI **for free**, expose the model through a Cloudflare Tunnel.

Run this **on the model server** (the machine that runs Ollama), not your laptop —
the server is always on, so CI always has the model.

## One-time setup

1. **Make Ollama listen on the network** (if it isn't already):
   ```
   # Ollama env: OLLAMA_HOST=0.0.0.0
   ```

2. **Install cloudflared** and log in (free Cloudflare account):
   ```
   # Windows: winget install --id Cloudflare.cloudflared
   cloudflared tunnel login
   ```

3. **Create a named tunnel + stable hostname** (needs a domain on Cloudflare):
   ```
   cloudflared tunnel create conflict-llm
   cloudflared tunnel route dns conflict-llm llm.<yourdomain>.com
   cloudflared tunnel run --url http://localhost:11434 conflict-llm
   ```
   (Run it as a service so it stays up: `cloudflared service install`.)

   *Quick test without a domain:* `cloudflared tunnel --url http://localhost:11434`
   prints a temporary `https://xxxx.trycloudflare.com` URL — fine for a trial, but
   it changes on restart, so use a named tunnel for the daily job.

4. **Add the GitHub secret** so CI uses it:
   ```
   gh secret set LOCAL_LLM_BASE_URL --body "https://llm.<yourdomain>.com/v1"
   ```
   (Note the **`/v1`** suffix — it's the OpenAI-compatible path.)

That's it. On the next run the pipeline logs `dedup confirmer: local-llm` and the
agentic enrichment runs in CI. If the tunnel/server is down, the LLM steps just
skip — the run still succeeds.

## Security
The tunnel exposes only the Ollama port. Add Cloudflare Access (allow only the
GitHub Actions egress, or a service token) if you want to lock it down.
