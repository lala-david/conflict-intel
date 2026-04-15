import Link from "next/link";
import { notFound } from "next/navigation";
import fs from "fs";
import path from "path";
import ReactMarkdown from "react-markdown";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ArrowLeft } from "lucide-react";

export const revalidate = 86400;

interface Props {
  params: { date: string };
}

function findBriefFile(date: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const [y, m] = date.split("-");
  const reportsDir = path.resolve(process.cwd(), "..", "reports", y, m);
  try {
    const weeks = fs.readdirSync(reportsDir).filter((w) => /^week-/.test(w));
    for (const w of weeks) {
      const full = path.join(reportsDir, w, `${date}.md`);
      if (fs.existsSync(full)) return full;
    }
  } catch {}
  return null;
}

export default function BriefDetailPage({ params }: Props) {
  const file = findBriefFile(params.date);
  if (!file) notFound();

  const content = fs.readFileSync(file, "utf-8");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-12">
        <Link
          href="/brief"
          className="mb-6 inline-flex items-center gap-1 text-xs text-text-dim hover:text-text-primary"
        >
          <ArrowLeft className="h-3 w-3" />
          All briefs
        </Link>

        <article className="prose prose-invert prose-sm max-w-none prose-headings:font-display prose-a:text-accent prose-a:no-underline hover:prose-a:underline">
          <ReactMarkdown>{content}</ReactMarkdown>
        </article>
      </main>
      <Footer />
    </>
  );
}
