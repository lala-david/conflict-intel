import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { CountryTimeline } from "@/components/charts/CountryTimeline";
import { TrackButton } from "@/components/ui/TrackButton";
import { NodeSpreadMapClient } from "@/components/map/NodeSpreadMapClient";
import {
  getCountryByName,
  getCountryEvents,
  getCountryTimeline,
  getCountryPoints,
  getCountryTopActors,
  getCountryList,
} from "@/lib/queries";
import { formatNumber, formatDate, getCategoryMeta, slugify } from "@/lib/utils";
import { ArrowLeft, Download } from "lucide-react";
import { ShareButton } from "@/components/ui/ShareButton";

export const revalidate = 3600;

// Pre-generate top 30 countries at build time
export async function generateStaticParams() {
  try {
    const countries = await getCountryList();
    return countries.slice(0, 30).map((c) => ({
      iso: encodeURIComponent(c.country),
    }));
  } catch {
    // DB not reachable at build time (TURSO env only set at runtime) →
    // skip prerendering; pages render on-demand (ISR) using runtime vars.
    return [];
  }
}

interface Props {
  params: { iso: string };
}

export async function generateMetadata({ params }: Props) {
  const name = decodeURIComponent(params.iso);
  const ogUrl = `/api/og/countries/${encodeURIComponent(name)}`;
  return {
    title: `${name} — Conflict & Security Intelligence`,
    description: `Armed violence events in ${name}. 1989-present. Terrorism, civil war, insurgency data.`,
    openGraph: {
      title: `${name} — Conflict & Security Intelligence`,
      description: `Armed violence events in ${name}. 420K events, 38 years.`,
      images: [{ url: ogUrl, width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogUrl],
    },
  };
}

export default async function CountryPage({ params }: Props) {
  const name = decodeURIComponent(params.iso);
  const country = await getCountryByName(name);
  if (!country) notFound();

  const [events, timeline, points, topActors] = await Promise.all([
    getCountryEvents(name, 30),
    getCountryTimeline(name),
    getCountryPoints(name, 800),
    getCountryTopActors(name, 8),
  ]);

  // Calculate category breakdown
  const catBreakdown = new Map<string, { count: number; deaths: number }>();
  for (const row of timeline) {
    const cur = catBreakdown.get(row.category) ?? { count: 0, deaths: 0 };
    cur.count += row.count;
    cur.deaths += row.deaths;
    catBreakdown.set(row.category, cur);
  }
  const topCats = Array.from(catBreakdown.entries())
    .map(([cat, v]) => ({ cat, ...v }))
    .sort((a, b) => b.count - a.count);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        {/* Back */}
        <Link
          href="/countries"
          className="mb-6 inline-flex items-center gap-1 text-xs text-text-dim hover:text-text-primary"
        >
          <ArrowLeft className="h-3 w-3" />
          All countries
        </Link>

        {/* Header */}
        <div className="mb-10 border-b border-border pb-8">
          <div className="flex items-start justify-between">
            <h1 className="font-display text-5xl font-bold">{country.country}</h1>
            <ShareButton title={`${country.country} — Conflict & Security Intelligence`} />
          </div>
          <div className="mt-3 flex items-center gap-3">
            <TrackButton type="country" value={name} />
            <a
              href={`/api/export/csv?country=${encodeURIComponent(name)}`}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-dim transition hover:bg-surface-2 hover:text-text-primary"
            >
              <Download className="h-3 w-3" />
              Download CSV
            </a>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat
              label="All-time events"
              value={formatNumber(country.event_count)}
            />
            <Stat
              label="All-time killed"
              value={formatNumber(country.total_fatalities)}
            />
            <Stat
              label="30-day events"
              value={formatNumber(country.recent_30d_events)}
            />
            <Stat
              label="30-day killed"
              value={formatNumber(country.recent_30d_fatalities)}
              accent={country.recent_30d_fatalities > 0}
            />
          </div>
        </div>

        {/* Timeline */}
        <section className="mb-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            38-Year Timeline
          </h2>
          <CountryTimeline data={timeline} />
        </section>

        {/* Where it happens: spread map */}
        {points.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Where it happens
            </h2>
            <NodeSpreadMapClient points={points} />
            <p className="mt-2 font-mono text-[11px] uppercase tracking-wider text-text-dim">
              {formatNumber(points.length)} geolocated events · dot size = fatalities · click a dot for details
            </p>
          </section>
        )}

        {/* Groups active here: node network → organization nodes */}
        {topActors.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Groups active here
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              {topActors.map((a) => (
                <Link
                  key={a.name}
                  href={`/organizations/${slugify(a.name)}`}
                  className="group flex items-center justify-between gap-4 rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-2"
                >
                  <div className="min-w-0">
                    <div className="truncate font-medium text-text-primary group-hover:text-accent">
                      {a.name}
                    </div>
                    <div className="mt-1 font-mono text-xs text-text-dim">
                      {formatNumber(a.fatalities)} killed
                    </div>
                  </div>
                  <span className="shrink-0 font-display text-xl font-semibold tabular-nums text-text-dim">
                    {formatNumber(a.events)}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Category breakdown */}
        {topCats.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              By Category
            </h2>
            <div className="rounded-lg border border-border bg-surface">
              {topCats.map((item) => {
                const meta = getCategoryMeta(item.cat);
                const pct =
                  (item.count /
                    topCats.reduce((s, c) => s + c.count, 0)) *
                  100;
                return (
                  <div
                    key={item.cat}
                    className="flex items-center gap-4 border-b border-border px-5 py-3 last:border-b-0"
                  >
                    <div className="w-36 font-medium text-text-primary">
                      {meta.label}
                    </div>
                    <div className="flex-1">
                      <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                        <div
                          className="h-full transition-all"
                          style={{
                            width: `${pct}%`,
                            background: meta.color,
                          }}
                        />
                      </div>
                    </div>
                    <div className="w-24 text-right font-mono text-sm tabular-nums text-text-dim">
                      {formatNumber(item.count)}
                    </div>
                    <div className="w-24 text-right font-mono text-sm tabular-nums text-text-dim">
                      {formatNumber(item.deaths)}💀
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Recent events */}
        <section className="mb-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Recent Events
          </h2>
          <div className="rounded-lg border border-border bg-surface">
            {events.map((event) => {
              const meta = getCategoryMeta(event.category);
              return (
                <Link
                  key={event.id}
                  href={`/events/${encodeURIComponent(event.id)}`}
                  className="group flex items-start justify-between gap-4 border-b border-border px-5 py-4 transition last:border-b-0 hover:bg-surface-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3 text-xs">
                      <span
                        className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white"
                        style={{ background: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="font-mono text-text-dim">
                        {formatDate(event.date)}
                      </span>
                      {event.location && (
                        <span className="text-text-dim">· {event.location}</span>
                      )}
                    </div>
                    <div className="mt-2 text-sm font-medium group-hover:text-accent">
                      {event.actor1 || "Unknown"}
                      {event.actor2 && event.actor2 !== "Civilians" && (
                        <span className="text-text-dim"> vs {event.actor2}</span>
                      )}
                    </div>
                    {event.notes && (
                      <div className="mt-1 line-clamp-2 text-xs text-text-dim">
                        {event.notes}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-lg font-semibold tabular-nums">
                      {formatNumber(event.fatalities)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-text-dim">
                      killed
                    </div>
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

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
        {label}
      </div>
      <div
        className={`mt-1 font-display text-3xl font-bold tabular-nums ${
          accent ? "text-accent" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}
