import { getDb } from "@/lib/db";

export function DataFreshness() {
  const db = getDb();

  const sources = db
    .prepare(
      `SELECT source, MAX(date) as latest, COUNT(*) as count
       FROM events WHERE is_aggregate = 0
       GROUP BY source
       ORDER BY MAX(date) DESC`
    )
    .all() as { source: string; latest: string; count: number }[];

  const updated = db
    .prepare(`SELECT updated_at FROM global_stats WHERE id = 1`)
    .get() as { updated_at: string } | null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-8">
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-text-dim">
          Data Freshness
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-5">
          {sources.slice(0, 10).map((s) => (
            <div key={s.source} className="text-xs">
              <div className="font-medium text-text-primary">{s.source}</div>
              <div className="font-mono text-text-dim">
                {s.latest?.slice(0, 10) || "N/A"} · {s.count.toLocaleString()}
              </div>
            </div>
          ))}
        </div>
        {updated && (
          <div className="mt-3 text-[10px] text-text-dim">
            Stats last computed: {updated.updated_at?.slice(0, 19)}
          </div>
        )}
      </div>
    </section>
  );
}
