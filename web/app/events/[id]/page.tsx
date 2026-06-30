import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getEventById, getRelatedEvents } from "@/lib/queries";
import { formatNumber, formatDate, getCategoryMeta } from "@/lib/utils";
import { ArrowLeft, MapPin, Calendar, Users, ExternalLink } from "lucide-react";
import { EventMiniMapClient } from "@/components/map/EventMiniMapClient";

export const revalidate = 86400; // 24h

interface Props {
  params: { id: string };
}

export async function generateMetadata({ params }: Props) {
  const event = await getEventById(decodeURIComponent(params.id));
  if (!event) return { title: "Event not found" };

  const meta = getCategoryMeta(event.category);
  const title = `${event.actor1 || "Unknown"} ${
    event.actor2 && event.actor2 !== "Civilians" ? `vs ${event.actor2}` : "attack"
  } in ${event.country} — ${formatDate(event.date)}`;
  const description = `${meta.label} event in ${event.location || event.country} on ${formatDate(event.date)}. ${event.fatalities} killed.`;

  return {
    title: `${title} | Conflict Researcher`,
    description,
    openGraph: { title, description },
  };
}

export default async function EventPage({ params }: Props) {
  const event = await getEventById(decodeURIComponent(params.id));
  if (!event) notFound();

  const related = await getRelatedEvents(event, 6);
  const meta = getCategoryMeta(event.category);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-1 text-xs text-text-dim hover:text-text-primary"
        >
          <ArrowLeft className="h-3 w-3" />
          Home
        </Link>

        {/* Category badge + date */}
        <div className="mb-4 flex items-center gap-3 text-xs">
          <span
            className="inline-flex rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-white"
            style={{ background: meta.color }}
          >
            {meta.label}
          </span>
          <span className="font-mono text-text-dim">
            {formatDate(event.date)}
          </span>
          {event.category_confidence && (
            <span className="font-mono text-text-dim">
              · {event.category_confidence} confidence
            </span>
          )}
        </div>

        {/* Title */}
        <h1 className="font-display text-3xl font-bold leading-tight md:text-4xl">
          {event.actor1 || "Unknown actors"}
          {event.actor2 && event.actor2 !== "Civilians" && (
            <span className="text-text-dim"> vs {event.actor2}</span>
          )}
        </h1>

        {/* Location */}
        <div className="mt-3 flex items-center gap-2 text-text-dim">
          <MapPin className="h-4 w-4" />
          <span>
            {event.location ? `${event.location}, ` : ""}
            <Link
              href={`/countries/${encodeURIComponent(event.country ?? "")}`}
              className="underline hover:text-text-primary"
            >
              {event.country}
            </Link>
          </span>
        </div>

        {/* Fatality highlight */}
        <div className="mt-8 rounded-lg border border-border bg-surface p-6">
          <div className="flex items-baseline gap-3">
            <span className="font-display text-6xl font-bold leading-none tabular-nums text-accent">
              {formatNumber(event.fatalities)}
            </span>
            <span className="text-lg text-text-dim">killed</span>
          </div>
          {((event.fatalities_low ?? 0) > 0 ||
            (event.fatalities_high ?? 0) > 0) && (
            <div className="mt-2 font-mono text-xs text-text-dim">
              Range: {event.fatalities_low ?? 0}–{event.fatalities_high ?? 0}
            </div>
          )}
          {(event.deaths_civilians ?? 0) > 0 && (
            <div className="mt-2 flex items-center gap-1 text-xs text-text-dim">
              <Users className="h-3 w-3" />
              {formatNumber(event.deaths_civilians ?? 0)} civilians
            </div>
          )}
        </div>

        {/* Map */}
        {event.latitude != null && event.longitude != null && (
          <section className="mt-8">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-text-dim">
              Location
            </h2>
            <EventMiniMapClient
              latitude={event.latitude}
              longitude={event.longitude}
              label={event.location || event.country || undefined}
            />
          </section>
        )}

        {/* Details */}
        <section className="mt-8">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-text-dim">
            Details
          </h2>
          <div className="rounded-lg border border-border bg-surface">
            <Detail label="Date" value={formatDate(event.date)} mono />
            <Detail
              label="Location"
              value={
                event.admin1
                  ? `${event.location || ""}${
                      event.location ? ", " : ""
                    }${event.admin1}, ${event.country}`
                  : `${event.location || ""}${event.location ? ", " : ""}${event.country}`
              }
            />
            {event.latitude != null && event.longitude != null && (
              <Detail
                label="Coordinates"
                value={`${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}`}
                mono
              />
            )}
            <Detail label="Perpetrator" value={event.actor1 || "Unknown"} />
            {event.actor2 && (
              <Detail label="Target / Other" value={event.actor2} />
            )}
            <Detail label="Source" value={event.source} mono />
            {event.event_type && (
              <Detail label="Event type" value={event.event_type} mono />
            )}
          </div>
        </section>

        {/* Notes */}
        {event.notes && (
          <section className="mt-8">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-text-dim">
              Description
            </h2>
            <div className="rounded-lg border border-border bg-surface p-5 text-sm leading-relaxed text-text-primary">
              {event.notes}
            </div>
          </section>
        )}

        {/* Source link */}
        {event.source_url && (
          <section className="mt-8">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-text-dim">
              External source
            </h2>
            <a
              href={event.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2 text-sm text-text-primary transition hover:bg-surface-2"
            >
              <ExternalLink className="h-4 w-4" />
              {new URL(event.source_url).hostname}
            </a>
          </section>
        )}

        {/* Related */}
        {related.length > 0 && (
          <section className="mt-12 border-t border-border pt-8">
            <h2 className="mb-4 font-display text-2xl font-bold">
              Related Events
            </h2>
            <p className="mb-4 text-xs text-text-dim">
              Same country, within 30 days
            </p>
            <div className="rounded-lg border border-border bg-surface">
              {related.map((r) => {
                const rMeta = getCategoryMeta(r.category);
                return (
                  <Link
                    key={r.id}
                    href={`/events/${encodeURIComponent(r.id)}`}
                    className="group flex items-start justify-between gap-4 border-b border-border px-5 py-3 transition last:border-b-0 hover:bg-surface-2"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-xs">
                        <span
                          className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-white"
                          style={{ background: rMeta.color }}
                        >
                          {rMeta.label}
                        </span>
                        <span className="font-mono text-text-dim">
                          {formatDate(r.date)}
                        </span>
                      </div>
                      <div className="mt-1 truncate text-sm group-hover:text-accent">
                        {r.actor1 || "Unknown"}
                      </div>
                    </div>
                    <div className="text-right font-mono text-sm tabular-nums">
                      {formatNumber(r.fatalities)}
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}
      </main>
      <Footer />
    </>
  );
}

function Detail({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-4 border-b border-border px-5 py-3 last:border-b-0">
      <div className="w-32 shrink-0 text-[10px] font-semibold uppercase tracking-widest text-text-dim">
        {label}
      </div>
      <div
        className={`min-w-0 flex-1 text-sm text-text-primary ${mono ? "font-mono" : ""}`}
      >
        {value}
      </div>
    </div>
  );
}
