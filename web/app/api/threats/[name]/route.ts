import { NextResponse } from "next/server";
import { queryOne } from "@/lib/db";

export const revalidate = 3600;

export async function GET(
  _req: Request,
  { params }: { params: { name: string } }
) {
  try {
    const name = decodeURIComponent(params.name);
    const cs = await queryOne<any>(
      `SELECT * FROM country_stats WHERE country = ?`,
      [name]
    );
    if (!cs) {
      return NextResponse.json({ error: "Country not found" }, { status: 404 });
    }
    return NextResponse.json(
      { threat: cs },
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
