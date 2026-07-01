import { formatNumber } from "@/lib/utils";

interface Props {
  totals: { events: number; fatalities: number; countries: number };
}

export function HeroStats({ totals }: Props) {
  const years = new Date().getFullYear() - 1989 + 1;

  return (
    <header className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 pt-16 pb-12">
        {/* Kicker */}
        <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.25em] text-accent">
          <span>Global Conflict Monitor</span>
          <span className="h-px flex-1 bg-border" aria-hidden />
          <span className="font-mono tracking-[0.2em] text-text-dim">Open Data</span>
        </div>

        {/* Masthead headline */}
        <h1 className="mt-6 max-w-4xl font-display text-4xl font-semibold leading-[1.05] tracking-tight text-text-primary sm:text-5xl md:text-6xl">
          Tracking organized violence across the world,{" "}
          <span className="italic text-text-dim">every single day.</span>
        </h1>

        {/* Standfirst */}
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-text-dim">
          Open-source intelligence fusing eight independent datasets — UCDP, GDELT,
          global sanctions and more — into one live, categorized record of armed
          conflict. Free and open, updated every morning.
        </p>

        {/* Editorial figures row */}
        <dl className="mt-12 grid grid-cols-2 gap-y-8 border-t border-border pt-8 md:grid-cols-4 md:divide-x md:divide-border">
          <Figure value={formatNumber(totals.events)} label="Events recorded" />
          <Figure value={formatNumber(totals.fatalities)} label="Fatalities documented" muted />
          <Figure value={formatNumber(totals.countries)} label="Countries covered" />
          <Figure value={`${years}`} label="Years of history · since 1989" />
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
        className={`font-display text-4xl font-semibold tabular-nums leading-none md:text-5xl ${
          muted ? "text-accent" : "text-text-primary"
        }`}
      >
        {value}
      </dd>
      <dt className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-dim">
        {label}
      </dt>
    </div>
  );
}
