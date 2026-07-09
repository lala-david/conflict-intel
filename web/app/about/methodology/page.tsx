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

const CATEGORIES = [
  "war",
  "civil_war",
  "terrorism",
  "mass_atrocity",
  "state_violence",
  "cartel_violence",
  "communal_violence",
  "insurgency",
  "counterterrorism",
  "armed_violence",
];

const CONFIDENCE: [string, string][] = [
  ["high", "The category is stated or unambiguous in the source (e.g. a UCDP dyad type, a GTD terrorism coding, or explicit language like “suicide bombing” / “cartel gunmen”)."],
  ["medium", "The signal is present but partial — the actor or motive is inferred from context rather than named outright."],
  ["low", "The category is a best guess from thin or conflicting text; the label should be treated as provisional."],
];

const GRADES: [string, string][] = [
  ["Verified", "A casualty-verified academic source (UCDP) or 3+ independent sources corroborate the incident."],
  ["Corroborated", "2+ independent sources report the incident."],
  ["Reported", "A single credible source — news, Wikipedia, or a government designation."],
  ["Machine-coded", "A single machine-coded media source (GDELT). Treat as a lead, not a confirmed fact."],
];

const SOURCE_TIERS: [string, string][] = [
  ["UCDP", "casualty-verified"],
  ["GTD", "academic"],
  ["GDELT", "media-coded"],
  ["News/RSS", "media"],
  ["Wikipedia", "reference"],
  ["OFAC/NCTC", "government"],
  ["Telegram", "OSINT"],
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

        <h2 className="mt-12 mb-3 font-display text-xl font-bold">How events are classified</h2>
        <p className="text-sm leading-relaxed text-text-dim">
          Every event is assigned one of ten violence categories by a combination of an{" "}
          <span className="text-text-primary">LLM and deterministic rules</span> run over the
          source text and metadata (actor names, dyad codes, incident language). The ten
          categories are:
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <span
              key={c}
              className="rounded border border-border bg-surface px-2.5 py-1 font-mono text-xs text-text-primary"
            >
              {c}
            </span>
          ))}
        </div>
        <p className="mt-4 text-sm leading-relaxed text-text-dim">
          Classification is <span className="text-text-primary">best-effort, not
          adjudicated</span>. Labels are derived automatically from how each source describes
          an incident; they are not reviewed by a panel of coders.{" "}
          <span className="text-text-primary">There is no formal inter-rater validation
          yet</span>, so treat categories — especially on machine-coded events — as a
          filtering aid rather than a settled determination.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-text-dim">
          Each label carries a <span className="font-mono text-text-primary">category_confidence</span>{" "}
          value reflecting how clear the classifying signal was in the source:
        </p>
        <div className="mt-3 divide-y divide-border rounded-lg border border-border bg-surface">
          {CONFIDENCE.map(([level, desc]) => (
            <div key={level} className="flex flex-col gap-0.5 px-5 py-3.5 sm:flex-row sm:gap-4">
              <div className="w-24 shrink-0 font-mono font-semibold text-text-primary">{level}</div>
              <div className="text-sm text-text-dim">{desc}</div>
            </div>
          ))}
        </div>

        <h2 className="mt-12 mb-3 font-display text-xl font-bold">Inclusion &amp; thresholds</h2>
        <p className="text-sm leading-relaxed text-text-dim">
          There is no single inclusion rule across the dataset — each source decides for itself
          what counts as an event, and the fused record inherits all of those rules at once:
        </p>
        <ul className="mt-3 space-y-2.5 text-sm leading-relaxed text-text-dim">
          <li>
            <span className="text-text-primary">UCDP GED</span> — codes organized violence
            above a <span className="text-text-primary">25-deaths-per-dyad-per-year</span>{" "}
            threshold; below that, an actor pairing simply does not appear.
          </li>
          <li>
            <span className="text-text-primary">GTD</span> — codes discrete terrorism
            incidents by its own definitional criteria, independent of any casualty floor.
          </li>
          <li>
            <span className="text-text-primary">GDELT</span> — machine-coded media events with{" "}
            <span className="text-text-primary">no casualty verification</span>; many entries
            carry 0 fatalities and exist only because an article was published.
          </li>
        </ul>
        <p className="mt-4 text-sm leading-relaxed text-text-dim">
          <span className="text-text-primary">Honest caveat</span> — the fused dataset inherits
          each source&apos;s biases. GDELT over-represents Western media coverage; UCDP lags
          roughly two months behind real time. Because sources overlap, aggregate totals may{" "}
          <span className="text-text-primary">double-count</span> incidents wherever
          deduplication missed a match. Read totals as an order-of-magnitude signal, not an
          exact body count.
        </p>

        <h2 className="mt-12 mb-3 font-display text-xl font-bold">Data grades — how to read reliability</h2>
        <p className="text-sm leading-relaxed text-text-dim">
          A companion feature surfaces a <span className="text-text-primary">reliability
          grade</span> on events, based on how many independent sources back the incident and
          how each was produced:
        </p>
        <div className="mt-3 divide-y divide-border rounded-lg border border-border bg-surface">
          {GRADES.map(([grade, desc]) => (
            <div key={grade} className="flex flex-col gap-0.5 px-5 py-3.5 sm:flex-row sm:gap-4">
              <div className="w-36 shrink-0 font-semibold text-text-primary">{grade}</div>
              <div className="text-sm text-text-dim">{desc}</div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm leading-relaxed text-text-dim">
          Grades draw on the underlying source tiers:
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {SOURCE_TIERS.map(([name, tier]) => (
            <span
              key={name}
              className="rounded border border-border bg-surface px-2.5 py-1 text-xs text-text-dim"
            >
              <span className="font-semibold text-text-primary">{name}</span>{" "}
              <span className="text-text-dim">({tier})</span>
            </span>
          ))}
        </div>
        <p className="mt-4 text-sm leading-relaxed text-text-dim">
          <span className="text-text-primary">Honest caveat</span> — these grades reflect{" "}
          <em>sourcing</em>, not independent forensic verification. A &quot;Verified&quot;
          grade means the sourcing bar was met, not that we re-confirmed the facts on the
          ground. The site is a triage layer; verify before citing.
        </p>

        <h2 className="mt-12 mb-3 font-display text-xl font-bold">How the threat index works</h2>
        <p className="text-sm leading-relaxed text-text-dim">
          The <span className="text-text-primary">threat index</span> — one global 0-100
          number, plus a per-country score — is a fast triage signal, not a forecast. It is
          built only from events already in this database, blending three inputs:
        </p>
        <ul className="mt-3 space-y-2.5 text-sm leading-relaxed text-text-dim">
          <li>
            <span className="text-text-primary">Fatality load</span> — recent deaths weighted
            by recency (the last 7 days count most, then the rest of the month, then the
            8-90 day tail), then log-compressed so casualties have diminishing marginal impact.
          </li>
          <li>
            <span className="text-text-primary">Tempo</span> — how frequently events are
            occurring, so sustained low-lethality violence still registers.
          </li>
          <li>
            <span className="text-text-primary">Acceleration</span> — the share of the
            quarter&apos;s deaths that fell in the last 30 days, which rewards conflicts that are
            escalating rather than winding down.
          </li>
        </ul>
        <div className="mt-4 flex flex-col gap-2 rounded-lg border border-border bg-surface px-5 py-4 text-sm sm:flex-row sm:gap-6">
          <div><span className="font-semibold text-text-primary">0-33</span> <span className="text-text-dim">Low</span></div>
          <div><span className="font-semibold text-text-primary">34-66</span> <span className="text-text-dim">Elevated</span></div>
          <div><span className="font-semibold text-text-primary">67-100</span> <span className="text-text-dim">Severe</span></div>
        </div>
        <p className="mt-4 text-sm leading-relaxed text-text-dim">
          <span className="text-text-primary">Honest caveat</span> — the score is driven by
          fatality <em>volume</em> and event tempo, <span className="text-text-primary">not</span>{" "}
          per-capita rates (there is no population data behind it). So a large active-war
          country will outscore a small country with intense but localized violence. Read it
          as &quot;how much organized violence is happening here right now,&quot; not as a
          normalized per-person risk. Values are tuned so typical active conflicts spread
          across roughly 40-95; 100 is reserved for catastrophic, escalating situations.
        </p>

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
