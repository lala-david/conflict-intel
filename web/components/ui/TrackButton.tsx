"use client";

import { useWatchlist, type TrackType } from "@/lib/useWatchlist";
import { Plus, Check } from "lucide-react";

interface Props {
  type: TrackType;
  value: string;
  className?: string;
  /** Icon-forward compact button, sized to sit inside dense list rows. */
  compact?: boolean;
}

/** Add/remove an entity (country, category, org) to the analyst's watchlist. */
export function TrackButton({ type, value, className = "", compact = false }: Props) {
  const { isTracked, toggle, ready } = useWatchlist();
  const tracked = ready && isTracked(type, value);

  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-md border font-semibold uppercase tracking-wider transition select-none";
  const size = compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs";
  const state = tracked
    ? "border-accent bg-accent/15 text-accent hover:bg-accent/25"
    : "border-border bg-surface-2 text-text-primary hover:border-accent hover:text-accent";

  return (
    <button
      type="button"
      aria-pressed={tracked}
      title={tracked ? `Tracking ${value}` : `Track ${value}`}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle(type, value);
      }}
      className={`${base} ${size} ${state} ${className}`}
    >
      {tracked ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
      {tracked ? "Tracking" : "Track"}
    </button>
  );
}
