import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getCategoryStats } from "@/lib/queries";
import { CATEGORY_META, formatNumber, slugify } from "@/lib/utils";
import type { Category } from "@/lib/types";
import { ArrowLeft } from "lucide-react";
import { TrackButton } from "@/components/ui/TrackButton";

export const runtime = "edge";

export const revalidate = 3600;

const CATEGORIES: Category[] = [
  "war", "civil_war", "terrorism", "mass_atrocity", "state_violence",
  "cartel_violence", "communal_violence", "insurgency", "counterterrorism", "armed_violence",
];

export async function generateStaticParams() {
  return CATEGORIES.map((c) => ({ name: slugify(c.replace("_", "-")) }));
}

interface Props {
  params: { name: string };
}

function resolveCategory(slug: string): Category | null {
  for (const c of CATEGORIES) {
    if (slugify(c.replace("_", "-")) === slug) return c;
  }
  return null;
}

export default async function CategoryDetailPage({ params }: Props) {
  const cat = resolveCategory(params.name);
  if (!cat) notFound();
  const meta = CATEGORY_META[cat];
  const data = await getCategoryStats(cat);
  if (!data) notFound();

  const maxYear = Math.max(...data.timeline.map((t) => t.count), 1);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <Link
          href="/categories"
          className="mb-6 inline-flex items-center gap-1 text-xs text-text-dim hover:text-text-primary"
        >
          <ArrowLeft className="h-3 w-3" />
          All categories
        </Link>

        <div className="mb-10 border-b border-border pb-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div
                className="h-4 w-4 rounded-full"
                style={{ background: meta.color }}
              />
              <h1 className="font-display text-5xl font-bold">{meta.label}</h1>
            </div>
            <TrackButton type="category" value={cat} />
          </div>
          <p className="mt-3 text-text-dim">{meta.description}</p>
          <div className="mt-6 flex gap-10">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
                Total events
              </div>
              <div className="mt-1 font-display text-3xl font-bold tabular-nums">
                {formatNumber(data.events)}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
                Total fatalities
              </div>
              <div className="mt-1 font-display text-3xl font-bold tabular-nums text-accent">
                {formatNumber(data.fatalities)}
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-12 md:grid-cols-2">
          <section>
            <h2 className="mb-4 font-display text-2xl font-bold">Top Countries</h2>
            <div className="rounded-lg border border-border bg-surface">
              {data.top_countries.map((c, i) => (
                <Link
                  key={c.country}
                  href={`/countries/${encodeURIComponent(c.country)}`}
                  className="group flex items-center justify-between border-b border-border px-5 py-3 text-sm transition last:border-b-0 hover:bg-surface-2"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-text-dim">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="font-medium group-hover:text-accent">{c.country}</span>
                  </div>
                  <span className="font-mono text-xs text-text-dim">
                    {formatNumber(c.count)}
                  </span>
                </Link>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-4 font-display text-2xl font-bold">Top Actors</h2>
            <div className="rounded-lg border border-border bg-surface">
              {data.top_actors.map((a, i) => (
                <div
                  key={a.name}
                  className="flex items-center justify-between border-b border-border px-5 py-3 text-sm last:border-b-0"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="font-mono text-xs text-text-dim">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="truncate font-medium">{a.name}</span>
                  </div>
                  <span className="font-mono text-xs text-text-dim">
                    {formatNumber(a.count)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">Historical Trend</h2>
          <div className="rounded-lg border border-border bg-surface p-5">
            <div className="flex h-32 items-end gap-[2px]">
              {data.timeline.map((t) => {
                const h = Math.max(2, (t.count / maxYear) * 128);
                return (
                  <div key={t.year} className="group relative flex-1" title={`${t.year}: ${t.count}`}>
                    <div
                      className="w-full rounded-t-sm transition-colors"
                      style={{
                        height: `${h}px`,
                        background: meta.color,
                        opacity: 0.7,
                      }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="mt-2 flex justify-between text-[9px] font-mono text-text-dim">
              <span>{data.timeline[0]?.year ?? ""}</span>
              <span>{data.timeline[data.timeline.length - 1]?.year ?? ""}</span>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
