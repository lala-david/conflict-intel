import { NextRequest, NextResponse } from "next/server";
import { getEventsForExport } from "@/lib/queries";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const country = params.get("country") || undefined;
  const category = params.get("category") || undefined;
  const from = params.get("from") || undefined;
  const to = params.get("to") || undefined;

  const events = getEventsForExport({ country, category, from, to }, 10000);

  const headers = [
    "id", "date", "source", "category", "actor1", "actor2",
    "country", "admin1", "location", "latitude", "longitude",
    "fatalities", "deaths_civilians", "notes",
  ];

  const rows = events.map((e) =>
    headers.map((h) => {
      const val = (e as any)[h];
      if (val == null) return "";
      const str = String(val);
      return str.includes(",") || str.includes('"') || str.includes("\n")
        ? `"${str.replace(/"/g, '""')}"`
        : str;
    }).join(",")
  );

  const csv = [headers.join(","), ...rows].join("\n");

  const filename = country
    ? `conflict-researcher-${country.toLowerCase().replace(/\s+/g, "-")}.csv`
    : "conflict-researcher-events.csv";

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "public, s-maxage=3600",
    },
  });
}
