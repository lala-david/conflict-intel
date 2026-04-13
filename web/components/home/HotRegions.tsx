import Link from "next/link";
import type { HotRegion } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface Props {
  regions: HotRegion[];
}

export function HotRegionsList({ regions }: Props) {
  const maxFatalities = Math.max(...regions.map((r) => r.fatalities), 1);

  return (
    <div>
      <div className="mb-4">
        <h2 className="font-display text-2xl font-bold">Hot Regions</h2>
        <p className="mt-1 text-sm text-text-dim">
          Deadliest countries in the last 90 days
        </p>
      </div>

      <div className="rounded-lg border border-border bg-surface">
        {regions.slice(0, 10).map((region, i) => {
          const pct = (region.fatalities / maxFatalities) * 100;
          return (
            <Link
              key={region.country}
              href={`/countries/${encodeURIComponent(region.country)}`}
              className="group block border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-text-dim">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="font-medium text-text-primary group-hover:text-accent">
                    {region.country}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-mono text-xs text-text-dim">
                    {formatNumber(region.events)} events
                  </span>
                  <span className="font-mono text-sm font-semibold tabular-nums text-text-primary">
                    {formatNumber(region.fatalities)}
                  </span>
                </div>
              </div>
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-full bg-accent/60 transition-all group-hover:bg-accent"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
