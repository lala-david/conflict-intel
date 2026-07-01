"use client";

import dynamic from "next/dynamic";
import type { SpreadPoint } from "./NodeSpreadMap";

const NodeSpreadMap = dynamic(
  () => import("./NodeSpreadMap").then((m) => ({ default: m.NodeSpreadMap })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[380px] items-center justify-center rounded-lg border border-border bg-surface">
        <div className="text-xs text-text-dim">Loading map…</div>
      </div>
    ),
  },
);

export function NodeSpreadMapClient(props: { points: SpreadPoint[]; height?: number }) {
  return <NodeSpreadMap {...props} />;
}
