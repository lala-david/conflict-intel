import { notFound } from "next/navigation";
import { getCountryByName } from "@/lib/queries";
import { formatNumber } from "@/lib/utils";

export const dynamic = "force-dynamic";

interface Props {
  params: { iso: string };
}

export default async function BadgeEmbed({ params }: Props) {
  const name = decodeURIComponent(params.iso);
  const country = await getCountryByName(name);
  if (!country) notFound();

  // Threat level based on 30-day fatalities
  const fat30 = country.recent_30d_fatalities;
  let level: { label: string; color: string };
  if (fat30 >= 100) level = { label: "SEVERE", color: "#991b1b" };
  else if (fat30 >= 20) level = { label: "HIGH", color: "#dc2626" };
  else if (fat30 >= 5) level = { label: "ELEVATED", color: "#d97706" };
  else if (fat30 > 0) level = { label: "MODERATE", color: "#eab308" };
  else level = { label: "LOW", color: "#16a34a" };

  return (
    <div
      style={{
        width: "300px",
        height: "100px",
        background: "#0a0a0a",
        border: "1px solid #404040",
        borderRadius: "8px",
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        overflow: "hidden",
      }}
    >
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontSize: "15px",
              fontWeight: 600,
              color: "#fafafa",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: "170px",
            }}
          >
            {country.country}
          </span>
          <span
            style={{
              fontSize: "9px",
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "#ffffff",
              background: level.color,
              padding: "3px 7px",
              borderRadius: "3px",
              textTransform: "uppercase",
            }}
          >
            {level.label}
          </span>
        </div>
        <div
          style={{
            fontSize: "10px",
            color: "#a3a3a3",
            marginTop: "4px",
            fontFamily: "ui-monospace, monospace",
          }}
        >
          30 DAYS · {formatNumber(country.recent_30d_events)} events ·{" "}
          {formatNumber(fat30)} killed
        </div>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <a
          href={`/countries/${encodeURIComponent(country.country)}`}
          target="_blank"
          rel="noopener"
          style={{
            fontSize: "10px",
            color: "#a3a3a3",
            textDecoration: "none",
          }}
        >
          Conflict Researcher ↗
        </a>
        <span
          style={{
            fontSize: "9px",
            color: "#525252",
            fontFamily: "ui-monospace, monospace",
          }}
        >
          all-time: {formatNumber(country.total_fatalities)} 💀
        </span>
      </div>
    </div>
  );
}
