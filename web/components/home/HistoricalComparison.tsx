import { queryOne } from "@/lib/db";
import { formatNumber } from "@/lib/utils";
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";

export async function HistoricalComparison() {
  // Current year fatalities
  const currentYear = new Date().getFullYear();
  const currentYearStats = (await queryOne<{ events: number; fatalities: number }>(
    `SELECT COUNT(*) as events, COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE is_aggregate = 0 AND substr(date, 1, 4) = ?`,
    [String(currentYear)]
  )) as { events: number; fatalities: number };

  // Previous year same period
  const dayOfYear = Math.floor(
    (Date.now() - new Date(currentYear, 0, 1).getTime()) / 86400000
  );
  const prevYearEnd = `${currentYear - 1}-${String(Math.floor(dayOfYear / 30) + 1).padStart(2, "0")}-${String((dayOfYear % 30) + 1).padStart(2, "0")}`;
  const prevYearStats = (await queryOne<{ events: number; fatalities: number }>(
    `SELECT COUNT(*) as events, COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE is_aggregate = 0
          AND date >= ? AND date <= ?`,
    [`${currentYear - 1}-01-01`, prevYearEnd]
  )) as { events: number; fatalities: number };

  // Peak year
  const peakYear = (await queryOne<{ year: string; fatalities: number }>(
    `SELECT substr(date, 1, 4) as year, COALESCE(SUM(fatalities), 0) as fatalities
         FROM events
        WHERE is_aggregate = 0 AND date >= '1970'
        GROUP BY year
        ORDER BY fatalities DESC
        LIMIT 1`
  )) as { year: string; fatalities: number };

  // Deadliest single event ever
  const deadliestEvent = (await queryOne<{ actor1: string; country: string; fatalities: number; date: string }>(
    `SELECT actor1, country, fatalities, date
         FROM events
        WHERE is_aggregate = 0
        ORDER BY fatalities DESC
        LIMIT 1`
  )) as { actor1: string; country: string; fatalities: number; date: string };

  const yoyChange = prevYearStats.fatalities > 0
    ? Math.round(((currentYearStats.fatalities - prevYearStats.fatalities) / prevYearStats.fatalities) * 100)
    : 0;
  const YoyIcon = yoyChange > 0 ? TrendingUp : TrendingDown;

  return (
    <section className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-dim">
        <BarChart3 className="h-3.5 w-3.5" />
        Historical Context
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {/* YTD vs previous year */}
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
            {currentYear} YTD vs {currentYear - 1}
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold tabular-nums">
              {formatNumber(currentYearStats.fatalities)}
            </span>
            <span className="text-xs text-text-dim">killed</span>
          </div>
          <div className={`mt-1 flex items-center gap-1 text-xs ${yoyChange > 0 ? "text-accent" : "text-cat-counterterrorism"}`}>
            <YoyIcon className="h-3 w-3" />
            {yoyChange > 0 ? "+" : ""}{yoyChange}% vs same period {currentYear - 1}
          </div>
        </div>

        {/* Peak year comparison */}
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
            Peak Year
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold tabular-nums">
              {peakYear.year}
            </span>
            <span className="text-xs text-text-dim">
              {formatNumber(peakYear.fatalities)} killed
            </span>
          </div>
          <div className="mt-1 text-xs text-text-dim">
            Current year is{" "}
            {Math.round((currentYearStats.fatalities / peakYear.fatalities) * 100)}% of peak
          </div>
        </div>

        {/* Deadliest single event */}
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
            Deadliest Single Event
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold tabular-nums text-accent">
              {formatNumber(deadliestEvent.fatalities)}
            </span>
            <span className="text-xs text-text-dim">killed</span>
          </div>
          <div className="mt-1 text-xs text-text-dim">
            {deadliestEvent.actor1} · {deadliestEvent.country} · {deadliestEvent.date?.slice(0, 4)}
          </div>
        </div>
      </div>
    </section>
  );
}
