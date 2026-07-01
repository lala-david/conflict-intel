import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { queryAll } from "@/lib/db";
import { CATEGORY_META, formatNumber, slugify } from "@/lib/utils";
import type { Category } from "@/lib/types";

export const revalidate = 3600;

export const metadata = {
  title: "Categories — Conflict & Security Intelligence",
  description: "10 violence categories: war, civil war, terrorism, insurgency, cartel violence, and more.",
};

export default async function CategoriesPage() {
  const rows = (await queryAll<{ category: Category; events: number; fatalities: number }>(
    `SELECT category, total_events as events, total_fatalities as fatalities FROM category_stats`
  ));

  const sorted = rows.sort((a, b) => b.events - a.events);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">Categories</h1>
        <p className="mt-2 text-text-dim">
          Events classified by academic-standard taxonomy
        </p>

        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sorted.map((r) => {
            const meta = CATEGORY_META[r.category];
            if (!meta) return null;
            return (
              <Link
                key={r.category}
                href={`/categories/${slugify(r.category.replace("_", "-"))}`}
                className="group block rounded-lg border border-border bg-surface p-5 transition hover:border-text-dim hover:bg-surface-2"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ background: meta.color }}
                  />
                  <div className="font-display text-lg font-bold text-text-primary group-hover:text-accent">
                    {meta.label}
                  </div>
                </div>
                <p className="mt-3 text-sm text-text-dim">{meta.description}</p>
                <div className="mt-4 flex items-baseline gap-4 font-mono text-xs text-text-dim">
                  <span>
                    <span className="text-xl font-bold tabular-nums text-text-primary">
                      {formatNumber(r.events)}
                    </span>{" "}
                    events
                  </span>
                  <span>
                    <span className="text-xl font-bold tabular-nums text-text-primary">
                      {formatNumber(r.fatalities)}
                    </span>{" "}
                    killed
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </main>
      <Footer />
    </>
  );
}
