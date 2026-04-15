import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const revalidate = 600;

export async function GET(req: NextRequest) {
  try {
    const limit = Math.min(parseInt(req.nextUrl.searchParams.get("limit") ?? "20"), 100);
    const db = getDb();

    // Recent micro-updates: last 7 days, ordered by date+collected_at
    const sparks = db
      .prepare(
        `SELECT id, source, date, actor1, actor2, country, location,
                latitude, longitude, fatalities, category, notes, source_url
           FROM events
          WHERE is_aggregate = 0
            AND date >= date('now', '-7 days')
          ORDER BY collected_at DESC, date DESC
          LIMIT ?`
      )
      .all(limit) as any[];

    return NextResponse.json(
      { count: sparks.length, sparks },
      { headers: { "Cache-Control": "public, s-maxage=600" } }
    );
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
