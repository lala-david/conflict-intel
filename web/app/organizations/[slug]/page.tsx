import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import {
  getTopOrganizations,
  getOrganizationEvents,
  getOrganizationTimeline,
  getOrganizationCountries,
  getRelatedOrganizations,
} from "@/lib/queries";
import {
  formatNumber,
  formatDate,
  getCategoryMeta,
  slugify,
  findBySlug,
} from "@/lib/utils";
import { ArrowLeft } from "lucide-react";
import { OrgTimelineChart } from "@/components/charts/OrgTimelineChart";

export const revalidate = 3600;

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props) {
  const orgs = await getTopOrganizations(500);
  const org = findBySlug(orgs, params.slug);
  if (!org) return { title: "Organization not found" };
  return {
    title: `${org.name} — Conflict Researcher`,
    description: `${formatNumber(org.events)} events, ${formatNumber(org.fatalities)} fatalities tracked. Activity from ${org.first_seen?.slice(0, 4)} to ${org.last_seen?.slice(0, 4)}.`,
  };
}

export default async function OrgPage({ params }: Props) {
  const orgs = await getTopOrganizations(500);
  const org = findBySlug(orgs, params.slug);
  if (!org) notFound();

  const events = await getOrganizationEvents(org.name, 30);
  const timeline = await getOrganizationTimeline(org.name);
  const countries = await getOrganizationCountries(org.name);
  const relatedOrgs = await getRelatedOrganizations(org.name, 8);

  const activeYears =
    parseInt(org.last_seen?.slice(0, 4) ?? "0") -
    parseInt(org.first_seen?.slice(0, 4) ?? "0") +
    1;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <Link
          href="/organizations"
          className="mb-6 inline-flex items-center gap-1 text-xs text-text-dim hover:text-text-primary"
        >
          <ArrowLeft className="h-3 w-3" />
          All organizations
        </Link>

        {/* Header */}
        <div className="mb-10 border-b border-border pb-8">
          <h1 className="font-display text-4xl font-bold leading-tight md:text-5xl">
            {org.name}
          </h1>
          <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label="Events" value={formatNumber(org.events)} />
            <Stat label="Fatalities" value={formatNumber(org.fatalities)} />
            <Stat label="Countries" value={String(org.countries)} />
            <Stat
              label="Years active"
              value={`${activeYears}y (${org.first_seen?.slice(0, 4)}–${org.last_seen?.slice(0, 4)})`}
            />
          </div>
        </div>

        {/* Timeline */}
        <section className="mb-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Activity Timeline
          </h2>
          <OrgTimelineChart data={timeline} />
        </section>

        {/* Geographic spread */}
        {countries.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Geographic Spread
            </h2>
            <div className="rounded-lg border border-border bg-surface">
              {countries.map((c, i) => {
                const maxCount = countries[0].count;
                const pct = (c.count / maxCount) * 100;
                return (
                  <Link
                    key={c.country}
                    href={`/countries/${encodeURIComponent(c.country)}`}
                    className="group flex items-center gap-4 border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
                  >
                    <div className="w-6 text-right font-mono text-xs text-text-dim">
                      {i + 1}
                    </div>
                    <div className="w-40 font-medium group-hover:text-accent">
                      {c.country}
                    </div>
                    <div className="flex-1">
                      <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                        <div
                          className="h-full bg-accent/70"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    <div className="w-20 text-right font-mono text-sm tabular-nums text-text-dim">
                      {formatNumber(c.count)}
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Related Organizations */}
        {relatedOrgs.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Related Organizations
            </h2>
            <p className="mb-4 text-xs text-text-dim">
              Groups active in the same countries within the same time periods
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {relatedOrgs.map((r) => (
                <Link
                  key={r.name}
                  href={`/organizations/${slugify(r.name)}`}
                  className="group rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-2"
                >
                  <div className="font-medium text-text-primary group-hover:text-accent">
                    {r.name}
                  </div>
                  <div className="mt-1 font-mono text-xs text-text-dim">
                    {formatNumber(r.events)} co-occurring events · {r.shared_countries} shared countries
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Recent events */}
        <section className="mb-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Recent Activity
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
                      <span className="text-text-dim">· {event.country}</span>
                      {event.location && (
                        <span className="truncate text-text-dim">
                          · {event.location}
                        </span>
                      )}
                    </div>
                    {event.actor2 && event.actor2 !== "Civilians" && (
                      <div className="mt-2 text-sm text-text-dim">
                        vs {event.actor2}
                      </div>
                    )}
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
        {label}
      </div>
      <div className="mt-1 font-display text-2xl font-bold tabular-nums">
        {value}
      </div>
    </div>
  );
}
