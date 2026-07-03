import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PageHeader } from "@/components/ui/PageHeader";
import { WalletTable } from "@/components/wallets/WalletTable";
import { getCryptoStats, getCryptoWallets } from "@/lib/queries";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Terror Financing — Sanctioned Crypto Wallets",
  description:
    "Publicly designated cryptocurrency wallet addresses linked to terrorist organizations and sanctioned threat actors — from OFAC/EU/UN, GraphSense and Ransomwhere — mapped to the groups we track.",
};

const CAT_COLOR: Record<string, string> = {
  terror: "#ef4444", sanction: "#f59e0b", extremism: "#fb7185",
  ransomware: "#f97316", hack: "#a855f7", scam: "#eab308", mixer: "#22d3ee",
};

export default async function WalletsPage({
  searchParams,
}: {
  searchParams: { cat?: string };
}) {
  const cat = searchParams?.cat;
  const [stats, wallets] = await Promise.all([
    getCryptoStats(),
    cat && cat !== "terror"
      ? getCryptoWallets({ category: cat, limit: 2000 })
      : getCryptoWallets({ terrorOnly: true, limit: 2000 }),
  ]);
  const active = cat ?? "terror";

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-12">
        <PageHeader
          kicker="Threat finance · on-chain intelligence"
          title="Terror-linked crypto wallets"
          standfirst="Cryptocurrency addresses publicly attributed to terrorist organizations and sanctioned threat actors — aggregated from OFAC/EU/UN sanctions, GraphSense forfeiture data and the Ransomwhere database, deduplicated and mapped to the groups we track."
        />

        {/* Stat strip */}
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Threat-finance wallets", value: stats.total, accent: false },
            { label: "Terror-linked", value: stats.terror, accent: true },
            { label: "Blockchains", value: stats.chains, accent: false },
            { label: "Groups mapped", value: stats.byOrg.length, accent: false },
          ].map((s) => (
            <div key={s.label} className="rounded-xl border border-border bg-surface p-4">
              <div
                className={`font-display text-3xl font-bold tabular-nums ${s.accent ? "text-accent" : "text-text-primary"}`}
              >
                {s.value.toLocaleString()}
              </div>
              <div className="mt-1 text-xs uppercase tracking-wider text-text-dim">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Groups */}
        {stats.byOrg.length > 0 && (
          <>
            <h2 className="mt-12 mb-4 font-display text-2xl font-bold">Designated groups</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {stats.byOrg.map((o) => (
                <div key={o.org} className="rounded-xl border border-border bg-surface p-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-accent" />
                    <span className="font-display text-lg font-semibold text-text-primary">{o.org}</span>
                  </div>
                  <div className="mt-2 font-mono text-sm text-text-dim">
                    <span className="text-accent">{o.n}</span> wallets · {o.chains} chain{o.chains > 1 ? "s" : ""}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Category filter */}
        <div className="mt-12 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-xs uppercase tracking-wider text-text-dim">Class:</span>
          <Link
            href="/wallets"
            className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
              active === "terror"
                ? "border-accent bg-accent/15 text-accent"
                : "border-border text-text-dim hover:text-text-primary"
            }`}
          >
            Terror ({stats.terror})
          </Link>
          {stats.byCategory
            .filter((c) => c.category !== "terror")
            .map((c) => (
              <Link
                key={c.category}
                href={`/wallets?cat=${c.category}`}
                className={`rounded-full border px-3 py-1 text-xs font-semibold capitalize transition ${
                  active === c.category
                    ? "border-current"
                    : "border-border text-text-dim hover:text-text-primary"
                }`}
                style={active === c.category ? { color: CAT_COLOR[c.category] ?? "#94a3b8" } : undefined}
              >
                {c.category} ({c.n})
              </Link>
            ))}
        </div>

        <div className="mt-5">
          <WalletTable wallets={wallets} />
        </div>

        <p className="mt-6 text-xs leading-relaxed text-text-dim">
          Sources: OpenSanctions (OFAC SDN, EU, UN), GraphSense TagPacks (authority/forfeiture data,
          e.g. DOJ al-Qaeda seizures), and Ransomwhere. These are publicly designated or reported
          addresses for sanctions screening and threat-finance analysis. Inclusion reflects the
          issuing authority&apos;s designation, not our assessment. Verify against the primary source
          before acting. Wallet addresses dedupe exactly; the terror subset is flagged and mapped to
          a canonical organization.
        </p>
      </main>
      <Footer />
    </>
  );
}
