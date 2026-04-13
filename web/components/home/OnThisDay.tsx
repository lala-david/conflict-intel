import Link from "next/link";
import type { Event } from "@/lib/types";
import { getCategoryMeta } from "@/lib/utils";
import { History } from "lucide-react";

interface Props {
  event: Event | null;
}

export function OnThisDay({ event }: Props) {
  if (!event) return null;

  const meta = getCategoryMeta(event.category);
  const year = event.date?.slice(0, 4) ?? "?";
  const fatalities = event.fatalities ?? 0;

  return (
    <section className="mx-auto max-w-7xl px-6 py-8">
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-dim">
          <History className="h-3.5 w-3.5" />
          On This Day
        </div>
        <Link
          href={`/events/${encodeURIComponent(event.id)}`}
          className="group mt-3 block"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <span className="font-mono text-sm text-text-dim">{year}</span>
              <span className="mx-2 text-text-dim">·</span>
              <span
                className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white"
                style={{ background: meta.color }}
              >
                {meta.label}
              </span>
              <span className="mx-2 text-text-dim">·</span>
              <span className="font-medium group-hover:text-accent">
                {event.actor1 || "Unknown"} — {event.country}
              </span>
            </div>
            <div className="text-right">
              <span className="font-mono text-lg font-bold tabular-nums text-accent">
                {fatalities.toLocaleString()}
              </span>
              <span className="ml-1 text-xs text-text-dim">killed</span>
            </div>
          </div>
          {event.notes && (
            <p className="mt-2 line-clamp-2 text-xs text-text-dim">
              {event.notes}
            </p>
          )}
        </Link>
      </div>
    </section>
  );
}
