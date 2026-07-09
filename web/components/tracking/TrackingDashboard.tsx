"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useWatchlist, type TrackItem } from "@/lib/useWatchlist";
import { getCategoryMeta, formatNumber, formatDate } from "@/lib/utils";
import { X, Plus, ChevronDown } from "lucide-react";
import { WatchlistBuilder } from "@/components/tracking/WatchlistBuilder";

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

interface Props {
  countries: string[];
  orgs: string[];
}

export function TrackingDashboard({ countries, orgs }: Props) {
  const { items, ready, remove } = useWatchlist();
  const [events, setEvents] = useState<Ev[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

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
      <div className="mt-10">
        <div className="mb-4">
          <h2 className="font-display text-2xl font-semibold">Build your watchlist</h2>
          <p className="mt-2 max-w-lg text-sm text-text-dim">
            Add the countries, categories and armed groups you follow — then see
            everything new across them in one feed. Start with a popular pick or search
            below. Saved on this device; no account needed.
          </p>
        </div>
        <WatchlistBuilder countries={countries} orgs={orgs} />
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
        <button
          type="button"
          aria-expanded={showAdd}
          onClick={() => setShowAdd((v) => !v)}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
            showAdd
              ? "border-accent bg-accent/15 text-accent"
              : "border-border bg-surface-2 text-text-primary hover:border-accent hover:text-accent"
          }`}
        >
          {showAdd ? <ChevronDown className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          Add more
        </button>
      </div>

      {showAdd && (
        <div className="mt-4">
          <WatchlistBuilder countries={countries} orgs={orgs} />
        </div>
      )}

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
