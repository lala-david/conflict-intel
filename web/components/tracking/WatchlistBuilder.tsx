"use client";

import { useMemo, useState } from "react";
import { useWatchlist, type TrackType } from "@/lib/useWatchlist";
import { CATEGORY_META } from "@/lib/utils";
import { Search, Plus, Check } from "lucide-react";

interface Option {
  type: TrackType;
  value: string;
  label: string;
}

const TYPE_LABEL: Record<TrackType, string> = {
  country: "Country",
  category: "Category",
  org: "Organization",
};

/** Hand-picked starting points so a first-timer gets value in one click. */
const POPULAR: Option[] = [
  { type: "country", value: "Ukraine", label: "Ukraine" },
  { type: "country", value: "Syria", label: "Syria" },
  { type: "country", value: "Nigeria", label: "Nigeria" },
  { type: "country", value: "Israel", label: "Israel" },
  { type: "country", value: "Sudan", label: "Sudan" },
  { type: "category", value: "terrorism", label: "Terrorism" },
  { type: "category", value: "war", label: "War" },
  { type: "category", value: "civil_war", label: "Civil War" },
];

interface Props {
  countries: string[];
  orgs: string[];
  /** Rendered inside a card already (empty state) vs. standalone (add-more). */
  bare?: boolean;
}

export function WatchlistBuilder({ countries, orgs, bare = false }: Props) {
  const { isTracked, toggle, ready } = useWatchlist();
  const [q, setQ] = useState("");

  const options = useMemo<Option[]>(() => {
    const cats = (Object.keys(CATEGORY_META) as (keyof typeof CATEGORY_META)[]).map(
      (k): Option => ({ type: "category", value: k, label: CATEGORY_META[k].label }),
    );
    const cs = countries.map((c): Option => ({ type: "country", value: c, label: c }));
    const os = orgs.map((o): Option => ({ type: "org", value: o, label: o }));
    return [...cs, ...cats, ...os];
  }, [countries, orgs]);

  const results = useMemo<Option[]>(() => {
    const term = q.trim().toLowerCase();
    if (!term) return [];
    const starts: Option[] = [];
    const contains: Option[] = [];
    for (const o of options) {
      const l = o.label.toLowerCase();
      if (l.startsWith(term)) starts.push(o);
      else if (l.includes(term)) contains.push(o);
      if (starts.length + contains.length > 60) break;
    }
    return [...starts, ...contains].slice(0, 24);
  }, [q, options]);

  const inner = (
    <>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search countries, categories, organizations…"
          className="w-full rounded-md border border-border bg-surface-2 py-2.5 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-dim focus:border-accent focus:outline-none"
        />
      </div>

      {q.trim() ? (
        <div className="mt-3 max-h-80 overflow-y-auto rounded-md border border-border bg-surface">
          {results.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-text-dim">
              No matches for “{q.trim()}”.
            </div>
          ) : (
            results.map((o) => {
              const tracked = ready && isTracked(o.type, o.value);
              return (
                <button
                  key={`${o.type}:${o.value}`}
                  type="button"
                  onClick={() => toggle(o.type, o.value)}
                  className="flex w-full items-center justify-between gap-3 border-b border-border px-4 py-2.5 text-left transition last:border-b-0 hover:bg-surface-2"
                >
                  <span className="min-w-0 flex-1">
                    <span className="truncate text-sm font-medium text-text-primary">
                      {o.label}
                    </span>
                    <span className="ml-2 font-mono text-[10px] uppercase tracking-wider text-text-dim">
                      {TYPE_LABEL[o.type]}
                    </span>
                  </span>
                  <span
                    className={`inline-flex shrink-0 items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-semibold uppercase tracking-wider transition ${
                      tracked
                        ? "border-accent bg-accent/15 text-accent"
                        : "border-border bg-surface-2 text-text-primary"
                    }`}
                  >
                    {tracked ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                    {tracked ? "Tracking" : "Track"}
                  </span>
                </button>
              );
            })
          )}
        </div>
      ) : (
        <div className="mt-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-dim">
            Popular to track
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {POPULAR.map((o) => {
              const tracked = ready && isTracked(o.type, o.value);
              return (
                <button
                  key={`${o.type}:${o.value}`}
                  type="button"
                  onClick={() => toggle(o.type, o.value)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                    tracked
                      ? "border-accent bg-accent/15 text-accent"
                      : "border-border bg-surface-2 text-text-primary hover:border-accent hover:text-accent"
                  }`}
                >
                  {tracked ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                  {o.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );

  if (bare) return inner;

  return (
    <div className="rounded-lg border border-border bg-surface p-5">{inner}</div>
  );
}
