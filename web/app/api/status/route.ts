import { NextResponse } from "next/server";
import { queryAll, queryOne } from "@/lib/db";

export const revalidate = 600;

/**
 * One-off historical imports, not daily feeds: they never get "fresher", so
 * judging them by collection age reported the whole pipeline DOWN forever.
 * They're listed as ARCHIVE and left out of overall_status. Anything not
 * listed is treated as a live feed, so a new source is watched by default.
 */
const ARCHIVE_SOURCES = new Set([
  "gtd",
  "ucdp-ged",
  "ucdp-ged-2025",
  "ucdp-candidate",
  "wikidata",
]);

export async function GET() {
  try {
    // Per-source freshness, precomputed by scripts/compute_stats.py into
    // event_sources. Aggregating the events table here read ~1.2M rows per
    // call — on a public endpoint, a handful of calls a day would spend D1's
    // whole 5M-row read quota and take the site down.
    const sources = await queryAll<{
      source: string;
      latest_event: string;
      last_collected: string;
      total_events: number;
    }>(
      `SELECT source, latest_event, last_collected, total_events
         FROM event_sources
        WHERE total_events > 0
        ORDER BY last_collected DESC`
    );

    // Live feeds: degraded if last collected > 36h ago, down after 4 days.
    const now = Date.now();
    const sourceStatus = sources.map((s) => {
      const lastCollect = s.last_collected ? new Date(s.last_collected).getTime() : 0;
      const ageHours = lastCollect ? (now - lastCollect) / 3600_000 : Infinity;
      let status: "OK" | "DEGRADED" | "DOWN" | "ARCHIVE";
      if (ARCHIVE_SOURCES.has(s.source)) status = "ARCHIVE";
      else if (ageHours < 36) status = "OK";
      else if (ageHours < 96) status = "DEGRADED";
      else status = "DOWN";
      return { ...s, status, age_hours: Math.round(ageHours) };
    });

    // Global stats freshness
    const globalStats = await queryOne<{ updated_at: string }>(
      `SELECT updated_at FROM global_stats WHERE id = 1`
    );

    const live = sourceStatus.filter((s) => s.status !== "ARCHIVE");
    const okCount = live.filter((s) => s.status === "OK").length;
    const overallStatus =
      okCount === live.length
        ? "OK"
        : okCount >= live.length * 0.6
        ? "DEGRADED"
        : "DOWN";

    return NextResponse.json(
      {
        overall_status: overallStatus,
        sources_total: live.length,
        sources_ok: okCount,
        sources_archive: sourceStatus.length - live.length,
        stats_updated_at: globalStats?.updated_at ?? null,
        sources: sourceStatus,
      },
      { headers: { "Cache-Control": "public, s-maxage=600" } }
    );
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
