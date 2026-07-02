import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-border bg-surface">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid gap-8 md:grid-cols-4">
          <div>
            <h3 className="font-display text-sm font-semibold text-text-primary">
              Conflict &amp; Security Intelligence
            </h3>
            <p className="mt-2 text-xs text-text-dim">
              Track global conflict. 420K events, 38 years, 172 countries,
              categorized by academic standard.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-dim">
              Browse
            </h4>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link href="/events" className="text-text-dim hover:text-text-primary">
                  Events
                </Link>
              </li>
              <li>
                <Link href="/countries" className="text-text-dim hover:text-text-primary">
                  Countries
                </Link>
              </li>
              <li>
                <Link href="/organizations" className="text-text-dim hover:text-text-primary">
                  Organizations
                </Link>
              </li>
              <li>
                <Link href="/categories" className="text-text-dim hover:text-text-primary">
                  Categories
                </Link>
              </li>
              <li>
                <Link href="/search" className="text-text-dim hover:text-text-primary">
                  Search
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-dim">
              Reports
            </h4>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link href="/brief" className="text-text-dim hover:text-text-primary">
                  Daily briefs
                </Link>
              </li>
              <li>
                <Link href="/weekly" className="text-text-dim hover:text-text-primary">
                  Weekly recaps
                </Link>
              </li>
              <li>
                <Link href="/api-docs" className="text-text-dim hover:text-text-primary">
                  API docs
                </Link>
              </li>
              <li>
                <Link href="/data" className="text-text-dim hover:text-text-primary">
                  Data download
                </Link>
              </li>
              <li>
                <Link href="/widgets" className="text-text-dim hover:text-text-primary">
                  Embed widgets
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-dim">
              About
            </h4>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link href="/about" className="text-text-dim hover:text-text-primary">
                  About
                </Link>
              </li>
              <li>
                <Link href="/about/methodology" className="text-text-dim hover:text-text-primary">
                  Methodology
                </Link>
              </li>
              <li>
                <a
                  href="https://t.me/ThreatPulse"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-text-dim hover:text-text-primary"
                >
                  Telegram
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/lala-david/conflict-intel"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-text-dim hover:text-text-primary"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between border-t border-border pt-6 text-xs text-text-dim">
          <span>© 2026 David · MIT License</span>
        </div>
      </div>
    </footer>
  );
}
