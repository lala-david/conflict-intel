import { ExternalLink } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";

interface Props {
  articles: { feed: string; title: string; url: string }[];
}

export function TodayAnalysis({ articles }: Props) {
  if (articles.length === 0) return null;

  return (
    <div>
      <SectionHeading kicker="From the field" title="Expert analysis" />
      <div className="rounded-lg border border-border bg-surface">
        {articles.map((a, i) => {
          const hasUrl = a.url && a.url !== "#";
          const Tag = hasUrl ? "a" : "div";
          const linkProps = hasUrl
            ? { href: a.url, target: "_blank", rel: "noopener noreferrer" }
            : {};

          return (
            <Tag
              key={i}
              {...linkProps}
              className={`group flex items-start gap-4 border-b border-border px-5 py-4 transition last:border-b-0 ${
                hasUrl
                  ? "hover:bg-surface-2 cursor-pointer"
                  : "opacity-70"
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-text-dim">
                  {a.feed || "Analysis"}
                </div>
                <div className="mt-1 line-clamp-2 text-sm font-medium text-text-primary group-hover:text-accent">
                  {a.title}
                </div>
              </div>
              {hasUrl && (
                <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0 text-text-dim group-hover:text-accent" />
              )}
            </Tag>
          );
        })}
      </div>
    </div>
  );
}
