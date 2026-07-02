import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { queryAll } from "@/lib/db";
import { formatNumber } from "@/lib/utils";

export const runtime = "edge";

export const revalidate = 3600;

export const metadata = {
  title: "Weekly Recap — Conflict & Security Intelligence",
};

interface WeekData {
  week: string;
  start: string;
  end: string;
  events: number;
  fatalities: number;
  countries: number;
}

async function getRecentWeeks(limit = 12): Promise<WeekData[]> {
  return await queryAll<WeekData>(
    `SELECT
         strftime('%Y-W%W', date) as week,
         MIN(date) as start,
         MAX(date) as end,
         COUNT(*) as events,
         COALESCE(SUM(fatalities), 0) as fatalities,
         COUNT(DISTINCT country) as countries
       FROM events
       WHERE is_aggregate = 0 AND date >= date('now', '-90 days')
       GROUP BY week
       ORDER BY week DESC
       LIMIT ?`,
    [limit]
  );
}

export default async function WeeklyPage() {
  const weeks = await getRecentWeeks(12);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="font-display text-4xl font-bold">Weekly Recap</h1>
        <p className="mt-2 text-text-dim">
          Automated weekly summaries of global conflict activity.
        </p>

        <div className="mt-8 space-y-4">
          {weeks.map((w) => (
            <Link
              key={w.week}
              href={`/weekly/${w.week}`}
              className="group block rounded-lg border border-border bg-surface p-5 transition hover:border-text-dim hover:bg-surface-2"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-display text-lg font-bold group-hover:text-accent">
                    {w.week}
                  </div>
                  <div className="mt-1 font-mono text-xs text-text-dim">
                    {w.start} → {w.end}
                  </div>
                </div>
                <div className="flex gap-6 text-right">
                  <div>
                    <div className="font-mono text-xl font-bold tabular-nums">
                      {formatNumber(w.events)}
                    </div>
                    <div className="text-[9px] uppercase tracking-wider text-text-dim">
                      events
                    </div>
                  </div>
                  <div>
                    <div className="font-mono text-xl font-bold tabular-nums text-accent">
                      {formatNumber(w.fatalities)}
                    </div>
                    <div className="text-[9px] uppercase tracking-wider text-text-dim">
                      killed
                    </div>
                  </div>
                  <div>
                    <div className="font-mono text-xl font-bold tabular-nums text-text-dim">
                      {w.countries}
                    </div>
                    <div className="text-[9px] uppercase tracking-wider text-text-dim">
                      countries
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
