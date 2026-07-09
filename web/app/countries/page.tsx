import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getCountryList } from "@/lib/queries";
import { formatNumber } from "@/lib/utils";
import { PageHeader } from "@/components/ui/PageHeader";
import { Flag } from "@/components/ui/Flag";
import { isoFor } from "@/lib/country-iso";
import { TrackButton } from "@/components/ui/TrackButton";

export const dynamic = "force-dynamic";


export const metadata = {
  title: "Countries — Conflict & Security Intelligence",
  description: "All 250+ countries tracked. Event counts and fatalities from 1970 to present.",
};

export default async function CountriesPage() {
  const countries = await getCountryList();
  const maxFat30 = Math.max(...countries.map((c) => c.recent_30d_fatalities), 1);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <PageHeader
          kicker="The world, ranked"
          title="Countries"
          standfirst={`Every one of ${formatNumber(countries.length)} countries we track, ranked by recent toll — all-time and last-30-day events and fatalities.`}
        />

        <div className="mt-8 overflow-hidden card-elevated">
          <div className="grid grid-cols-12 gap-4 border-b border-border bg-surface-2 px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-dim">
            <div className="col-span-1">#</div>
            <div className="col-span-4">Country</div>
            <div className="col-span-2 text-right">All-time events</div>
            <div className="col-span-2 text-right">All-time killed</div>
            <div className="col-span-1 text-right">30d events</div>
            <div className="col-span-2 text-right">30d killed</div>
          </div>
          {countries.map((c, i) => {
            const pct = (c.recent_30d_fatalities / maxFat30) * 100;
            return (
              <div
                key={c.country}
                className="group relative border-b border-border transition last:border-b-0 hover:bg-surface-2"
              >
                <Link
                  href={`/countries/${encodeURIComponent(c.country)}`}
                  aria-label={`View ${c.country}`}
                  className="absolute inset-0 z-0"
                />
                <div className="pointer-events-none relative z-10 grid grid-cols-12 gap-4 py-3 pl-5 pr-28 text-sm">
                  <div className="col-span-1 font-mono text-xs text-text-dim">
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="col-span-4 flex items-center gap-2.5 font-medium text-text-primary group-hover:text-accent">
                    <Flag iso={isoFor(c.country)} size="md" />
                    {c.country}
                  </div>
                  <div className="col-span-2 text-right font-mono tabular-nums text-text-dim">
                    {formatNumber(c.event_count)}
                  </div>
                  <div className="col-span-2 text-right font-mono tabular-nums text-text-dim">
                    {formatNumber(c.total_fatalities)}
                  </div>
                  <div className="col-span-1 text-right font-mono tabular-nums text-text-dim">
                    {formatNumber(c.recent_30d_events)}
                  </div>
                  <div className="col-span-2 text-right font-mono tabular-nums">
                    <span className={c.recent_30d_fatalities > 0 ? "text-accent" : "text-text-dim"}>
                      {formatNumber(c.recent_30d_fatalities)}
                    </span>
                  </div>
                </div>
                <div className="absolute right-4 top-1/2 z-20 -translate-y-1/2">
                  <TrackButton type="country" value={c.country} compact />
                </div>
                {c.recent_30d_fatalities > 0 && (
                  <div
                    className="absolute bottom-0 left-0 z-10 h-0.5 bg-accent/40"
                    style={{ width: `${pct}%` }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </main>
      <Footer />
    </>
  );
}
