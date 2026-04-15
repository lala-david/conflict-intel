import { NextResponse } from "next/server";
import {
  getTopOrganizations,
  getOrganizationStats,
  getOrganizationEvents,
  getOrganizationTimeline,
  getOrganizationCountries,
  getRelatedOrganizations,
} from "@/lib/queries";
import { findBySlug } from "@/lib/utils";

export const revalidate = 3600;

export async function GET(
  _req: Request,
  { params }: { params: { slug: string } }
) {
  try {
    const orgs = getTopOrganizations(500);
    const found = findBySlug(orgs, params.slug);
    if (!found) {
      return NextResponse.json({ error: "Organization not found" }, { status: 404 });
    }
    const stats = getOrganizationStats(found.name);
    const events = getOrganizationEvents(found.name, 30);
    const timeline = getOrganizationTimeline(found.name);
    const countries = getOrganizationCountries(found.name);
    const related = getRelatedOrganizations(found.name, 8);

    return NextResponse.json(
      { organization: stats, events, timeline, countries, related },
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
