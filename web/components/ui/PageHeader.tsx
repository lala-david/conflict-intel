import type { ReactNode } from "react";

interface Props {
  /** Small red uppercase label above the title */
  kicker?: string;
  title: ReactNode;
  /** Standfirst / lede paragraph */
  standfirst?: ReactNode;
  /** Optional right-aligned slot (e.g. a figure or action) */
  aside?: ReactNode;
}

/** Editorial page masthead: red kicker · large serif title · standfirst · hairline rule. */
export function PageHeader({ kicker, title, standfirst, aside }: Props) {
  return (
    <header className="border-b border-border pb-8">
      <div className="flex items-end justify-between gap-6">
        <div className="min-w-0">
          {kicker && (
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
              {kicker}
            </div>
          )}
          <h1 className="mt-3 font-display text-4xl font-semibold leading-[1.05] tracking-tight text-text-primary md:text-6xl">
            {title}
          </h1>
          {standfirst && (
            <p className="mt-4 max-w-2xl text-lg leading-relaxed text-text-dim">
              {standfirst}
            </p>
          )}
        </div>
        {aside && <div className="hidden shrink-0 sm:block">{aside}</div>}
      </div>
    </header>
  );
}
