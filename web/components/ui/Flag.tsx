interface Props {
  iso?: string | null;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const DIM = {
  sm: { w: 18, h: 13, cdn: "w40" },
  md: { w: 24, h: 18, cdn: "w40" },
  lg: { w: 40, h: 30, cdn: "w80" },
} as const;

/** Country flag from flagcdn (ISO 3166-1 alpha-2). Renders nothing without a valid code. */
export function Flag({ iso, className = "", size = "md" }: Props) {
  if (!iso || iso.length !== 2) return null;
  const code = iso.toLowerCase();
  const d = DIM[size];
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://flagcdn.com/${d.cdn}/${code}.png`}
      srcSet={`https://flagcdn.com/w80/${code}.png 2x`}
      alt=""
      width={d.w}
      height={d.h}
      loading="lazy"
      className={`inline-block shrink-0 rounded-[3px] object-cover ring-1 ring-white/10 ${className}`}
      style={{ width: d.w, height: d.h }}
    />
  );
}
