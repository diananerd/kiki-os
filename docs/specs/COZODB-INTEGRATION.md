---
id: cozodb-integration
title: CozoDB Integration
type: SPEC
status: draft
version: 0.0.0
implements: [cozodb-integration]
depends_on:
  - memory-architecture
  - semantic-graph
  - storage-layout
depended_on_by:
  - semantic-graph
last_updated: 2026-04-30
---
# CozoDB Integration

## Purpose

Specify how CozoDB is configured, embedded, and operated for the semantic graph: backend choice, schemas, query patterns, validity discipline, backup, and migration.

## Why CozoDB

- Datalog is the right query language for graphs.
- Native bitemporal `Validity` type — we don't roll our own.
- Pure Rust, embedded; no separate process.
- Multiple backend stores; we pick rocksdb for durability.
- Stored procedures ("rules") let us encode domain patterns once.

## Backend

We use the **rocksdb** backend on disk. SQLite backend is available but slower for our workload. Memory-only is used for tests.

```
/var/lib/kiki/users/<uid>/memory/semantic/
└── cozo.rocks/                        rocksdb directory
```

A small `config.toml` records the schema version and backend tuning:

```toml
[cozo]
backend = "rocksdb"

[cozo.rocksdb]
write_buffer_size_mb = 64
max_open_files = 256

[schema]
version = 3
```

## Schema migrations

Each migration is a Datalog script committed in git:

```
04-memory/cozo-migrations/
├── 0001_initial.cozo
├── 0002_add_provenance.cozo
└── 0003_per_predicate_index.cozo
```

memoryd runs pending migrations on startup; each migration is recorded in a `_migrations` relation. Forward-only; we don't roll back schemas (we add new ones).

## Core relations

```
:create entity {
    id: String =>
    kind: String,
    name: String,
    created_at: Validity,
    confidence: Float,
}

:create property {
    entity: String,
    name: String,
    valid: Validity =>
    value: Json,
    confidence: Float,
    source: String,             # "user" | "tool:<id>" | ...
    audit_id: String,
}

:create relation {
    subject: String,
    predicate: String,
    object: String,
    valid: Validity =>
    confidence: Float,
    weight: Float?,
    source: String,
    audit_id: String,
}

:create supersession {
    fact_id: String =>
    superseded_by: String,
    at: Validity,
    reason: String,
}
```

Note the validity field is part of the key for property and relation — that's how supersession works without overwriting.

## Validity

CozoDB's `Validity` is a (timestamp, retracted) pair. We use it for *transaction time* (when we wrote it). For *valid time* (when it's true in the world), we wrap the validity in our own `valid_from` / `valid_to` fields encoded into the Json `value` for properties or as a separate fact range.

This split looks redundant but matches how we use them: transaction time is enforced by the engine; valid time is application semantics.

See `BITEMPORAL-FACTS.md` for the model.

## Common queries

### Get current property

```
?[v] := *property{entity: 'user-1', name: 'lives_in', valid: validity, value: v},
        valid_now(validity)
```

### Time-travel: what did we believe at T?

```
?[v] := *property{entity: 'user-1', name: 'lives_in',
                  valid: @T validity, value: v}
```

### Walk relations

```
?[friend] := *relation{subject: 'user-1', predicate: 'knows',
                        object: friend, valid: v}, valid_now(v)
?[friend_of_friend] := ?[user-1, _, friend], ?[friend, _, friend_of_friend]
```

### Confidence-weighted

```
?[v, score] := *property{entity: $e, name: $n, value: v,
                          confidence: c, valid: vv}, valid_now(vv),
                score = c
:order -score
:limit 5
```

## Stored rules

We define helper rules in migrations:

```
:rule valid_now(v) := ts(v) <= now() && !retracted(v)
:rule entity_facts(e) := *property{entity: e, name, valid: v}, valid_now(v)
```

Rules give the agent's planner a small typed surface to use without composing low-level joins.

## Vector extension

CozoDB supports HNSW indexes for vector columns. We use a small per-entity embedding for similarity-based entity lookup:

```
:create entity_embedding {id: String => embedding: <F32; 384>}
:hnsw create entity_embedding:idx { dim: 384, m: 32, ef_construction: 200,
                                    distance: Cosine }
```

Embedder for entity vectors is bge-m3 over the entity's name + summary (small).

## Backup

rocksdb's directory is a btrfs snapshot target. CozoDB has built-in `::export` and `::import` that produce a portable Datalog dump; we use export for export-import flows (see `IMPORT-EXPORT.md` if we add it) but rely on filesystem snapshots for live backups.

## Capabilities

memoryd holds the only handle to the rocksdb backend. Other components reach the semantic store via the Cap'n Proto facade.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Schema migration fails           | refuse to start; surface to    |
|                                  | maintenance                    |
| rocksdb compaction stalls        | log; alert; keep operating     |
|                                  | (read-only fallback if needed) |
| Datalog query timeout            | reject with timeout.deadline   |
| HNSW index missing               | rebuild background; lexical    |
|                                  | search in the meantime         |

## Performance

- Single property fetch: <1ms
- Bounded traversal (depth 3, fanout 10): <20ms
- HNSW similarity top-K: <10ms p99
- Bulk assert (1k facts): <500ms

## Acceptance criteria

- [ ] CozoDB starts on rocksdb backend reliably
- [ ] Schema migrations run forward-only
- [ ] Bitemporal queries match `BITEMPORAL-FACTS.md`
- [ ] Stored rules are loaded at startup
- [ ] Vector index works for entity lookup

## References

- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/BITEMPORAL-FACTS.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `02-platform/STORAGE-LAYOUT.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[SEMANTIC-GRAPH]]  [[STORAGE-LAYOUT]]
