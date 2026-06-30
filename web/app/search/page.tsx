import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { searchEvents, searchCountries, searchOrgs } from "@/lib/queries";
import { formatNumber, formatDate, getCategoryMeta, slugify } from "@/lib/utils";
import { Search } from "lucide-react";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Search — Conflict Researcher",
};

interface Props {
  searchParams: { q?: string };
}

export default async function SearchPage({ searchParams }: Props) {
  const q = searchParams.q || "";
  const countries = q ? await searchCountries(q) : [];
  const orgs = q ? await searchOrgs(q) : [];
  const events = q ? await searchEvents(q, 15) : [];

  const totalResults = countries.length + orgs.length + events.length;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="font-display text-4xl font-bold">Search</h1>
        <p className="mt-2 text-sm text-text-dim">
          Search 420K events across countries, organizations, and incidents.
        </p>

        {/* Search form */}
        <form action="/search" method="GET" className="mt-6">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" />
              <input
                type="text"
                name="q"
                defaultValue={q}
                placeholder="Nigeria, Hamas, suicide bombing..."
                autoFocus
                className="w-full rounded-lg border border-border bg-surface py-3 pl-10 pr-4 text-sm text-text-primary placeholder:text-text-dim focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-accent px-6 py-3 text-sm font-medium text-white hover:bg-accent/90"
            >
              Search
            </button>
          </div>
        </form>

        {q && (
          <div className="mt-8">
            <p className="text-sm text-text-dim">
              {totalResults} results for &quot;{q}&quot;
            </p>

            {/* Countries */}
            {countries.length > 0 && (
              <section className="mt-6">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-dim">
                  Countries
                </h2>
                <div className="rounded-lg border border-border bg-surface">
                  {countries.map((c) => (
                    <Link
                      key={c.country}
                      href={`/countries/${encodeURIComponent(c.country)}`}
                      className="group flex items-center justify-between border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
                    >
                      <span className="font-medium group-hover:text-accent">
                        {c.country}
                      </span>
                      <span className="font-mono text-xs text-text-dim">
                        {formatNumber(c.total_events)} events ·{" "}
                        {formatNumber(c.total_fatalities)} killed
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Organizations */}
            {orgs.length > 0 && (
              <section className="mt-6">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-dim">
                  Organizations
                </h2>
                <div className="rounded-lg border border-border bg-surface">
                  {orgs.map((o) => (
                    <Link
                      key={o.name}
                      href={`/organizations/${slugify(o.name)}`}
                      className="group flex items-center justify-between border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
                    >
                      <span className="font-medium group-hover:text-accent">
                        {o.name}
                      </span>
                      <span className="font-mono text-xs text-text-dim">
                        {formatNumber(o.total_events)} events
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Events */}
            {events.length > 0 && (
              <section className="mt-6">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-dim">
                  Events
                </h2>
                <div className="rounded-lg border border-border bg-surface">
                  {events.map((event) => {
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
                              className="inline-flex rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase text-white"
                              style={{ background: meta.color }}
                            >
                              {meta.label}
                            </span>
                            <span className="font-mono text-text-dim">
                              {formatDate(event.date)}
                            </span>
                            <span className="text-text-dim">
                              · {event.country}
                            </span>
                          </div>
                          <div className="mt-1 truncate text-sm group-hover:text-accent">
                            {event.actor1 || "Unknown"}
                          </div>
                        </div>
                        <div className="font-mono text-sm font-semibold tabular-nums">
                          {formatNumber(event.fatalities)}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </section>
            )}

            {totalResults === 0 && (
              <div className="mt-12 text-center text-sm text-text-dim">
                No results found. Try a different search term.
              </div>
            )}
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
