/**
 * Daily brief access — host-agnostic, Cloudflare-Workers-safe (no filesystem).
 *
 * Reports live as Markdown in the git repo (reports/YYYY/MM/week-NN/YYYY-MM-DD.md).
 *
 * Root cause of the previously-empty /brief: `listBriefs` used the GitHub *tree*
 * API (api.github.com), which is unauthenticated-rate-limited (60/hr) across
 * Cloudflare Workers' shared egress IPs and requires a User-Agent the Workers
 * fetch may not send → 403 → []. `getBrief` also depended on `listBriefs` to
 * resolve a path, so both the archive and detail pages broke together.
 *
 * Fix: the brief *list* is now read from a small build-time manifest
 * (lib/briefs.generated.json, produced by scripts/generate-briefs.mjs and
 * bundled into the Worker) — zero network, always populated. Individual brief
 * *content* is fetched from the raw.githubusercontent CDN, which serves static
 * blobs and is NOT subject to the api.github.com rate limit.
 */
import manifest from "./briefs.generated.json";

const REPO = process.env.NEXT_PUBLIC_REPO ?? "lala-david/conflict-intel";
const BRANCH = process.env.NEXT_PUBLIC_REPO_BRANCH ?? "main";

export interface BriefRef {
  date: string;
  week: string;
  path: string;
}

// Bundled at build time, already sorted newest-first by the generator.
const BRIEFS: BriefRef[] = manifest as BriefRef[];

export async function listBriefs(limit = 90): Promise<BriefRef[]> {
  return BRIEFS.slice(0, limit);
}

export async function getBrief(date: string): Promise<string | null> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const ref = BRIEFS.find((b) => b.date === date);
  if (!ref) return null;
  try {
    const r = await fetch(`https://raw.githubusercontent.com/${REPO}/${BRANCH}/${ref.path}`, {
      next: { revalidate: 86400 },
    });
    return r.ok ? await r.text() : null;
  } catch {
    return null;
  }
}
