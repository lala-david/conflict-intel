/**
 * Build-time brief manifest generator.
 *
 * The Daily Brief markdown lives in the git repo under
 *   reports/YYYY/MM/week-NN/YYYY-MM-DD.md
 * On the Cloudflare Workers runtime there is no filesystem and the GitHub
 * *tree* API (api.github.com) is unauthenticated-rate-limited from Workers'
 * shared egress IPs, so listing briefs at request time is unreliable.
 *
 * This script scans the repo at build time and emits a small, deterministic
 * manifest (date + week + path only — a few KB) that gets bundled into the
 * Worker. `web/lib/briefs.ts` imports it to list briefs with zero network,
 * and fetches individual brief *content* from the raw.githubusercontent CDN
 * (which is not subject to the api.github.com rate limit).
 *
 * Run before build:  node scripts/generate-briefs.mjs
 * (ideally wired as an npm `prebuild` step so the manifest stays fresh).
 */
import { readdirSync, statSync, writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..", ".."); // web/scripts -> repo root
const REPORTS_DIR = join(REPO_ROOT, "reports");
const OUT_FILE = resolve(__dirname, "..", "lib", "briefs.generated.json");

// reports/YYYY/MM/week-NN/YYYY-MM-DD.md  (forward-slash, repo-relative)
const BRIEF_RE = /^reports\/(\d{4})\/(\d{2})\/(week-\d+)\/(\d{4}-\d{2}-\d{2})\.md$/;

/** Recursively collect repo-relative file paths under a directory. */
function walk(dir, base) {
  const out = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return out;
  }
  for (const name of entries) {
    const full = join(dir, name);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) {
      out.push(...walk(full, base));
    } else {
      out.push(full.slice(base.length + 1).split("\\").join("/"));
    }
  }
  return out;
}

const paths = walk(REPORTS_DIR, REPO_ROOT);
const briefs = [];
for (const p of paths) {
  const m = BRIEF_RE.exec(p);
  if (m) briefs.push({ date: m[4], week: m[3], path: p });
}
// Newest first.
briefs.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

writeFileSync(OUT_FILE, JSON.stringify(briefs, null, 0) + "\n", "utf8");
console.log(`[generate-briefs] wrote ${briefs.length} briefs -> ${OUT_FILE}`);
