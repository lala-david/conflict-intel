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
