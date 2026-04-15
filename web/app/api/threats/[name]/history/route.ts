import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const revalidate = 3600;

export async function GET(
  req: NextRequest,
  { params }: { params: { name: string } }
) {
  try {
    const name = decodeURIComponent(params.name);
    const granularity = req.nextUrl.searchParams.get("granularity") ?? "monthly";

    const db = getDb();
    let groupBy: string;
    if (granularity === "yearly") {
      groupBy = "substr(date, 1, 4)";
    } else if (granularity === "daily") {
      groupBy = "date";
    } else {
      groupBy = "substr(date, 1, 7)"; // monthly
    }

    const series = db
      .prepare(
        `SELECT ${groupBy} as period,
                COUNT(*) as events,
                COALESCE(SUM(fatalities), 0) as fatalities
           FROM events
          WHERE is_aggregate = 0 AND country = ? AND date >= '1989'
          GROUP BY period
          ORDER BY period`
      )
      .all(name) as { period: string; events: number; fatalities: number }[];

    if (series.length === 0) {
      return NextResponse.json({ error: "Country not found" }, { status: 404 });
    }

    return NextResponse.json(
      { country: name, granularity, count: series.length, series },
      {
        headers: {
          "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=7200",
        },
      }
    );
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
