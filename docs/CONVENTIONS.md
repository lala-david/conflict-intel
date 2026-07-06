# Data & Pipeline Conventions

The single source of truth for how data flows and is named in this project.
**Every new pipeline or feature must follow these rules — from design, not as a retrofit.**

---

## 1. Medallion architecture (Bronze → Silver → Gold)

All ingestion is a medallion pipeline, matching `scripts/pipeline/`.

| Layer | Purpose | Where |
|-------|---------|-------|
| **Bronze** | Extract each source → land raw record dicts **immutably** as Parquet | `pipeline/bronze.py` `land(source, records, run_id)` → `data/bronze/<source>/dt=YYYY-MM-DD/<run_id>.parquet` |
| **Silver** | Normalize · enrich · **dedupe** · link → clean serving tables | `events`, `crypto_addresses`, `sanctions` |
| **Gold** | Pre-computed serving aggregates | `*_stats` tables (`global_stats`, `country_stats`, `crypto_stats`, …) |

**Contracts**
- A source is a `Connector`/`FnConnector` returning `list[dict]` (`pipeline/base.py`); errors are isolated per source via `ExtractResult`.
- Every Bronze extract records health: `pipeline/health.py` `record(run_id, [ExtractResult])` → `collection_health`.
- The events registry is `pipeline/registry.py`; orchestration is `pipeline/run.py` (the daily CI runs `python scripts/pipeline/run.py`).
- A **self-contained sub-pipeline** is allowed and encouraged for a distinct domain (see `pipeline/crypto.py` — its own Bronze→Silver→Gold, invoked from `run.py`). It still lands Bronze, records health, and writes Silver/Gold like the events pipeline.

**Adding a source (checklist)**
1. Bronze: a fetch fn → `bronze.land("<source>", records, run_id)` + health.
2. Silver: normalize into the domain table (dedupe + label + link).
3. Gold: refresh the relevant `*_stats`.
4. Sync: ensure the table is in `scripts/export_for_turso.py` / `scripts/sync_to_turso.py`.

---

## 2. Naming

- **snake_case** everywhere: table names, column names, source slugs, Python funcs/vars, files.
- **Bronze source slug** = lowercase, snake_case. The events pipeline uses bare slugs (`gdelt`, `ucdp`, `expert_rss`, `telegram`); a sub-pipeline prefixes its domain (`crypto_opensanctions`, `crypto_graphsense`, `crypto_nbctf`, `crypto_ransomwhere`).
- **Row-level `source` value** (e.g. `crypto_addresses.source`) = `provider[/dataset]`: a provider slug, optionally namespaced with `/` for a sub-dataset. Examples: `nbctf`, `ransomwhere`, `opensanctions/us_ofac_sdn`, `graphsense/aft-alqaeda-forfeit_vc`.
- **Tables**: singular domain noun for row tables (`events`, `sanctions`, `crypto_addresses`); Gold aggregates end in `_stats`.
- **Fetch functions**: `fetch_<source>()`; collectors live in `scripts/<domain>_source.py` (e.g. `crypto_source.py`) or `scripts/sources.py` (events).
- **Booleans**: `is_<thing>` (`is_terror`, `is_aggregate`, `is_new`).
- **Foreign-ish links**: `<thing>_of` / `<thing>_id` (`dup_of`).

---

## 3. Data labeling

### Event category (`events.category`) — organized-violence taxonomy
`war` · `civil_war` · `insurgency` · `terrorism` · `counterterrorism` ·
`state_violence` · `communal_violence` · `cartel_violence` · `armed_violence` ·
`mass_atrocity` · `armed_assault`. Unset → `NULL` (avoid the empty string).

### Crypto class (`crypto_addresses.category`) — threat-finance taxonomy
`terror` · `sanction` · `extremism` · `ransomware` · `hack` · `scam` · `mixer`.
Only these (the "threat-actor" set in `pipeline/crypto.py::PRODUCT_CATEGORIES`) are
surfaced in the product; bulk consumer-fraud is dropped in Silver.

### Flags
- **`is_terror`** (crypto): 1 iff attributed to a terrorist organization. Determined by the
  OFAC sanction **program** (`SDGT`/`SDT`/`FTO`/`US-TERR`), a GraphSense `abuse: terrorism`
  pack, an NBCTF seizure, or a curated name hint — **not** by a keyword guess alone.
- **`is_aggregate`** (events): 1 for cumulative/rollup rows (e.g. UCDP multi-year totals);
  excluded from every serving query and chart.
- **`org`** (crypto): canonical conflict-organization label from the curated alias map in
  `pipeline/crypto.py::_ORG_ALIASES` (high precision; `NULL` when unknown — never fuzzy-guessed).

### Dedup
- **Exact keys dedupe exactly, no LLM.** Crypto wallet addresses are exact strings →
  dedupe by address (terror-attributed record wins).
- **Fuzzy same-entity dedup uses the local LLM** (`pipeline/dedup.py`): events that may be
  the same incident. It degrades to a similarity-only heuristic when the local LLM
  (`LOCAL_LLM_BASE_URL`) is unreachable — so CI never blocks on it. Non-canonical rows are
  marked `dup_of` (never hard-deleted in the daily path).

---

## 4. Serving & sync

- Cloudflare Worker (OpenNext) reads **Turso**; `TURSO_DATABASE_URL` lives in `web/wrangler.jsonc`.
- Daily CI seeds the full DB from the `db-latest` release (correct stats), collects, then
  `scripts/sync_to_turso.py` appends new events and full-replaces stats/crypto — with a guard
  that skips the replace if the local DB is incomplete (protects the production snapshot).

See also: memory `always-medallion-architecture`, `deployment-cloudflare-turso`.
