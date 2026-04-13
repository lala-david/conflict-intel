"use client";

import dynamic from "next/dynamic";

const WorldMap = dynamic(
  () => import("./WorldMap").then((m) => ({ default: m.WorldMap })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[520px] items-center justify-center rounded-xl border border-border bg-surface">
        <div className="text-sm text-text-dim">Loading map...</div>
      </div>
    ),
  }
);

interface Props {
  countryScores: {
    country: string;
    country_code: string;
    threat_score: number;
    fatalities_90d: number;
    events_90d: number;
  }[];
}

export function WorldMapClient({ countryScores }: Props) {
  return <WorldMap countryScores={countryScores} />;
}
