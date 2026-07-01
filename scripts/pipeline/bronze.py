"""
Bronze layer — immutable raw landing.

Every fetched record is stored verbatim as JSON inside a Parquet file,
partitioned by source and ingest date, tagged with lineage metadata
(_source, _fetched_at, _run_id). Nothing is parsed or dropped here — this is
the replayable source of truth we can re-process Silver from without re-fetching.
"""
import json
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
BRONZE_DIR = ROOT / "data" / "bronze"


def land(source: str, records: list[dict], run_id: str) -> Path | None:
    """Write raw records to data/bronze/{source}/dt=YYYY-MM-DD/{run_id}.parquet."""
    if not records:
        return None

    fetched_at = datetime.now().isoformat()
    dt = fetched_at[:10]
    rows = [
        {
            "_source": source,
            "_fetched_at": fetched_at,
            "_run_id": run_id,
            "_raw": json.dumps(r, ensure_ascii=False, default=str),
        }
        for r in records
    ]

    table = pa.Table.from_pylist(rows)
    part_dir = BRONZE_DIR / source / f"dt={dt}"
    part_dir.mkdir(parents=True, exist_ok=True)
    path = part_dir / f"{run_id}.parquet"
    pq.write_table(table, path, compression="zstd")
    return path


def read_bronze(source: str, dt: str) -> list[dict]:
    """Replay raw records for a source/date back into dicts (for re-processing Silver)."""
    part_dir = BRONZE_DIR / source / f"dt={dt}"
    if not part_dir.exists():
        return []
    out: list[dict] = []
    for f in sorted(part_dir.glob("*.parquet")):
        table = pq.read_table(f, columns=["_raw"])
        out.extend(json.loads(x.as_py()) for x in table.column("_raw"))
    return out
