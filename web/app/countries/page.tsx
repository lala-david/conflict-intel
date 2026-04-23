import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getCountryList } from "@/lib/queries";
import { formatNumber } from "@/lib/utils";

export const revalidate = 3600;

export const metadata = {
  title: "Countries — Conflict Researcher",
  description: "All 172 countries tracked. Event counts and fatalities from 1989 to present.",
};

export default function CountriesPage() {
  const countries = getCountryList();
  const maxFat30 = Math.max(...countries.map((c) => c.recent_30d_fatalities), 1);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">Countries</h1>
        <p className="mt-2 text-text-dim">
          {formatNumber(countries.length)} countries tracked · All-time and 30-day stats
        </p>

        <div className="mt-8 overflow-hidden rounded-lg border border-border bg-surface">
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
              <Link
                key={c.country}
                href={`/countries/${encodeURIComponent(c.country)}`}
                className="group relative grid grid-cols-12 gap-4 border-b border-border px-5 py-3 text-sm transition last:border-b-0 hover:bg-surface-2"
              >
                <div className="col-span-1 font-mono text-xs text-text-dim">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="col-span-4 font-medium text-text-primary group-hover:text-accent">
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
                {c.recent_30d_fatalities > 0 && (
                  <div
                    className="absolute bottom-0 left-0 h-0.5 bg-accent/40"
                    style={{ width: `${pct}%` }}
                  />
                )}
              </Link>
            );
          })}
        </div>
      </main>
      <Footer />
    </>
  );
}
