/**
 * Database client — libSQL / Turso (edge-compatible).
 *
 * Uses `@libsql/client/web` so it runs on the Cloudflare Workers (edge) runtime,
 * which has no filesystem or native modules. Requires TURSO_DATABASE_URL
 * (+ TURSO_AUTH_TOKEN) in every environment — including local dev.
 *
 * Local dev: point TURSO_DATABASE_URL at your Turso DB (read-only browsing is
 * fine), or run a local libSQL server (`turso dev`) and use its URL.
 *
 * libSQL is async over the network, so every query helper returns a Promise.
 */
import { createClient, type Client, type InArgs } from "@libsql/client/web";

let _client: Client | null = null;

function getClient(): Client {
  if (_client) return _client;
  const url = process.env.TURSO_DATABASE_URL;
  if (!url) {
    throw new Error(
      "TURSO_DATABASE_URL is not set. Set it (and TURSO_AUTH_TOKEN) — see DEPLOYMENT.md.",
    );
  }
  _client = createClient({ url, authToken: process.env.TURSO_AUTH_TOKEN });
  return _client;
}

/** Run a query and return all rows, cast to T. */
export async function queryAll<T = any>(sql: string, args: InArgs = []): Promise<T[]> {
  const rs = await getClient().execute({ sql, args });
  return rs.rows as unknown as T[];
}

/** Run a query and return the first row (or null), cast to T. */
export async function queryOne<T = any>(sql: string, args: InArgs = []): Promise<T | null> {
  const rs = await getClient().execute({ sql, args });
  return (rs.rows[0] as unknown as T) ?? null;
}
