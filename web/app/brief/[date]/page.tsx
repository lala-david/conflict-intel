import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ArrowLeft } from "lucide-react";
import { getBrief } from "@/lib/briefs";

export const revalidate = 86400;

interface Props {
  params: { date: string };
}

export default async function BriefDetailPage({ params }: Props) {
  const content = await getBrief(params.date);
  if (!content) notFound();

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

        <article className="prose prose-invert prose-sm max-w-none prose-headings:font-display prose-a:text-accent prose-a:no-underline hover:prose-a:underline prose-table:block prose-table:overflow-x-auto prose-th:text-left prose-td:align-top">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </article>
      </main>
      <Footer />
    </>
  );
}
