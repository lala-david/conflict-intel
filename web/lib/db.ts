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
// Cloudflare context env (getCloudflareContext().env), NOT process.env — the
// latter only holds build-time vars. Read the CF context first, fall back to
// process.env for local dev / build. Must be called at request time.
function cfEnv(key: string): string {
  try {
    const v = (getCloudflareContext().env as any)?.[key];
    if (v) return String(v);
  } catch {
    // not in a Cloudflare request context (local dev, build) — fall through
  }
  return process.env[key] ?? "";
}

function httpUrl(): string {
  return cfEnv("TURSO_DATABASE_URL")
    .replace(/^libsql:\/\//, "https://")
    .replace(/\/+$/, "");
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

async function exec(sql: string, args: SqlArg[]): Promise<{ cols: string[]; rows: any[][] }> {
  const url = httpUrl();
  if (!url) throw new Error("TURSO_DATABASE_URL is not set — see DEPLOYMENT.md.");
  const res = await fetch(`${url}/v2/pipeline`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${cfEnv("TURSO_AUTH_TOKEN")}`,
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

/** Run a query and return all rows, cast to T. */
export async function queryAll<T = any>(sql: string, args: SqlArg[] = []): Promise<T[]> {
  const { cols, rows } = await exec(sql, args);
  return rows.map((row) => {
    const obj: any = {};
    cols.forEach((c, i) => (obj[c] = fromCell(row[i])));
    return obj as T;
  });
}

/** Run a query and return the first row (or null), cast to T. */
export async function queryOne<T = any>(sql: string, args: SqlArg[] = []): Promise<T | null> {
  const rows = await queryAll<T>(sql, args);
  return rows[0] ?? null;
}
