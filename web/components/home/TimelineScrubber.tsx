"use client";

import { useMemo } from "react";

interface Props {
  data: { year: number; events: number; fatalities: number }[];
}

const BAR_MAX_HEIGHT = 80; // px

export function TimelineScrubber({ data }: Props) {
  const maxFatalities = useMemo(
    () => Math.max(...data.map((d) => d.fatalities), 1),
    [data]
  );

  if (data.length === 0) {
    return (
      <div className="flex h-20 items-center justify-center text-sm text-text-dim">
        No timeline data available
      </div>
    );
  }

  return (
    <div>
      {/* Bar chart */}
      <div
        className="flex items-end gap-[2px]"
        style={{ height: BAR_MAX_HEIGHT }}
      >
        {data.map((d) => {
          const h = Math.max(2, (d.fatalities / maxFatalities) * BAR_MAX_HEIGHT);
          return (
            <div
              key={d.year}
              className="group relative flex-1"
            >
              <div
                className="w-full rounded-t-sm bg-accent/60 transition-colors group-hover:bg-accent"
                style={{ height: `${h}px` }}
              />
              {/* Tooltip */}
              <div className="pointer-events-none absolute -top-[72px] left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded border border-border bg-background px-2 py-1.5 text-[10px] text-text-primary shadow-lg group-hover:block">
                <div className="font-bold">{d.year}</div>
                <div className="text-text-dim">
                  {d.events.toLocaleString()} events
                </div>
                <div className="text-accent">
                  {d.fatalities.toLocaleString()} killed
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Year labels */}
      <div className="mt-2 flex justify-between text-[9px] font-mono text-text-dim">
        {data
          .filter((_, i) => i % 5 === 0 || i === data.length - 1)
          .map((d) => (
            <span key={d.year}>{d.year}</span>
          ))}
      </div>
    </div>
  );
}
