import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PageHeader } from "@/components/ui/PageHeader";
import { getCryptoStats, getCryptoWallets } from "@/lib/queries";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Terror Financing — Sanctioned Crypto Wallets",
  description:
    "Publicly designated cryptocurrency wallet addresses linked to sanctioned terrorist organizations, sourced from OFAC / EU / UN sanctions lists and mapped to the groups we track.",
};

const CHAIN_LABEL: Record<string, string> = {
  XBT: "Bitcoin", BTC: "Bitcoin", ETH: "Ethereum", TRX: "Tron", USDT: "Tether",
  USDC: "USDC", XMR: "Monero", LTC: "Litecoin", BCH: "Bitcoin Cash", DASH: "Dash",
  ZEC: "Zcash", ARB: "Arbitrum", BTG: "Bitcoin Gold",
};

export default async function WalletsPage() {
  const [stats, wallets] = await Promise.all([
    getCryptoStats(),
    getCryptoWallets({ terrorOnly: true, limit: 1000 }),
  ]);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-12">
        <PageHeader
          kicker="Threat finance · sanctions intelligence"
          title="Terror-linked crypto wallets"
          standfirst="Cryptocurrency addresses publicly designated by OFAC, the EU and the UN as belonging to sanctioned terrorist organizations — mapped to the groups we track. Defensive intelligence for sanctions screening and financial-crime analysis."
        />

        {/* Stat strip */}
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Sanctioned wallets", value: stats.total.toLocaleString() },
            { label: "Terror-linked", value: stats.terror.toLocaleString() },
            { label: "Blockchains", value: stats.chains.toLocaleString() },
            { label: "Groups", value: stats.byOrg.length.toLocaleString() },
          ].map((s) => (
            <div key={s.label} className="rounded-lg border border-border bg-surface p-4">
              <div className="font-display text-3xl font-bold tabular-nums text-text-primary">
                {s.value}
              </div>
              <div className="mt-1 text-xs uppercase tracking-wider text-text-dim">{s.label}</div>
            </div>
          ))}
        </div>

        {/* By organization */}
        <h2 className="mt-12 mb-4 font-display text-2xl font-bold">By organization</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {stats.byOrg.map((o) => (
            <div
              key={o.org}
              className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3"
            >
              <span className="font-medium text-text-primary">{o.org}</span>
              <span className="font-mono text-sm text-accent">
                {o.n} wallet{o.n > 1 ? "s" : ""} · {o.chains} chain{o.chains > 1 ? "s" : ""}
              </span>
            </div>
          ))}
        </div>

        {/* Wallet table */}
        <h2 className="mt-12 mb-4 font-display text-2xl font-bold">
          Designated addresses <span className="text-text-dim">({wallets.length})</span>
        </h2>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-2 text-xs uppercase tracking-wider text-text-dim">
              <tr>
                <th className="px-4 py-3">Chain</th>
                <th className="px-4 py-3">Wallet address</th>
                <th className="px-4 py-3">Organization</th>
                <th className="px-4 py-3">Labels</th>
                <th className="px-4 py-3">Sanctioned entity</th>
                <th className="px-4 py-3">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {wallets.map((w) => (
                <tr key={`${w.chain}-${w.address}`} className="hover:bg-surface">
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-xs text-text-primary">
                      {CHAIN_LABEL[w.chain] ?? w.chain}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <code className="break-all font-mono text-xs text-text-dim">{w.address}</code>
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 font-medium text-accent">{w.org}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
                        terror
                      </span>
                      {w.topics
                        .split(",")
                        .map((t) => t.trim())
                        .filter((t) => t && t !== "terror")
                        .map((t) => (
                          <span
                            key={t}
                            className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-text-dim"
                          >
                            {t}
                          </span>
                        ))}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-text-dim">{w.entity_name}</td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-xs text-text-dim">
                    {w.source.replace("opensanctions/", "")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-6 text-xs leading-relaxed text-text-dim">
          Source: OpenSanctions (OFAC SDN, EU, UN consolidated lists). These are publicly
          designated addresses for sanctions screening and threat-finance analysis. Inclusion
          reflects the issuing authority&apos;s designation, not our assessment. Addresses may be
          reused or dormant; always verify against the primary list before acting.
        </p>
      </main>
      <Footer />
    </>
  );
}
