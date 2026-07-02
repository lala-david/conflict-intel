import Link from "next/link";
import type { Category } from "@/lib/types";
import { CATEGORY_META, formatNumber, slugify } from "@/lib/utils";
import { SectionHeading } from "@/components/ui/SectionHeading";

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
      <SectionHeading
        kicker="By type"
        title="Categories of violence"
        action={
          <Link href="/categories" className="hover:text-text-primary">
            View all →
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-5">
        {entries.map(([cat, stats]) => {
          const meta = CATEGORY_META[cat];
          if (!meta) return null;
          return (
            <Link
              key={cat}
              href={`/categories/${slugify(cat.replace("_", "-"))}`}
              className="group block bg-surface p-4 transition hover:bg-surface-2"
            >
              <div
                className="h-1 w-8 rounded-full"
                style={{ background: meta.color }}
              />
              <div className="mt-3 text-sm font-medium text-text-primary group-hover:text-accent">
                {meta.label}
              </div>
              <div className="mt-2 font-display text-2xl font-semibold tabular-nums leading-none text-text-primary">
                {formatNumber(stats.events)}
              </div>
              <div className="mt-1 font-mono text-[11px] uppercase tracking-wider text-text-dim">
                events · {formatNumber(stats.fatalities)} killed
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
