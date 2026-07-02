/**
 * Shared DB query helpers.
 *
 * All queries exclude is_aggregate=1 events by default (Tigray 121K-fatality
 * single events are cumulative aggregates and would dominate every chart).
 */
import { queryAll, queryOne } from "./db";
import type {
  Category,
  CategoryStats,
  Country,
  Event,
  HomeData,
  HotRegion,
  SpreadPoint,
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
async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const now = Date.now();
  if (_cache[key] && _cache[key].exp > now) return _cache[key].data as T;
  const data = await fn();
  _cache[key] = { data, exp: now + ttlMs };
  return data;
}

// ─── Home page data ───
export async function getHomeData(): Promise<HomeData> {
  return await cached("home", 300_000, _getHomeDataInner); // 5 min cache
}

async function _getHomeDataInner(): Promise<HomeData> {
  const since90 = daysAgo(90);
  const since7 = daysAgo(7);
  const since14 = daysAgo(14);

  // All six queries are independent → run concurrently (one round-trip window
  // to Turso instead of six sequential ones).
  const [g, trendRows, prev7, catRows, hotRegions, recentEvents] = await Promise.all([
    queryOne<any>(`SELECT * FROM global_stats WHERE id = 1`),
    queryAll<{ date: string; daily: number }>(
      `SELECT date, COALESCE(SUM(fatalities), 0) as daily
         FROM events
        WHERE is_aggregate = 0 AND date >= ?
        GROUP BY date ORDER BY date`,
      [since7]
    ),
    queryOne<{ total: number }>(
      `SELECT COALESCE(SUM(fatalities), 0) as total
         FROM events
        WHERE is_aggregate = 0 AND date >= ? AND date < ?`,
      [since14, since7]
    ),
    queryAll<{ category: Category; events: number; fatalities: number }>(
      `SELECT category, total_events as events, total_fatalities as fatalities FROM category_stats`
    ),
    queryAll<HotRegion>(
      `SELECT country, events_90d as events, fatalities_90d as fatalities
         FROM country_stats
        WHERE fatalities_90d > 0
        ORDER BY fatalities_90d DESC
        LIMIT 10`
    ),
    queryAll<Event>(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0 AND date >= ?
          AND (fatalities > 0 OR category = 'terrorism')
        ORDER BY date DESC, fatalities DESC
        LIMIT 15`,
      [since90]
    ),
  ]);

  const totals = g
    ? { events: g.total_events, fatalities: g.total_fatalities, countries: g.total_countries }
    : { events: 0, fatalities: 0, countries: 0 };

  const trend7d = trendRows.map((r) => r.daily);
  const cur7 = trend7d.reduce((a, b) => a + b, 0);
  const prevAvg = (prev7?.total ?? 0) / 7;
  const curAvg = cur7 / Math.max(trend7d.length, 1);
  const delta = prevAvg > 0 ? Math.round(((curAvg - prevAvg) / prevAvg) * 100) : 0;

  const threatIndex: ThreatIndex = {
    value: g?.threat_index ?? 0,
    delta,
    trend7d,
  };

  const categories = catRows.reduce((acc, r) => {
    acc[r.category] = { events: r.events, fatalities: r.fatalities };
    return acc;
  }, {} as Record<Category, { events: number; fatalities: number }>);

  return {
    threatIndex,
    totals,
    categories,
    hotRegions,
    recentEvents,
  };
}

// ─── Country queries ───
export async function getCountryList(): Promise<Country[]> {
  return await queryAll<Country>(
    `SELECT country,
              total_events as event_count,
              total_fatalities,
              events_30d as recent_30d_events,
              fatalities_30d as recent_30d_fatalities
         FROM country_stats
        ORDER BY total_fatalities DESC
        LIMIT 200`
  );
}

export async function getCountryByName(name: string): Promise<Country | null> {
  return await queryOne<Country>(
    `SELECT country, total_events as event_count, total_fatalities,
              events_30d as recent_30d_events, fatalities_30d as recent_30d_fatalities
         FROM country_stats WHERE country = ?`,
    [name]
  );
}

export async function getCountryTimeline(
  country: string
): Promise<{ year: number; category: string; count: number; deaths: number }[]> {
  return await queryAll<{
    year: number;
    category: string;
    count: number;
    deaths: number;
  }>(
    `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
              category,
              COUNT(*) as count,
              COALESCE(SUM(fatalities), 0) as deaths
         FROM events
        WHERE is_aggregate = 0 AND country = ? AND date >= '1989'
        GROUP BY year, category
        ORDER BY year`,
    [country]
  );
}

export async function getCountryEvents(country: string, limit = 15): Promise<Event[]> {
  return await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0 AND country = ? AND dup_of IS NULL
        ORDER BY date DESC
        LIMIT ?`,
    [country, limit]
  );
}

export async function getCountryPoints(
  country: string,
  limit = 800
): Promise<SpreadPoint[]> {
  return await queryAll<SpreadPoint>(
    `SELECT id, longitude, latitude, fatalities, date, category, country,
              location, actor1, actor2
       FROM events
      WHERE country = ? AND is_aggregate = 0 AND dup_of IS NULL
        AND latitude IS NOT NULL AND longitude IS NOT NULL
      ORDER BY date DESC
      LIMIT ?`,
    [country, limit]
  );
}

export async function getCountryTopActors(
  country: string,
  limit = 8
): Promise<{ name: string; events: number; fatalities: number }[]> {
  return await queryAll<{ name: string; events: number; fatalities: number }>(
    `SELECT actor1 as name,
              COUNT(*) as events,
              COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE country = ? AND is_aggregate = 0
          AND actor1 != '' AND actor1 NOT LIKE 'Government of%'
          AND length(actor1) < 60
        GROUP BY actor1
        ORDER BY events DESC
        LIMIT ?`,
    [country, limit]
  );
}

// ─── Event queries ───
export async function getEventById(id: string): Promise<Event | null> {
  return await queryOne<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events WHERE id = ?`,
    [id]
  );
}

export async function getRelatedEvents(event: Event, limit = 6): Promise<Event[]> {
  // Same country, ±30 days, not this event
  return await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE country = ? AND id != ?
          AND date BETWEEN date(?, '-30 days') AND date(?, '+30 days')
          AND is_aggregate = 0
        ORDER BY ABS(julianday(date) - julianday(?))
        LIMIT ?`,
    [event.country, event.id, event.date, event.date, event.date, limit]
  );
}

// ─── Organization queries ───
export async function getTopOrganizations(limit = 100): Promise<{
  name: string;
  events: number;
  fatalities: number;
  countries: number;
  first_seen: string;
  last_seen: string;
}[]> {
  return await queryAll<{
    name: string;
    events: number;
    fatalities: number;
    countries: number;
    first_seen: string;
    last_seen: string;
  }>(
    `SELECT name,
              total_events as events,
              total_fatalities as fatalities,
              countries,
              first_seen,
              last_seen
         FROM org_stats
        ORDER BY total_events DESC
        LIMIT ?`,
    [limit]
  );
}

export async function getOrganizationEvents(name: string, limit = 30): Promise<Event[]> {
  return await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND dup_of IS NULL
        ORDER BY date DESC
        LIMIT ?`,
    [name, limit]
  );
}

export async function getOrganizationPoints(
  name: string,
  limit = 500
): Promise<SpreadPoint[]> {
  return await queryAll<SpreadPoint>(
    `SELECT id, longitude, latitude, fatalities, date, category, country,
              location, actor1, actor2
       FROM events
      WHERE actor1 = ? AND is_aggregate = 0 AND dup_of IS NULL
        AND latitude IS NOT NULL AND longitude IS NOT NULL
      ORDER BY date DESC
      LIMIT ?`,
    [name, limit]
  );
}

export async function getOrganizationTimeline(
  name: string
): Promise<{ year: number; count: number; deaths: number }[]> {
  return await queryAll<{ year: number; count: number; deaths: number }>(
    `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
              COUNT(*) as count,
              COALESCE(SUM(fatalities), 0) as deaths
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND date >= '1989'
        GROUP BY year
        ORDER BY year`,
    [name]
  );
}

export async function getOrganizationCountries(
  name: string
): Promise<{ country: string; count: number }[]> {
  return await queryAll<{ country: string; count: number }>(
    `SELECT country, COUNT(*) as count
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND country != ''
        GROUP BY country
        ORDER BY COUNT(*) DESC
        LIMIT 15`,
    [name]
  );
}

export async function getOrganizationStats(name: string): Promise<{
  name: string;
  events: number;
  fatalities: number;
  countries: string[];
  first_seen: string;
  last_seen: string;
} | null> {
  const base = await queryOne<{
    name: string;
    events: number;
    fatalities: number;
    first_seen: string;
    last_seen: string;
  }>(
    `SELECT actor1 as name,
              COUNT(*) as events,
              COALESCE(SUM(fatalities), 0) as fatalities,
              MIN(date) as first_seen,
              MAX(date) as last_seen
         FROM events
        WHERE actor1 = ? AND is_aggregate = 0
        GROUP BY actor1`,
    [name]
  );

  if (!base) return null;

  const countries = await queryAll<{ country: string }>(
    `SELECT DISTINCT country FROM events
        WHERE actor1 = ? AND is_aggregate = 0 AND country != ''
        ORDER BY country`,
    [name]
  );

  return {
    ...base,
    countries: countries.map((c) => c.country),
  };
}

// ─── Category queries ───
export async function getCategoryStats(category: Category): Promise<CategoryStats & {
  top_countries: { country: string; count: number }[];
  top_actors: { name: string; count: number }[];
  timeline: { year: number; count: number }[];
}> {
  const base = await queryOne<CategoryStats>(
    `SELECT category, COUNT(*) as events, COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE category = ? AND is_aggregate = 0
        GROUP BY category`,
    [category]
  );

  const topCountries = await queryAll<{ country: string; count: number }>(
    `SELECT country, COUNT(*) as count FROM events
        WHERE category = ? AND is_aggregate = 0 AND country != ''
        GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10`,
    [category]
  );

  const topActors = await queryAll<{ name: string; count: number }>(
    `SELECT actor1 as name, COUNT(*) as count FROM events
        WHERE category = ? AND is_aggregate = 0
          AND actor1 != '' AND actor1 NOT LIKE 'Government of%'
        GROUP BY actor1 ORDER BY COUNT(*) DESC LIMIT 10`,
    [category]
  );

  const timeline = await queryAll<{ year: number; count: number }>(
    `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year, COUNT(*) as count
         FROM events
        WHERE category = ? AND is_aggregate = 0 AND date >= '1989'
        GROUP BY year ORDER BY year`,
    [category]
  );

  return {
    ...(base as CategoryStats),
    top_countries: topCountries,
    top_actors: topActors,
    timeline,
  };
}

// ─── Search ───
export async function searchEvents(q: string, limit = 20): Promise<Event[]> {
  if (!q || q.length < 2) return [];
  const like = `%${q}%`;
  return await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0
          AND (actor1 LIKE ? OR actor2 LIKE ? OR country LIKE ? OR notes LIKE ?)
        ORDER BY fatalities DESC
        LIMIT ?`,
    [like, like, like, like, limit]
  );
}

export async function searchCountries(q: string): Promise<{ country: string; total_events: number; total_fatalities: number }[]> {
  if (!q || q.length < 2) return [];
  return await queryAll<any>(
    `SELECT country, total_events, total_fatalities FROM country_stats WHERE country LIKE ? ORDER BY total_fatalities DESC LIMIT 10`,
    [`%${q}%`]
  );
}

export async function searchOrgs(q: string): Promise<{ name: string; total_events: number; total_fatalities: number }[]> {
  if (!q || q.length < 2) return [];
  return await queryAll<any>(
    `SELECT name, total_events, total_fatalities FROM org_stats WHERE name LIKE ? ORDER BY total_events DESC LIMIT 10`,
    [`%${q}%`]
  );
}

// ─── On This Day (38-year archive) ───
export async function getOnThisDay(): Promise<Event | null> {
  const today = new Date();
  const monthDay = `${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return await queryOne<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE substr(date, 6, 5) = ? AND is_aggregate = 0 AND fatalities >= 10
        ORDER BY fatalities DESC
        LIMIT 1`,
    [monthDay]
  );
}

// ─── Today's Expert Analysis ───
export async function getTodayAnalysis(limit = 4): Promise<{ feed: string; title: string; url: string }[]> {
  const since7d = daysAgo(7);
  return await queryAll<{ feed: string; title: string; url: string }>(
    `SELECT sub_event_type as feed, notes as title, source_url as url
         FROM events
        WHERE source = 'expert_rss' AND date >= ?
          AND notes IS NOT NULL AND notes != ''
          AND source_url IS NOT NULL AND source_url != ''
        ORDER BY date DESC, id DESC
        LIMIT ?`,
    [since7d, limit]
  );
}

// ─── 38-year timeline (homepage) ───
export async function getYearlyTimeline(): Promise<{ year: number; events: number; fatalities: number }[]> {
  return await queryAll<{ year: number; events: number; fatalities: number }>(
    `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
              COUNT(*) as events,
              COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE is_aggregate = 0 AND date >= '1989'
        GROUP BY year
        ORDER BY year`
  );
}

// ─── Related organizations (co-occurring in same events/countries) ───
export async function getRelatedOrganizations(
  name: string,
  limit = 8
): Promise<{ name: string; events: number; shared_countries: number }[]> {
  // Actors active in the same countries as `name`. Avoids the catastrophic
  // events×events self-join (which hangs for any actor in a busy country) by
  // matching on a bounded set of the actor's countries instead.
  return await queryAll<{ name: string; events: number; shared_countries: number }>(
    `SELECT actor1 as name,
              COUNT(*) as events,
              COUNT(DISTINCT country) as shared_countries
         FROM events
        WHERE country IN (
                SELECT country FROM events
                 WHERE actor1 = ? AND is_aggregate = 0 AND country != ''
                 GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10
              )
          AND actor1 != ?
          AND actor1 != ''
          AND actor1 NOT LIKE 'Government of%'
          AND is_aggregate = 0
        GROUP BY actor1
        ORDER BY events DESC
        LIMIT ?`,
    [name, name, limit]
  );
}

// ─── CSV export data ───
export async function getEventsForExport(
  filters: { country?: string; category?: string; from?: string; to?: string },
  limit = 10000
): Promise<Event[]> {
  const conditions: string[] = ["is_aggregate = 0"];
  const params: any[] = [];

  if (filters.country) { conditions.push("country = ?"); params.push(filters.country); }
  if (filters.category) { conditions.push("category = ?"); params.push(filters.category); }
  if (filters.from) { conditions.push("date >= ?"); params.push(filters.from); }
  if (filters.to) { conditions.push("date <= ?"); params.push(filters.to); }

  return await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE ${conditions.join(" AND ")}
        ORDER BY date DESC
        LIMIT ?`,
    [...params, limit]
  );
}

// ─── Country threat scores for map choropleth ───
export async function getCountryThreatScores(): Promise<{
  country: string;
  country_code: string;
  threat_score: number;
  fatalities_90d: number;
  events_90d: number;
}[]> {
  return await queryAll<any>(
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
  );
}

// ─── Global stats for map ───
export async function getMapHotspots(): Promise<{
  lat: number;
  lon: number;
  fatalities: number;
  category: string;
  country: string;
}[]> {
  const since90 = daysAgo(90);
  return await queryAll<{
    lat: number;
    lon: number;
    fatalities: number;
    category: string;
    country: string;
  }>(
    `SELECT latitude as lat, longitude as lon, fatalities, category, country
         FROM events
        WHERE is_aggregate = 0
          AND date >= ?
          AND latitude IS NOT NULL AND longitude IS NOT NULL
          AND fatalities > 0
        ORDER BY fatalities DESC
        LIMIT 500`,
    [since90]
  );
}
