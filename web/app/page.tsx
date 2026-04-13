import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ThreatIndexCard } from "@/components/home/ThreatIndex";
import { CategoryCards } from "@/components/home/CategoryCards";
import { HotRegionsList } from "@/components/home/HotRegions";
import { EventFeed } from "@/components/home/EventFeed";
import { OnThisDay } from "@/components/home/OnThisDay";
import { TodayAnalysis } from "@/components/home/TodayAnalysis";
import { WorldMapSection } from "@/components/map/WorldMapSection";
import { DataFreshness } from "@/components/home/DataFreshness";
import { getHomeData, getOnThisDay, getTodayAnalysis, getYearlyTimeline } from "@/lib/queries";
import { HistoricalComparison } from "@/components/home/HistoricalComparison";
import { TimelineScrubber } from "@/components/home/TimelineScrubber";
import Link from "next/link";

export const revalidate = 3600;

export default async function HomePage() {
  const data = await getHomeData();
  const onThisDay = await getOnThisDay();
  const analysis = await getTodayAnalysis(6);
  const yearlyTimeline = await getYearlyTimeline();

  return (
    <>
      <Header />
      <main>
        {/* Hero: Threat Index + Key Stats */}
        <ThreatIndexCard data={data.threatIndex} totals={data.totals} />

        {/* Global Map */}
        <WorldMapSection />

        {/* 37-Year Timeline */}
        <section className="mx-auto max-w-7xl px-6 py-8">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="font-display text-2xl font-bold">37 Years of Conflict</h2>
            <span className="text-sm text-text-dim">1989 – {new Date().getFullYear()}</span>
          </div>
          <div className="rounded-lg border border-border bg-surface p-5">
            <TimelineScrubber data={yearlyTimeline} />
          </div>
        </section>

        {/* Categories Grid */}
        <CategoryCards categories={data.categories} />

        {/* Two-column: Hot Regions + Expert Analysis */}
        <div className="mx-auto max-w-7xl px-6 py-12">
          <div className="grid gap-8 lg:grid-cols-2">
            <HotRegionsList regions={data.hotRegions} />
            <TodayAnalysis articles={analysis} />
          </div>
        </div>

        {/* Recent Events Feed */}
        <EventFeed events={data.recentEvents} />

        {/* Historical Comparison */}
        <HistoricalComparison />

        {/* On This Day */}
        <OnThisDay event={onThisDay} />

        {/* Subscribe CTA */}
        <section className="mx-auto max-w-7xl px-6 py-16">
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <h3 className="font-display text-2xl font-bold">
              Daily Brief — Free
            </h3>
            <p className="mt-2 text-sm text-text-dim">
              Get the daily conflict brief on{" "}
              <a
                href="https://t.me/ThreatPulse"
                className="text-accent hover:underline"
              >
                @ThreatPulse
              </a>{" "}
              Telegram. Auto-published every morning.
            </p>
            <div className="mt-6 flex items-center justify-center gap-4">
              <a
                href="https://t.me/ThreatPulse"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-white hover:bg-accent/90"
              >
                Subscribe on Telegram
              </a>
              <Link
                href="/brief"
                className="rounded-md border border-border px-5 py-2.5 text-sm font-medium text-text-primary hover:bg-surface-2"
              >
                Browse archive
              </Link>
            </div>
          </div>
        </section>

        {/* Data Freshness */}
        <DataFreshness />
      </main>
      <Footer />
    </>
  );
}
