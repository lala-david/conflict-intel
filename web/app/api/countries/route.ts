import { NextResponse } from "next/server";
import { getCountryList } from "@/lib/queries";

export const runtime = "edge";

export const revalidate = 3600;

export async function GET() {
  try {
    const countries = await getCountryList();
    return NextResponse.json(
      { count: countries.length, countries },
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
