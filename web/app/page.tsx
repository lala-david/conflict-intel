import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { HeroStats } from "@/components/home/HeroStats";
import { CategoryCards } from "@/components/home/CategoryCards";
import { HotRegionsList } from "@/components/home/HotRegions";
import { EventFeed } from "@/components/home/EventFeed";
import { WorldMapSection } from "@/components/map/WorldMapSection";
import { getHomeData } from "@/lib/queries";
import Link from "next/link";
import { Suspense } from "react";

function MapSkeleton() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-4 h-8 w-56 animate-pulse rounded bg-surface-2" />
      <div className="flex h-[460px] animate-pulse items-center justify-center rounded-xl border border-border bg-surface text-sm text-text-dim">
        Loading map…
      </div>
    </section>
  );
}

export const dynamic = "force-dynamic";


export default async function HomePage() {
  const data = await getHomeData();

  return (
    <>
      <Header />
      <main>
        {/* Hero */}
        <HeroStats totals={data.totals} />

        {/* Global Map — streamed so the rest of the page isn't blocked on its query */}
        <Suspense fallback={<MapSkeleton />}>
          <WorldMapSection />
        </Suspense>

        {/* Categories */}
        <CategoryCards categories={data.categories} />

        {/* Deadliest regions */}
        <div className="mx-auto max-w-7xl px-6 py-12">
          <HotRegionsList regions={data.hotRegions} />
        </div>

        {/* Recent Events */}
        <EventFeed events={data.recentEvents.slice(0, 6)} />

        {/* Subscribe CTA */}
        <section className="mx-auto max-w-7xl px-6 py-16">
          <div className="rounded-xl border border-border bg-surface p-10 text-center">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
              Your watchlist
            </div>
            <h3 className="mt-2 font-display text-3xl font-semibold tracking-tight md:text-4xl">
              Track what matters to you.
            </h3>
            <p className="mx-auto mt-3 max-w-lg text-sm text-text-dim">
              Follow the countries and topics you cover and get one live feed of
              everything new — no account required. Or get the daily brief on{" "}
              <a
                href="https://t.me/ThreatPulse"
                className="text-accent hover:underline"
              >
                @ThreatPulse
              </a>
              .
            </p>
            <div className="mt-6 flex items-center justify-center gap-4">
              <Link
                href="/tracking"
                className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent/90"
              >
                Start tracking →
              </Link>
              <Link
                href="/brief"
                className="rounded-md border border-border px-5 py-2.5 text-sm font-medium text-text-primary hover:bg-surface-2"
              >
                Daily brief
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
