/**
 * Query-time PROVENANCE & CORROBORATION for events.
 *
 * The pipeline clusters duplicate source records of the SAME incident via the
 * `dup_of` column: a canonical event has `dup_of IS NULL`; every other source
 * record of that incident carries `dup_of = <canonical id>`. Each row keeps its
 * own `source` / `source_url` / `category_confidence` / fatality range, so the
 * corroboration that already lives in the data can be surfaced without any
 * schema change or resync — it's all computed here at read time.
 *
 * `dup_of` is indexed (idx_events_dup), so every read below is a cheap indexed
 * lookup (single id) or a bounded grouped scan (a page's worth of ids).
 */
import { queryAll, queryOne } from "@/lib/db";
import { getSourceMeta, type Tier } from "@/components/ui/SourceBadge";
import type { Confidence } from "@/lib/types";

// ── source tiers ───────────────────────────────────────────────────────────

/**
 * Trust tier for a raw `source` string — reuses the single source→tier mapping
 * already defined for the SourceBadge chip so the grade and the badge can never
 * drift apart.
 */
export function sourceTier(source?: string | null): Tier {
  return getSourceMeta(source).tier;
}

/**
 * How "good" a tier is when a single incident carries several sources. Used to
 * pick the strongest source when computing a composite grade.
 */
const TIER_RANK: Record<Tier, number> = {
  verified: 6, // casualty-verified academic conflict data (UCDP)
  academic: 5, // peer-reviewed academic dataset (GTD)
  gov: 4, // government / official designation list
  reference: 3, // encyclopedic (Wikipedia / Wikidata)
  news: 2, // news / RSS wire report
  media: 1, // machine-coded from media (GDELT) — lowest
  osint: 2, // open-source / social channel
  other: 0,
};

/** The strongest tier among a set of sources (for the composite grade). */
export function bestTier(sources: Array<{ source?: string | null }>): Tier {
  let best: Tier = "other";
  for (const s of sources) {
    const t = sourceTier(s.source);
    if (TIER_RANK[t] > TIER_RANK[best]) best = t;
  }
  return best;
}

// ── reliability grade ──────────────────────────────────────────────────────

export interface ReliabilityGrade {
  /** short label, e.g. "Verified" */
  label: string;
  /** one-line rationale shown under the badge */
  desc: string;
  /** accent color (hex, works inline on dark bg) */
  color: string;
  /** subtle tinted background */
  bg: string;
}

/**
 * Composite reliability grade for an incident. Grade rules (strongest first):
 *
 *  • Verified     — a casualty-verified UCDP source (tier "verified"), OR the
 *                   incident is attested by 3+ independent sources.
 *  • Corroborated — 2+ independent sources agree on the incident.
 *  • Machine-coded— a SINGLE machine-coded media source only (GDELT, tier
 *                   "media"): lowest confidence, no human corroboration.
 *  • Reported     — a single credible human/curated source (news, encyclopedic,
 *                   government, academic, OSINT) with no second source yet.
 *
 * `confidence` (the row's category_confidence) is not used to promote a grade —
 * corroboration count and source tier decide it — but it's threaded through so
 * callers can display it beside the grade.
 */
export function reliabilityGrade({
  tier,
  sourceCount,
  confidence,
}: {
  tier: Tier;
  sourceCount: number;
  confidence?: Confidence | null;
}): ReliabilityGrade {
  void confidence; // displayed by callers, not a grade input (see doc above)

  if (tier === "verified" || sourceCount >= 3) {
    return {
      label: "Verified",
      desc:
        tier === "verified"
          ? "Casualty-verified academic source (UCDP)"
          : `Attested by ${sourceCount} independent sources`,
      color: "#34d399",
      bg: "rgba(52,211,153,0.12)",
    };
  }

  if (sourceCount >= 2) {
    return {
      label: "Corroborated",
      desc: `Corroborated by ${sourceCount} independent sources`,
      color: "#38bdf8",
      bg: "rgba(56,189,248,0.12)",
    };
  }

  if (tier === "media") {
    return {
      label: "Machine-coded",
      desc: "Single machine-coded media source (GDELT) — uncorroborated",
      color: "#fbbf24",
      bg: "rgba(251,191,36,0.12)",
    };
  }

  return {
    label: "Reported",
    desc: "Single credible source — not yet independently corroborated",
    color: "#94a3b8",
    bg: "rgba(148,163,184,0.12)",
  };
}

// ── per-event provenance ───────────────────────────────────────────────────

export interface ProvenanceSource {
  source: string;
  sourceUrl: string | null;
  provider: string;
  tier: Tier;
}

export interface EventProvenance {
  /** distinct corroborating sources (canonical row + all its dups) */
  sources: ProvenanceSource[];
  /** number of distinct sources */
  sourceCount: number;
  fatalitiesLow: number | null;
  fatalitiesHigh: number | null;
  grade: ReliabilityGrade;
}

interface SourceRow {
  source: string | null;
  source_url: string | null;
}

/**
 * Full provenance for one canonical event: the distinct corroborating sources
 * (the event's own record plus every source record clustered onto it via
 * `dup_of`), a distinct-source count, the fatality range, and a composite
 * reliability grade. Both reads are indexed (PK / idx_events_dup).
 */
export async function getEventProvenance(id: string): Promise<EventProvenance | null> {
  const [rows, event] = await Promise.all([
    queryAll<SourceRow>(
      `SELECT DISTINCT source, source_url FROM events WHERE id = ? OR dup_of = ?`,
      [id, id],
    ),
    queryOne<{
      fatalities_low: number | null;
      fatalities_high: number | null;
      category_confidence: Confidence | null;
    }>(
      `SELECT fatalities_low, fatalities_high, category_confidence FROM events WHERE id = ?`,
      [id],
    ),
  ]);

  if (!event) return null;

  // Collapse to distinct sources (a source can appear with several urls); keep
  // the first url seen for each source so we always have a link if one exists.
  const bySource = new Map<string, ProvenanceSource>();
  for (const r of rows) {
    const key = (r.source || "unknown").toLowerCase();
    const existing = bySource.get(key);
    if (existing) {
      if (!existing.sourceUrl && r.source_url) existing.sourceUrl = r.source_url;
      continue;
    }
    const meta = getSourceMeta(r.source);
    bySource.set(key, {
      source: r.source || "unknown",
      sourceUrl: r.source_url,
      provider: meta.provider,
      tier: meta.tier,
    });
  }

  const sources = Array.from(bySource.values()).sort(
    (a, b) => TIER_RANK[b.tier] - TIER_RANK[a.tier],
  );
  const sourceCount = sources.length;

  const grade = reliabilityGrade({
    tier: bestTier(sources),
    sourceCount,
    confidence: event.category_confidence,
  });

  return {
    sources,
    sourceCount,
    fatalitiesLow: event.fatalities_low,
    fatalitiesHigh: event.fatalities_high,
    grade,
  };
}

// ── batched corroboration (list pages) ─────────────────────────────────────

/**
 * Corroboration counts for a LIST of canonical events, in ONE grouped query.
 * Returns a map id → distinct-ish source count = 1 (the canonical row itself)
 * plus the number of dup rows clustered onto it. The id list is bounded by the
 * caller (a page of ~30–50) and every id is a bound parameter (safe IN-list).
 *
 * Note this counts source *records*, not strictly distinct source strings — for
 * a compact "+N sources" list indicator that's the intended, cheap signal; the
 * event detail page computes the exact distinct-source figure.
 */
export async function getCorroboration(ids: string[]): Promise<Map<string, number>> {
  const counts = new Map<string, number>();
  if (ids.length === 0) return counts;

  // Every canonical event has at least its own record.
  for (const id of ids) counts.set(id, 1);

  const placeholders = ids.map(() => "?").join(",");
  const rows = await queryAll<{ cid: string; c: number }>(
    `SELECT dup_of AS cid, COUNT(*) AS c
       FROM events
      WHERE dup_of IN (${placeholders})
      GROUP BY dup_of`,
    ids,
  );

  for (const r of rows) {
    if (r.cid == null) continue;
    counts.set(r.cid, (counts.get(r.cid) ?? 1) + r.c);
  }

  return counts;
}
