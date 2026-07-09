/**
 * Query + filter helpers for the /events browse experience.
 *
 * Kept separate from web/lib/queries.ts (owned elsewhere). All reads go through
 * the shared db helpers and stay LIMIT-bounded / index-friendly: the events
 * table is indexed on date, country, category, fatalities and source, so every
 * filter here maps to one of those columns (plus a bounded COUNT for paging).
 */
import { queryAll, queryOne } from "@/lib/db";
import type { Category, Confidence, Event } from "@/lib/types";

export const EVENT_CATEGORIES: Category[] = [
  "war", "civil_war", "terrorism", "mass_atrocity", "state_violence",
  "cartel_violence", "communal_violence", "insurgency", "counterterrorism", "armed_violence",
];

export const EVENT_CONFIDENCES: Confidence[] = ["high", "medium", "low"];

const CATEGORY_SET = new Set<string>(EVENT_CATEGORIES);
const CONFIDENCE_SET = new Set<string>(EVENT_CONFIDENCES);

/** Raw query params for the events page, already string-typed off the URL. */
export interface EventFilters {
  q?: string;
  category?: string;
  country?: string;
  from?: string;
  to?: string;
  /** minimum fatalities threshold (inclusive) */
  minFatalities?: string;
  /** exact source string, e.g. "ucdp-ged", "gtd", "gdelt" */
  source?: string;
  /** category_confidence: high | medium | low */
  confidence?: string;
}

/**
 * Full distinct country list for the filter dropdown — every country with
 * recorded events, not just the top N. Reads the pre-aggregated country_stats
 * table (~255 rows) so it's a cheap indexed scan, ordered by fatalities so the
 * heaviest-hit countries surface first.
 */
export function getEventCountries(): Promise<{ country: string }[]> {
  return queryAll<{ country: string }>(
    `SELECT country FROM country_stats
      WHERE country IS NOT NULL AND country != ''
      ORDER BY total_fatalities DESC`
  );
}

/** Distinct source strings present in the events table, for the source filter. */
export function getEventSources(): Promise<string[]> {
  return queryAll<{ source: string }>(
    `SELECT DISTINCT source FROM events
      WHERE source IS NOT NULL AND source != ''
      ORDER BY source ASC`
  ).then((rows) => rows.map((r) => r.source));
}

/**
 * Translate URL filters into a parameterised WHERE clause. All values are bound
 * (never interpolated) and each condition targets an indexed column. Unknown /
 * out-of-range values are ignored so a hand-edited URL can't break the query.
 */
export function buildEventWhere(
  f: EventFilters,
  validSources: Set<string>
): { where: string; params: (string | number)[] } {
  const conditions: string[] = ["is_aggregate = 0", "dup_of IS NULL"];
  const params: (string | number)[] = [];

  if (f.q && f.q.length >= 2) {
    const like = `%${f.q}%`;
    conditions.push("(actor1 LIKE ? OR actor2 LIKE ? OR country LIKE ? OR notes LIKE ?)");
    params.push(like, like, like, like);
  }

  if (f.category && CATEGORY_SET.has(f.category)) {
    conditions.push("category = ?");
    params.push(f.category);
  }

  if (f.country) {
    conditions.push("country = ?");
    params.push(f.country);
  }

  if (f.from) {
    conditions.push("date >= ?");
    params.push(f.from);
  }

  if (f.to) {
    conditions.push("date <= ?");
    params.push(f.to);
  }

  const minFatal = f.minFatalities ? parseInt(f.minFatalities, 10) : NaN;
  if (Number.isFinite(minFatal) && minFatal > 0) {
    conditions.push("fatalities >= ?");
    params.push(minFatal);
  }

  if (f.source && validSources.has(f.source)) {
    conditions.push("source = ?");
    params.push(f.source);
  }

  if (f.confidence && CONFIDENCE_SET.has(f.confidence)) {
    conditions.push("category_confidence = ?");
    params.push(f.confidence);
  }

  return { where: conditions.join(" AND "), params };
}

/** Total matching rows — bounded COUNT for pagination. */
export async function countEvents(
  where: string,
  params: (string | number)[]
): Promise<number> {
  const row = await queryOne<{ total: number }>(
    `SELECT COUNT(*) as total FROM events WHERE ${where}`,
    params
  );
  return row?.total ?? 0;
}

/** One page of events, newest-first, LIMIT/OFFSET bounded. */
export function fetchEvents(
  where: string,
  params: (string | number)[],
  limit: number,
  offset: number
): Promise<Event[]> {
  return queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
            admin1, location, latitude, longitude, fatalities,
            deaths_civilians, fatalities_low, fatalities_high,
            category, category_confidence, is_aggregate, notes, source_url
       FROM events
      WHERE ${where}
      ORDER BY date DESC, fatalities DESC
      LIMIT ? OFFSET ?`,
    [...params, limit, offset]
  );
}
