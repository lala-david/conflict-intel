import { queryAll } from "@/lib/db";
import { formatNumber, formatDate, getCategoryMeta } from "@/lib/utils";
import type { Event } from "@/lib/types";

export const runtime = "edge";

export const revalidate = 1800;

export default async function FeedEmbed() {
  const events = await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE is_aggregate = 0
          AND date >= date('now', '-30 days')
          AND (fatalities > 0 OR category = 'terrorism')
        ORDER BY date DESC, fatalities DESC
        LIMIT 7`
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        overflow: "auto",
        background: "#0a0a0a",
        color: "#fafafa",
        fontFamily: "Inter, system-ui, sans-serif",
        padding: "14px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "#a3a3a3",
          marginBottom: "10px",
        }}
      >
        Live Threat Feed
      </div>
      {events.map((e) => {
        const meta = getCategoryMeta(e.category);
        return (
          <a
            key={e.id}
            href={`/events/${encodeURIComponent(e.id)}`}
            target="_top"
            style={{
              display: "block",
              padding: "10px 0",
              borderTop: "1px solid #262626",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "10px" }}>
              <span
                style={{
                  background: meta.color,
                  color: "white",
                  padding: "2px 6px",
                  borderRadius: "3px",
                  fontWeight: 600,
                  fontSize: "9px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                {meta.label}
              </span>
              <span style={{ color: "#a3a3a3" }}>{formatDate(e.date)}</span>
              <span style={{ color: "#a3a3a3" }}>· {e.country}</span>
            </div>
            <div
              style={{
                fontSize: "13px",
                fontWeight: 500,
                marginTop: "4px",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {e.actor1 || "Unknown"}
              {e.actor2 && e.actor2 !== "Civilians" && (
                <span style={{ color: "#a3a3a3" }}> vs {e.actor2}</span>
              )}
            </div>
            {e.fatalities > 0 && (
              <div style={{ fontSize: "11px", color: "#dc2626", fontWeight: 600, marginTop: "2px" }}>
                {formatNumber(e.fatalities)} killed
              </div>
            )}
          </a>
        );
      })}
      <div style={{ marginTop: "10px", fontSize: "9px", color: "#525252", textAlign: "center" }}>
        <a href="/" target="_top" style={{ color: "#525252", textDecoration: "none" }}>
          Conflict & Security Intelligence ↗
        </a>
      </div>
    </div>
  );
}
