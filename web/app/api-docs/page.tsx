import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata = {
  title: "API — Conflict & Security Intelligence",
  description: "REST API for armed violence data. Free, open, no auth.",
};

interface Endpoint {
  method: string;
  path: string;
  description: string;
  example: string;
}

const ENDPOINTS: Endpoint[] = [
  // Aggregates
  {
    method: "GET",
    path: "/api/stats",
    description:
      "Global stats blob — threat index, totals, category breakdown, hot regions, 15 recent events.",
    example: `curl http://localhost:3000/api/stats`,
  },
  {
    method: "GET",
    path: "/api/status",
    description:
      "Source health check — per-source freshness (OK/DEGRADED/DOWN), last collected timestamp, total events.",
    example: `curl http://localhost:3000/api/status`,
  },
  // Threats (countries with threat scoring)
  {
    method: "GET",
    path: "/api/threats",
    description:
      "All countries with current 90-day threat scores. Sorted by threat_score DESC.",
    example: `curl http://localhost:3000/api/threats`,
  },
  {
    method: "GET",
    path: "/api/threats/{name}",
    description:
      "Country threat detail — score, fatalities (30d/90d), top category, last event.",
    example: `curl http://localhost:3000/api/threats/Nigeria`,
  },
  {
    method: "GET",
    path: "/api/threats/{name}/history",
    description:
      "Time series for a country (1989-present). Param: granularity=daily|monthly|yearly (default monthly).",
    example: `curl "http://localhost:3000/api/threats/Nigeria/history?granularity=yearly"`,
  },
  // Countries
  {
    method: "GET",
    path: "/api/countries",
    description: "List all countries sorted by total fatalities.",
    example: `curl http://localhost:3000/api/countries`,
  },
  {
    method: "GET",
    path: "/api/countries/{name}",
    description:
      "Country detail: stats, 38-year timeline, 50 most recent events.",
    example: `curl http://localhost:3000/api/countries/Nigeria`,
  },
  // Events
  {
    method: "GET",
    path: "/api/events",
    description:
      "Filtered event list. Params: country, category, from, to, source, q (search), limit (max 500), offset.",
    example: `curl "http://localhost:3000/api/events?country=Nigeria&category=terrorism&from=2024-01-01&limit=10"`,
  },
  {
    method: "GET",
    path: "/api/events/{id}",
    description: "Single event detail + 6 related events (same country, ±30 days).",
    example: `curl http://localhost:3000/api/events/612988`,
  },
  // Organizations
  {
    method: "GET",
    path: "/api/orgs",
    description: "List of armed organizations (top by event count). Param: limit (max 500).",
    example: `curl "http://localhost:3000/api/orgs?limit=50"`,
  },
  {
    method: "GET",
    path: "/api/orgs/{slug}",
    description:
      "Organization detail: stats, events, timeline, countries, related orgs.",
    example: `curl http://localhost:3000/api/orgs/al-shabaab`,
  },
  // Real-time / Geo
  {
    method: "GET",
    path: "/api/sparks",
    description:
      "Recent micro-updates feed (last 7 days, ordered by collection time). Param: limit (max 100).",
    example: `curl "http://localhost:3000/api/sparks?limit=20"`,
  },
  {
    method: "GET",
    path: "/api/hotspots",
    description:
      "GeoJSON FeatureCollection — top 500 events by fatalities (last 90 days).",
    example: `curl http://localhost:3000/api/hotspots`,
  },
  // Export
  {
    method: "GET",
    path: "/api/export/csv",
    description:
      "Download events as CSV (max 10,000 rows). Params: country, category, from, to.",
    example: `curl -o events.csv "http://localhost:3000/api/export/csv?country=Nigeria&from=2024-01-01"`,
  },
  {
    method: "GET",
    path: "/api/og/countries/{name}",
    description:
      "Dynamic Open Graph image (1200×630 PNG) for social sharing.",
    example: `curl http://localhost:3000/api/og/countries/Nigeria -o og.png`,
  },
];

export default function ApiDocsPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">API</h1>
        <p className="mt-3 text-text-dim">
          REST API for the Conflict & Security Intelligence database. Free, no auth, no
          rate limit (yet). JSON responses. Cache-friendly.
        </p>

        <div className="mt-6 flex gap-4 rounded-lg border border-border bg-surface p-4 text-xs">
          <div>
            <div className="font-semibold uppercase tracking-wider text-text-dim">
              Base URL
            </div>
            <code className="mt-1 block font-mono text-accent">
              https://conflict-researcher.david.dev
            </code>
          </div>
          <div>
            <div className="font-semibold uppercase tracking-wider text-text-dim">
              Format
            </div>
            <code className="mt-1 block font-mono text-text-primary">
              application/json
            </code>
          </div>
          <div>
            <div className="font-semibold uppercase tracking-wider text-text-dim">
              Auth
            </div>
            <code className="mt-1 block font-mono text-text-primary">None</code>
          </div>
        </div>

        <h2 className="mt-12 mb-4 font-display text-2xl font-bold">Endpoints</h2>
        <div className="space-y-6">
          {ENDPOINTS.map((ep) => (
            <div
              key={ep.path}
              className="rounded-lg border border-border bg-surface p-5"
            >
              <div className="flex items-center gap-3">
                <span className="rounded bg-accent px-2 py-0.5 font-mono text-[10px] font-semibold text-white">
                  {ep.method}
                </span>
                <code className="font-mono text-sm text-text-primary">
                  {ep.path}
                </code>
              </div>
              <p className="mt-2 text-sm text-text-dim">{ep.description}</p>
              <pre className="mt-3 overflow-x-auto rounded bg-background p-3 font-mono text-xs text-accent">
                {ep.example}
              </pre>
            </div>
          ))}
        </div>

        <h2 className="mt-12 mb-4 font-display text-2xl font-bold">
          Response example
        </h2>
        <pre className="overflow-x-auto rounded-lg border border-border bg-background p-5 font-mono text-xs leading-relaxed text-text-primary">
{`{
  "threatIndex": {
    "value": 73,
    "delta": 6,
    "trend7d": [42, 51, 68, 73, 71, 75, 73]
  },
  "totals": {
    "events": 419936,
    "fatalities": 4180000,
    "countries": 161
  },
  "categories": {
    "terrorism": { "events": 27895, "fatalities": 168236 },
    "civil_war":  { "events": 154189, "fatalities": 1392707 },
    "war":        { "events": 38773, "fatalities": 478756 },
    ...
  },
  "hotRegions": [...],
  "recentEvents": [...]
}`}
        </pre>

        <h2 className="mt-12 mb-4 font-display text-2xl font-bold">
          Rate limiting
        </h2>
        <p className="text-sm text-text-dim">
          None currently. Please be considerate — cache responses
          client-side. Responses already ship with{" "}
          <code className="text-accent">Cache-Control: s-maxage=3600</code> for
          Vercel/CDN caching.
        </p>

        <h2 className="mt-12 mb-4 font-display text-2xl font-bold">
          Download the full database
        </h2>
        <p className="text-sm text-text-dim">
          For research or bulk analysis, the entire 420K event SQLite
          database is available directly. See{" "}
          <a href="/data" className="text-accent hover:underline">
            Data Download
          </a>
          .
        </p>
      </main>
      <Footer />
    </>
  );
}
