# Knowledge Graph & Ontology — Staged Roadmap

How we layer an ontology / knowledge graph over our normalized conflict events
(actors · events · places · dates · sources). Grounded in verified research
(25/25 claims confirmed against primary sources: Stanford OD101, W3C PROV-O,
OASIS STIX 2.1, UCDP codebook, NeOn/SAMOD papers).

**Guiding principle:** reuse established vocabularies, right-size the tech, and
grow the graph *incrementally* on top of the existing Bronze/Silver/Gold medallion
— not a big-bang RDF rewrite.

---

## 0. Scope via competency questions (OD101 Step 1)

The ontology exists to answer these — they scope the model and later validate it:

- Which actors operate in country X, and where does their activity cluster?
- Who is allied with / rival of / a splinter of actor Y?
- What is the timeline of events for actor Y / country X?
- For a given event, what are the sources and how confident are we?
- Which actors co-occur across the same places and time windows? (link analysis)

## 1. Methodology (named, staged)

Follow **Ontology Development 101** (Noy & McGuinness, Stanford) — 7 steps:
1. Determine domain & scope · 2. **Reuse** existing ontologies · 3. Enumerate terms ·
4. Define classes/hierarchy · 5. Define properties · 6. Define facets (type,
cardinality, domain/range) · 7. Create instances.

Situated inside **NeOn** (reuse-centric, 9 scenarios; Scenario 1 = spec→implementation
producing an ORSD with competency questions) and delivered **SAMOD**-style
(kickoff → design → test in small iterations, CQs → queries as the test).

## 2. Vocabularies to reuse (do NOT reinvent) — verified

| Layer | Standard | What we take |
|-------|----------|--------------|
| **Event backbone** | **SEM** (Simple Event Model) | `Event` · `Actor` · `Place` · `Time`; `hasActor` + `RoleType` (attacker/perpetrator); minimal-commitment (ideal for messy web data) |
| **Provenance / confidence** | **W3C PROV-O** | `Entity`/`Activity`/`Agent` + `wasDerivedFrom` / `wasAttributedTo` — per-source lineage |
| **Actors & relationships** | **STIX 2.1** (OASIS) | `Threat Actor` · `Campaign` · `Identity` · `Location`; **reified relationships (SRO)** carrying `relationship_type` + confidence |
| **Domain taxonomy** | **UCDP codebook** | event definition; **dyad** (`side_a`/`side_b`) = ready-made actor↔actor primitive; `type_of_violence` (1 state / 2 non-state / 3 one-sided) as a disjoint partition |

> Multi-source conflicts are handled by SEM's `View`→`accordingTo`→`Authority`
> (or PROV attribution): competing UCDP/GDELT/Telegram claims each keep their source.
> (STIX is natively cyber-scoped — we borrow Threat-Actor/Location + the SRO graph
> pattern, not Malware/Intrusion-Set.)

## 3. Entity / relationship model (sketch)

```
        (perpetrated_by / sem:hasActor, role=attacker)
  Event ───────────────────────────────▶ Actor
    │  │ (located_in / stix located-at)     │ ▲
    │  └──────────────▶ Place               │ │ allied_with / rival_of / splintered_from
    │                                       │ │ (reified edge, from UCDP dyad)
    │ (occurred_at) ▶ Time                  ▼ │
    │                                     Actor
    └─(sourced_from / prov:wasDerivedFrom)▶ Source ──(accordingTo)──▶ Authority
```

Nodes: **Event, Actor, Place, Source** (+ Time as attribute). Edges are **first-class**
(reified) so they can carry `confidence` and `source` — the STIX SRO pattern.

## 4. Tech stack — right-sized (our recommendation)

The research deliberately left this open; our engineering call for **~500K events, solo/small**:

- ❌ **Full RDF/OWL triplestore** — reasoning/SPARQL power we don't need; heavy ops.
- ❌ **Neo4j server** — another service to run; overkill at this scale.
- ✅ **Property-graph tables inside our existing SQLite** — `nodes` + `edges` tables
  (Gold layer), queried with recursive CTEs for link analysis. DuckDB for heavier
  graph analytics if needed. The ontology lives as a **documented schema mapping**
  (this file) — SEM/PROV/STIX/UCDP are the *vocabulary we conform to*, not a runtime
  dependency. Export to RDF/STIX JSON later **only if** an integration needs it.

This keeps everything in one file-based DB, matches the medallion, and ships features fast.

## 5. Staged roadmap (incremental on the medallion)

- **Stage 1 — Entity resolution (Silver+):** dedupe/resolve `Actor` (alias map, string
  similarity) and `Place` (GeoNames/coords reconciliation). Output: stable node IDs.
- **Stage 2 — Materialize the graph (Gold):** build `nodes` (Actor/Place/Event/Source)
  and `edges` (perpetrated_by, located_in, sourced_from, actor↔actor from dyads)
  tables from `events`. Each edge keeps `source` + `confidence`.
- **Stage 3 — Product features:** link-analysis view (shared places/time), real
  "related actors" (replace today's country-proximity heuristic), alliance inference
  (from dyad + `splintered_from`), unified timelines — surfaced on the node pages
  and a graph view.
- **Stage 4 — Interop (optional):** export nodes/edges to STIX 2.1 JSON / RDF for
  partners, validated by the Stage-0 competency questions as SPARQL/SQL tests.

---

### Sources
Stanford OD101 (protege.stanford.edu) · NeOn Methodology (oa.upm.es) · SAMOD
(arxiv 2308.06018) · W3C PROV-O (w3.org/TR/prov-o) · OASIS STIX 2.1
(docs.oasis-open.org/cti/stix/v2.1) · SEM (semanticweb.cs.vu.nl/2009/11/sem) ·
UCDP GED codebook (ucdp.uu.se).
