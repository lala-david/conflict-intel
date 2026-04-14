"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { CATEGORY_META } from "@/lib/utils";
import type { Category } from "@/lib/types";

interface Props {
  data: { year: number; category: string; count: number; deaths: number }[];
}

export function CountryTimeline({ data }: Props) {
  // Pivot: rows by year, columns by category
  const years = Array.from(new Set(data.map((d) => d.year))).sort(
    (a, b) => a - b
  );
  const categoriesInData = Array.from(new Set(data.map((d) => d.category)));

  const pivoted = years.map((year) => {
    const row: Record<string, number> = { year };
    for (const cat of categoriesInData) {
      const match = data.find((d) => d.year === year && d.category === cat);
      row[cat] = match?.deaths ?? 0;
    }
    return row;
  });

  if (pivoted.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-lg border border-border bg-surface text-sm text-text-dim">
        No timeline data
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={pivoted} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="#262626" vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fill: "#a3a3a3", fontSize: 11 }}
            stroke="#404040"
          />
          <YAxis tick={{ fill: "#a3a3a3", fontSize: 11 }} stroke="#404040" />
          <Tooltip
            contentStyle={{
              background: "#171717",
              border: "1px solid #404040",
              borderRadius: 6,
              fontSize: 12,
            }}
            labelStyle={{ color: "#fafafa" }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            iconSize={10}
          />
          {categoriesInData.map((cat) => {
            const meta = CATEGORY_META[cat as Category];
            return (
              <Area
                key={cat}
                type="monotone"
                dataKey={cat}
                stackId="1"
                stroke={meta?.color ?? "#475569"}
                fill={meta?.color ?? "#475569"}
                fillOpacity={0.7}
                name={meta?.label ?? cat}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
