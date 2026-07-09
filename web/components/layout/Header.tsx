"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X, Search } from "lucide-react";
import { CommandPalette } from "@/components/ui/CommandPalette";

const NAV_ITEMS = [
  { href: "/tracking", label: "Tracking" },
  { href: "/events", label: "Events" },
  { href: "/countries", label: "Countries" },
  { href: "/organizations", label: "Organizations" },
  { href: "/categories", label: "Categories" },
  { href: "/wallets", label: "Wallets" },
  { href: "/brief", label: "Brief" },
];

export function Header() {
  const [open, setOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  // ⌘K / Ctrl+K opens the command palette (unless typing in a field).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-t-2 border-accent border-b border-border bg-background/85 backdrop-blur-md">
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-5 py-3.5 sm:px-6">
        <Link href="/" className="group flex min-w-0 items-baseline gap-2.5">
          <span className="truncate font-display text-[15px] font-bold leading-none tracking-tight text-text-primary sm:text-lg md:text-xl">
            Conflict <span className="text-accent">&amp;</span> Security{" "}
            <span className="hidden sm:inline">Intelligence</span>
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
          {/* Command palette (⌘K) */}
          <button
            onClick={() => setPaletteOpen(true)}
            className="flex items-center gap-2 rounded-md border border-border bg-surface/60 px-2.5 py-1.5 text-text-dim transition hover:bg-surface-2 hover:text-text-primary"
            title="Search (⌘K)"
          >
            <Search className="h-4 w-4" />
            <span className="hidden font-mono text-[11px] lg:inline">⌘K</span>
          </button>

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
            <button
              onClick={() => {
                setOpen(false);
                setPaletteOpen(true);
              }}
              className="flex items-center gap-2 text-left text-sm font-medium text-text-primary"
            >
              <Search className="h-4 w-4" /> Search
            </button>
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
