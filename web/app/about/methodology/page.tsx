import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata = {
  title: "Methodology — Conflict & Security Intelligence",
  description: "Data classification rules, sources, and known limitations.",
};

export default function MethodologyPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">Methodology</h1>

        <div className="prose prose-invert prose-sm mt-8 max-w-none">
          <h2 className="mt-10 font-display">Classification Decision Tree</h2>
          <p>
            Events are classified into 10 mutually exclusive categories using
            rule-based logic (no LLM):
          </p>
          <ol>
            <li>
              <strong>Interstate military engagement</strong> → <code>war</code>
            </li>
            <li>
              <strong>Designated terror group vs civilians</strong> →{" "}
              <code>terrorism</code>
            </li>
            <li>
              <strong>State mass killing (100+ civilian deaths, 1 day)</strong> →{" "}
              <code>mass_atrocity</code>
            </li>
            <li>
              <strong>Government security forces vs civilians</strong> →{" "}
              <code>state_violence</code>
            </li>
            <li>
              <strong>Drug cartel / organized crime</strong> →{" "}
              <code>cartel_violence</code>
            </li>
            <li>
              <strong>Ethnic/sectarian communal clash</strong> →{" "}
              <code>communal_violence</code>
            </li>
            <li>
              <strong>Non-state armed group vs government</strong> →{" "}
              <code>insurgency</code>
            </li>
            <li>
              <strong>Government counterterrorism operation</strong> →{" "}
              <code>counterterrorism</code>
            </li>
            <li>
              <strong>Intrastate armed conflict (organized)</strong> →{" "}
              <code>civil_war</code>
            </li>
            <li>
              <strong>Default / unclassified</strong> →{" "}
              <code>armed_violence</code>
            </li>
          </ol>

          <h2 className="mt-10 font-display">Aggregate Filtering</h2>
          <p>
            UCDP occasionally records <em>cumulative</em> events (e.g., "Tigray war:
            121,000 fatalities in a single entry"). These are flagged with{" "}
            <code>is_aggregate=1</code> and excluded from all charts and
            statistics by default. Currently 108 events flagged.
          </p>

          <h2 className="mt-10 font-display">Country Normalization</h2>
          <p>
            Source data uses mixed country coding (UCDP uses names, GDELT uses FIPS 10-4,
            OFAC uses ISO). All are normalized to canonical names via a curated map
            (172 countries). Disputed territories (Palestinian Territories, Taiwan,
            Western Sahara) follow UCDP convention.
          </p>

          <h2 className="mt-10 font-display">Known Limitations</h2>
          <ul>
            <li>
              <strong>UCDP 2-month lag</strong> — UCDP Candidate releases
              provisional data on a 2-month delay. Recent events may be under-counted
              until UCDP processes them.
            </li>
            <li>
              <strong>GDELT no fatalities</strong> — GDELT does not provide casualty
              counts. Those events default to 0 fatalities.
            </li>
            <li>
              <strong>Media bias</strong> — Western media over-represented in GDELT;
              African/Asian events under-reported.
            </li>
            <li>
              <strong>Classification ambiguity</strong> — counterterrorism vs
              state_violence can be subjective (e.g., government claims "CT operation"
              that kills civilians). Confidence level is recorded.
            </li>
          </ul>

          <h2 className="mt-10 font-display">Data Quality Checks</h2>
          <ul>
            <li>0 ID duplicates across 420K events</li>
            <li>0 invalid date formats</li>
            <li>0 future-dated events</li>
            <li>0 coordinate out-of-range values</li>
            <li>0 negative fatalities</li>
          </ul>

          <h2 className="mt-10 font-display">Citation</h2>
          <pre className="overflow-x-auto rounded-lg border border-border bg-background p-4 text-xs">
{`Conflict & Security Intelligence (2026).
Daily Global Armed Violence Monitor.
https://github.com/lala-david/terror

Primary data:
  Pettersson et al. (2024). UCDP GED. CC BY 4.0.
  Leetaru, K. & Schrodt, P. (2013). GDELT.`}
          </pre>

          <p>
            See <Link href="/data">Data Download</Link> for the full SQLite database.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
