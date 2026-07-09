"use client";

import { motion, type Variants } from "framer-motion";
import { CountUp } from "@/components/home/CountUp";

interface Props {
  totals: { events: number; fatalities: number; countries: number };
}

const EASE = [0.16, 1, 0.3, 1] as const;

const item: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

/**
 * The since-1970 monument + supporting figures. Formerly the whole hero; now
 * folded below THE WIRE stage (see components/home/TheWire.tsx). Rendered inside
 * TheWire's staggered container, so it animates in with the rest of the hero.
 */
export function HeroFigures({ totals }: Props) {
  const years = new Date().getFullYear() - 1970 + 1;

  return (
    <>
      {/* The monument — human cost, given gravity */}
      <motion.div
        variants={item}
        className="mt-12 border-t border-border pt-9 md:mt-14 md:pt-10"
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
          Every unit is a human life ended — a person, a family, a town changed
          forever. Counted here one event at a time.
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
    </>
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
