import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { queryAll, queryOne } from "@/lib/db";
import { formatNumber, formatDate, getCategoryMeta } from "@/lib/utils";
import type { Event, Category } from "@/lib/types";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Events — Conflict & Security Intelligence",
  description: "Browse 420,000+ armed violence events from 1989 to present.",
};

interface Props {
  searchParams: {
    q?: string;
    category?: string;
    country?: string;
    from?: string;
    to?: string;
    page?: string;
  };
}

const PER_PAGE = 30;

const ALL_CATEGORIES: Category[] = [
  "war", "civil_war", "terrorism", "mass_atrocity", "state_violence",
  "cartel_violence", "communal_violence", "insurgency", "counterterrorism", "armed_violence",
];

export default async function EventsPage({ searchParams }: Props) {
  const page = Math.max(1, parseInt(searchParams.page ?? "1"));
  const offset = (page - 1) * PER_PAGE;

  // Build dynamic WHERE clause
  const conditions: string[] = ["is_aggregate = 0", "dup_of IS NULL"];
  const params: any[] = [];

  if (searchParams.q && searchParams.q.length >= 2) {
    const like = `%${searchParams.q}%`;
    conditions.push("(actor1 LIKE ? OR actor2 LIKE ? OR country LIKE ? OR notes LIKE ?)");
    params.push(like, like, like, like);
  }

  if (searchParams.category && ALL_CATEGORIES.includes(searchParams.category as Category)) {
    conditions.push("category = ?");
    params.push(searchParams.category);
  }

  if (searchParams.country) {
    conditions.push("country = ?");
    params.push(searchParams.country);
  }

  if (searchParams.from) {
    conditions.push("date >= ?");
    params.push(searchParams.from);
  }

  if (searchParams.to) {
    conditions.push("date <= ?");
    params.push(searchParams.to);
  }

  const where = conditions.join(" AND ");

  // Count total results
  const countRow = (await queryOne<{ total: number }>(
    `SELECT COUNT(*) as total FROM events WHERE ${where}`,
    [...params]
  )) as { total: number };
  const total = countRow.total;
  const totalPages = Math.ceil(total / PER_PAGE);

  // Fetch events
  const events = await queryAll<Event>(
    `SELECT id, source, date, event_type, actor1, actor2, country, country_code,
              admin1, location, latitude, longitude, fatalities,
              deaths_civilians, fatalities_low, fatalities_high,
              category, category_confidence, is_aggregate, notes, source_url
         FROM events
        WHERE ${where}
        ORDER BY date DESC, fatalities DESC
        LIMIT ? OFFSET ?`,
    [...params, PER_PAGE, offset]
  );

  // Distinct countries for filter dropdown
  const countries = await queryAll<{ country: string }>(
    `SELECT DISTINCT country FROM country_stats ORDER BY total_fatalities DESC LIMIT 50`
  );

  // Build URL helper
  function buildUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const merged = { ...searchParams, ...overrides };
    for (const [k, v] of Object.entries(merged)) {
      if (v && v !== "") p.set(k, v);
    }
    return `/events?${p.toString()}`;
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <PageHeader
          kicker="1989 — today"
          title="Every event, searchable"
          standfirst="More than 420,000 individual records of organized violence, categorized by academic standard. Filter by actor, country, category or date."
          aside={
            <div className="text-right">
              <div className="font-display text-4xl font-semibold tabular-nums text-text-primary">
                {formatNumber(total)}
              </div>
              <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-text-dim">
                matching events
              </div>
            </div>
          }
        />

        {/* Filters */}
        <form className="mt-8 grid gap-4 rounded-lg border border-border bg-surface p-5 md:grid-cols-5">
          {/* Search */}
          <div className="md:col-span-2">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" />
              <input
                type="text"
                name="q"
                defaultValue={searchParams.q ?? ""}
                placeholder="Actor, country, keyword..."
                className="w-full rounded-md border border-border bg-background py-2 pl-10 pr-3 text-sm text-text-primary placeholder-text-dim focus:border-accent focus:outline-none"
              />
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Category
            </label>
            <select
              name="category"
              defaultValue={searchParams.category ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              <option value="">All categories</option>
              {ALL_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {getCategoryMeta(c).label}
                </option>
              ))}
            </select>
          </div>

          {/* Country */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Country
            </label>
            <select
              name="country"
              defaultValue={searchParams.country ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              <option value="">All countries</option>
              {countries.map((c) => (
                <option key={c.country} value={c.country}>
                  {c.country}
                </option>
              ))}
            </select>
          </div>

          {/* Submit */}
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
            >
              Filter
            </button>
          </div>

          {/* Date range row */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              From
            </label>
            <input
              type="date"
              name="from"
              defaultValue={searchParams.from ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              To
            </label>
            <input
              type="date"
              name="to"
              defaultValue={searchParams.to ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            />
          </div>

          {/* Clear */}
          <div className="flex items-end md:col-span-3">
            {(searchParams.q || searchParams.category || searchParams.country || searchParams.from || searchParams.to) && (
              <Link
                href="/events"
                className="text-sm text-text-dim hover:text-accent"
              >
                Clear all filters
              </Link>
            )}
          </div>
        </form>

        {/* Results */}
        <div className="mt-8 rounded-lg border border-border bg-surface">
          {events.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-text-dim">
              No events found matching your filters.
            </div>
          ) : (
            events.map((event) => {
              const meta = getCategoryMeta(event.category);
              return (
                <Link
                  key={event.id}
                  href={`/events/${encodeURIComponent(event.id)}`}
                  className="group flex items-start justify-between gap-4 border-b border-border px-5 py-4 transition last:border-b-0 hover:bg-surface-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white"
                        style={{ background: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="font-mono text-text-dim">
                        {formatDate(event.date)}
                      </span>
                      <span className="text-text-dim">· {event.country}</span>
                      {event.location && (
                        <span className="truncate text-text-dim">
                          · {event.location}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 truncate text-sm font-medium text-text-primary group-hover:text-accent">
                      {event.actor1 || "Unknown"}
                      {event.actor2 && event.actor2 !== "Civilians" && (
                        <span className="text-text-dim"> vs {event.actor2}</span>
                      )}
                    </div>
                    {event.notes && (
                      <div className="mt-1 line-clamp-1 text-xs text-text-dim">
                        {event.notes}
                      </div>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="font-display text-2xl font-semibold tabular-nums leading-none">
                      {formatNumber(event.fatalities)}
                    </div>
                    <div className="mt-1 text-[10px] uppercase tracking-wider text-text-dim">
                      killed
                    </div>
                  </div>
                </Link>
              );
            })
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-center gap-2">
            {page > 1 && (
              <Link
                href={buildUrl({ page: String(page - 1) })}
                className="rounded-md border border-border px-4 py-2 text-sm text-text-dim hover:bg-surface-2"
              >
                Previous
              </Link>
            )}
            <span className="px-4 py-2 text-sm text-text-dim">
              Page {page} of {formatNumber(totalPages)}
            </span>
            {page < totalPages && (
              <Link
                href={buildUrl({ page: String(page + 1) })}
                className="rounded-md border border-border px-4 py-2 text-sm text-text-dim hover:bg-surface-2"
              >
                Next
              </Link>
            )}
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
