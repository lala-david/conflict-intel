/**
 * Historical timeline queries (homepage "56 years of organized violence").
 *
 * Kept separate from lib/queries.ts by design. Reads the per-year rollup that
 * scripts/compute_stats.py materializes into `yearly_stats` (calendar years since
 * 1970; is_aggregate=1 rows — cumulative single-event totals like the Tigray 121K
 * figure — and dup_of duplicates excluded, so the shape reflects discrete
 * recorded events, not double-counts). Aggregating the events table live here
 * read ~500K rows per render and was 83% of all D1 reads.
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
    `SELECT year, events, fatalities
       FROM yearly_stats
      WHERE events > 0
      ORDER BY year`
  );
  // Guard against a malformed trailing/partial year slipping past substr().
  return rows.filter((r) => r.year >= 1970 && r.year <= new Date().getFullYear());
}
