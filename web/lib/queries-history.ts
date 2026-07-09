/**
 * Historical timeline queries (homepage "56 years of organized violence").
 *
 * Kept separate from lib/queries.ts by design. Aggregates the full events table
 * by calendar year since 1970. is_aggregate=1 rows (cumulative single-event
 * totals like the Tigray 121K figure) and dup_of duplicates are excluded so the
 * yearly shape reflects discrete recorded events, not double-counts.
 */
import { queryAll } from "@/lib/db";

export interface YearPoint {
  year: number;
  events: number;
  fatalities: number;
}

/** Per-year {year, events, fatalities} from 1970 to present, ordered ascending. */
export async function getYearlyHistory(): Promise<YearPoint[]> {
  const rows = await queryAll<{ year: number; events: number; fatalities: number }>(
    `SELECT CAST(substr(date, 1, 4) AS INTEGER) as year,
            COUNT(*)                            as events,
            COALESCE(SUM(fatalities), 0)        as fatalities
       FROM events
      WHERE is_aggregate = 0
        AND dup_of IS NULL
        AND date >= '1970'
      GROUP BY year
      ORDER BY year`
  );
  // Guard against a malformed trailing/partial year slipping past substr().
  return rows.filter((r) => r.year >= 1970 && r.year <= new Date().getFullYear());
}
