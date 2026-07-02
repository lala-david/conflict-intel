import { NextRequest, NextResponse } from "next/server";
import { getTopOrganizations } from "@/lib/queries";

export const revalidate = 3600;

export async function GET(req: NextRequest) {
  try {
    const limit = Math.min(parseInt(req.nextUrl.searchParams.get("limit") ?? "100"), 500);
    const orgs = await getTopOrganizations(limit);
    return NextResponse.json(
      { count: orgs.length, organizations: orgs },
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
