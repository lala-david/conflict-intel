import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Download, Github, Database } from "lucide-react";

export const metadata = {
  title: "Data Download — Conflict & Security Intelligence",
  description: "Download the full 420K event database or query via API.",
};

export default function DataPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">Data</h1>
        <p className="mt-3 text-text-dim">
          The full database is open. Use it however you want, attribution
          appreciated.
        </p>

        <section className="mt-10">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Full database (SQLite)
          </h2>
          <a
            href="https://github.com/lala-david/conflict-intel/releases/download/db-latest/conflict.db"
            className="flex items-center gap-4 rounded-lg border border-border bg-surface p-5 transition hover:bg-surface-2"
          >
            <Database className="h-8 w-8 text-accent" />
            <div className="flex-1">
              <div className="font-semibold">conflict.db</div>
              <div className="text-xs text-text-dim">
                SQLite · 420K events · ~330 MB · refreshed daily · 1989–present
              </div>
            </div>
            <Download className="h-5 w-5 text-text-dim" />
          </a>
          <p className="mt-3 text-xs text-text-dim">
            Schema: see{" "}
            <a
              href="/about/methodology"
              className="text-accent hover:underline"
            >
              methodology
            </a>
            . Includes category, is_aggregate, fatality breakdowns, coordinates.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            CSV Export
          </h2>
          <p className="mb-3 text-sm text-text-dim">
            Download filtered event data as CSV. Max 10,000 rows per export.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <a
              href="/api/export/csv"
              className="flex items-center gap-3 rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-2"
            >
              <Download className="h-5 w-5 text-accent" />
              <div>
                <div className="font-semibold text-sm">All events (recent)</div>
                <div className="text-xs text-text-dim">Latest 10,000 events as CSV</div>
              </div>
            </a>
            <a
              href="/api/export/csv?category=terrorism"
              className="flex items-center gap-3 rounded-lg border border-border bg-surface p-4 transition hover:bg-surface-2"
            >
              <Download className="h-5 w-5 text-cat-terrorism" />
              <div>
                <div className="font-semibold text-sm">Terrorism events</div>
                <div className="text-xs text-text-dim">Filtered by terrorism category</div>
              </div>
            </a>
          </div>
          <p className="mt-3 text-xs text-text-dim">
            Custom filters: <code className="text-accent">/api/export/csv?country=Nigeria&amp;from=2024-01-01&amp;to=2024-12-31</code>
          </p>
        </section>

        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            Source code
          </h2>
          <a
            href="https://github.com/lala-david/conflict-intel"
            target="_blank"
            rel="noopener"
            className="flex items-center gap-4 rounded-lg border border-border bg-surface p-5 transition hover:bg-surface-2"
          >
            <Github className="h-8 w-8 text-text-primary" />
            <div className="flex-1">
              <div className="font-semibold">lala-david/conflict-intel</div>
              <div className="text-xs text-text-dim">
                MIT licensed · Python pipeline + Next.js dashboard
              </div>
            </div>
          </a>
        </section>

        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">
            API
          </h2>
          <p className="text-sm text-text-dim">
            For programmatic access without downloading the full DB, see the{" "}
            <a href="/api-docs" className="text-accent hover:underline">
              API documentation
            </a>
            .
          </p>
        </section>

        <section className="mt-12">
          <h2 className="mb-4 font-display text-2xl font-bold">Citation</h2>
          <pre className="overflow-x-auto rounded-lg border border-border bg-surface p-5 font-mono text-xs">
{`Conflict & Security Intelligence (2026).
Daily Global Armed Violence Monitor.
https://github.com/lala-david/conflict-intel

Primary data:
  Pettersson et al. (2024). UCDP GED. CC BY 4.0.
  Leetaru, K. & Schrodt, P. (2013). GDELT.`}
          </pre>
        </section>
      </main>
      <Footer />
    </>
  );
}
