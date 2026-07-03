"use client";

import { useMemo, useState } from "react";
import { Copy, Check, ExternalLink, Search } from "lucide-react";
import type { CryptoWallet } from "@/lib/types";

const CHAIN_META: Record<string, { name: string; color: string; explorer?: (a: string) => string }> = {
  BTC: { name: "Bitcoin", color: "#f7931a", explorer: (a) => `https://mempool.space/address/${a}` },
  ETH: { name: "Ethereum", color: "#627eea", explorer: (a) => `https://etherscan.io/address/${a}` },
  TRX: { name: "Tron", color: "#ef4444", explorer: (a) => `https://tronscan.org/#/address/${a}` },
  USDT: { name: "Tether", color: "#26a17b", explorer: (a) => `https://blockchair.com/search?q=${a}` },
  USDC: { name: "USDC", color: "#2775ca", explorer: (a) => `https://blockchair.com/search?q=${a}` },
  LTC: { name: "Litecoin", color: "#a6a9aa", explorer: (a) => `https://blockchair.com/litecoin/address/${a}` },
  BCH: { name: "Bitcoin Cash", color: "#0ac18e", explorer: (a) => `https://blockchair.com/bitcoin-cash/address/${a}` },
  XMR: { name: "Monero", color: "#ff6600" },
  ZEC: { name: "Zcash", color: "#ecb244", explorer: (a) => `https://blockchair.com/zcash/address/${a}` },
  DASH: { name: "Dash", color: "#008ce7", explorer: (a) => `https://blockchair.com/dash/address/${a}` },
  ARB: { name: "Arbitrum", color: "#28a0f0", explorer: (a) => `https://arbiscan.io/address/${a}` },
};

const CAT_COLOR: Record<string, string> = {
  terror: "#ef4444", sanction: "#f59e0b", extremism: "#fb7185",
  ransomware: "#f97316", hack: "#a855f7", scam: "#eab308", mixer: "#22d3ee",
};

function CopyBtn({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(text);
        setDone(true);
        setTimeout(() => setDone(false), 1200);
      }}
      className="text-text-dim transition hover:text-text-primary"
      title="Copy address"
    >
      {done ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

export function WalletTable({ wallets }: { wallets: CryptoWallet[] }) {
  const [q, setQ] = useState("");
  const rows = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return wallets;
    return wallets.filter(
      (w) =>
        w.address.toLowerCase().includes(s) ||
        w.entity_name.toLowerCase().includes(s) ||
        (w.org ?? "").toLowerCase().includes(s) ||
        w.chain.toLowerCase().includes(s),
    );
  }, [q, wallets]);

  return (
    <div>
      <div className="relative mb-4 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search address, entity, chain…"
          className="w-full rounded-lg border border-border bg-surface py-2.5 pl-9 pr-3 text-sm text-text-primary outline-none placeholder:text-text-dim focus:border-accent"
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-surface-2 text-[11px] uppercase tracking-wider text-text-dim">
            <tr>
              <th className="px-4 py-3">Chain</th>
              <th className="px-4 py-3">Wallet address</th>
              <th className="px-4 py-3">Organization</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Sanctioned entity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((w) => {
              const cm = CHAIN_META[w.chain] ?? { name: w.chain, color: "#64748b" };
              const url = cm.explorer?.(w.address);
              return (
                <tr key={`${w.chain}-${w.address}`} className="group transition hover:bg-surface">
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <span
                      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold"
                      style={{ color: cm.color, backgroundColor: `${cm.color}1a` }}
                    >
                      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: cm.color }} />
                      {w.chain}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <code className="break-all font-mono text-xs text-text-primary">{w.address}</code>
                      <span className="flex shrink-0 items-center gap-1.5 opacity-0 transition group-hover:opacity-100">
                        <CopyBtn text={w.address} />
                        {url && (
                          <a href={url} target="_blank" rel="noreferrer" className="text-text-dim hover:text-accent" title="View on explorer">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 font-medium text-accent">{w.org ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                      style={{ color: CAT_COLOR[w.category] ?? "#94a3b8", backgroundColor: `${CAT_COLOR[w.category] ?? "#94a3b8"}1a` }}
                    >
                      {w.category}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-text-dim">{w.entity_name}</td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-text-dim">
                  No addresses match “{q}”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-text-dim">
        Showing {rows.length.toLocaleString()} of {wallets.length.toLocaleString()} addresses.
      </p>
    </div>
  );
}
