import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getTopOrganizations } from "@/lib/queries";
import { formatNumber, slugify } from "@/lib/utils";
import { TrackButton } from "@/components/ui/TrackButton";

export const dynamic = "force-dynamic";


export const metadata = {
  title: "Organizations — Conflict & Security Intelligence",
  description: "Top 100 non-state armed groups by activity. Years active, event counts, fatalities.",
};

export default async function OrganizationsPage() {
  const orgs = await getTopOrganizations(100);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">Organizations</h1>
        <p className="mt-2 text-text-dim">
          Top {orgs.length} non-state armed groups by event count
        </p>

        <div className="mt-8 overflow-hidden card-elevated">
          <div className="grid grid-cols-12 gap-4 border-b border-border bg-surface-2 px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-dim">
            <div className="col-span-1">#</div>
            <div className="col-span-4">Name</div>
            <div className="col-span-2 text-right">Events</div>
            <div className="col-span-2 text-right">Fatalities</div>
            <div className="col-span-1 text-right">Countries</div>
            <div className="col-span-2 text-right">Active</div>
          </div>
          {orgs.map((o, i) => (
            <div
              key={o.name}
              className="group relative border-b border-border transition last:border-b-0 hover:bg-surface-2"
            >
              <Link
                href={`/organizations/${slugify(o.name)}`}
                aria-label={`View ${o.name}`}
                className="absolute inset-0 z-0"
              />
              <div className="pointer-events-none relative z-10 grid grid-cols-12 gap-4 py-3 pl-5 pr-28 text-sm">
                <div className="col-span-1 font-mono text-xs text-text-dim">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="col-span-4 truncate font-medium group-hover:text-accent">
                  {o.name}
                </div>
                <div className="col-span-2 text-right font-mono tabular-nums text-text-dim">
                  {formatNumber(o.events)}
                </div>
                <div className="col-span-2 text-right font-mono tabular-nums text-text-dim">
                  {formatNumber(o.fatalities)}
                </div>
                <div className="col-span-1 text-right font-mono tabular-nums text-text-dim">
                  {o.countries}
                </div>
                <div className="col-span-2 text-right font-mono text-xs text-text-dim">
                  {o.first_seen?.slice(0, 4)}–{o.last_seen?.slice(0, 4)}
                </div>
              </div>
              <div className="absolute right-4 top-1/2 z-20 -translate-y-1/2">
                <TrackButton type="org" value={o.name} compact />
              </div>
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
