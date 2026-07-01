"""
Medallion data pipeline (Bronze → Silver → Gold).

- Bronze: immutable raw source payloads landed as partitioned Parquet.
- Silver: cleaned, normalized, deduplicated events (the `events` table).
- Gold: curated aggregates for serving (`global_stats`, `country_stats`, …).

Modular source connectors + per-source health/observability.
Right-sized: Parquet + SQLite/DuckDB, not Iceberg (this dataset is ~280MB).
"""
