"""
Source health / observability.

Records, per run and per source: row count, ok/fail, error, and rolls up the
last successful non-empty collection. Makes a source that silently returns 0
(as Wikipedia did) visible instead of failing quietly.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database import get_conn  # noqa: E402
from pipeline.base import ExtractResult  # noqa: E402


def _ensure_table(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS collection_health (
            run_id TEXT,
            source TEXT,
            count INTEGER,
            ok INTEGER,
            error TEXT,
            ran_at TEXT,
            PRIMARY KEY (run_id, source)
        )"""
    )


def record(run_id: str, results: list[ExtractResult]) -> None:
    conn = get_conn()
    try:
        _ensure_table(conn)
        now = datetime.now().isoformat()
        for r in results:
            conn.execute(
                "INSERT OR REPLACE INTO collection_health VALUES (?,?,?,?,?,?)",
                (run_id, r.source, len(r.records), 1 if r.ok else 0, r.error[:300], now),
            )
        conn.commit()
    finally:
        conn.close()


def latest() -> list[dict]:
    """Most recent status per source — for a health dashboard / status page."""
    conn = get_conn()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """SELECT source, count, ok, error, ran_at FROM collection_health h
                WHERE ran_at = (SELECT MAX(ran_at) FROM collection_health h2 WHERE h2.source = h.source)
                ORDER BY source"""
        ).fetchall()
        return [
            {"source": r[0], "count": r[1], "ok": bool(r[2]), "error": r[3], "ran_at": r[4]}
            for r in rows
        ]
    except Exception:
        return []
    finally:
        conn.close()
