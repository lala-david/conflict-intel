"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, CornerDownLeft } from "lucide-react";
import { isoFor } from "@/lib/country-iso";
import { slugify } from "@/lib/utils";
import { Flag } from "@/components/ui/Flag";

type Item = {
  label: string;
  sub?: string;
  href: string;
  group: "Go to" | "Countries" | "Organizations" | "Pages";
  iso?: string;
};

const PAGES: Item[] = [
  { label: "Tracking", href: "/tracking", group: "Pages" },
  { label: "Events", href: "/events", group: "Pages" },
  { label: "Countries", href: "/countries", group: "Pages" },
  { label: "Organizations", href: "/organizations", group: "Pages" },
  { label: "Categories", href: "/categories", group: "Pages" },
  { label: "Wallets", href: "/wallets", group: "Pages" },
  { label: "Daily brief", href: "/brief", group: "Pages" },
  { label: "Weekly recaps", href: "/weekly", group: "Pages" },
  { label: "Data download", href: "/data", group: "Pages" },
  { label: "API docs", href: "/api-docs", group: "Pages" },
  { label: "Methodology", href: "/about/methodology", group: "Pages" },
];

// Fetched once per session and reused across opens.
let _indexCache: Item[] | null = null;

async function loadIndex(): Promise<Item[]> {
  if (_indexCache) return _indexCache;
  const [c, o] = await Promise.all([
    fetch("/api/countries").then((r) => r.json()).catch(() => ({ countries: [] })),
    fetch("/api/orgs?limit=300").then((r) => r.json()).catch(() => ({ organizations: [] })),
  ]);
  const countries: Item[] = (c.countries ?? []).map((x: any) => ({
    label: x.country,
    sub: `${(x.total_fatalities ?? 0).toLocaleString()} fatalities`,
    href: `/countries/${isoFor(x.country)}`,
    group: "Countries" as const,
    iso: isoFor(x.country),
  }));
  const orgs: Item[] = (o.organizations ?? []).map((x: any) => ({
    label: x.name,
    sub: `${(x.total_events ?? 0).toLocaleString()} events`,
    href: `/organizations/${slugify(x.name)}`,
    group: "Organizations" as const,
  }));
  _indexCache = [...countries, ...orgs];
  return _indexCache;
}

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [index, setIndex] = useState<Item[]>([]);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      loadIndex().then(setIndex);
      // focus after paint
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    const items: Item[] = [];
    if (query) {
      items.push({
        label: `Search all events for “${q.trim()}”`,
        href: `/search?q=${encodeURIComponent(q.trim())}`,
        group: "Go to",
      });
    }
    const pool = [...PAGES, ...index];
    const matched = query
      ? pool.filter((i) => i.label.toLowerCase().includes(query))
      : PAGES;
    // cap per group so the list stays scannable
    const caps: Record<string, number> = { Pages: 8, Countries: 6, Organizations: 6 };
    const seen: Record<string, number> = {};
    for (const i of matched) {
      seen[i.group] = (seen[i.group] ?? 0) + 1;
      if (seen[i.group] <= (caps[i.group] ?? 99)) items.push(i);
    }
    return items;
  }, [q, index]);

  useEffect(() => {
    if (active >= results.length) setActive(Math.max(0, results.length - 1));
  }, [results.length, active]);

  const go = useCallback(
    (item?: Item) => {
      const target = item ?? results[active];
      if (!target) return;
      onClose();
      router.push(target.href);
    },
    [results, active, onClose, router]
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go();
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  // keep the active row in view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center bg-background/70 px-4 pt-[12vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search className="h-4 w-4 shrink-0 text-text-dim" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
            }}
            placeholder="Search countries, organizations, pages…"
            className="w-full bg-transparent py-3.5 text-sm text-text-primary placeholder:text-text-dim focus:outline-none"
          />
          <kbd className="hidden shrink-0 rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-text-dim sm:block">
            ESC
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[52vh] overflow-y-auto py-2">
          {results.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-text-dim">
              No matches for “{q}”.
            </div>
          )}
          {results.map((item, i) => {
            const prev = results[i - 1];
            const showGroup = !prev || prev.group !== item.group;
            return (
              <div key={`${item.href}-${i}`}>
                {showGroup && (
                  <div className="px-4 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-text-dim">
                    {item.group}
                  </div>
                )}
                <button
                  data-idx={i}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(item)}
                  className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition ${
                    i === active ? "bg-surface-2 text-text-primary" : "text-text-dim"
                  }`}
                >
                  {item.iso ? (
                    <Flag iso={item.iso} size="sm" />
                  ) : (
                    <span className="h-2 w-2 shrink-0 rounded-full bg-border" />
                  )}
                  <span className="min-w-0 flex-1 truncate text-text-primary">
                    {item.label}
                  </span>
                  {item.sub && (
                    <span className="shrink-0 font-mono text-[11px] text-text-dim">
                      {item.sub}
                    </span>
                  )}
                  {i === active && (
                    <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-text-dim" />
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t border-border px-4 py-2 text-[10px] text-text-dim">
          <span className="font-mono">↑↓ navigate · ↵ open · esc close</span>
          <span>Conflict &amp; Security Intelligence</span>
        </div>
      </div>
    </div>
  );
}
