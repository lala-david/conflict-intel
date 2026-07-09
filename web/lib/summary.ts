/**
 * Deterministic, template-based prose summaries for country & organization pages.
 *
 * These turn the numeric stats already fetched on a page into a short,
 * natural-language paragraph — a long-tail ranking surface for SEO that also
 * gives human readers a plain-English orientation. No LLM, fully deterministic.
 *
 * Every field is optional / defensively handled: the generators never emit
 * "undefined", "NaN", empty clauses, or broken grammar when data is missing
 * or zero. Clauses that lack their data are simply dropped.
 */
import { formatNumber, getCategoryMeta } from "./utils";

/** "1 event" / "3 events" — safe pluralization for a non-negative count. */
function plural(n: number, singular: string, pluralForm?: string): string {
  const word = n === 1 ? singular : pluralForm ?? `${singular}s`;
  return `${formatNumber(n)} ${word}`;
}

/** Join finished sentences, trimming stray whitespace. */
function paragraph(...sentences: (string | null | undefined)[]): string {
  return sentences
    .map((s) => (s ?? "").trim())
    .filter(Boolean)
    .join(" ");
}

// ─── Country summary ───────────────────────────────────────────────────────

export interface CountrySummaryInput {
  name: string;
  eventCount: number;
  totalFatalities: number;
  /** Raw category key (e.g. "civil_war") of the most common category. */
  topCategory?: string | null;
  /** Year with the most recorded events. */
  peakYear?: number | null;
  /** Name of the most active actor. */
  topActor?: string | null;
  /** Length of the recent window in days (e.g. 30). */
  recentDays: number;
  recentEvents: number;
  recentFatalities: number;
}

export function countrySummary(i: CountrySummaryInput): string {
  const name = (i.name || "This country").trim();
  const events = Math.max(0, i.eventCount || 0);
  const fatalities = Math.max(0, i.totalFatalities || 0);

  if (events === 0) {
    return `No armed-violence events have been recorded in ${name} since 1970 in this dataset.`;
  }

  // Sentence 1 — headline totals, optionally with the dominant category.
  const catLabel = i.topCategory ? getCategoryMeta(i.topCategory).label.toLowerCase() : "";
  const catClause = catLabel ? `, most commonly classified as ${catLabel}` : "";
  const s1 = `${name} has recorded ${plural(events, "armed-violence event")} and ${plural(
    fatalities,
    "fatality",
    "fatalities"
  )} since 1970${catClause}.`;

  // Sentence 2 — peak year and/or most active actor (drop if neither present).
  let s2: string | null = null;
  const peak = i.peakYear && i.peakYear > 0 ? `Activity peaked in ${i.peakYear}` : "";
  const actor = i.topActor?.trim() ? `the most active actor is ${i.topActor.trim()}` : "";
  if (peak && actor) s2 = `${peak}, and ${actor}.`;
  else if (peak) s2 = `${peak}.`;
  else if (actor) s2 = `${actor.charAt(0).toUpperCase()}${actor.slice(1)}.`;

  // Sentence 3 — recent window.
  const days = Math.max(1, i.recentDays || 30);
  const rEvents = Math.max(0, i.recentEvents || 0);
  const rFatalities = Math.max(0, i.recentFatalities || 0);
  const s3 =
    rEvents === 0
      ? `No events have been recorded there in the last ${days} days.`
      : `Over the last ${days} days there ${rEvents === 1 ? "was" : "were"} ${plural(
          rEvents,
          "event"
        )} and ${plural(rFatalities, "fatality", "fatalities")}.`;

  return paragraph(s1, s2, s3);
}

// ─── Organization summary ──────────────────────────────────────────────────

export interface OrgSummaryInput {
  name: string;
  events: number;
  fatalities: number;
  /** Number of distinct countries the group is active in. */
  countries?: number | null;
  firstYear?: number | null;
  lastYear?: number | null;
  /** Year with the most recorded events. */
  peakYear?: number | null;
  /** Most affected / most active country name. */
  topCountry?: string | null;
}

export function orgSummary(i: OrgSummaryInput): string {
  const name = (i.name || "This group").trim();
  const events = Math.max(0, i.events || 0);
  const fatalities = Math.max(0, i.fatalities || 0);

  if (events === 0) {
    return `No events have been attributed to ${name} in this dataset.`;
  }

  // Sentence 1 — totals, optionally with country spread and active date range.
  const countries = i.countries && i.countries > 0 ? i.countries : 0;
  const spread = countries > 0 ? ` across ${plural(countries, "country", "countries")}` : "";
  const s1 = `${name} has been linked to ${plural(events, "recorded event")} and ${plural(
    fatalities,
    "fatality",
    "fatalities"
  )}${spread}.`;

  // Sentence 2 — active date range.
  const fy = i.firstYear && i.firstYear > 0 ? i.firstYear : null;
  const ly = i.lastYear && i.lastYear > 0 ? i.lastYear : null;
  let s2: string | null = null;
  if (fy && ly) {
    s2 = fy === ly ? `Activity was recorded in ${fy}.` : `Activity spans ${fy} to ${ly}.`;
  } else if (fy) {
    s2 = `Activity was first recorded in ${fy}.`;
  }

  // Sentence 3 — peak year and/or most affected country.
  const peak = i.peakYear && i.peakYear > 0 ? `Activity peaked in ${i.peakYear}` : "";
  const country = i.topCountry?.trim()
    ? `${i.topCountry.trim()} is the most affected country`
    : "";
  let s3: string | null = null;
  if (peak && country) s3 = `${peak}, and ${country}.`;
  else if (peak) s3 = `${peak}.`;
  else if (country) s3 = `${country.charAt(0).toUpperCase()}${country.slice(1)}.`;

  return paragraph(s1, s2, s3);
}
