"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

interface Props {
  data: { year: number; count: number; deaths: number }[];
}

export function OrgTimelineChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex h-[260px] items-center justify-center rounded-lg border border-border bg-surface text-sm text-text-dim">
        No timeline data
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="#262626" vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fill: "#a3a3a3", fontSize: 11 }}
            stroke="#404040"
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: "#a3a3a3", fontSize: 11 }}
            stroke="#404040"
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: "#a3a3a3", fontSize: 11 }}
            stroke="#404040"
          />
          <Tooltip
            contentStyle={{
              background: "#171717",
              border: "1px solid #404040",
              borderRadius: 6,
              fontSize: 12,
            }}
            labelStyle={{ color: "#fafafa" }}
          />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} iconSize={10} />
          <Bar
            yAxisId="left"
            dataKey="count"
            name="Events"
            fill="#6d28d9"
            fillOpacity={0.7}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="deaths"
            name="Fatalities"
            stroke="#dc2626"
            strokeWidth={2}
            dot={{ r: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
