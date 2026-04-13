import { formatNumber } from "@/lib/utils";
import { Database, Globe2, Calendar, Skull } from "lucide-react";

interface Props {
  totals: { events: number; fatalities: number; countries: number };
}

export function HeroStats({ totals }: Props) {
  return (
    <div className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="max-w-2xl">
          <h1 className="font-display text-4xl font-bold leading-tight tracking-tight md:text-5xl">
            Global Armed Violence Monitor
          </h1>
          <p className="mt-4 text-lg text-text-dim">
            Open-source intelligence from 8 sources. Categorized by academic standard. Updated daily.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-2 gap-6 md:grid-cols-4">
          <StatCard
            icon={<Database className="h-4 w-4" />}
            value={formatNumber(totals.events)}
            label="Events tracked"
          />
          <StatCard
            icon={<Skull className="h-4 w-4" />}
            value={formatNumber(totals.fatalities)}
            label="Fatalities recorded"
          />
          <StatCard
            icon={<Globe2 className="h-4 w-4" />}
            value={formatNumber(totals.countries)}
            label="Countries covered"
          />
          <StatCard
            icon={<Calendar className="h-4 w-4" />}
            value="37"
            label="Years of data (1989–)"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-text-dim">
        {icon}
        <span className="font-semibold uppercase tracking-widest">{label}</span>
      </div>
      <div className="mt-2 font-display text-3xl font-bold tabular-nums md:text-4xl">
        {value}
      </div>
    </div>
  );
}
