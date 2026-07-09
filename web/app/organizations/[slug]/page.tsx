import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { TrackButton } from "@/components/ui/TrackButton";
import { NodeSpreadMapClient } from "@/components/map/NodeSpreadMapClient";
import {
  getTopOrganizations,
  getOrganizationEvents,
  getOrganizationTimeline,
  getOrganizationCountries,
  getOrganizationPoints,
  getRelatedOrganizations,
  getCryptoWallets,
} from "@/lib/queries";
import { WalletTable } from "@/components/wallets/WalletTable";

// Map an actor name to the canonical crypto-wallet organization label.
const CRYPTO_ORG_MAP: [RegExp, string][] = [
  [/islamic state|isis|isil|daesh/i, "Islamic State"],
  [/hamas|qassam/i, "Hamas"],
  [/hizballah|hezbollah/i, "Hezbollah"],
  [/houthi|ansarallah/i, "Houthis (Ansarallah)"],
  [/al[- ]?qa'?ida|al[- ]?qaeda/i, "al-Qaeda"],
  [/al[- ]?shabaab/i, "al-Shabaab"],
  [/islamic jihad|\bpij\b/i, "Palestinian Islamic Jihad"],
  [/boko haram/i, "Boko Haram"],
  [/taliban|haqqani/i, "Taliban / Haqqani"],
];
function cryptoOrgFor(name: string): string | null {
  for (const [re, canon] of CRYPTO_ORG_MAP) if (re.test(name)) return canon;
  return null;
}
import {
  formatNumber,
  formatDate,
  getCategoryMeta,
  slugify,
  findBySlug,
} from "@/lib/utils";
import { ArrowLeft } from "lucide-react";
import { OrgTimelineChart } from "@/components/charts/OrgTimelineChart";
import { orgSummary } from "@/lib/summary";

export const revalidate = 3600;

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props) {
  const orgs = await getTopOrganizations(500);
  const org = findBySlug(orgs, params.slug);
  if (!org) return { title: "Organization not found" };
  return {
    title: `${org.name} — Conflict & Security Intelligence`,
    description: `${formatNumber(org.events)} events, ${formatNumber(org.fatalities)} fatalities tracked. Activity from ${org.first_seen?.slice(0, 4)} to ${org.last_seen?.slice(0, 4)}.`,
  };
}

export default async function OrgPage({ params }: Props) {
  const orgs = await getTopOrganizations(500);
  const org = findBySlug(orgs, params.slug);
  if (!org) notFound();

  const cryptoOrg = cryptoOrgFor(org.name);
  const [events, timeline, countries, points, relatedOrgs, wallets] = await Promise.all([
    getOrganizationEvents(org.name, 30),
    getOrganizationTimeline(org.name),
    getOrganizationCountries(org.name),
    getOrganizationPoints(org.name, 500),
    getRelatedOrganizations(org.name, 8),
    cryptoOrg ? getCryptoWallets({ org: cryptoOrg, limit: 300 }) : Promise.resolve([]),
  ]);

  const activeYears =
    parseInt(org.last_seen?.slice(0, 4) ?? "0") -
    parseInt(org.first_seen?.slice(0, 4) ?? "0") +
    1;

  // Peak year: the year with the most recorded events.
  let peakYear: number | null = null;
  let peakCount = -1;
  for (const row of timeline) {
    if (row.count > peakCount) {
      peakCount = row.count;
      peakYear = row.year;
    }
  }

  const firstYear = parseInt(org.first_seen?.slice(0, 4) ?? "") || null;
  const lastYear = parseInt(org.last_seen?.slice(0, 4) ?? "") || null;

  // Direct co-actors: a GENUINE relationship, not same-country co-occurrence.
  // These are the groups recorded as the SECOND actor (actor2) in this org's own
  // events — the parties it is actually pitted against / operating alongside on
  // the ground. Derived from `points` (already fetched, up to 500 events), so no
  // extra query. actor2 in the feeds is often a target noun ("Civilians",
  // "Market", "Checkpoint"), so we keep only actor2 values that are themselves a
  // tracked organization (present in the top-orgs list) — that filter is what
  // makes this a group-to-group link rather than target noise.
  const orgNameSet = new Set(orgs.map((o) => o.name));
  const coActorCounts = new Map<string, number>();
  for (const p of points) {
    const a2 = p.actor2?.trim();
    if (!a2 || a2 === org.name || a2 === "Civilians") continue;
    if (!orgNameSet.has(a2)) continue;
    coActorCounts.set(a2, (coActorCounts.get(a2) ?? 0) + 1);
  }
  const coActors = [...coActorCounts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  // Deterministic prose summary (SEO long-tail + human orientation).
  const summary = orgSummary({
    name: org.name,
    events: org.events,
    fatalities: org.fatalities,
    countries: org.countries,
    firstYear,
    lastYear,
    peakYear,
    topCountry: countries[0]?.country ?? null,
  });

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
          <div className="flex flex-wrap items-start justify-between gap-4">
            <h1 className="font-display text-4xl font-bold leading-tight md:text-5xl">
              {org.name}
            </h1>
            <TrackButton type="org" value={org.name} />
          </div>
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

        {/* Auto-generated prose summary */}
        {summary && (
          <p className="mb-12 max-w-3xl text-base leading-relaxed text-text-dim">
            {summary}
          </p>
        )}

        {/* Timeline */}
        <section className="mb-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Activity Timeline
          </h2>
          <OrgTimelineChart data={timeline} />
        </section>

        {/* Where they operate: spread map + country breakdown */}
        {(points.length > 0 || countries.length > 0) && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Where they operate
            </h2>
            {points.length > 0 && (
              <div className="mb-4">
                <NodeSpreadMapClient points={points} />
                <p className="mt-2 font-mono text-[11px] uppercase tracking-wider text-text-dim">
                  {formatNumber(points.length)} geolocated events · dot size = fatalities · click a dot for details
                </p>
              </div>
            )}
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

        {/* Known crypto wallets */}
        {wallets.length > 0 && (
          <section className="mb-12">
            <div className="mb-4 flex items-baseline justify-between">
              <h2 className="font-display text-2xl font-bold">
                Known crypto wallets{" "}
                <span className="text-accent">{wallets.length}</span>
              </h2>
              <Link href="/wallets" className="text-xs text-text-dim hover:text-accent">
                All terror-financing wallets →
              </Link>
            </div>
            <p className="mb-4 text-xs text-text-dim">
              Cryptocurrency addresses publicly attributed to this group (OFAC/EU/UN sanctions,
              DOJ forfeiture). Click an address to view it on a blockchain explorer.
            </p>
            <WalletTable wallets={wallets} />
          </section>
        )}

        {/* Direct co-actors — genuine actor1↔actor2 links from this org's events */}
        {coActors.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Direct co-actors
            </h2>
            <p className="mb-4 text-xs text-text-dim">
              Groups recorded as the opposing or second party in {org.name}&apos;s own
              events — a direct operational relationship, not just shared geography
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {coActors.map((r) => (
                <Link
                  key={r.name}
                  href={`/organizations/${slugify(r.name)}`}
                  className="group rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-2"
                >
                  <div className="font-medium text-text-primary group-hover:text-accent">
                    {r.name}
                  </div>
                  <div className="mt-1 font-mono text-xs text-text-dim">
                    {formatNumber(r.count)} shared events
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Related Organizations */}
        {relatedOrgs.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Also active nearby
            </h2>
            <p className="mb-4 text-xs text-text-dim">
              Groups active in the same countries within the same time periods
              (regional overlap, not a confirmed direct link)
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
