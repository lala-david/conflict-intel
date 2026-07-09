"use client";

import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceDot,
} from "recharts";
import type { YearPoint } from "@/lib/queries-history";

interface Props {
  data: YearPoint[];
}

type Metric = "fatalities" | "events";

/**
 * Curated context for the deadliest inflection years. Only years that actually
 * surface as peaks in the data get a label — everything else stays a bare year,
 * so the annotations track the real shape rather than a hardcoded narrative.
 */
const ERA_LABELS: Record<number, string> = {
  1971: "Bangladesh war",
  1975: "Indochina / Cambodia",
  1983: "Iran–Iraq War",
  1988: "Afghanistan · Iran–Iraq",
  1994: "Rwanda genocide",
  1999: "DR Congo war",
  2003: "Iraq invasion",
  2014: "ISIS surge",
  2016: "Syria · Iraq peak",
  2017: "Mosul · Raqqa",
  2022: "Ukraine",
  2023: "Gaza · Sudan",
  2024: "Gaza · Sudan",
};

const ACCENT = "#EF4444";

function compactNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

/** Pick the standout peak years — highest by metric, spaced ≥4 years apart. */
function pickPeaks(data: YearPoint[], metric: Metric, max = 6): YearPoint[] {
  const sorted = [...data].sort((a, b) => b[metric] - a[metric]);
  const peaks: YearPoint[] = [];
  for (const p of sorted) {
    if (peaks.length >= max) break;
    if (peaks.every((q) => Math.abs(q.year - p.year) >= 4)) peaks.push(p);
  }
  return peaks.sort((a, b) => a.year - b.year);
}

export function HistoryRidgeline({ data }: Props) {
  const [metric, setMetric] = useState<Metric>("fatalities");

  const peaks = useMemo(() => pickPeaks(data, metric), [data, metric]);
  const maxVal = useMemo(
    () => Math.max(...data.map((d) => d[metric]), 1),
    [data, metric]
  );

  if (data.length === 0) {
    return (
      <div className="flex h-[340px] items-center justify-center rounded-xl border border-border bg-surface text-sm text-text-dim">
        No historical data available
      </div>
    );
  }

  const spanFrom = data[0].year;
  const spanTo = data[data.length - 1].year;

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      {/* Metric toggle */}
      <div className="mb-3 flex items-center justify-between gap-4">
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-text-dim">
          {spanFrom}–{spanTo} · per year
        </div>
        <div className="flex overflow-hidden rounded-md border border-border text-[11px] font-semibold">
          {(["fatalities", "events"] as Metric[]).map((m) => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`px-3 py-1 capitalize transition-colors ${
                metric === m
                  ? "bg-accent text-white"
                  : "bg-surface-2 text-text-dim hover:text-text-primary"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <AreaChart
          data={data}
          margin={{ top: 34, right: 12, left: 4, bottom: 4 }}
        >
          <defs>
            <linearGradient id="ridgeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={ACCENT} stopOpacity={0.55} />
              <stop offset="55%" stopColor={ACCENT} stopOpacity={0.18} />
              <stop offset="100%" stopColor={ACCENT} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#2A2E36" vertical={false} strokeDasharray="2 4" />
          <XAxis
            dataKey="year"
            tick={{ fill: "#98A0AC", fontSize: 11, fontFamily: "monospace" }}
            stroke="#2A2E36"
            interval="preserveStartEnd"
            minTickGap={40}
            tickLine={false}
          />
          <YAxis
            width={44}
            tick={{ fill: "#98A0AC", fontSize: 11, fontFamily: "monospace" }}
            stroke="#2A2E36"
            tickLine={false}
            domain={[0, maxVal * 1.15]}
            tickFormatter={(v: number) => compactNum(v)}
          />
          <Tooltip
            cursor={{ stroke: ACCENT, strokeWidth: 1, strokeOpacity: 0.4 }}
            contentStyle={{
              background: "#15171B",
              border: "1px solid #2A2E36",
              borderRadius: 8,
              fontSize: 12,
              boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            }}
            labelStyle={{ color: "#ECEEF1", fontWeight: 700, marginBottom: 2 }}
            formatter={(value: number, name: string) => [
              (value as number).toLocaleString("en-US"),
              name === "fatalities" ? "killed" : "events",
            ]}
          />
          <Area
            type="monotone"
            dataKey={metric}
            stroke={ACCENT}
            strokeWidth={1.75}
            fill="url(#ridgeFill)"
            isAnimationActive={false}
            activeDot={{ r: 3.5, fill: ACCENT, stroke: "#0C0D0F", strokeWidth: 1.5 }}
          />
          {peaks.map((p) => {
            const label = ERA_LABELS[p.year];
            return (
              <ReferenceDot
                key={p.year}
                x={p.year}
                y={p[metric]}
                r={3.5}
                fill={ACCENT}
                stroke="#0C0D0F"
                strokeWidth={1.5}
                isFront
                label={{
                  position: "top",
                  value: label ? `${p.year} · ${label}` : String(p.year),
                  fill: "#ECEEF1",
                  fontSize: 10,
                  fontWeight: 600,
                  offset: 8,
                }}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>

      {/* Peak legend row — the deadliest years, spelled out */}
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 border-t border-border pt-3 text-[11px]">
        {peaks.map((p) => (
          <div key={p.year} className="flex items-baseline gap-1.5">
            <span className="h-1.5 w-1.5 shrink-0 translate-y-[-1px] rounded-full bg-accent" />
            <span className="font-mono font-semibold text-text-primary">
              {p.year}
            </span>
            {ERA_LABELS[p.year] && (
              <span className="text-text-dim">{ERA_LABELS[p.year]}</span>
            )}
            <span className="tabular-nums text-accent">
              {compactNum(p[metric])}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
