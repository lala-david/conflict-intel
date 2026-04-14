import Link from "next/link";
import type { Category } from "@/lib/types";
import { CATEGORY_META, formatNumber, slugify } from "@/lib/utils";

interface Props {
  categories: Record<Category, { events: number; fatalities: number }>;
}

export function CategoryCards({ categories }: Props) {
  const entries = (
    Object.entries(categories) as [
      Category,
      { events: number; fatalities: number }
    ][]
  ).sort((a, b) => b[1].events - a[1].events);

  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-6 flex items-baseline justify-between">
        <h2 className="font-display text-2xl font-bold">Categories</h2>
        <Link
          href="/categories"
          className="text-sm text-text-dim hover:text-text-primary"
        >
          View all →
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {entries.map(([cat, stats]) => {
          const meta = CATEGORY_META[cat];
          return (
            <Link
              key={cat}
              href={`/categories/${slugify(cat.replace("_", "-"))}`}
              className="group block rounded-lg border border-border bg-surface p-4 transition hover:border-text-dim hover:bg-surface-2"
            >
              <div
                className="h-1 w-8 rounded-full"
                style={{ background: meta.color }}
              />
              <div className="mt-3 text-sm font-medium text-text-primary">
                {meta.label}
              </div>
              <div className="mt-1 font-mono text-xs text-text-dim">
                {formatNumber(stats.events)} events
              </div>
              <div className="mt-0.5 font-mono text-xs text-text-dim">
                {formatNumber(stats.fatalities)} killed
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
