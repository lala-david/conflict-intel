"use client";

import dynamic from "next/dynamic";

const EventMiniMap = dynamic(
  () => import("./EventMiniMap").then((m) => ({ default: m.EventMiniMap })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[240px] items-center justify-center rounded-lg border border-border bg-surface">
        <div className="text-xs text-text-dim">Loading map...</div>
      </div>
    ),
  }
);

interface Props {
  latitude: number;
  longitude: number;
  label?: string;
}

export function EventMiniMapClient(props: Props) {
  return <EventMiniMap {...props} />;
}
