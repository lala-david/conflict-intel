import type { Confidence } from "@/lib/types";

/**
 * Per-event provenance chip. Maps a raw `source` string to a trust tier so an
 * analyst can tell a casualty-verified UCDP death apart from a machine-coded
 * GDELT blip at a glance. Compact, mono, dark-token styled.
 */

export type Tier =
  | "verified"
  | "academic"
  | "media"
  | "news"
  | "reference"
  | "gov"
  | "osint"
  | "other";

interface TierStyle {
  /** short pill label */
  label: string;
  /** longer descriptor for tooltip / detail contexts */
  desc: string;
  /** dot + accent color (hex, works inline on dark bg) */
  color: string;
  /** subtle tinted background */
  bg: string;
}

const TIER_STYLE: Record<Tier, TierStyle> = {
  verified: { label: "casualty-verified", desc: "Casualty-verified academic conflict data", color: "#34d399", bg: "rgba(52,211,153,0.12)" },
  academic: { label: "academic", desc: "Peer-reviewed academic dataset", color: "#38bdf8", bg: "rgba(56,189,248,0.12)" },
  media: { label: "media-coded", desc: "Machine-coded from media reports — lower confidence", color: "#fbbf24", bg: "rgba(251,191,36,0.12)" },
  news: { label: "news", desc: "News / RSS wire report", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" },
  reference: { label: "reference", desc: "Encyclopedic / reference source", color: "#a78bfa", bg: "rgba(167,139,250,0.12)" },
  gov: { label: "government", desc: "Government / official designation list", color: "#22d3ee", bg: "rgba(34,211,238,0.12)" },
  osint: { label: "OSINT", desc: "Open-source / social channel — unverified", color: "#fb7185", bg: "rgba(251,113,133,0.12)" },
  other: { label: "source", desc: "Uncategorized source", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" },
};

export interface SourceMeta {
  /** provider name shown on the chip, e.g. "UCDP" */
  provider: string;
  tier: Tier;
  style: TierStyle;
}

/** Map a raw `source` string to provider + trust tier. */
export function getSourceMeta(source?: string | null): SourceMeta {
  const s = (source || "").toLowerCase().trim();
  let provider: string;
  let tier: Tier;

  if (s.startsWith("ucdp")) {
    provider = "UCDP";
    tier = "verified";
  } else if (s === "gtd") {
    provider = "GTD";
    tier = "academic";
  } else if (s === "gdelt") {
    provider = "GDELT";
    tier = "media";
  } else if (s === "google_news") {
    provider = "Google News";
    tier = "news";
  } else if (s === "expert_rss") {
    provider = "Expert RSS";
    tier = "news";
  } else if (s === "wikipedia") {
    provider = "Wikipedia";
    tier = "reference";
  } else if (s === "wikidata") {
    provider = "Wikidata";
    tier = "reference";
  } else if (s === "ofac") {
    provider = "OFAC";
    tier = "gov";
  } else if (s === "nctc") {
    provider = "NCTC";
    tier = "gov";
  } else if (s === "telegram") {
    provider = "Telegram";
    tier = "osint";
  } else {
    provider = source ? source.toUpperCase() : "UNKNOWN";
    tier = "other";
  }

  return { provider, tier, style: TIER_STYLE[tier] };
}

interface Props {
  source?: string | null;
  /** show the tier descriptor after the provider, e.g. "UCDP · casualty-verified" */
  showLabel?: boolean;
  /** total distinct corroborating sources for the incident; renders "+N" when >1 */
  count?: number;
  className?: string;
}

/** Compact provenance pill: colored dot + provider (+ optional tier label / corroboration count). */
export function SourceBadge({ source, showLabel = true, count, className = "" }: Props) {
  const { provider, style } = getSourceMeta(source);
  const extra = count && count > 1 ? count - 1 : 0;
  return (
    <span
      title={
        extra
          ? `${provider} · ${style.desc} · corroborated by ${count} sources`
          : `${provider} · ${style.desc}`
      }
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] font-medium leading-none tracking-wide ${className}`}
      style={{ background: style.bg, borderColor: style.color + "40", color: style.color }}
    >
      <span
        className="h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ background: style.color }}
      />
      <span className="uppercase">{provider}</span>
      {showLabel && (
        <span className="font-normal normal-case opacity-80">· {style.label}</span>
      )}
      {extra > 0 && (
        <span className="font-normal normal-case opacity-90">+{extra}</span>
      )}
    </span>
  );
}

const CONFIDENCE_COLOR: Record<Confidence, string> = {
  high: "#34d399",
  medium: "#fbbf24",
  low: "#fb7185",
};

/** Small confidence dot + label for category_confidence (high/medium/low). */
export function ConfidenceBadge({
  confidence,
  className = "",
}: {
  confidence?: Confidence | null;
  className?: string;
}) {
  if (!confidence) return null;
  const color = CONFIDENCE_COLOR[confidence] ?? "#94a3b8";
  return (
    <span
      title={`Category confidence: ${confidence}`}
      className={`inline-flex items-center gap-1.5 font-mono text-[10px] font-medium tracking-wide text-text-dim ${className}`}
    >
      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color }} />
      {confidence} confidence
    </span>
  );
}
