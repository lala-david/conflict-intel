import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { getEventById, getRelatedEvents } from "@/lib/queries";
import { formatNumber, formatDate, getCategoryMeta, cleanNote } from "@/lib/utils";
import { ArrowLeft, MapPin, Calendar, Users, ExternalLink } from "lucide-react";
import { EventMiniMapClient } from "@/components/map/EventMiniMapClient";
import { SourceBadge, ConfidenceBadge } from "@/components/ui/SourceBadge";
import { getEventProvenance } from "@/lib/queries-provenance";
import { getEventReview } from "@/lib/queries-reviews";

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
    title: `${title} | Conflict & Security Intelligence`,
    description,
    openGraph: { title, description },
  };
}

export default async function EventPage({ params }: Props) {
  const event = await getEventById(decodeURIComponent(params.id));
  if (!event) notFound();

  const [related, provenance, review] = await Promise.all([
    getRelatedEvents(event, 6),
    getEventProvenance(event.id),
    getEventReview(event.id),
  ]);
  const meta = getCategoryMeta(event.category);

  const CONFIDENCE_DEF: Record<string, string> = {
    high: "Category assignment is unambiguous from the source record.",
    medium: "Category inferred with some interpretation of the source record.",
    low: "Category is a best-effort guess — treat with caution.",
  };

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

        {/* Category badge + provenance + date */}
        <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs">
          <span
            className="inline-flex rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-white"
            style={{ background: meta.color }}
          >
            {meta.label}
          </span>
          <SourceBadge source={event.source} />
          {event.category_confidence && (
            <ConfidenceBadge confidence={event.category_confidence} />
          )}
          <span className="font-mono text-text-dim">
            · {formatDate(event.date)}
          </span>
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

        {/* Provenance & corroboration */}
        {provenance && (
          <section className="mt-8 rounded-lg border border-border bg-surface p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-text-dim">
                Provenance &amp; corroboration
              </h2>
              <span
                className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold tracking-wide"
                style={{
                  background: provenance.grade.bg,
                  borderColor: provenance.grade.color + "40",
                  color: provenance.grade.color,
                }}
              >
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: provenance.grade.color }}
                />
                {provenance.grade.label}
              </span>
            </div>

            <p className="mt-2 text-sm text-text-dim">{provenance.grade.desc}</p>

            {/* Source list */}
            <div className="mt-5">
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-text-dim">
                {provenance.sourceCount > 1
                  ? `Corroborated by ${provenance.sourceCount} sources`
                  : "Single source"}
              </div>
              <ul className="flex flex-col gap-2">
                {provenance.sources.map((s) => (
                  <li
                    key={s.source}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-background px-3 py-2"
                  >
                    <SourceBadge source={s.source} />
                    {s.sourceUrl ? (
                      <a
                        href={s.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-mono text-[11px] text-text-dim underline transition hover:text-text-primary"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {(() => {
                          try {
                            return new URL(s.sourceUrl).hostname;
                          } catch {
                            return "source link";
                          }
                        })()}
                      </a>
                    ) : (
                      <span className="font-mono text-[11px] text-text-dim/60">
                        no link
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* Fatality range + confidence */}
            <div className="mt-5 grid gap-4 border-t border-border pt-4 sm:grid-cols-2">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
                  Fatality estimate
                </div>
                <div className="mt-1 font-mono text-sm text-text-primary">
                  {(() => {
                    const lo = provenance.fatalitiesLow;
                    const hi = provenance.fatalitiesHigh;
                    if (lo != null && hi != null && lo !== hi)
                      return `${formatNumber(lo)}–${formatNumber(hi)} killed`;
                    const v = hi ?? lo ?? event.fatalities;
                    return `${formatNumber(v)} killed`;
                  })()}
                </div>
              </div>
              {event.category_confidence && (
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
                    Category confidence
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <ConfidenceBadge confidence={event.category_confidence} />
                  </div>
                  <p className="mt-1 text-xs text-text-dim">
                    {CONFIDENCE_DEF[event.category_confidence]}
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* AI verification (automated cross-check — not human-verified) */}
        {review && (
          <section className="mt-8 rounded-lg border border-border bg-surface p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-text-dim">
                AI verification
              </h2>
              {review.aiGrade && (
                <span
                  className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold tracking-wide"
                  style={{
                    background: aiGradeMeta(review.aiGrade).bg,
                    borderColor: aiGradeMeta(review.aiGrade).color + "40",
                    color: aiGradeMeta(review.aiGrade).color,
                  }}
                >
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ background: aiGradeMeta(review.aiGrade).color }}
                  />
                  AI grade: {aiGradeMeta(review.aiGrade).label}
                </span>
              )}
            </div>

            {/* Cross-check chips */}
            <div className="mt-4 flex flex-wrap gap-2">
              {review.consistency && (
                <ReviewChip label="Consistency" value={review.consistency} />
              )}
              {review.tollAgreement && (
                <ReviewChip label="Toll" value={review.tollAgreement} />
              )}
              {review.geoConfidence && (
                <ReviewChip label="Geo confidence" value={review.geoConfidence} />
              )}
            </div>

            {/* Summary */}
            {review.summary && (
              <p className="mt-4 text-sm leading-relaxed text-text-primary">
                {review.summary}
              </p>
            )}

            {/* Disclaimer */}
            <div className="mt-4 border-t border-border pt-3 text-[11px] text-text-dim">
              <span className="font-semibold text-text-dim">
                AI-reviewed · not human-verified.
              </span>{" "}
              Automated cross-check of the corroborating sources
              {review.model ? ` by ${review.model}` : ""}
              {review.reviewedAt
                ? ` on ${formatDate(review.reviewedAt.slice(0, 10))}`
                : ""}
              . A human console confirms forensic grade separately.
            </div>
          </section>
        )}

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
            {event.collected_at && (
              <Detail label="Recorded (UTC)" value={event.collected_at} mono />
            )}
          </div>
        </section>

        {/* Notes */}
        {cleanNote(event.notes) && (
          <section className="mt-8">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-text-dim">
              Description
            </h2>
            <div className="rounded-lg border border-border bg-surface p-5 text-sm leading-relaxed text-text-primary">
              {cleanNote(event.notes)}
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

/** Color/label for an AI-proposed reliability grade (on-brand dark tokens). */
function aiGradeMeta(grade: string): { label: string; color: string; bg: string } {
  switch (grade.toLowerCase()) {
    case "verified":
      return { label: "Verified", color: "#34d399", bg: "rgba(52,211,153,0.12)" };
    case "corroborated":
      return { label: "Corroborated", color: "#38bdf8", bg: "rgba(56,189,248,0.12)" };
    case "reported":
      return { label: "Reported", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" };
    case "machine-coded":
      return { label: "Machine-coded", color: "#fbbf24", bg: "rgba(251,191,36,0.12)" };
    default:
      return { label: "Unclear", color: "#f87171", bg: "rgba(248,113,113,0.12)" };
  }
}

function ReviewChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-[11px]">
      <span className="font-semibold uppercase tracking-widest text-text-dim">
        {label}
      </span>
      <span className="font-mono text-text-primary">{value}</span>
    </span>
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
