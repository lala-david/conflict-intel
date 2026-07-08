-- App-owned demand-capture table (not part of the pipeline's conflict.db schema).
-- Apply once to D1 after the initial import so the /api/waitlist writes have a home:
--   cd web && npx wrangler d1 execute conflict-intel --remote --file=../scripts/d1_waitlist_schema.sql
CREATE TABLE IF NOT EXISTS waitlist (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  email      TEXT NOT NULL,
  interest   TEXT,
  note       TEXT,
  source     TEXT,
  created_at TEXT
);
