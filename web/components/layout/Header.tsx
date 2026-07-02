"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X, Search } from "lucide-react";

const NAV_ITEMS = [
  { href: "/tracking", label: "Tracking" },
  { href: "/events", label: "Events" },
  { href: "/countries", label: "Countries" },
  { href: "/organizations", label: "Organizations" },
  { href: "/categories", label: "Categories" },
  { href: "/brief", label: "Brief" },
];

export function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-t-2 border-accent border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">
        <Link href="/" className="group flex items-baseline gap-2.5">
          <span className="font-display text-xl font-bold leading-none tracking-tight text-text-primary">
            Conflict <span className="text-accent">&amp;</span> Security Intelligence
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-6 text-[13px] font-medium uppercase tracking-wide md:flex">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-text-dim transition hover:text-text-primary"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {/* Search button */}
          <Link
            href="/search"
            className="rounded-md p-2 text-text-dim transition hover:bg-surface-2 hover:text-text-primary"
            title="Search"
          >
            <Search className="h-4 w-4" />
          </Link>

          <a
            href="https://t.me/ThreatPulse"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary transition hover:bg-surface-2 md:block"
          >
            Subscribe
          </a>

          {/* Mobile hamburger */}
          <button
            onClick={() => setOpen(!open)}
            className="rounded-md p-1.5 text-text-dim hover:text-text-primary md:hidden"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="border-t border-border bg-background px-6 py-4 md:hidden">
          <nav className="flex flex-col gap-3">
            <Link
              href="/search"
              onClick={() => setOpen(false)}
              className="text-sm font-medium text-text-primary"
            >
              Search
            </Link>
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="text-sm text-text-dim transition hover:text-text-primary"
              >
                {item.label}
              </Link>
            ))}
            <a
              href="https://t.me/ThreatPulse"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 rounded-md bg-accent px-3 py-2 text-center text-xs font-medium text-white"
            >
              Subscribe on Telegram
            </a>
          </nav>
        </div>
      )}
    </header>
  );
}
