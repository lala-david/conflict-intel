import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PageHeader } from "@/components/ui/PageHeader";
import { TrackingDashboard } from "@/components/tracking/TrackingDashboard";

export const runtime = "edge";

export const metadata = {
  title: "Tracking — Conflict & Security Intelligence",
  description: "Track the countries and categories you follow. Your personal conflict watchlist.",
};

export default function TrackingPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <PageHeader
          kicker="Your watchlist"
          title="Tracking"
          standfirst="Follow the countries and categories that matter to you, and see everything new across them in one feed — updated daily."
        />
        <TrackingDashboard />
      </main>
      <Footer />
    </>
  );
}
