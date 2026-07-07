/**
 * Shared UI utilities
 */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Category } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return "0";
  return n.toLocaleString("en-US");
}

export function formatDate(date: string): string {
  if (!date || date.length < 10) return date || "";
  const d = new Date(date);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Clean an event's raw notes for display: strip source URLs, Telegram links,
 * promo tails ("Follow @x", "for more news"), and de-dupe repeated segments.
 * Source data (esp. UCDP citations + Telegram) carries this cruft.
 */
export function cleanNote(s?: string | null): string {
  if (!s) return "";
  let t = s
    .replace(/https?:\/\/\S+/gi, " ")
    .replace(/\bt\.me\/\S+/gi, " ")
    .replace(/\b(?:follow|subscribe(?:\s+to)?|join)\s+@?[\w.]+(?:\s+(?:for\s+more|channel|news)[^.;|·]*)?/gi, " ")
    .replace(/\bfor more (?:news|updates|info)\b/gi, " ")
    .replace(/\b(?:READ|NEW|BREAKING|WATCH|VIDEO)\s*:\s*/gi, " ")
    .replace(/@[\w.]+/g, " ")
    .replace(/\s*[|;]\s*/g, " · ")
    .replace(/\bINCIDENT\s*#\d+\b/gi, " ")
    .replace(/\s{2,}/g, " ")
    .replace(/(^[\s·|;,–—-]+)|([\s·|;,–—-]+$)/g, "")
    .trim();
  // de-dupe repeated " · " segments (source data often concatenates duplicates)
  const seen = new Set<string>();
  t = t
    .split(" · ")
    .map((x) => x.trim())
    .filter((x) => x && !seen.has(x.toLowerCase()) && seen.add(x.toLowerCase()))
    .join(" · ");
  return t;
}

export function formatDateShort(date: string): string {
  if (!date || date.length < 10) return date || "";
  const d = new Date(date);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export const CATEGORY_META: Record<
  Category,
  { label: string; color: string; description: string; emoji: string }
> = {
  war: {
    label: "War",
    color: "#991b1b",
    description: "Interstate armed conflict",
    emoji: "🪖",
  },
  civil_war: {
    label: "Civil War",
    color: "#dc2626",
    description: "Intrastate armed conflict",
    emoji: "⚔️",
  },
  terrorism: {
    label: "Terrorism",
    color: "#6d28d9",
    description: "Designated terror group vs civilians",
    emoji: "💣",
  },
  mass_atrocity: {
    label: "Mass Atrocity",
    color: "#7f1d1d",
    description: "State mass killing",
    emoji: "⚠️",
  },
  state_violence: {
    label: "State Violence",
    color: "#db2777",
    description: "Government vs civilians",
    emoji: "🚨",
  },
  cartel_violence: {
    label: "Cartel Violence",
    color: "#d97706",
    description: "Organized crime conflict",
    emoji: "🔫",
  },
  communal_violence: {
    label: "Communal Violence",
    color: "#0d9488",
    description: "Ethnic/sectarian conflict",
    emoji: "👥",
  },
  insurgency: {
    label: "Insurgency",
    color: "#2563eb",
    description: "Non-state vs government",
    emoji: "🎯",
  },
  counterterrorism: {
    label: "Counterterrorism",
    color: "#16a34a",
    description: "Government CT operation",
    emoji: "🛡️",
  },
  armed_violence: {
    label: "Armed Violence",
    color: "#475569",
    description: "Other non-state violence",
    emoji: "⚡",
  },
};

export function getCategoryMeta(cat: string | null) {
  if (!cat) return CATEGORY_META.armed_violence;
  return CATEGORY_META[cat as Category] ?? CATEGORY_META.armed_violence;
}

export function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function findBySlug<T extends { name: string }>(
  items: T[],
  slug: string
): T | undefined {
  return items.find((item) => slugify(item.name) === slug);
}
