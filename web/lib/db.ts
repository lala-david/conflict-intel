/**
 * Turso client — zero-dependency, edge/Workers-native.
 *
 * Talks to Turso's hrana HTTP pipeline endpoint with plain `fetch`, so there are
 * no native modules or WebSocket deps to bundle (which broke @libsql/client on
 * the Cloudflare Workers runtime). Requires TURSO_DATABASE_URL (+ TURSO_AUTH_TOKEN)
 * in every environment. A `libsql://` URL is normalized to `https://`.
 *
 * Local dev: point TURSO_DATABASE_URL at your Turso DB, or run `turso dev`.
 */
import { getCloudflareContext } from "@opennextjs/cloudflare";

export type SqlArg = string | number | bigint | boolean | null;

// On the Cloudflare Workers runtime, dashboard vars/secrets arrive on the
// Cloudflare context env, NOT process.env. The SYNC getCloudflareContext() only
// resolves inside a page render; in API route handlers it throws. The async
// form initialises the context and works everywhere, so use it and fall back to
// process.env for local dev / build.
async function getCreds(): Promise<{ url: string; token: string }> {
  let env: Record<string, any> = {};
  try {
    const ctx = await getCloudflareContext({ async: true });
    env = (ctx?.env as any) ?? {};
  } catch {
    /* not on the Workers runtime (local dev / build) */
  }
  const rawUrl = env.TURSO_DATABASE_URL ?? process.env.TURSO_DATABASE_URL ?? "";
  return {
    url: String(rawUrl).replace(/^libsql:\/\//, "https://").replace(/\/+$/, ""),
    token: String(env.TURSO_AUTH_TOKEN ?? process.env.TURSO_AUTH_TOKEN ?? ""),
  };
}

function toArg(v: SqlArg) {
  if (v === null || v === undefined) return { type: "null" as const };
  if (typeof v === "boolean") return { type: "integer" as const, value: v ? "1" : "0" };
  if (typeof v === "bigint") return { type: "integer" as const, value: v.toString() };
  if (typeof v === "number") {
    return Number.isInteger(v)
      ? { type: "integer" as const, value: String(v) }
      : { type: "float" as const, value: v };
  }
  return { type: "text" as const, value: v };
}

function fromCell(c: { type: string; value?: any } | null): any {
  if (!c || c.type === "null") return null;
  if (c.type === "integer") return Number(c.value);
  if (c.type === "float") return typeof c.value === "number" ? c.value : Number(c.value);
  return c.value; // text / blob
}

async function exec(
  sql: string,
  args: SqlArg[],
  url: string,
  token: string,
): Promise<{ cols: string[]; rows: any[][] }> {
  if (!url) throw new Error("TURSO_DATABASE_URL is not set — see DEPLOYMENT.md.");
  const res = await fetch(`${url}/v2/pipeline`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      requests: [
        { type: "execute", stmt: { sql, args: args.map(toArg) } },
        { type: "close" },
      ],
    }),
  });
  if (!res.ok) throw new Error(`Turso HTTP ${res.status}: ${await res.text()}`);
  const data: any = await res.json();
  const first = data.results?.[0];
  if (!first || first.type === "error") {
    throw new Error(first?.error?.message ?? "Turso query failed");
  }
  const result = first.response.result;
  return { cols: result.cols.map((c: any) => c.name), rows: result.rows };
}

function rowsToObjects<T>(cols: string[], rows: any[][]): T[] {
  return rows.map((row) => {
    const obj: any = {};
    cols.forEach((c, i) => (obj[c] = fromCell(row[i])));
    return obj as T;
  });
}

// djb2 hash → short stable cache key
function hashKey(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = (((h << 5) + h) ^ s.charCodeAt(i)) >>> 0;
  return h.toString(36) + s.length.toString(36);
}

const CACHE_TTL = 600; // seconds — data refreshes ~daily, so 10 min is safe

/**
 * Run a query, caching the result at the Cloudflare edge (caches.default) keyed
 * by sql+args. Repeat reads across requests in the same colo skip Turso entirely.
 * No binding/infra needed; falls back to a direct query where the Cache API is
 * unavailable (local dev / build).
 */
export async function queryAll<T = any>(sql: string, args: SqlArg[] = []): Promise<T[]> {
  // Resolve creds before any Cache API call (which can drop the ALS context).
  const { url, token } = await getCreds();

  const cache: Cache | undefined = (globalThis as any).caches?.default;
  const keyReq = cache
    ? new Request(`https://q.cache/${hashKey(JSON.stringify([sql, args]))}`)
    : undefined;

  if (cache && keyReq) {
    try {
      const hit = await cache.match(keyReq);
      if (hit) return (await hit.json()) as T[];
    } catch {
      /* ignore cache read errors */
    }
  }

  const { cols, rows } = await exec(sql, args, url, token);
  const data = rowsToObjects<T>(cols, rows);

  // Don't cache large result sets — JSON.stringify'ing them costs more CPU than
  // the round-trip it saves and can blow the Worker's memory/CPU budget.
  if (cache && keyReq && rows.length <= 2000) {
    try {
      await cache.put(
        keyReq,
        new Response(JSON.stringify(data), {
          headers: { "Content-Type": "application/json", "Cache-Control": `max-age=${CACHE_TTL}` },
        }),
      );
    } catch {
      /* ignore cache write errors */
    }
  }
  return data;
}

/** Run a query and return the first row (or null), cast to T. */
export async function queryOne<T = any>(sql: string, args: SqlArg[] = []): Promise<T | null> {
  const rows = await queryAll<T>(sql, args);
  return rows[0] ?? null;
}

/** Run a write (INSERT/UPDATE/DELETE) — never cached. */
export async function execute(sql: string, args: SqlArg[] = []): Promise<void> {
  const { url, token } = await getCreds();
  await exec(sql, args, url, token);
}
