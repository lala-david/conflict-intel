import { NextResponse } from "next/server";
import {
  getCountryByName,
  getCountryEvents,
  getCountryTimeline,
} from "@/lib/queries";

export const revalidate = 3600;

export async function GET(
  _req: Request,
  { params }: { params: { name: string } }
) {
  try {
    const name = decodeURIComponent(params.name);
    const country = getCountryByName(name);
    if (!country) {
      return NextResponse.json({ error: "Country not found" }, { status: 404 });
    }
    const events = getCountryEvents(name, 50);
    const timeline = getCountryTimeline(name);
    return NextResponse.json(
      { country, events, timeline },
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
