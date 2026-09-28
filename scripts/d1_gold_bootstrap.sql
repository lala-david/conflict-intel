-- One-off D1 bootstrap for the homepage gold tables + index cleanup (2026-09).
--
-- Run AFTER D1's daily quota resets (00:00 UTC) and only after checking that D1
-- already has the covering composites:
--
--   wrangler d1 execute conflict-intel --remote --command \
--     "SELECT name FROM sqlite_master WHERE type='index' AND name IN
--      ('idx_ev_actor_date','idx_ev_country_date','idx_ev_country_actor',
--       'idx_events_date_fatal','idx_events_cat_agg','idx_events_agg_date_fat')"
--
-- All six must be present. If any is missing, do NOT run the DROPs below: building
-- a 600K-row index on D1 writes ~600K index rows, far past the free tier's 100K
-- rows written/day, so a missing composite has to be handled separately.
--
-- The gold tables are computed on D1 itself rather than synced from the laptop,
-- so they match the events D1 actually holds (the laptop DB also has backfilled
-- events D1 doesn't have yet). Cost: ~700K rows read (14% of the 5M/day quota),
-- 841 rows written. The statements mirror scripts/compute_stats.py; the next
-- regular sync_to_d1.py run replaces these tables with the pipeline's copy.
--
--   wrangler d1 execute conflict-intel --remote --file=../scripts/d1_gold_bootstrap.sql

-- 1) prefix-redundant indexes (see 55dbe63d) — ~66MB, takes D1 back under 500MB
DROP INDEX IF EXISTS idx_events_date;
DROP INDEX IF EXISTS idx_events_country;
DROP INDEX IF EXISTS idx_events_actor1;
DROP INDEX IF EXISTS idx_events_category;
DROP INDEX IF EXISTS idx_events_aggregate;
DROP INDEX IF EXISTS idx_events_agg_date;

-- 2) gold tables read by the homepage (see eb1f054d / cabdb17f)
CREATE TABLE IF NOT EXISTS yearly_stats (
    year INTEGER PRIMARY KEY,
    events INTEGER, fatalities INTEGER,
    fatalities_all INTEGER,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS wire_hotspots (
    rank INTEGER PRIMARY KEY,
    lat REAL, lng REAL, fatalities INTEGER,
    category TEXT, country TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS country_codes (
    country TEXT PRIMARY KEY,
    country_code TEXT
);

DELETE FROM yearly_stats;
INSERT INTO yearly_stats (year, events, fatalities, fatalities_all, updated_at)
SELECT CAST(substr(date, 1, 4) AS INTEGER) AS year,
       SUM(CASE WHEN dup_of IS NULL THEN 1 ELSE 0 END),
       COALESCE(SUM(CASE WHEN dup_of IS NULL THEN fatalities END), 0),
       COALESCE(SUM(fatalities), 0),
       datetime('now')
  FROM events
 WHERE is_aggregate = 0 AND date >= '1970'
 GROUP BY year;

DELETE FROM wire_hotspots;
INSERT INTO wire_hotspots (rank, lat, lng, fatalities, category, country, updated_at)
SELECT ROW_NUMBER() OVER (ORDER BY fatalities DESC, date DESC),
       latitude, longitude, fatalities, category, country, datetime('now')
  FROM events
 WHERE is_aggregate = 0 AND dup_of IS NULL
   AND latitude IS NOT NULL AND latitude != 0
   AND longitude IS NOT NULL AND longitude != 0
   AND date >= date('now', '-730 days')
 ORDER BY fatalities DESC, date DESC
 LIMIT 500;

DELETE FROM country_codes;
INSERT INTO country_codes (country, country_code)
SELECT country, country_code
  FROM events
 WHERE country_code IS NOT NULL AND country_code != ''
 GROUP BY country;
