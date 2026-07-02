import { NextResponse } from "next/server";
import { getEventById, getRelatedEvents } from "@/lib/queries";

export const runtime = "edge";

export const revalidate = 86400;

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const event = await getEventById(decodeURIComponent(params.id));
    if (!event) {
      return NextResponse.json({ error: "Event not found" }, { status: 404 });
    }
    const related = await getRelatedEvents(event, 6);
    return NextResponse.json(
      { event, related },
      {
        headers: {
          "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=172800",
        },
      }
    );
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
