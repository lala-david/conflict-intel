/**
 * Database client — Cloudflare D1 in production, local SQLite in dev/build.
 *
 * On the Workers runtime queries run against the D1 binding `DB` (native SQLite,
 * no external service, no auth token). Off Workers (local `next dev` / `next build`)
 * it reads the pipeline's data/conflict.db directly via better-sqlite3, which is
 * marked external so it never enters the Worker bundle (see next.config.mjs).
 *
 * Read results are edge-cached (caches.default, 10 min) so repeat reads in a colo
 * skip D1 entirely and stay well under the free-tier row-read budget.
 */
import { getCloudflareContext } from "@opennextjs/cloudflare";

export type SqlArg = string | number | bigint | boolean | null;

// ── backend resolution ────────────────────────────────────────────────────

/** The D1 binding on the Workers runtime, or null in local dev / build. */
async function getD1(): Promise<any | null> {
  // The async form initialises the Cloudflare context, so it resolves in both
  // page renders and API route handlers. Off Workers it throws → local fallback.
  try {
    const ctx = await getCloudflareContext({ async: true });
    return (ctx?.env as any)?.DB ?? null;
  } catch {
    return null;
  }
}

/** Lazily-opened local SQLite handle (dev/build only — never on Workers). */
let _local: any = null;
function getLocal(): any {
  if (_local) return _local;
  // better-sqlite3 is an external package (next.config.mjs); require it at call
  // time so it stays out of the Worker bundle and only loads under Node.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const Database = require("better-sqlite3");
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const path = require("path");
  const dbPath = path.resolve(process.cwd(), "..", "data", "conflict.db");
  _local = new Database(dbPath, { fileMustExist: true });
  // The waitlist table is app-owned (not part of the pipeline schema); ensure it
  // exists locally so the signup form works in dev. On D1 it's created at setup.
  _local.exec(
    `CREATE TABLE IF NOT EXISTS waitlist (
      id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, interest TEXT,
      note TEXT, source TEXT, created_at TEXT
    )`,
  );
  return _local;
}

// better-sqlite3 (and D1's bind) reject raw booleans — coerce to 0/1.
function normArgs(args: SqlArg[]): (string | number | bigint | null)[] {
  return args.map((v) => (typeof v === "boolean" ? (v ? 1 : 0) : v));
}

async function runRead(d1: any | null, sql: string, args: (string | number | bigint | null)[]): Promise<any[]> {
  if (d1) {
    const stmt = args.length ? d1.prepare(sql).bind(...args) : d1.prepare(sql);
    const { results } = await stmt.all();
    return results ?? [];
  }
  return getLocal().prepare(sql).all(...args);
}

// ── query helpers ─────────────────────────────────────────────────────────

// djb2 hash → short stable cache key
function hashKey(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = (((h << 5) + h) ^ s.charCodeAt(i)) >>> 0;
  return h.toString(36) + s.length.toString(36);
}

const CACHE_TTL = 600; // seconds — data refreshes ~daily, so 10 min is safe

/**
 * Run a query, caching the result at the Cloudflare edge (caches.default) keyed
 * by sql+args. Repeat reads across requests in the same colo skip D1 entirely.
 * Falls back to a direct query where the Cache API is unavailable (local dev).
 */
export async function queryAll<T = any>(sql: string, args: SqlArg[] = []): Promise<T[]> {
  // Resolve the backend before any Cache API call (which can drop the ALS context).
  const d1 = await getD1();
  const a = normArgs(args);

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

  const data = (await runRead(d1, sql, a)) as T[];

  // Don't cache large result sets — JSON.stringify'ing them costs more CPU than
  // the round-trip it saves and can blow the Worker's memory/CPU budget.
  if (cache && keyReq && data.length <= 2000) {
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
  const d1 = await getD1();
  const a = normArgs(args);
  if (d1) {
    const stmt = a.length ? d1.prepare(sql).bind(...a) : d1.prepare(sql);
    await stmt.run();
    return;
  }
  getLocal().prepare(sql).run(...a);
}
