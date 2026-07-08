import Link from "next/link";
import { formatNumber } from "@/lib/utils";
import { ShaderBackdrop } from "@/components/ui/ShaderBackdrop";

interface Props {
  totals: { events: number; fatalities: number; countries: number };
}

export function HeroStats({ totals }: Props) {
  const years = new Date().getFullYear() - 1970 + 1;

  return (
    <header className="relative isolate overflow-hidden border-b border-border">
      <ShaderBackdrop />
      <div className="mx-auto max-w-7xl px-5 pt-14 pb-10 sm:px-6 md:pt-20 md:pb-12">
        {/* Kicker */}
        <div className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-accent sm:text-[11px] sm:tracking-[0.25em]">
          <span>Global Conflict Monitor</span>
          <span className="h-px flex-1 bg-border" aria-hidden />
          <span className="font-mono tracking-[0.2em] text-text-dim">Updated daily</span>
        </div>

        {/* Masthead headline */}
        <h1 className="mt-6 max-w-4xl font-display text-[2rem] font-semibold leading-[1.05] tracking-tight text-text-primary sm:text-5xl md:text-7xl">
          Track the conflicts{" "}
          <span className="italic text-text-dim">you follow.</span>
        </h1>

        {/* One-line value + primary actions */}
        <p className="mt-5 max-w-xl text-base leading-relaxed text-text-dim">
          One live feed of global organized violence. Follow the countries and
          topics that matter — see everything new in one place.
        </p>
        <div className="mt-7 flex flex-wrap items-center gap-3">
          <Link
            href="/tracking"
            className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent/90"
          >
            Start tracking →
          </Link>
          <Link
            href="/events"
            className="rounded-md border border-border px-5 py-2.5 text-sm font-medium text-text-primary transition hover:bg-surface-2"
          >
            Browse events
          </Link>
        </div>

        {/* Editorial figures row */}
        <dl className="mt-14 grid grid-cols-2 gap-y-8 border-t border-border pt-8 md:grid-cols-4 md:divide-x md:divide-border">
          <Figure value={formatNumber(totals.events)} label="Events recorded" />
          <Figure value={formatNumber(totals.fatalities)} label="Fatalities documented" muted />
          <Figure value={formatNumber(totals.countries)} label="Countries covered" />
          <Figure value={`${years}`} label="Years of history · since 1970" />
        </dl>
      </div>
    </header>
  );
}

function Figure({
  value,
  label,
  muted = false,
}: {
  value: string;
  label: string;
  muted?: boolean;
}) {
  return (
    <div className="md:px-6 md:first:pl-0">
      <dd
        className={`font-display text-[1.75rem] font-semibold tabular-nums leading-none sm:text-4xl md:text-5xl ${
          muted ? "text-accent" : "text-text-primary"
        }`}
      >
        {value}
      </dd>
      <dt className="mt-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-dim sm:text-[11px] sm:tracking-[0.18em]">
        {label}
      </dt>
    </div>
  );
}
