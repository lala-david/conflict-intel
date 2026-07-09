"use client";

import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import { ShaderBackdrop } from "@/components/ui/ShaderBackdrop";
import { ThreatGlobe } from "@/components/ui/ThreatGlobe";
import { CountUp } from "@/components/home/CountUp";

interface Props {
  totals: { events: number; fatalities: number; countries: number };
}

const EASE = [0.16, 1, 0.3, 1] as const;

const container: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.09, delayChildren: 0.04 },
  },
};

const item: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

export function HeroStats({ totals }: Props) {
  const years = new Date().getFullYear() - 1970 + 1;

  return (
    <header className="relative isolate overflow-hidden border-b border-border">
      <ShaderBackdrop />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto max-w-7xl px-5 pt-14 pb-10 sm:px-6 md:pt-20 md:pb-12"
      >
        {/* Kicker */}
        <motion.div
          variants={item}
          className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-accent sm:text-[11px] sm:tracking-[0.25em]"
        >
          <span>Global Conflict Monitor</span>
          <span className="h-px flex-1 bg-border" aria-hidden />
          <span className="font-mono tracking-[0.2em] text-text-dim">
            Updated daily
          </span>
        </motion.div>

        {/* Top band: masthead + copy on the left, rotating threat globe on the right */}
        <div className="grid items-center gap-8 md:grid-cols-[1.15fr_0.85fr] lg:gap-12">
          <div>
            {/* Masthead headline */}
            <motion.h1
              variants={item}
              className="mt-6 max-w-4xl font-display text-[2rem] font-semibold leading-[1.05] tracking-tight text-text-primary sm:text-5xl md:text-6xl lg:text-7xl"
            >
              Track the conflicts{" "}
              <span className="italic text-text-dim">you follow.</span>
            </motion.h1>

            {/* One-line value + primary actions */}
            <motion.p
              variants={item}
              className="mt-5 max-w-xl text-base leading-relaxed text-text-dim"
            >
              One live feed of global organized violence. Follow the countries
              and topics that matter — see everything new in one place.
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
          </div>

          {/* Signature focal visual — the rotating threat globe */}
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.1, ease: EASE, delay: 0.15 }}
            className="relative hidden justify-center md:flex"
          >
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "radial-gradient(60% 60% at 50% 45%, rgba(239,68,68,0.18), transparent 60%)",
              }}
              aria-hidden
            />
            <ThreatGlobe className="max-w-[440px] drop-shadow-[0_0_70px_rgba(239,68,68,0.22)]" />
          </motion.div>
        </div>

        {/* The monument — human cost, given gravity */}
        <motion.div
          variants={item}
          className="mt-12 border-t border-border pt-9 md:mt-16 md:pt-10"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-accent sm:text-[11px]">
            The human cost
          </div>
          <dd className="mt-3 font-display text-6xl font-semibold leading-[0.95] tracking-tight text-text-primary tabular-nums sm:text-7xl md:text-8xl lg:text-[8.5rem]">
            <CountUp value={totals.fatalities} />
          </dd>
          <dt className="mt-4 text-sm font-semibold uppercase tracking-[0.14em] text-text-dim sm:text-[15px]">
            Fatalities documented since 1970
          </dt>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-text-dim">
            Every unit is a human life ended — a person, a family, a town
            changed forever. Counted here one event at a time.
          </p>
        </motion.div>

        {/* Supporting figures */}
        <motion.dl
          variants={item}
          className="mt-10 grid grid-cols-3 gap-y-8 border-t border-border pt-8 md:divide-x md:divide-border"
        >
          <Figure value={totals.events} label="Events recorded" />
          <Figure value={totals.countries} label="Countries covered" />
          <Figure value={years} label="Years of history · since 1970" />
        </motion.dl>
      </motion.div>
    </header>
  );
}

function Figure({ value, label }: { value: number; label: string }) {
  return (
    <div className="md:px-6 md:first:pl-0">
      <dd className="font-display text-[1.75rem] font-semibold leading-none tabular-nums text-text-primary sm:text-4xl md:text-5xl">
        <CountUp value={value} />
      </dd>
      <dt className="mt-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-dim sm:text-[11px] sm:tracking-[0.18em]">
        {label}
      </dt>
    </div>
  );
}
