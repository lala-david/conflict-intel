/**
 * Server queries dedicated to THE WIRE hero.
 *
 * Kept separate from lib/queries.ts on purpose. Provides the two inputs the
 * live hero needs:
 *   1. the latest ~40 events, to replay as a streaming incident ticker
 *   2. the total fatalities over the recent window, to derive a per-second
 *      global death rate for the live counter
 */
import { queryAll, queryOne } from "@/lib/db";
import type { Category } from "@/lib/types";

/** Number of days in the "recent" window used for the live death rate. */
export const WIRE_WINDOW_DAYS = 90;

/** Seconds in the recent window — the denominator for the per-second rate. */
export const WIRE_WINDOW_SECONDS = WIRE_WINDOW_DAYS * 24 * 60 * 60;

/** Slim event shape streamed to the ticker (only what the wire renders). */
export interface WireEvent {
  id: string;
  date: string;
  country: string | null;
  fatalities: number;
  category: Category | null;
  actor1: string | null;
}

export interface WireData {
  /** Latest events, newest first — replayed as a streaming ticker. */
  events: WireEvent[];
  /** Total fatalities over the recent window (denominator = WIRE_WINDOW_SECONDS). */
  fatalities90d: number;
}

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export async function getWireData(): Promise<WireData> {
  const since = daysAgo(WIRE_WINDOW_DAYS);

  const [events, agg] = await Promise.all([
    queryAll<WireEvent>(
      `SELECT id, date, country, fatalities, category, actor1
         FROM events
        WHERE is_aggregate = 0 AND date >= ?
          AND (fatalities > 0 OR category = 'terrorism')
        ORDER BY date DESC, fatalities DESC
        LIMIT 40`,
      [since]
    ),
    queryOne<{ total: number }>(
      `SELECT COALESCE(SUM(fatalities), 0) as total
         FROM events
        WHERE is_aggregate = 0 AND date >= ?`,
      [since]
    ),
  ]);

  return { events, fatalities90d: agg?.total ?? 0 };
}
