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

/** A geolocated event plotted on the globe. */
export interface WireHotspot {
  lat: number;
  lng: number;
  fatalities: number;
  category: Category | null;
}

export interface WireData {
  /** Latest events, newest first — replayed as a streaming ticker. */
  events: WireEvent[];
  /** Real event coordinates to plot on the globe (recent, weighted by toll). */
  hotspots: WireHotspot[];
  /** Documented fatalities so far this calendar year — the live counter's value. */
  yearFatalities: number;
  /** The calendar year the counter reflects. */
  year: number;
}

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export async function getWireData(): Promise<WireData> {
  const year = new Date().getFullYear();
  const yearStart = `${year}-01-01`;

  const [events, hotspots, yearAgg] = await Promise.all([
    queryAll<WireEvent>(
      `SELECT id, date, country, fatalities, category, actor1
         FROM events
        WHERE is_aggregate = 0 AND date >= ?
          AND (fatalities > 0 OR category = 'terrorism')
        ORDER BY date DESC, fatalities DESC
        LIMIT 40`,
      [daysAgo(WIRE_WINDOW_DAYS)]
    ),
    // Real event coordinates for the globe — recent + deadliest, last ~2 years so
    // the globe is always populated even while the current year is still sparse.
    queryAll<WireHotspot>(
      `SELECT latitude AS lat, longitude AS lng, fatalities, category
         FROM events
        WHERE is_aggregate = 0 AND dup_of IS NULL
          AND latitude IS NOT NULL AND latitude != 0
          AND longitude IS NOT NULL AND longitude != 0
          AND date >= ?
        ORDER BY fatalities DESC, date DESC
        LIMIT 500`,
      [daysAgo(730)]
    ),
    queryOne<{ total: number }>(
      `SELECT COALESCE(SUM(fatalities), 0) as total
         FROM events
        WHERE is_aggregate = 0 AND date >= ?`,
      [yearStart]
    ),
  ]);

  return { events, hotspots, yearFatalities: yearAgg?.total ?? 0, year };
}
