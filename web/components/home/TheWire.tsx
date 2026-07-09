"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import { ShaderBackdrop } from "@/components/ui/ShaderBackdrop";
import { ThreatGlobe } from "@/components/ui/ThreatGlobe";
import { HeroFigures } from "@/components/home/HeroStats";
import { getCategoryMeta, formatDateShort, formatNumber } from "@/lib/utils";
import type { WireEvent } from "@/lib/queries-wire";

// Client-side mirror of WIRE_WINDOW_SECONDS. Imported constants would pull the
// server-only db module into the client bundle, so we recompute it locally.
const WINDOW_SECONDS = 90 * 24 * 60 * 60;

const EASE = [0.16, 1, 0.3, 1] as const;

interface Props {
  events: WireEvent[];
  fatalities90d: number;
  totals: { events: number; fatalities: number; countries: number };
}

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.04 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

export function TheWire({ events, fatalities90d, totals }: Props) {
  const reduced = useReducedMotion() ?? false;
  const ratePerSecond = fatalities90d > 0 ? fatalities90d / WINDOW_SECONDS : 0;

  return (
    <header className="relative isolate overflow-hidden border-b border-border">
      <ShaderBackdrop />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto max-w-7xl px-5 pt-14 pb-10 sm:px-6 md:pt-20 md:pb-14"
      >
        {/* Kicker */}
        <motion.div
          variants={item}
          className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-accent sm:text-[11px] sm:tracking-[0.25em]"
        >
          <span>Global Conflict Monitor</span>
          <span className="h-px flex-1 bg-border" aria-hidden />
          <span className="inline-flex items-center gap-1.5 font-mono tracking-[0.2em] text-text-dim">
            <LiveDot reduced={reduced} /> Live wire
          </span>
        </motion.div>

        {/* Masthead */}
        <motion.h1
          variants={item}
          className="mt-6 max-w-4xl font-display text-[2rem] font-semibold leading-[1.05] tracking-tight text-text-primary sm:text-5xl md:text-6xl lg:text-7xl"
        >
          Track the conflicts{" "}
          <span className="italic text-text-dim">you follow.</span>
        </motion.h1>
        <motion.p
          variants={item}
          className="mt-5 max-w-xl text-base leading-relaxed text-text-dim"
        >
          One live feed of global organized violence. Follow the countries and
          topics that matter — see everything new in one place.
        </motion.p>
        <motion.div
          variants={item}
          className="mt-7 flex flex-wrap items-center gap-3"
        >
          <Link
            href="/tracking"
            className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent/90"
          >
            Start tracking →
          </Link>
          <Link
            href="/events"
            className="rounded-md border border-border px-5 py-2.5 text-sm font-medium text-text-primary transition hover:bg-surface-2"
          >
            Browse events
          </Link>
        </motion.div>

        {/* THE WIRE stage: rotating globe + streaming incident ticker */}
        <motion.div
          variants={item}
          className="mt-10 grid items-center gap-8 md:mt-14 lg:grid-cols-[1fr_0.82fr] lg:gap-12"
        >
          {/* Signature focal visual */}
          <div className="relative flex justify-center">
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "radial-gradient(58% 58% at 50% 46%, rgba(239,68,68,0.20), transparent 62%)",
              }}
              aria-hidden
            />
            <ThreatGlobe className="max-w-[440px] drop-shadow-[0_0_70px_rgba(239,68,68,0.22)]" />
          </div>

          <WireTicker events={events} reduced={reduced} />
        </motion.div>

        {/* The emotional core — the live rising death counter */}
        <motion.div variants={item}>
          <DeathCounter ratePerSecond={ratePerSecond} reduced={reduced} />
        </motion.div>

        {/* Folded monument + supporting figures (from the former HeroStats) */}
        <HeroFigures totals={totals} />
      </motion.div>
    </header>
  );
}

/* ── Live status dot ─────────────────────────────────────────────────────── */
function LiveDot({ reduced }: { reduced: boolean }) {
  return (
    <span className="relative inline-flex h-1.5 w-1.5">
      {!reduced && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
      )}
      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
    </span>
  );
}

/* ── Live death counter — the memorial's beating heart ───────────────────── */
function DeathCounter({
  ratePerSecond,
  reduced,
}: {
  ratePerSecond: number;
  reduced: boolean;
}) {
  const [count, setCount] = useState(0);
  const barRef = useRef<HTMLSpanElement>(null);

  const perHour = Math.round(ratePerSecond * 3600);
  const perDay = Math.round(ratePerSecond * 86400);

  useEffect(() => {
    if (reduced || ratePerSecond <= 0) return;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const exact = ((now - start) / 1000) * ratePerSecond;
      const whole = Math.floor(exact);
      // setState bails out (no re-render) while the integer is unchanged.
      setCount((c) => (c === whole ? c : whole));
      // Progress toward the next life lost — updated per-frame without re-render.
      if (barRef.current) {
        barRef.current.style.transform = `scaleX(${exact - whole})`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [ratePerSecond, reduced]);

  return (
    <section className="mt-12 border-t border-border pt-9 md:mt-16 md:pt-10">
      {/* One grave line, in Fraunces */}
      <p className="font-display text-lg italic leading-snug text-text-dim sm:text-xl">
        The killing does not pause while you read this.
      </p>

      {reduced ? (
        <>
          <div className="mt-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-accent sm:text-[11px]">
            In an average hour of organized violence
          </div>
          <div className="mt-3 font-display text-6xl font-semibold leading-[0.95] tracking-tight text-text-primary tabular-nums sm:text-7xl md:text-8xl">
            {perHour.toLocaleString("en-US")}
          </div>
          <p className="mt-4 max-w-xl text-sm leading-relaxed text-text-dim">
            people are killed, on average — roughly{" "}
            <span className="font-mono text-text-primary">
              {perDay.toLocaleString("en-US")}
            </span>{" "}
            every day, derived from the last 90 days of recorded fatalities.
          </p>
        </>
      ) : (
        <>
          <div className="mt-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-accent sm:text-[11px]">
            Since you opened this page
          </div>
          <div className="mt-3 flex items-baseline gap-3">
            <span className="font-display text-6xl font-semibold leading-[0.95] tracking-tight text-text-primary tabular-nums sm:text-7xl md:text-8xl">
              ~{count.toLocaleString("en-US")}
            </span>
          </div>
          {/* Hairline: progress toward the next life lost */}
          <div className="mt-4 h-px w-full max-w-md overflow-hidden bg-border">
            <span
              ref={barRef}
              className="block h-full w-full origin-left bg-accent"
              style={{ transform: "scaleX(0)" }}
              aria-hidden
            />
          </div>
          <p className="mt-4 max-w-xl text-sm leading-relaxed text-text-dim">
            people have been killed in organized violence — at the current global
            rate of{" "}
            <span className="font-mono text-text-primary">
              {perDay.toLocaleString("en-US")}
            </span>{" "}
            a day. Each number was a life.
          </p>
        </>
      )}
    </section>
  );
}

/* ── Live incident ticker — recent events "arrive" one at a time ─────────── */
const TICKER_MAX = 7;
const TICKER_INTERVAL_MS = 2600;

function WireTicker({
  events,
  reduced,
}: {
  events: WireEvent[];
  reduced: boolean;
}) {
  // Reduced motion → final state: the full (capped) list, no streaming.
  const seed = reduced ? Math.min(events.length, TICKER_MAX) : Math.min(events.length, 2);

  const [feed, setFeed] = useState<{ key: number; e: WireEvent }[]>(() =>
    events.slice(0, seed).map((e, i) => ({ key: i, e }))
  );
  const idxRef = useRef(seed);
  const keyRef = useRef(seed);

  useEffect(() => {
    if (reduced || events.length === 0) return;
    const id = setInterval(() => {
      const e = events[idxRef.current % events.length];
      idxRef.current += 1;
      const key = keyRef.current++;
      setFeed((prev) => [{ key, e }, ...prev].slice(0, TICKER_MAX));
    }, TICKER_INTERVAL_MS);
    return () => clearInterval(id);
  }, [events, reduced]);

  return (
    <div className="rounded-xl border border-border bg-surface/70 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="inline-flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-text-primary">
          <LiveDot reduced={reduced} />
          The wire
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-text-dim">
          Incoming
        </span>
      </div>

      <div className="relative h-[300px] overflow-hidden px-2 py-2">
        <ul className="flex flex-col gap-0.5">
          <AnimatePresence initial={false} mode="popLayout">
            {feed.map(({ key, e }) => {
              const meta = getCategoryMeta(e.category);
              return (
                <motion.li
                  key={key}
                  layout={!reduced}
                  initial={reduced ? false : { opacity: 0, y: -14 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduced ? undefined : { opacity: 0 }}
                  transition={{ duration: 0.45, ease: EASE }}
                  className="flex items-center gap-2.5 rounded-md px-2 py-2"
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ background: meta.color }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1 truncate text-[13px] text-text-dim">
                    <span className="font-mono text-text-dim">
                      {formatDateShort(e.date)}
                    </span>
                    <span className="mx-1.5 text-border">·</span>
                    <span className="text-text-primary">{e.country || "—"}</span>
                  </span>
                  <span className="shrink-0 font-mono text-[13px] tabular-nums text-text-primary">
                    {formatNumber(e.fatalities)}
                    <span className="ml-1 text-[10px] uppercase tracking-wider text-text-dim">
                      killed
                    </span>
                  </span>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>

        {/* fade the stream out at the bottom */}
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-surface to-transparent"
          aria-hidden
        />
      </div>
    </div>
  );
}
