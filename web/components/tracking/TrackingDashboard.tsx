"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useWatchlist, type TrackItem } from "@/lib/useWatchlist";
import { getCategoryMeta, formatNumber, formatDate } from "@/lib/utils";
import { X, Bell } from "lucide-react";

interface Ev {
  id: string;
  date: string;
  actor1: string;
  actor2: string;
  country: string;
  location: string;
  fatalities: number;
  category: string;
}

function labelFor(item: TrackItem) {
  if (item.type === "category") return getCategoryMeta(item.value).label;
  return item.value;
}

export function TrackingDashboard() {
  const { items, ready, remove } = useWatchlist();
  const [events, setEvents] = useState<Ev[]>([]);
  const [loading, setLoading] = useState(false);

  const key = items.map((i) => `${i.type}:${i.value}`).sort().join("|");

  useEffect(() => {
    if (!ready || items.length === 0) {
      setEvents([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      const results = await Promise.all(
        items.map(async (i) => {
          const p = new URLSearchParams({ limit: "15" });
          if (i.type === "country") p.set("country", i.value);
          if (i.type === "category") p.set("category", i.value);
          if (i.type === "org") p.set("actor", i.value);
          try {
            const r = await fetch(`/api/events?${p.toString()}`);
            if (!r.ok) return [] as Ev[];
            const d = await r.json();
            return (d.events ?? []) as Ev[];
          } catch {
            return [] as Ev[];
          }
        }),
      );
      if (cancelled) return;
      const seen = new Set<string>();
      const merged = results
        .flat()
        .filter((e) => (seen.has(e.id) ? false : (seen.add(e.id), true)))
        .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : b.fatalities - a.fatalities))
        .slice(0, 60);
      setEvents(merged);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ready]);

  if (!ready) return null;

  if (items.length === 0) {
    return (
      <div className="mt-10 rounded-lg border border-dashed border-border bg-surface p-10 text-center">
        <Bell className="mx-auto h-6 w-6 text-text-dim" />
        <h2 className="mt-4 font-display text-2xl font-semibold">Your watchlist is empty</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-text-dim">
          Track the countries and categories you follow, then see everything new in
          one place. Start from any country or category page.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link
            href="/countries"
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
          >
            Browse countries
          </Link>
          <Link
            href="/categories"
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-2"
          >
            Browse categories
          </Link>
        </div>
      </div>
    );
  }

  const totalFatalities = events.reduce((s, e) => s + (e.fatalities || 0), 0);

  return (
    <div className="mt-8">
      {/* Watchlist chips */}
      <div className="flex flex-wrap items-center gap-2">
        {items.map((i) => (
          <span
            key={`${i.type}:${i.value}`}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-xs"
          >
            <span className="font-medium text-text-primary">{labelFor(i)}</span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
              {i.type}
            </span>
            <button
              type="button"
              aria-label={`Stop tracking ${labelFor(i)}`}
              onClick={() => remove(i.type, i.value)}
              className="text-text-dim transition hover:text-accent"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ))}
      </div>

      {/* Summary */}
      <dl className="mt-8 grid grid-cols-3 gap-y-6 border-y border-border py-6">
        <Figure value={String(items.length)} label="Tracked" />
        <Figure value={formatNumber(events.length)} label="Recent events" />
        <Figure value={formatNumber(totalFatalities)} label="Fatalities" accent />
      </dl>

      {/* Merged feed */}
      <h2 className="mt-8 mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
        Latest across your watchlist
      </h2>
      {loading && events.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface px-5 py-12 text-center text-sm text-text-dim">
          Loading…
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-surface">
          {events.map((e) => {
            const meta = getCategoryMeta(e.category);
            return (
              <Link
                key={e.id}
                href={`/events/${encodeURIComponent(e.id)}`}
                className="group flex items-start justify-between gap-4 border-b border-border px-5 py-4 transition last:border-b-0 hover:bg-surface-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span
                      className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white"
                      style={{ background: meta.color }}
                    >
                      {meta.label}
                    </span>
                    <span className="font-mono text-text-dim">{formatDate(e.date)}</span>
                    <span className="text-text-dim">· {e.country}</span>
                  </div>
                  <div className="mt-2 truncate text-sm font-medium text-text-primary group-hover:text-accent">
                    {e.actor1 || "Unknown"}
                    {e.actor2 && e.actor2 !== "Civilians" && (
                      <span className="text-text-dim"> vs {e.actor2}</span>
                    )}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="font-display text-2xl font-semibold tabular-nums leading-none">
                    {formatNumber(e.fatalities)}
                  </div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-text-dim">
                    killed
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Figure({ value, label, accent = false }: { value: string; label: string; accent?: boolean }) {
  return (
    <div>
      <dd
        className={`font-display text-3xl font-semibold tabular-nums leading-none ${
          accent ? "text-accent" : "text-text-primary"
        }`}
      >
        {value}
      </dd>
      <dt className="mt-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-dim">
        {label}
      </dt>
    </div>
  );
}
