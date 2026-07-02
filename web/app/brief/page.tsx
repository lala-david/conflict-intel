import Link from "next/link";
import fs from "fs";
import path from "path";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PageHeader } from "@/components/ui/PageHeader";
import { ArrowRight } from "lucide-react";

export const revalidate = 3600;

export const metadata = {
  title: "Daily Briefs — Conflict & Security Intelligence",
  description: "Archive of daily intelligence briefs. Auto-generated every morning.",
};

interface BriefMeta {
  date: string;
  week: string;
  month: string;
}

function listBriefs(): BriefMeta[] {
  const reportsDir = path.resolve(process.cwd(), "..", "reports");
  const results: BriefMeta[] = [];
  try {
    const years = fs.readdirSync(reportsDir).filter((y) => /^\d{4}$/.test(y));
    for (const y of years.sort().reverse()) {
      const yearDir = path.join(reportsDir, y);
      const months = fs.readdirSync(yearDir).filter((m) => /^\d{2}$/.test(m));
      for (const m of months.sort().reverse()) {
        const monthDir = path.join(yearDir, m);
        const weeks = fs.readdirSync(monthDir).filter((w) => /^week-/.test(w));
        for (const w of weeks.sort().reverse()) {
          const weekDir = path.join(monthDir, w);
          const files = fs.readdirSync(weekDir).filter((f) => /^\d{4}-\d{2}-\d{2}\.md$/.test(f));
          for (const f of files.sort().reverse()) {
            results.push({
              date: f.replace(".md", ""),
              week: w,
              month: `${y}-${m}`,
            });
          }
        }
      }
    }
  } catch {}
  return results.slice(0, 60);
}

export default function BriefArchivePage() {
  const briefs = listBriefs();

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
