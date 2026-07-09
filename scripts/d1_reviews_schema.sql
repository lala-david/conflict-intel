-- AI verification notes — one small row per REVIEWED event (kept small: only the
-- top-N high-value events the AI pass has cross-checked, not every event).
-- Written locally by scripts/ai_verify.py into conflict.db; this mirror lets the
-- live site (Cloudflare D1) read the same reviews. Apply once to D1, then have the
-- daily sync push new rows (see scripts/sync_to_d1.py — add "event_reviews").
--
--   cd web && npx wrangler d1 execute conflict-intel --remote --yes --file=../scripts/d1_reviews_schema.sql
CREATE TABLE IF NOT EXISTS event_reviews (
  event_id       TEXT PRIMARY KEY,
  ai_grade       TEXT,
  consistency    TEXT,
  toll_agreement TEXT,
  geo_confidence TEXT,
  summary        TEXT,
  model          TEXT,
  reviewed_at    TEXT
);
