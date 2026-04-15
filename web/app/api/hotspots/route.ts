import { NextResponse } from "next/server";
import { getMapHotspots } from "@/lib/queries";

export const revalidate = 3600;

export async function GET() {
  try {
    const hotspots = getMapHotspots();
    const geojson = {
      type: "FeatureCollection" as const,
      features: hotspots.map((h, i) => ({
        type: "Feature" as const,
        id: i,
        geometry: { type: "Point" as const, coordinates: [h.lon, h.lat] },
        properties: {
          fatalities: h.fatalities,
          category: h.category,
          country: h.country,
        },
      })),
    };
    return NextResponse.json(geojson, {
      headers: {
        "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=7200",
      },
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
