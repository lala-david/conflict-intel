import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getDb } from "@/lib/db";
import { formatNumber, getCategoryMeta, formatDate } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";
import type { Event } from "@/lib/types";

export const revalidate = 3600;

interface Props {
  params: { week: string };
}

export default function WeeklyDetailPage({ params }: Props) {
  const week = params.week; // e.g. "2026-W14"
  const db = getDb();

  // Get events for this week
  const weekEvents = db
    .prepare(
      `SELECT * FROM events
       WHERE is_aggregate = 0 AND strftime('%Y-W%W', date) = ?
       ORDER BY fatalities DESC`
    )
    .all(week) as Event[];

  if (weekEvents.length === 0) notFound();

  const totalFat = weekEvents.reduce((s, e) => s + (e.fatalities || 0), 0);
  const countries = new Set(weekEvents.map((e) => e.country).filter(Boolean));
  const dates = weekEvents.map((e) => e.date).filter(Boolean).sort();

  // Category breakdown
  const catMap = new Map<string, { count: number; fat: number }>();
  for (const e of weekEvents) {
    const cat = e.category || "unknown";
    const cur = catMap.get(cat) || { count: 0, fat: 0 };
    cur.count++;
    cur.fat += e.fatalities || 0;
    catMap.set(cat, cur);
  }
  const catBreakdown = Array.from(catMap.entries())
    .map(([cat, v]) => ({ cat, ...v }))
    .sort((a, b) => b.count - a.count);

  // Top countries
  const countryMap = new Map<string, { count: number; fat: number }>();
  for (const e of weekEvents) {
    if (!e.country) continue;
    const cur = countryMap.get(e.country) || { count: 0, fat: 0 };
    cur.count++;
    cur.fat += e.fatalities || 0;
    countryMap.set(e.country, cur);
  }
  const topCountries = Array.from(countryMap.entries())
    .map(([c, v]) => ({ country: c, ...v }))
    .sort((a, b) => b.fat - a.fat)
    .slice(0, 10);

  // Deadliest events
  const deadliest = weekEvents.filter((e) => e.fatalities > 0).slice(0, 10);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <Link
          href="/weekly"
          className="mb-6 inline-flex items-center gap-1 text-xs text-text-dim hover:text-text-primary"
        >
          <ArrowLeft className="h-3 w-3" /> Weekly Recap
        </Link>

        <h1 className="font-display text-4xl font-bold">{week}</h1>
        <p className="mt-2 font-mono text-sm text-text-dim">
          {dates[0]} → {dates[dates.length - 1]}
        </p>

        {/* Summary */}
        <div className="mt-8 grid grid-cols-3 gap-4">
          <StatCard label="Events" value={formatNumber(weekEvents.length)} />
          <StatCard
            label="Fatalities"
            value={formatNumber(totalFat)}
            accent
          />
          <StatCard label="Countries" value={String(countries.size)} />
        </div>

        {/* Category breakdown */}
        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            By Category
          </h2>
          <div className="rounded-lg border border-border bg-surface">
            {catBreakdown.map((item) => {
              const meta = getCategoryMeta(item.cat);
              const pct = (item.count / weekEvents.length) * 100;
              return (
                <div
                  key={item.cat}
                  className="flex items-center gap-4 border-b border-border px-5 py-3 last:border-b-0"
                >
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ background: meta.color }}
                  />
                  <div className="w-36 text-sm font-medium">{meta.label}</div>
                  <div className="flex-1">
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="h-full"
                        style={{ width: `${pct}%`, background: meta.color }}
                      />
                    </div>
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-text-dim">
                    {item.count}
                  </div>
                  <div className="w-20 text-right font-mono text-xs text-text-dim">
                    {formatNumber(item.fat)} 💀
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Top countries */}
        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Top Countries
          </h2>
          <div className="rounded-lg border border-border bg-surface">
            {topCountries.map((c, i) => (
              <Link
                key={c.country}
                href={`/countries/${encodeURIComponent(c.country)}`}
                className="group flex items-center gap-4 border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
              >
                <span className="w-6 text-right font-mono text-xs text-text-dim">
                  {i + 1}
                </span>
                <span className="w-40 font-medium group-hover:text-accent">
                  {c.country}
                </span>
                <span className="font-mono text-xs text-text-dim">
                  {c.count} events
                </span>
                <span className="ml-auto font-mono text-sm font-semibold tabular-nums text-accent">
                  {formatNumber(c.fat)}
                </span>
              </Link>
            ))}
          </div>
        </section>

        {/* Deadliest events */}
        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Deadliest Events
          </h2>
          <div className="rounded-lg border border-border bg-surface">
            {deadliest.map((event) => {
              const meta = getCategoryMeta(event.category);
              return (
                <Link
                  key={event.id}
                  href={`/events/${encodeURIComponent(event.id)}`}
                  className="group flex items-start justify-between gap-4 border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 text-xs">
                      <span
                        className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase text-white"
                        style={{ background: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="font-mono text-text-dim">
                        {formatDate(event.date)}
                      </span>
                      <span className="text-text-dim">· {event.country}</span>
                    </div>
                    <div className="mt-1 truncate text-sm group-hover:text-accent">
                      {event.actor1 || "Unknown"}
                    </div>
                  </div>
                  <div className="font-mono text-lg font-semibold tabular-nums text-accent">
                    {formatNumber(event.fatalities)}
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function StatCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
        {label}
      </div>
      <div
        className={`mt-2 font-display text-3xl font-bold tabular-nums ${
          accent ? "text-accent" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}
