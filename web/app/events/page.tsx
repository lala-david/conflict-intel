import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { formatNumber, formatDate, getCategoryMeta, cleanNote } from "@/lib/utils";
import {
  EVENT_CATEGORIES,
  EVENT_CONFIDENCES,
  buildEventWhere,
  countEvents,
  fetchEvents,
  getEventCountries,
  getEventSources,
} from "@/lib/queries-events";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Flag } from "@/components/ui/Flag";
import { SourceBadge, getSourceMeta } from "@/components/ui/SourceBadge";
import { getCorroboration } from "@/lib/queries-provenance";
import { isoFor } from "@/lib/country-iso";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Events — Conflict & Security Intelligence",
  description: "Browse 570,000+ armed violence events from 1970 to present.",
};

interface Props {
  searchParams: {
    q?: string;
    category?: string;
    country?: string;
    from?: string;
    to?: string;
    min_fatalities?: string;
    source?: string;
    confidence?: string;
    page?: string;
  };
}

const PER_PAGE = 30;

export default async function EventsPage({ searchParams }: Props) {
  const page = Math.max(1, parseInt(searchParams.page ?? "1") || 1);

  // Full country + source lists for the filter dropdowns (all, not top-N).
  const [countries, sources] = await Promise.all([
    getEventCountries(),
    getEventSources(),
  ]);
  const sourceSet = new Set(sources);

  const filters = {
    q: searchParams.q,
    category: searchParams.category,
    country: searchParams.country,
    from: searchParams.from,
    to: searchParams.to,
    minFatalities: searchParams.min_fatalities,
    source: searchParams.source,
    confidence: searchParams.confidence,
  };

  const { where, params } = buildEventWhere(filters, sourceSet);

  const total = await countEvents(where, params);
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const currentPage = Math.min(page, totalPages);
  const offset = (currentPage - 1) * PER_PAGE;

  const events = await fetchEvents(where, params, PER_PAGE, offset);

  // One batched query for the whole page: id → number of corroborating sources.
  const corroboration = await getCorroboration(events.map((e) => e.id));

  const hasFilters = !!(
    searchParams.q ||
    searchParams.category ||
    searchParams.country ||
    searchParams.from ||
    searchParams.to ||
    searchParams.min_fatalities ||
    searchParams.source ||
    searchParams.confidence
  );

  // Build URL helper — merges current params with overrides, drops empties.
  function buildUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const merged = { ...searchParams, ...overrides };
    for (const [k, v] of Object.entries(merged)) {
      if (v && v !== "") p.set(k, v);
    }
    const qs = p.toString();
    return qs ? `/events?${qs}` : "/events";
  }

  // Compact page-number window around the current page.
  const pageWindow: number[] = [];
  {
    const span = 2;
    let start = Math.max(1, currentPage - span);
    let end = Math.min(totalPages, currentPage + span);
    // keep a stable width of up to 5 numbers when near the edges
    if (currentPage <= span) end = Math.min(totalPages, 1 + span * 2);
    if (currentPage > totalPages - span) start = Math.max(1, totalPages - span * 2);
    for (let i = start; i <= end; i++) pageWindow.push(i);
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <PageHeader
          kicker="1970 — today"
          title="Every event, searchable"
          standfirst="More than 570,000 individual records of organized violence, categorized by academic standard. Filter by actor, country, category, date, severity, source or confidence."
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

        {/* Filters — GET form so every filter lands in the (shareable) URL */}
        <form className="mt-8 grid gap-4 rounded-lg border border-border bg-surface p-5 md:grid-cols-6">
          {/* Search */}
          <div className="md:col-span-3">
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
          <div className="md:col-span-2">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Category
            </label>
            <select
              name="category"
              defaultValue={searchParams.category ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              <option value="">All categories</option>
              {EVENT_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {getCategoryMeta(c).label}
                </option>
              ))}
            </select>
          </div>

          {/* Country — full list */}
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

          {/* Source */}
          <div className="md:col-span-2">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Source
            </label>
            <select
              name="source"
              defaultValue={searchParams.source ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              <option value="">All sources</option>
              {sources.map((s) => (
                <option key={s} value={s}>
                  {getSourceMeta(s).provider} ({s})
                </option>
              ))}
            </select>
          </div>

          {/* Confidence */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Confidence
            </label>
            <select
              name="confidence"
              defaultValue={searchParams.confidence ?? ""}
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              <option value="">Any confidence</option>
              {EVENT_CONFIDENCES.map((c) => (
                <option key={c} value={c}>
                  {c[0].toUpperCase() + c.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Min fatalities */}
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              Min. fatalities
            </label>
            <input
              type="number"
              min={0}
              name="min_fatalities"
              defaultValue={searchParams.min_fatalities ?? ""}
              placeholder="0"
              className="w-full rounded-md border border-border bg-background py-2 px-3 text-sm text-text-primary placeholder-text-dim focus:border-accent focus:outline-none"
            />
          </div>

          {/* From */}
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

          {/* To */}
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

          {/* Submit */}
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
            >
              Filter
            </button>
          </div>

          {/* Clear */}
          {hasFilters && (
            <div className="flex items-end">
              <Link
                href="/events"
                className="text-sm text-text-dim hover:text-accent"
              >
                Clear all filters
              </Link>
            </div>
          )}
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
              const note = cleanNote(event.notes);
              const hasActor =
                !!event.actor1 &&
                event.actor1 !== "Unknown" &&
                event.actor1 !== (event.country || "").toUpperCase();
              const title = hasActor ? event.actor1 : note || "Unattributed incident";
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
                      <span className="inline-flex items-center gap-1.5 text-text-dim">
                        · <Flag iso={event.country_code || isoFor(event.country)} size="sm" /> {event.country}
                      </span>
                      {event.location && (
                        <span className="truncate text-text-dim">
                          · {event.location}
                        </span>
                      )}
                      <SourceBadge
                        source={event.source}
                        count={corroboration.get(event.id)}
                      />
                    </div>
                    <div className="mt-2 truncate text-sm font-medium text-text-primary group-hover:text-accent">
                      {title}
                      {hasActor && event.actor2 && event.actor2 !== "Civilians" && (
                        <span className="text-text-dim"> vs {event.actor2}</span>
                      )}
                    </div>
                    {hasActor && note && (
                      <div className="mt-1 line-clamp-1 text-xs text-text-dim">
                        {note}
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

        {/* Pagination — first / prev / numbered window / next / last + jump */}
        {totalPages > 1 && (
          <nav
            aria-label="Pagination"
            className="mt-6 flex flex-col items-center gap-3"
          >
            <div className="flex flex-wrap items-center justify-center gap-1.5">
              <PageLink
                href={buildUrl({ page: "1" })}
                disabled={currentPage <= 1}
                label="« First"
              />
              <PageLink
                href={buildUrl({ page: String(currentPage - 1) })}
                disabled={currentPage <= 1}
                label="‹ Prev"
              />

              {pageWindow[0] > 1 && (
                <span className="px-2 text-sm text-text-dim">…</span>
              )}
              {pageWindow.map((n) => (
                <Link
                  key={n}
                  href={buildUrl({ page: String(n) })}
                  aria-current={n === currentPage ? "page" : undefined}
                  className={
                    n === currentPage
                      ? "rounded-md border border-accent bg-accent px-3.5 py-2 text-sm font-medium text-white"
                      : "rounded-md border border-border px-3.5 py-2 text-sm text-text-dim hover:bg-surface-2"
                  }
                >
                  {formatNumber(n)}
                </Link>
              ))}
              {pageWindow[pageWindow.length - 1] < totalPages && (
                <span className="px-2 text-sm text-text-dim">…</span>
              )}

              <PageLink
                href={buildUrl({ page: String(currentPage + 1) })}
                disabled={currentPage >= totalPages}
                label="Next ›"
              />
              <PageLink
                href={buildUrl({ page: String(totalPages) })}
                disabled={currentPage >= totalPages}
                label="Last »"
              />
            </div>

            {/* Jump-to-page — GET form preserving every active filter */}
            <form action="/events" className="flex items-center gap-2 text-sm text-text-dim">
              {Object.entries(searchParams).map(([k, v]) =>
                k === "page" || !v ? null : (
                  <input key={k} type="hidden" name={k} value={v} />
                ),
              )}
              <span>
                Page{" "}
                <span className="tabular-nums text-text-primary">{formatNumber(currentPage)}</span>{" "}
                of {formatNumber(totalPages)} · jump to
              </span>
              <input
                type="number"
                name="page"
                min={1}
                max={totalPages}
                defaultValue={currentPage}
                className="w-20 rounded-md border border-border bg-background px-2 py-1.5 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
              <button
                type="submit"
                className="rounded-md border border-border px-3 py-1.5 text-sm text-text-primary hover:bg-surface-2"
              >
                Go
              </button>
            </form>
          </nav>
        )}
      </main>
      <Footer />
    </>
  );
}

/** A pagination control that renders as a link, or a dimmed span when disabled. */
function PageLink({
  href,
  label,
  disabled,
}: {
  href: string;
  label: string;
  disabled: boolean;
}) {
  if (disabled) {
    return (
      <span className="cursor-default rounded-md border border-border px-3.5 py-2 text-sm text-text-dim/40">
        {label}
      </span>
    );
  }
  return (
    <Link
      href={href}
      className="rounded-md border border-border px-3.5 py-2 text-sm text-text-dim hover:bg-surface-2"
    >
      {label}
    </Link>
  );
}
