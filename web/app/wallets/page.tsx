import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { WalletTable } from "@/components/wallets/WalletTable";
import { ThreatGlobe } from "@/components/ui/ThreatGlobe";
import { getCryptoStats, getCryptoWallets } from "@/lib/queries";
import { ShieldAlert, Radar, Boxes, Link2 } from "lucide-react";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Terror-Financing Wallets — Conflict & Security Intelligence",
  description:
    "Cryptocurrency wallet addresses publicly attributed to terrorist organizations — OFAC/EU/UN sanctions, DOJ forfeitures, NBCTF seizures — mapped to the groups we track.",
};

const CHAIN_COLOR: Record<string, string> = {
  BTC: "#f7931a", ETH: "#8a92b2", TRX: "#ef4444", XMR: "#ff6600",
  LTC: "#345d9d", USDT: "#26a17b", BCH: "#0ac18e",
};

function Bars({
  items, total, colorFor,
}: {
  items: { label: string; n: number }[];
  total: number;
  colorFor?: (label: string) => string;
}) {
  const max = Math.max(...items.map((i) => i.n), 1);
  return (
    <div className="space-y-2.5">
      {items.map((it) => {
        const pct = ((it.n / total) * 100).toFixed(1);
        return (
          <div key={it.label} className="group">
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="font-medium text-text-primary">{it.label}</span>
              <span className="font-mono tabular-nums text-text-dim">
                {it.n.toLocaleString()} <span className="text-text-dim/60">· {pct}%</span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${(it.n / max) * 100}%`,
                  background: colorFor ? colorFor(it.label) : "#ef4444",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default async function WalletsPage() {
  const [stats, wallets] = await Promise.all([
    getCryptoStats(),
    getCryptoWallets({ terrorOnly: true, limit: 2000 }),
  ]);

  // proportions computed from the terror set (not the whole 17k)
  const chainCounts = new Map<string, number>();
  for (const w of wallets) chainCounts.set(w.chain, (chainCounts.get(w.chain) || 0) + 1);
  const byChain = [...chainCounts.entries()]
    .map(([label, n]) => ({ label, n }))
    .sort((a, b) => b.n - a.n);
  const byOrg = stats.byOrg
    .map((o) => ({ label: o.org, n: o.n }))
    .sort((a, b) => b.n - a.n);
  const sample = wallets.slice(0, 14);

  return (
    <>
      <Header />
      <main>
        {/* Hero with animated threat globe */}
        <section className="relative overflow-hidden border-b border-border">
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(70% 100% at 80% 20%, rgba(239,68,68,0.16), transparent 55%)",
            }}
          />
          <div className="relative mx-auto max-w-6xl px-6 py-14">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
                <Radar className="h-3.5 w-3.5" />
                Threat finance · on-chain intelligence
              </div>
              <h1 className="mt-4 font-display text-4xl font-bold leading-tight tracking-tight md:text-5xl">
                Terror-financing <span className="text-accent">wallets</span>
              </h1>
              <p className="mt-3 max-w-md text-sm leading-relaxed text-text-dim">
                Every crypto address publicly attributed to a designated terrorist
                organization — OFAC/EU/UN sanctions, DOJ forfeitures and NBCTF seizures,
                deduped and mapped to the groups we track.
              </p>
              <dl className="mt-7 grid max-w-md grid-cols-3 gap-4">
                {[
                  { icon: ShieldAlert, label: "Terror wallets", value: wallets.length },
                  { icon: Link2, label: "Groups", value: byOrg.length },
                  { icon: Boxes, label: "Blockchains", value: byChain.length },
                ].map((s) => (
                  <div key={s.label}>
                    <s.icon className="h-4 w-4 text-accent" />
                    <dd className="mt-1.5 font-display text-3xl font-bold tabular-nums text-text-primary">
                      {s.value.toLocaleString()}
                    </dd>
                    <dt className="text-[11px] uppercase tracking-wider text-text-dim">{s.label}</dt>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-6xl px-6 py-10">
          {/* Proportion charts — ratios, not a raw dump */}
          <div className="grid gap-8 lg:grid-cols-2">
            <div className="card-elevated p-6">
              <h2 className="mb-4 font-display text-lg font-bold">
                By organization <span className="text-text-dim">· {byOrg.length}</span>
              </h2>
              <Bars items={byOrg} total={wallets.length} />
            </div>
            <div className="card-elevated p-6">
              <h2 className="mb-4 font-display text-lg font-bold">By blockchain</h2>
              <Bars
                items={byChain}
                total={wallets.length}
                colorFor={(c) => CHAIN_COLOR[c] || "#8a92b2"}
              />
            </div>
          </div>

          {/* Sample addresses — a preview, not all of them */}
          <div className="mt-12 mb-4 flex items-baseline justify-between">
            <h2 className="font-display text-lg font-bold">
              Address ledger <span className="text-text-dim">· sample of {wallets.length}</span>
            </h2>
            <a href="/api-docs" className="text-xs text-text-dim hover:text-accent">
              Full set via API →
            </a>
          </div>
          <WalletTable wallets={sample} />

          <p className="mt-6 max-w-3xl text-xs leading-relaxed text-text-dim">
            Showing a sample. Sources: OpenSanctions (OFAC SDN, EU, UN), DOJ terror-finance
            forfeitures and Israel&apos;s NBCTF seizures. Inclusion reflects the issuing
            authority&apos;s designation, not our assessment; addresses may be reused or
            dormant — verify against the primary source before acting.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
