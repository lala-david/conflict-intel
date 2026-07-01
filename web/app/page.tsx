import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { HeroStats } from "@/components/home/HeroStats";
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
import { SectionHeading } from "@/components/ui/SectionHeading";
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
        {/* Hero */}
        <HeroStats totals={data.totals} />

        {/* Global Map */}
        <WorldMapSection />

        {/* 38-Year Timeline */}
        <section className="mx-auto max-w-7xl px-6 py-8">
          <SectionHeading
            kicker="1989 — today"
            title="Nearly four decades of conflict"
            action={<span>{new Date().getFullYear() - 1989 + 1} years</span>}
          />
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
          <div className="rounded-xl border border-border bg-surface p-10 text-center">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
              Every morning
            </div>
            <h3 className="mt-2 font-display text-3xl font-semibold tracking-tight md:text-4xl">
              The Daily Brief, free.
            </h3>
            <p className="mt-3 text-sm text-text-dim">
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
