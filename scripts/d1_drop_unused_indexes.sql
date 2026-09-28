-- D1-only: drop event indexes that nothing on the D1 side uses (2026-09).
--
--   cd web && npx wrangler d1 execute conflict-intel --remote --yes --file=../scripts/d1_drop_unused_indexes.sql
--
-- On D1 every index entry a write touches is billed as a written row (free tier:
-- 100K/day), so each events index costs one extra write per inserted event. These
-- four serve no query that runs against D1:
--
--   * web: EXPLAIN QUERY PLAN over the site's event queries — the 36 static ones
--     plus the /events and /api/events filter builders across 16 filter
--     combinations (count + page each) — shows no plan change and no new scan
--     with them gone.
--   * sync_to_d1.py: looks events up by primary key, country (idx_ev_country_*)
--     and dup_of (idx_events_dup) only.
--
-- Dropping them takes an event insert on D1 from ~14 to ~10 written rows.
--
-- LOCAL KEEPS THEM on purpose: idx_events_date_fatal is what serves date lookups in
-- the pipeline since idx_events_date was folded into it (scripts/database.py), and
-- scripts/backfill.py looks events up by source_url. init_db never touches D1, so
-- the two schemas are allowed to differ here.
DROP INDEX IF EXISTS idx_events_fatalities;
DROP INDEX IF EXISTS idx_events_date_fatal;
DROP INDEX IF EXISTS idx_events_cat_agg;
DROP INDEX IF EXISTS idx_events_source_url;
