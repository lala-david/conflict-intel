/**
 * Sitemap-only queries. Kept out of lib/queries.ts on purpose so the main
 * query surface stays focused; the sitemap owns its own bounded reads.
 *
 * The events table holds ~570K server-rendered `/events/[id]` pages. We cannot
 * list them all (the sitemap would be enormous and the query would time out),
 * so we surface the top-ranking long-tail: the most recent, highest-fatality
 * events. The query is hard-capped and selects only `id` + `date` to stay fast
 * and to keep the response small enough to edge-cache.
 */
import { queryAll } from "./db";

/** Hard ceiling on event URLs added to the sitemap. */
export const SITEMAP_EVENTS_CAP = 5000;

export interface SitemapEvent {
  id: string;
  date: string;
}

/**
 * Top events by recency then fatalities — the breaking-news long-tail most
 * worth indexing. Bounded by `limit` (defaults to the cap) and projects only
 * the two columns the sitemap needs.
 */
export async function getSitemapEventIds(
  limit: number = SITEMAP_EVENTS_CAP
): Promise<SitemapEvent[]> {
  const n = Math.min(Math.max(1, Math.floor(limit) || SITEMAP_EVENTS_CAP), SITEMAP_EVENTS_CAP);
  return await queryAll<SitemapEvent>(
    `SELECT id, date
       FROM events
      WHERE is_aggregate = 0 AND dup_of IS NULL
      ORDER BY date DESC, fatalities DESC
      LIMIT ?`,
    [n]
  );
}
