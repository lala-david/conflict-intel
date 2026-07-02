/**
 * Daily brief access — host-agnostic (no filesystem).
 *
 * Reports live as Markdown in the git repo (reports/YYYY/MM/week-NN/YYYY-MM-DD.md).
 * Instead of reading them off disk (which breaks on serverless/edge hosts), we
 * list them via the GitHub trees API and fetch content from raw.githubusercontent.
 * Both are cached (revalidate 1h). Works on Node and edge runtimes.
 */
const REPO = process.env.NEXT_PUBLIC_REPO ?? "lala-david/conflict-intel";
const BRANCH = process.env.NEXT_PUBLIC_REPO_BRANCH ?? "main";

export interface BriefRef {
  date: string;
  week: string;
  path: string;
}

const BRIEF_RE = /^reports\/(\d{4})\/(\d{2})\/(week-\d+)\/(\d{4}-\d{2}-\d{2})\.md$/;

export async function listBriefs(limit = 90): Promise<BriefRef[]> {
  try {
    const r = await fetch(
      `https://api.github.com/repos/${REPO}/git/trees/${BRANCH}?recursive=1`,
      { next: { revalidate: 3600 }, headers: { Accept: "application/vnd.github+json" } },
    );
    if (!r.ok) return [];
    const data = (await r.json()) as { tree?: { path: string }[] };
    const out: BriefRef[] = [];
    for (const t of data.tree ?? []) {
      const m = BRIEF_RE.exec(t.path);
      if (m) out.push({ date: m[4], week: m[3], path: t.path });
    }
    out.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    return out.slice(0, limit);
  } catch {
    return [];
  }
}

export async function getBrief(date: string): Promise<string | null> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const ref = (await listBriefs(1000)).find((b) => b.date === date);
  if (!ref) return null;
  try {
    const r = await fetch(`https://raw.githubusercontent.com/${REPO}/${BRANCH}/${ref.path}`, {
      next: { revalidate: 3600 },
    });
    return r.ok ? await r.text() : null;
  } catch {
    return null;
  }
}
