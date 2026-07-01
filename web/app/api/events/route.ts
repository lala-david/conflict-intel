import { NextRequest, NextResponse } from "next/server";
import { queryAll, queryOne } from "@/lib/db";
import type { Event } from "@/lib/types";

export const dynamic = "force-dynamic";

const ALL_CATEGORIES = [
  "war", "civil_war", "terrorism", "mass_atrocity", "state_violence",
  "cartel_violence", "communal_violence", "insurgency", "counterterrorism", "armed_violence",
];

export async function GET(req: NextRequest) {
  try {
    const params = req.nextUrl.searchParams;
    const country = params.get("country");
    const category = params.get("category");
    const actor = params.get("actor");
    const from = params.get("from");
    const to = params.get("to");
    const source = params.get("source");
    const q = params.get("q");
    const limit = Math.min(parseInt(params.get("limit") ?? "50"), 500);
    const offset = Math.max(parseInt(params.get("offset") ?? "0"), 0);

    const conditions: string[] = ["is_aggregate = 0"];
    const values: any[] = [];

    if (country) { conditions.push("country = ?"); values.push(country); }
    if (category && ALL_CATEGORIES.includes(category)) {
      conditions.push("category = ?"); values.push(category);
    }
    if (actor) { conditions.push("actor1 = ?"); values.push(actor); }
    if (from) { conditions.push("date >= ?"); values.push(from); }
    if (to) { conditions.push("date <= ?"); values.push(to); }
    if (source) { conditions.push("source = ?"); values.push(source); }
    if (q && q.length >= 2) {
      const like = `%${q}%`;
      conditions.push("(actor1 LIKE ? OR actor2 LIKE ? OR notes LIKE ?)");
      values.push(like, like, like);
    }

    const where = conditions.join(" AND ");

    const total = ((await queryOne<{ c: number }>(
      `SELECT COUNT(*) as c FROM events WHERE ${where}`,
      [...values]
    )) as { c: number }).c;

    const events = await queryAll<Event>(
      `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
                admin1, location, latitude, longitude, fatalities,
                deaths_civilians, fatalities_low, fatalities_high,
                category, category_confidence, is_aggregate, notes, source_url
           FROM events
          WHERE ${where}
          ORDER BY date DESC, fatalities DESC
          LIMIT ? OFFSET ?`,
      [...values, limit, offset]
    );

    return NextResponse.json(
      { total, count: events.length, limit, offset, events },
      { headers: { "Cache-Control": "public, s-maxage=600" } }
    );
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
