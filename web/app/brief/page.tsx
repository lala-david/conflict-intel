import Link from "next/link";
import fs from "fs";
import path from "path";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { FileText } from "lucide-react";

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
        <h1 className="font-display text-5xl font-bold">Daily Briefs</h1>
        <p className="mt-2 text-text-dim">
          Auto-generated intelligence briefs. Published daily at 06:00 UTC.
        </p>

        {briefs.length === 0 ? (
          <div className="mt-10 rounded-lg border border-border bg-surface p-8 text-center text-sm text-text-dim">
            No briefs available yet.
          </div>
        ) : (
          <div className="mt-10 rounded-lg border border-border bg-surface">
            {briefs.map((b) => (
              <Link
                key={b.date}
                href={`/brief/${b.date}`}
                className="group flex items-center justify-between border-b border-border px-5 py-4 transition last:border-b-0 hover:bg-surface-2"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-text-dim" />
                  <div>
                    <div className="font-medium text-text-primary group-hover:text-accent">
                      {b.date}
                    </div>
                    <div className="font-mono text-xs text-text-dim">{b.week}</div>
                  </div>
                </div>
                <span className="text-xs text-text-dim">Read →</span>
              </Link>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
