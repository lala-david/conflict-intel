import Link from "next/link";
import type { Event } from "@/lib/types";
import { formatDate, getCategoryMeta, formatNumber } from "@/lib/utils";
import { SectionHeading } from "@/components/ui/SectionHeading";

interface Props {
  events: Event[];
}

export function EventFeed({ events }: Props) {
  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <SectionHeading
        kicker="On the wire"
        title="Recent events"
        action={<span>Last 90 days</span>}
      />

      <div className="rounded-lg border border-border bg-surface">
        {events.map((event) => {
          const meta = getCategoryMeta(event.category);
          const actor = event.actor1 || "Unknown";
          return (
            <Link
              key={event.id}
              href={`/events/${encodeURIComponent(event.id)}`}
              className="group block border-b border-border px-5 py-4 transition last:border-b-0 hover:bg-surface-2"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3 text-xs">
                    <span
                      className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white"
                      style={{ background: meta.color }}
                    >
                      {meta.label}
                    </span>
                    <span className="font-mono text-text-dim">
                      {formatDate(event.date)}
                    </span>
                    <span className="text-text-dim">·</span>
                    <span className="text-text-dim">{event.country}</span>
                  </div>
                  <div className="mt-2 truncate text-sm font-medium text-text-primary group-hover:text-accent">
                    {actor}
                    {event.actor2 && event.actor2 !== "Civilians" && (
                      <span className="text-text-dim"> vs {event.actor2}</span>
                    )}
                  </div>
                  {event.location && (
                    <div className="mt-0.5 truncate text-xs text-text-dim">
                      {event.location}
                    </div>
                  )}
                </div>

                <div className="shrink-0 text-right">
                  <div className="font-display text-2xl font-semibold tabular-nums leading-none text-text-primary">
                    {formatNumber(event.fatalities)}
                  </div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-text-dim">
                    killed
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
