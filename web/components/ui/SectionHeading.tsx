import type { ReactNode } from "react";

interface Props {
  /** Small red uppercase label above the title */
  kicker?: string;
  title: string;
  /** Optional right-aligned action (link, note) */
  action?: ReactNode;
}

/** Editorial section header: red kicker · serif title · hairline rule. */
export function SectionHeading({ kicker, title, action }: Props) {
  return (
    <div className="mb-6 border-b border-border pb-3">
      <div className="flex items-end justify-between gap-4">
        <div>
          {kicker && (
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
              {kicker}
            </div>
          )}
          <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-text-primary md:text-3xl">
            {title}
          </h2>
        </div>
        {action && (
          <div className="shrink-0 pb-1 text-sm text-text-dim">{action}</div>
        )}
      </div>
    </div>
  );
}
