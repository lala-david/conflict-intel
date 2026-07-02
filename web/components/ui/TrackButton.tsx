"use client";

import { useWatchlist, type TrackType } from "@/lib/useWatchlist";
import { Plus, Check } from "lucide-react";

interface Props {
  type: TrackType;
  value: string;
  className?: string;
}

/** Add/remove an entity (country, category) to the analyst's watchlist. */
export function TrackButton({ type, value, className = "" }: Props) {
  const { isTracked, toggle, ready } = useWatchlist();
  const tracked = ready && isTracked(type, value);

  return (
    <button
      type="button"
      aria-pressed={tracked}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle(type, value);
      }}
      className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition ${
        tracked
          ? "border-accent bg-accent/10 text-accent"
          : "border-border text-text-dim hover:border-text-dim hover:text-text-primary"
      } ${className}`}
    >
      {tracked ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
      {tracked ? "Tracking" : "Track"}
    </button>
  );
}
