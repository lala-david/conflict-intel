import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { WalletTable } from "@/components/wallets/WalletTable";
import { getCryptoStats, getCryptoWallets } from "@/lib/queries";
import { ShieldAlert } from "lucide-react";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Terror-Financing Wallets — Conflict & Security Intelligence",
  description:
    "Cryptocurrency wallet addresses publicly attributed to terrorist organizations — from OFAC/EU/UN sanctions and DOJ forfeiture data — mapped to the groups we track. On-chain threat-finance intelligence.",
};

export default async function WalletsPage() {
  const [stats, wallets] = await Promise.all([
    getCryptoStats(),
    getCryptoWallets({ terrorOnly: true, limit: 3000 }),
  ]);
  const chains = new Set(wallets.map((w) => w.chain)).size;

  return (
    <>
      <Header />
      <main>
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-border">
          <div
            className="pointer-events-none absolute inset-0 opacity-70"
            style={{
              background:
                "radial-gradient(60% 120% at 15% 0%, rgba(239,68,68,0.18), transparent 60%), radial-gradient(50% 100% at 100% 100%, rgba(239,68,68,0.10), transparent 55%)",
            }}
          />
          <div className="relative mx-auto max-w-6xl px-6 py-10">
            <div className="flex flex-wrap items-end justify-between gap-6">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
                  <ShieldAlert className="h-3.5 w-3.5" />
                  Threat finance · on-chain intelligence
                </div>
                <h1 className="mt-4 font-display text-4xl font-bold leading-tight tracking-tight md:text-5xl">
                  Terror-financing <span className="text-accent">wallets</span>
                </h1>
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-text-dim">
                  Addresses publicly attributed to terrorist organizations — OFAC/EU/UN
                  sanctions, DOJ forfeitures and NBCTF seizures, deduped and mapped to groups.
                </p>
              </div>

              {/* inline stat trio */}
              <div className="flex gap-6">
                {[
                  { label: "Terror wallets", value: wallets.length },
                  { label: "Groups", value: stats.byOrg.length },
                  { label: "Chains", value: chains },
                ].map((s) => (
                  <div key={s.label}>
                    <div className="font-display text-3xl font-bold tabular-nums text-text-primary">
                      {s.value.toLocaleString()}
                    </div>
                    <div className="text-[11px] uppercase tracking-wider text-text-dim">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-6xl px-6 py-8">
          {/* Group cards */}
          {stats.byOrg.length > 0 && (
            <>
              <h2 className="mb-4 font-display text-xl font-bold">Designated organizations</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {stats.byOrg.map((o) => (
                  <div
                    key={o.org}
                    className="group relative overflow-hidden rounded-xl border border-border bg-surface p-5 transition hover:border-accent/50"
                  >
                    <div className="absolute left-0 top-0 h-full w-1 bg-accent/70" />
                    <div className="font-display text-lg font-semibold text-text-primary">{o.org}</div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="font-display text-3xl font-bold tabular-nums text-accent">{o.n}</span>
                      <span className="text-sm text-text-dim">wallets · {o.chains} chain{o.chains > 1 ? "s" : ""}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Table */}
          <h2 className="mb-4 mt-12 font-display text-xl font-bold">
            Designated addresses <span className="text-text-dim">({wallets.length})</span>
          </h2>
          <WalletTable wallets={wallets} />

          <p className="mt-6 max-w-3xl text-xs leading-relaxed text-text-dim">
            Sources: OpenSanctions (OFAC SDN, EU, UN) and GraphSense TagPacks (authority /
            forfeiture data — e.g. DOJ al-Qaeda seizures). Publicly designated addresses for
            sanctions screening and threat-finance analysis; inclusion reflects the issuing
            authority&apos;s designation, not our assessment. Addresses may be reused or dormant —
            verify against the primary source before acting.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
