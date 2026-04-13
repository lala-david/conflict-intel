/**
 * Shared DB query helpers.
 *
 * All queries exclude is_aggregate=1 events by default (Tigray 121K-fatality
 * single events are cumulative aggregates and would dominate every chart).
 */
import { getDb } from "./db";
import type {
  Category,
  CategoryStats,
  Country,
  Event,
  HomeData,
  HotRegion,
  ThreatIndex,
} from "./types";

const RECENT_WINDOW_DAYS = 90;

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

// Simple in-memory cache (TTL 5 min)
const _cache: Record<string, { data: any; exp: number }> = {};
function cached<T>(key: string, ttlMs: number, fn: () => T): T {
  const now = Date.now();
  if (_cache[key] && _cache[key].exp > now) return _cache[key].data as T;
  const data = fn();
  _cache[key] = { data, exp: now + ttlMs };
  return data;
}

// ─── Home page data ───
export function getHomeData(): HomeData {
  return cached("home", 300_000, _getHomeDataInner); // 5 min cache
}

function _getHomeDataInner(): HomeData {
  const db = getDb();
  const since90 = daysAgo(90);

  // ─── Pre-computed tables (instant) ───
  const g = db.prepare(`SELECT * FROM global_stats WHERE id = 1`).get() as any;
  const totals = g
    ? { events: g.total_events, fatalities: g.total_fatalities, countries: g.total_countries }
    : { events: 0, fatalities: 0, countries: 0 };

  // 7-day trend: fatalities per day for the last 7 days
  const since7 = daysAgo(7);
  const trendRows = db
    .prepare(
      `SELECT date, COALESCE(SUM(fatalities), 0) as daily
         FROM events
        WHERE is_aggregate = 0 AND date >= ?
        GROUP BY date ORDER BY date`
    )
    .all(since7) as { date: string; daily: number }[];
  const trend7d = trendRows.map((r) => r.daily);

  // Delta: compare last 7d fatalities avg vs previous 7d
  const since14 = daysAgo(14);
  const prev7 = db
    .prepare(
      `SELECT COALESCE(SUM(fatalities), 0) as total
         FROM events
        WHERE is_aggregate = 0 AND date >= ? AND date < ?`
    )
    .get(since14, since7) as { total: number };
  const cur7 = trend7d.reduce((a, b) => a + b, 0);
  const prevAvg = (prev7?.total ?? 0) / 7;
  const curAvg = cur7 / Math.max(trend7d.length, 1);
  const delta = prevAvg > 0 ? Math.round(((curAvg - prevAvg) / prevAvg) * 100) : 0;

  const threatIndex: ThreatIndex = {
    value: g?.threat_index ?? 0,
    delta,
    trend7d,
  };

  // Categories (pre-computed)
  const catRows = db
    .prepare(`SELECT category, total_events as events, total_fatalities as fatalities FROM category_stats`)
    .all() as { category: Category; events: number; fatalities: number }[];

  const categories = catRows.reduce((acc, r) => {
    acc[r.category] = { events: r.events, fatalities: r.fatalities };
    return acc;
  }, {} as Record<Category, { events: number; fatalities: number }>);

  // Hot regions (pre-computed, 90 days)
  const hotRegions = db
    .prepare(
      `SELECT country, events_90d as events, fatalities_90d as fatalities
         FROM country_stats
        WHERE fatalities_90d > 0
        ORDER BY fatalities_90d DESC
        LIMIT 10`
    )
    .all() as HotRegion[];

  // Recent events (90 days, indexed query — fast)
  const recentEvents = db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0 AND date >= ?
          AND (fatalities > 0 OR category = 'terrorism')
        ORDER BY date DESC, fatalities DESC
        LIMIT 15`
    )
    .all(since90) as Event[];

  return {
    threatIndex,
    totals,
    categories,
    hotRegions,
    recentEvents,
  };
}

// ─── Country queries ───
export function getCountryList(): Country[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT country,
              total_events as event_count,
              total_fatalities,
              events_30d as recent_30d_events,
              fatalities_30d as recent_30d_fatalities
         FROM country_stats
        ORDER BY total_fatalities DESC
        LIMIT 200`
    )
    .all() as Country[];
}

export function getCountryByName(name: string): Country | null {
  const db = getDb();
  return db
    .prepare(
      `SELECT country, total_events as event_count, total_fatalities,
              events_30d as recent_30d_events, fatalities_30d as recent_30d_fatalities
         FROM country_stats WHERE country = ?`
    )
    .get(name) as Country | null;
}

export function getCountryTimeline(
  country: string
): { year: number; category: string; count: number; deaths: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
              category,
              COUNT(*) as count,
              COALESCE(SUM(fatalities), 0) as deaths
         FROM events
        WHERE is_aggregate = 0 AND country = ? AND date >= '1989'
        GROUP BY year, category
        ORDER BY year`
    )
    .all(country) as {
    year: number;
    category: string;
    count: number;
    deaths: number;
  }[];
}

export function getCountryEvents(country: string, limit = 15): Event[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0 AND country = ?
        ORDER BY date DESC
        LIMIT ?`
    )
    .all(country, limit) as Event[];
}

// ─── Event queries ───
export function getEventById(id: string): Event | null {
  const db = getDb();
  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events WHERE id = ?`
    )
    .get(id) as Event | null;
}

export function getRelatedEvents(event: Event, limit = 6): Event[] {
  const db = getDb();
  // Same country, ±30 days, not this event
  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE country = ? AND id != ?
          AND date BETWEEN date(?, '-30 days') AND date(?, '+30 days')
          AND is_aggregate = 0
        ORDER BY ABS(julianday(date) - julianday(?))
        LIMIT ?`
    )
    .all(event.country, event.id, event.date, event.date, event.date, limit) as Event[];
}

// ─── Organization queries ───
export function getTopOrganizations(limit = 100): {
  name: string;
  events: number;
  fatalities: number;
  countries: number;
  first_seen: string;
  last_seen: string;
}[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT name,
              total_events as events,
              total_fatalities as fatalities,
              countries,
              first_seen,
              last_seen
         FROM org_stats
        ORDER BY total_events DESC
        LIMIT ?`
    )
    .all(limit) as {
    name: string;
    events: number;
    fatalities: number;
    countries: number;
    first_seen: string;
    last_seen: string;
  }[];
}

export function getOrganizationEvents(name: string, limit = 30): Event[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0
        ORDER BY date DESC
        LIMIT ?`
    )
    .all(name, limit) as Event[];
}

export function getOrganizationTimeline(
  name: string
): { year: number; count: number; deaths: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
              COUNT(*) as count,
              COALESCE(SUM(fatalities), 0) as deaths
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND date >= '1989'
        GROUP BY year
        ORDER BY year`
    )
    .all(name) as { year: number; count: number; deaths: number }[];
}

export function getOrganizationCountries(
  name: string
): { country: string; count: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT country, COUNT(*) as count
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND country != ''
        GROUP BY country
        ORDER BY COUNT(*) DESC
        LIMIT 15`
    )
    .all(name) as { country: string; count: number }[];
}

export function getOrganizationStats(name: string): {
  name: string;
  events: number;
  fatalities: number;
  countries: string[];
  first_seen: string;
  last_seen: string;
} | null {
  const db = getDb();
  const base = db
    .prepare(
      `SELECT actor1 as name,
              COUNT(*) as events,
              COALESCE(SUM(fatalities), 0) as fatalities,
              MIN(date) as first_seen,
              MAX(date) as last_seen
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0
        GROUP BY actor1`
    )
    .get(name) as {
    name: string;
    events: number;
    fatalities: number;
    first_seen: string;
    last_seen: string;
  } | null;

  if (!base) return null;

  const countries = db
    .prepare(
      `SELECT DISTINCT country FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND country != ''
        ORDER BY country`
    )
    .all(name) as { country: string }[];

  return {
    ...base,
    countries: countries.map((c) => c.country),
  };
}

// ─── Category queries ───
export function getCategoryStats(category: Category): CategoryStats & {
  top_countries: { country: string; count: number }[];
  top_actors: { name: string; count: number }[];
  timeline: { year: number; count: number }[];
} {
  const db = getDb();
  const base = db
    .prepare(
      `SELECT category, COUNT(*) as events, COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE category = ? AND is_aggregate = 0
        GROUP BY category`
    )
    .get(category) as CategoryStats;

  const topCountries = db
    .prepare(
      `SELECT country, COUNT(*) as count FROM events
        WHERE category = ? AND is_aggregate = 0 AND country != ''
        GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10`
    )
    .all(category) as { country: string; count: number }[];

  const topActors = db
    .prepare(
      `SELECT actor1 as name, COUNT(*) as count FROM events
        WHERE category = ? AND is_aggregate = 0
          AND actor1 != '' AND actor1 NOT LIKE 'Government of%'
        GROUP BY actor1 ORDER BY COUNT(*) DESC LIMIT 10`
    )
    .all(category) as { name: string; count: number }[];

  const timeline = db
    .prepare(
      `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year, COUNT(*) as count
         FROM events
        WHERE category = ? AND is_aggregate = 0 AND date >= '1989'
        GROUP BY year ORDER BY year`
    )
    .all(category) as { year: number; count: number }[];

  return {
    ...base,
    top_countries: topCountries,
    top_actors: topActors,
    timeline,
  };
}

// ─── Search ───
export function searchEvents(q: string, limit = 20): Event[] {
  if (!q || q.length < 2) return [];
  const db = getDb();
  const like = `%${q}%`;
  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0
          AND (actor1 LIKE ? OR actor2 LIKE ? OR country LIKE ? OR notes LIKE ?)
        ORDER BY fatalities DESC
        LIMIT ?`
    )
    .all(like, like, like, like, limit) as Event[];
}

export function searchCountries(q: string): { country: string; total_events: number; total_fatalities: number }[] {
  if (!q || q.length < 2) return [];
  const db = getDb();
  return db
    .prepare(`SELECT country, total_events, total_fatalities FROM country_stats WHERE country LIKE ? ORDER BY total_fatalities DESC LIMIT 10`)
    .all(`%${q}%`) as any[];
}

export function searchOrgs(q: string): { name: string; total_events: number; total_fatalities: number }[] {
  if (!q || q.length < 2) return [];
  const db = getDb();
  return db
    .prepare(`SELECT name, total_events, total_fatalities FROM org_stats WHERE name LIKE ? ORDER BY total_events DESC LIMIT 10`)
    .all(`%${q}%`) as any[];
}

// ─── On This Day (37-year archive) ───
export function getOnThisDay(): Event | null {
  const db = getDb();
  const today = new Date();
  const monthDay = `${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE substr(date, 6, 5) = ? AND is_aggregate = 0 AND fatalities >= 10
        ORDER BY fatalities DESC
        LIMIT 1`
    )
    .get(monthDay) as Event | null;
}

// ─── Today's Expert Analysis ───
export function getTodayAnalysis(limit = 4): { feed: string; title: string; url: string }[] {
  const db = getDb();
  const since7d = daysAgo(7);
  return db
    .prepare(
      `SELECT sub_event_type as feed, notes as title, source_url as url
         FROM events
        WHERE source = 'expert_rss' AND date >= ?
          AND notes IS NOT NULL AND notes != ''
          AND source_url IS NOT NULL AND source_url != ''
        ORDER BY date DESC, id DESC
        LIMIT ?`
    )
    .all(since7d, limit) as { feed: string; title: string; url: string }[];
}

// ─── 37-year timeline (homepage) ───
export function getYearlyTimeline(): { year: number; events: number; fatalities: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
              COUNT(*) as events,
              COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE is_aggregate = 0 AND date >= '1989'
        GROUP BY year
        ORDER BY year`
    )
    .all() as { year: number; events: number; fatalities: number }[];
}

// ─── Related organizations (co-occurring in same events/countries) ───
export function getRelatedOrganizations(
  name: string,
  limit = 8
): { name: string; events: number; shared_countries: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT e2.actor1 as name,
              COUNT(*) as events,
              COUNT(DISTINCT e2.country) as shared_countries
         FROM events e1
         JOIN events e2 ON e1.country = e2.country
           AND e2.actor1 != e1.actor1
           AND e2.actor1 != ''
           AND e2.actor1 NOT LIKE 'Government of%'
           AND e2.is_aggregate = 0
           AND ABS(julianday(e1.date) - julianday(e2.date)) <= 365
        WHERE e1.actor1 = ? AND e1.is_aggregate = 0
        GROUP BY e2.actor1
        ORDER BY events DESC
        LIMIT ?`
    )
    .all(name, limit) as { name: string; events: number; shared_countries: number }[];
}

// ─── CSV export data ───
export function getEventsForExport(
  filters: { country?: string; category?: string; from?: string; to?: string },
  limit = 10000
): Event[] {
  const db = getDb();
  const conditions: string[] = ["is_aggregate = 0"];
  const params: any[] = [];

  if (filters.country) { conditions.push("country = ?"); params.push(filters.country); }
  if (filters.category) { conditions.push("category = ?"); params.push(filters.category); }
  if (filters.from) { conditions.push("date >= ?"); params.push(filters.from); }
  if (filters.to) { conditions.push("date <= ?"); params.push(filters.to); }

  return db
    .prepare(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE ${conditions.join(" AND ")}
        ORDER BY date DESC
        LIMIT ?`
    )
    .all(...params, limit) as Event[];
}

// ─── Country threat scores for map choropleth ───
export function getCountryThreatScores(): {
  country: string;
  country_code: string;
  threat_score: number;
  fatalities_90d: number;
  events_90d: number;
}[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT cs.country,
              COALESCE(e.country_code, '') as country_code,
              cs.threat_score,
              cs.fatalities_90d,
              cs.events_90d
         FROM country_stats cs
         LEFT JOIN (
           SELECT country, country_code
           FROM events
           WHERE country_code IS NOT NULL AND country_code != ''
           GROUP BY country
         ) e ON e.country = cs.country
        WHERE cs.fatalities_90d > 0
        ORDER BY cs.threat_score DESC`
    )
    .all() as any[];
}

// ─── Global stats for map ───
export function getMapHotspots(): {
  lat: number;
  lon: number;
  fatalities: number;
  category: string;
  country: string;
}[] {
  const db = getDb();
  const since90 = daysAgo(90);
  return db
    .prepare(
      `SELECT latitude as lat, longitude as lon, fatalities, category, country
         FROM events
        WHERE is_aggregate = 0
          AND date >= ?
          AND latitude IS NOT NULL AND longitude IS NOT NULL
          AND fatalities > 0
        ORDER BY fatalities DESC
        LIMIT 500`
    )
    .all(since90) as {
    lat: number;
    lon: number;
    fatalities: number;
    category: string;
    country: string;
  }[];
}
