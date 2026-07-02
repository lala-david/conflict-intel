import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const runtime = "edge";

export const metadata = {
  title: "About — Conflict & Security Intelligence",
  description: "Open-source global armed violence monitor. 420K events, 38 years, academic standards.",
};

export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">About</h1>

        <div className="prose prose-invert prose-sm mt-8 max-w-none">
          <p className="text-lg text-text-dim">
            <strong className="text-text-primary">Conflict & Security Intelligence</strong> is an
            open-source daily intelligence pipeline that aggregates global armed violence
            data from 70+ sources (420K events, 1989–2026) and classifies them by
            academic standard.
          </p>

          <h2 className="mt-10 font-display">Why it exists</h2>
          <p>
            Enterprise conflict intelligence products (Janes, Recorded Future, Stratfor)
            cost $100K+/year. Academic databases (UCDP) lag 2+ months. News aggregators
            lack rigor. This project provides rigorously classified, up-to-date data for
            free.
          </p>

          <h2 className="mt-10 font-display">Data sources</h2>
          <ul>
            <li><strong>UCDP GED</strong> — 386K historical events (1989-2024, academic gold standard)</li>
            <li><strong>UCDP Candidate</strong> — 30K+ provisional events (2025+)</li>
            <li><strong>GDELT</strong> — real-time global event database (media-derived)</li>
            <li><strong>Wikipedia</strong> — notable terror incidents</li>
            <li><strong>43 RSS feeds</strong> — ISW, CTC Sentinel, Soufan, ICG, Jamestown, Bellingcat, HRW, ReliefWeb, and more</li>
            <li><strong>OpenSanctions</strong> — UN/US/EU sanctions tracking</li>
            <li><strong>OFAC</strong> — US Treasury designations</li>
            <li><strong>NCTC Korea</strong> — Korean government daily PDFs</li>
          </ul>

          <h2 className="mt-10 font-display">Pipeline</h2>
          <ol>
            <li>Parallel source collection (70+ sources across 9 connectors)</li>
            <li>Cross-source event linking (deduplication)</li>
            <li>Organization mapping (286 designated groups + 341 persons)</li>
            <li>Country normalization (FIPS ↔ ISO, 172 countries)</li>
            <li>Category classification (10 violence categories)</li>
            <li>Casualty extraction (regex from news text)</li>
            <li>Threat scoring (sigmoid-normalized, 0-10 per country)</li>
            <li>Hotspot detection (geographic grid clustering)</li>
            <li>Aggregate filtering (multi-year cumulative events excluded)</li>
          </ol>
          <p>
            Executes daily at 06:00 UTC via GitHub Actions. Full source code on{" "}
            <a href="https://github.com/lala-david/conflict-intel">GitHub</a>.
          </p>

          <h2 className="mt-10 font-display">License</h2>
          <p>
            Code: MIT License. Data: primary sources retain their own licenses
            (UCDP: CC BY 4.0; GDELT: public domain). See{" "}
            <Link href="/about/methodology">methodology</Link> for citation details.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
