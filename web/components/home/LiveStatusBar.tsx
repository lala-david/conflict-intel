import { formatNumber, timeAgo } from "@/lib/utils";
import type { ThreatIndex } from "@/lib/types";

// Threat index is 0–100 (see scripts/compute_stats.py). Green (calm) → amber →
// red (elevated). More violence is "worse", so an upward trend renders red.
function threatColor(v: number): string {
  if (v >= 67) return "#EF4444";
  if (v >= 34) return "#D97706";
  return "#16A34A";
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const pts = data.length ? data : [0];
  const max = Math.max(...pts, 1);
  const w = 62;
  const h = 18;
  const step = pts.length > 1 ? w / (pts.length - 1) : w;
  const line = pts.map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * (h - 2) - 1).toFixed(1)}`).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="shrink-0">
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Slim analyst status strip — surfaces the threat index, weekly trend and data
 *  freshness that the pipeline already computes but the homepage never showed. */
export function LiveStatusBar({
  threat,
  updatedAt,
}: {
  threat: ThreatIndex;
  updatedAt: string | null;
}) {
  const weekly = threat.trend7d.reduce((a, b) => a + b, 0);
  const tc = threatColor(threat.value);
  const up = threat.delta > 0;

  return (
    <div className="border-b border-border bg-surface/40">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-3 px-5 py-3 text-xs sm:px-6">
        {/* Threat index */}
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: tc }} aria-hidden />
          <span className="font-semibold uppercase tracking-[0.14em] text-text-dim">
            Threat index
          </span>
          <span className="font-mono font-semibold tabular-nums text-text-primary">
            {Math.round(threat.value)}
            <span className="text-text-dim">/100</span>
          </span>
        </div>

        {/* Weekly fatalities + 7-day sparkline + delta */}
        <div className="flex items-center gap-2.5">
          <span className="font-semibold uppercase tracking-[0.14em] text-text-dim">
            7-day fatalities
          </span>
          <span className="font-mono font-semibold tabular-nums text-text-primary">
            {formatNumber(weekly)}
          </span>
          <Sparkline data={threat.trend7d} color={tc} />
          {threat.delta !== 0 && (
            <span
              className="font-mono font-semibold tabular-nums"
              style={{ color: up ? "#EF4444" : "#16A34A" }}
            >
              {up ? "▲" : "▼"} {Math.abs(threat.delta)}%
            </span>
          )}
        </div>

        {/* Data freshness — pulsing "live" dot */}
        {updatedAt && (
          <div className="flex items-center gap-2 sm:ml-auto">
            <span className="relative flex h-1.5 w-1.5" aria-hidden>
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            <span className="font-mono text-text-dim">Updated {timeAgo(updatedAt)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
