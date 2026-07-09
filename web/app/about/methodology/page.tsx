import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata = {
  title: "Methodology — Conflict & Security Intelligence",
  description:
    "How we fuse UCDP, GDELT, sanctions and news into one live, categorized record of global organized violence.",
};

const SOURCES: [string, string][] = [
  ["GTD (START, Univ. of Maryland)", "Global Terrorism Database — 170K terrorism events, 1970–2016 (historical backfill). Redistribution per START's terms."],
  ["UCDP GED", "Georeferenced, casualty-verified organized-violence events, 1989–present."],
  ["GDELT", "Machine-coded global event stream for real-time coverage."],
  ["OpenSanctions · OFAC/EU/UN", "Sanctioned entities and designated crypto wallets."],
  ["DOJ · NBCTF", "Terror-financing forfeitures and Israeli seizure orders."],
  ["News · Telegram", "Curated OSINT feeds for the latest incidents."],
];

export default function MethodologyPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-14">
        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
          How it works
        </div>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-tight">Methodology</h1>
        <p className="mt-4 leading-relaxed text-text-dim">
          We fuse several open datasets into one live, deduplicated, categorized record of
          global organized violence — cross-checked across sources, geocoded, and refreshed
          daily.
        </p>

        <h2 className="mt-12 mb-4 font-display text-xl font-bold">Sources</h2>
        <div className="divide-y divide-border rounded-lg border border-border bg-surface">
          {SOURCES.map(([name, desc]) => (
            <div key={name} className="flex flex-col gap-0.5 px-5 py-3.5 sm:flex-row sm:gap-4">
              <div className="w-60 shrink-0 font-semibold text-text-primary">{name}</div>
              <div className="text-sm text-text-dim">{desc}</div>
            </div>
          ))}
        </div>

        <h2 className="mt-12 mb-3 font-display text-xl font-bold">The essentials</h2>
        <ul className="space-y-2.5 text-sm leading-relaxed text-text-dim">
          <li>
            <span className="text-text-primary">Categorized</span> — every event is typed
            (war, civil war, terrorism, cartel violence, …) for filtering.
          </li>
          <li>
            <span className="text-text-primary">Deduplicated</span> — the same incident from
            multiple sources is collapsed; cumulative rollups are excluded from stats.
          </li>
          <li>
            <span className="text-text-primary">Caveats</span> — UCDP lags ~2 months; GDELT
            carries no casualty counts (defaults to 0) and over-represents Western media.
            Treat as a triage layer; verify before citing.
          </li>
        </ul>

        <p className="mt-12 text-xs leading-relaxed text-text-dim">
          Open source and open data —{" "}
          <a href="/data" className="text-accent hover:underline">download the full database</a>{" "}
          or see the{" "}
          <a
            href="https://github.com/lala-david/conflict-intel"
            className="text-accent hover:underline"
          >
            code on GitHub
          </a>
          . Primary data: UCDP GED (Pettersson et al., CC BY 4.0) · GDELT (Leetaru &amp; Schrodt).
        </p>
      </main>
      <Footer />
    </>
  );
}
