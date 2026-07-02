import { NextResponse } from "next/server";
import { queryAll, queryOne } from "@/lib/db";

export const revalidate = 600;

export async function GET() {
  try {
    // Per-source freshness
    const sources = await queryAll<{
      source: string;
      latest_event: string;
      last_collected: string;
      total_events: number;
    }>(
      `SELECT source,
                MAX(date) as latest_event,
                MAX(collected_at) as last_collected,
                COUNT(*) as total_events
           FROM events
          WHERE is_aggregate = 0
          GROUP BY source
          ORDER BY MAX(collected_at) DESC`
    );

    // Status: degraded if last_collected > 2 days old
    const now = Date.now();
    const sourceStatus = sources.map((s) => {
      const lastCollect = s.last_collected ? new Date(s.last_collected).getTime() : 0;
      const ageHours = lastCollect ? (now - lastCollect) / 3600_000 : Infinity;
      let status: "OK" | "DEGRADED" | "DOWN";
      if (ageHours < 36) status = "OK";
      else if (ageHours < 96) status = "DEGRADED";
      else status = "DOWN";
      return { ...s, status, age_hours: Math.round(ageHours) };
    });

    // Global stats freshness
    const globalStats = await queryOne<{ updated_at: string }>(
      `SELECT updated_at FROM global_stats WHERE id = 1`
    );

    const okCount = sourceStatus.filter((s) => s.status === "OK").length;
    const overallStatus =
      okCount === sources.length
        ? "OK"
        : okCount >= sources.length * 0.6
        ? "DEGRADED"
        : "DOWN";

    return NextResponse.json(
      {
        overall_status: overallStatus,
        sources_total: sources.length,
        sources_ok: okCount,
        stats_updated_at: globalStats?.updated_at ?? null,
        sources: sourceStatus,
      },
      { headers: { "Cache-Control": "public, s-maxage=600" } }
    );
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
