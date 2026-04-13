/**
 * Database client — reads from the existing terror.db SQLite file at project root
 *
 * Uses better-sqlite3 for synchronous reads (fast for read-only queries in RSC).
 * For production deployment on Vercel, this will be replaced with Turso (libSQL).
 */
import Database from "better-sqlite3";
import path from "path";

// Path to the pipeline's SQLite database (one level up from web/)
const DB_PATH = path.resolve(process.cwd(), "..", "data", "terror.db");

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db) return _db;
  _db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
  return _db;
}

// Close on process exit
if (typeof process !== "undefined") {
  process.on("beforeExit", () => {
    if (_db) {
      _db.close();
      _db = null;
    }
  });
}
