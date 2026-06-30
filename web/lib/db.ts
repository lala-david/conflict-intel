/**
 * Database client — libSQL (Turso in production, local SQLite file in dev).
 *
 * - Production (Cloudflare Pages): set TURSO_DATABASE_URL + TURSO_AUTH_TOKEN.
 * - Local dev: falls back to the pipeline's terror.db file one level up from web/.
 *
 * libSQL is async over the network, so every query helper returns a Promise.
 */
import { createClient, type Client, type InArgs } from "@libsql/client";
import path from "path";

let _client: Client | null = null;

function getClient(): Client {
  if (_client) return _client;

  const url = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (url) {
    _client = createClient({ url, authToken });
  } else {
    // Local fallback: read the pipeline's SQLite file directly.
    const dbPath = path
      .resolve(process.cwd(), "..", "data", "terror.db")
      .split(path.sep)
      .join("/");
    _client = createClient({ url: "file:" + dbPath });
  }
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
