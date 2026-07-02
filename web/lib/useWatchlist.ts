"use client";

import { useCallback, useEffect, useState } from "react";

export type TrackType = "country" | "category" | "org";
export interface TrackItem {
  type: TrackType;
  value: string;
}

const KEY = "csi:watchlist:v1";
const EVT = "csi:watchlist:change";

function read(): TrackItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(items: TrackItem[]) {
  localStorage.setItem(KEY, JSON.stringify(items));
  window.dispatchEvent(new Event(EVT));
}

/**
 * Client-side watchlist for the tracking solution — persisted in localStorage,
 * synced across components/tabs. No account required (zero-friction v1).
 */
export function useWatchlist() {
  const [items, setItems] = useState<TrackItem[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setItems(read());
    setReady(true);
    const handler = () => setItems(read());
    window.addEventListener(EVT, handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener(EVT, handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  const isTracked = useCallback(
    (type: TrackType, value: string) =>
      items.some((i) => i.type === type && i.value === value),
    [items],
  );

  const toggle = useCallback((type: TrackType, value: string) => {
    const cur = read();
    const exists = cur.some((i) => i.type === type && i.value === value);
    write(
      exists
        ? cur.filter((i) => !(i.type === type && i.value === value))
        : [...cur, { type, value }],
    );
  }, []);

  const remove = useCallback((type: TrackType, value: string) => {
    write(read().filter((i) => !(i.type === type && i.value === value)));
  }, []);

  return { items, ready, isTracked, toggle, remove };
}
