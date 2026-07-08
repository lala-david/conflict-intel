import { ImageResponse } from "@vercel/og";
import { getCountryByName } from "@/lib/queries";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  { params }: { params: { name: string } }
) {
  const name = decodeURIComponent(params.name);
  const country = await getCountryByName(name);

  if (!country) {
    return new Response("Not found", { status: 404 });
  }

  const fat30 = country.recent_30d_fatalities;
  let level = "LOW";
  let levelColor = "#16a34a";
  if (fat30 >= 100) { level = "SEVERE"; levelColor = "#991b1b"; }
  else if (fat30 >= 20) { level = "HIGH"; levelColor = "#dc2626"; }
  else if (fat30 >= 5) { level = "ELEVATED"; levelColor = "#d97706"; }
  else if (fat30 > 0) { level = "MODERATE"; levelColor = "#eab308"; }

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#0a0a0a",
          padding: "60px",
          fontFamily: "Inter, system-ui, sans-serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: "72px", fontWeight: 700, color: "#fafafa", lineHeight: 1.1 }}>
              {country.country}
            </div>
            <div style={{ display: "flex", gap: "40px", marginTop: "24px" }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ fontSize: "48px", fontWeight: 700, color: "#fafafa" }}>
                  {country.event_count.toLocaleString()}
                </div>
                <div style={{ fontSize: "16px", color: "#a3a3a3", letterSpacing: "0.1em", textTransform: "uppercase" as const }}>
                  Events
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ fontSize: "48px", fontWeight: 700, color: "#dc2626" }}>
                  {country.total_fatalities.toLocaleString()}
                </div>
                <div style={{ fontSize: "16px", color: "#a3a3a3", letterSpacing: "0.1em", textTransform: "uppercase" as const }}>
                  Killed
                </div>
              </div>
            </div>
          </div>
          <div
            style={{
              background: levelColor,
              color: "#fff",
              padding: "12px 24px",
              borderRadius: "8px",
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "0.1em",
            }}
          >
            {level}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#dc2626" }} />
            <div style={{ fontSize: "24px", fontWeight: 600, color: "#fafafa" }}>
              Conflict & Security Intelligence
            </div>
          </div>
          <div style={{ fontSize: "16px", color: "#525252" }}>
            570K+ events · since 1970 · 250+ countries
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
