import { NextResponse } from "next/server";
import { getCountryThreatScores } from "@/lib/queries";

export const revalidate = 3600;

export async function GET() {
  try {
    const scores = await getCountryThreatScores();
    return NextResponse.json(
      { count: scores.length, threats: scores },
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
