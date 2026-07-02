import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PageHeader } from "@/components/ui/PageHeader";
import { ArrowRight } from "lucide-react";
import { listBriefs } from "@/lib/briefs";

export const revalidate = 3600;

export const metadata = {
  title: "Daily Briefs — Conflict & Security Intelligence",
  description: "Archive of daily intelligence briefs. Auto-generated every morning.",
};

export default async function BriefArchivePage() {
  const briefs = await listBriefs(60);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <PageHeader
          kicker="Published every morning · 06:00 UTC"
          title="The Daily Brief"
          standfirst="A structured intelligence read of the day's organized violence — threat assessment, conflict events, and cross-source news clusters. Auto-generated, human-readable."
        />

        {briefs.length === 0 ? (
          <div className="mt-10 rounded-lg border border-border bg-surface p-8 text-center text-sm text-text-dim">
            No briefs available yet.
          </div>
        ) : (
          <div className="mt-10 divide-y divide-border border-y border-border">
            {briefs.map((b) => (
              <Link
                key={b.date}
                href={`/brief/${b.date}`}
                className="group flex items-center justify-between gap-4 py-5 transition"
              >
                <div className="flex items-baseline gap-4">
                  <span className="font-display text-2xl font-semibold tabular-nums text-text-primary transition group-hover:text-accent">
                    {b.date}
                  </span>
                  <span className="font-mono text-[11px] uppercase tracking-wider text-text-dim">
                    {b.week}
                  </span>
                </div>
                <span className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-text-dim transition group-hover:text-accent">
                  Read
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
