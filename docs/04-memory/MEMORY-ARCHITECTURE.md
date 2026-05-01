---
id: memory-architecture
title: Memory Architecture
type: DESIGN
status: draft
version: 0.0.0
implements: [memory-architecture]
depends_on:
  - principles
  - agentd-daemon
  - storage-layout
depended_on_by:
  - bitemporal-facts
  - compaction
  - consent-flow
  - contradiction-resolution
  - cozodb-integration
  - dreaming
  - drift-mitigation
  - episodic-memory
  - identity-files
  - lancedb-integration
  - memory-facade
  - memory-sync
  - privacy-model
  - procedural-memory
  - pruning
  - retrieval
  - semantic-graph
  - sensory-buffer
  - working-memory
last_updated: 2026-04-30
---
# Memory Architecture

## Problem

An agent that genuinely lives with a user accumulates state — turns, facts, preferences, routines, the user's identity model. A monolithic conversation log is the wrong shape: it loses structure, blows past context windows, and confuses "what was said" with "what is true". A single vector store is also wrong: not everything is best searched by similarity, and not all facts are equal.

We need an architecture that distinguishes:

- the immediate sensory stream
- the active working set
- the autobiography of past sessions
- the user's facts as a graph that evolves over time
- how-to recipes the agent has learned
- the identity model itself, treated with care

## Constraints

- **Local-first.** Memory lives on the device; backups are user-controlled.
- **Per-user partition.** A device with multiple users keeps memories separate.
- **Bitemporal where it matters.** Facts can change; we need to know what was true *and* what we believed at any given time.
- **Tamper-evident.** Memory writes are auditable; identity changes require explicit consent.
- **Performance budget.** Recall <200ms p99; ingest doesn't block the agent loop.
- **Graceful drift.** Old beliefs become outdated; we mitigate, we do not pretend perfect recall.

## Decision

Six memory layers, each with a different role, store, and lifecycle:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 0  Sensory     RAM ring buffer (rtrb + memmap2)       │
│           audio frames, raw transcripts, transient signals  │
│           lifetime: seconds to minutes                       │
├─────────────────────────────────────────────────────────────┤
│ Layer 1  Working     in-process active context               │
│           current task, latches, recent turns                │
│           lifetime: session                                  │
├─────────────────────────────────────────────────────────────┤
│ Layer 2  Episodic    LanceDB (vector + scalar)               │
│           per-session transcripts and summaries              │
│           lifetime: months to years (retention policy)       │
├─────────────────────────────────────────────────────────────┤
│ Layer 3  Semantic    CozoDB (Datalog graph, Validity type)   │
│           bitemporal facts about entities                    │
│           lifetime: indefinite, with supersession            │
├─────────────────────────────────────────────────────────────┤
│ Layer 4  Procedural  TOML+Markdown files + sqlite-vec sidecar│
│           how-to recipes, learned skills                     │
│           lifetime: indefinite, version-controlled           │
├─────────────────────────────────────────────────────────────┤
│ Layer 5  Identity    Markdown in a per-user git repo         │
│           SOUL, IDENTITY, USER files                         │
│           lifetime: lifetime; non-bypassable consent         │
└─────────────────────────────────────────────────────────────┘
```

A hot-path KV store (**redb**) sits beside Working memory for O(1) lookups (latches, session metadata). DuckDB and SQLite are used for analytics and small structured tables. Git provides the version-controlled substrate under Identity.

## Rationale

### Why six layers and not one

Memory in cognitive psychology is not monolithic; neither should be a system that lives with you. Each layer has different access patterns, retention horizons, and trust requirements. Mixing them in one store has known failure modes (vector noise drowning facts, summaries overwriting raw evidence, identity changes happening invisibly).

### Why these specific stores

- **rtrb + memmap2** for sensory: lock-free ring buffer with a memory-mapped backing — bounded RAM, frame-level access, no syscalls on the hot path.
- **redb** for hot KV: pure Rust, mmap-backed, ACID, fast.
- **LanceDB** for episodic: native columnar with built-in vector indexing and *versioning* (transaction time for free).
- **CozoDB** for semantic: Datalog with a `Validity` type that gives us bitemporal facts natively.
- **sqlite-vec + TOML+Markdown** for procedural: human-editable files, tiny vector sidecar for retrieval.
- **Git + Markdown** for identity: every change is a commit, every commit is consent-flow-gated.
- **DuckDB** for analytics over the audit log and counters.

### Why bitemporal

Real life rewrites itself. "The user lives in Seattle" was true; now it isn't; and we must remember both. Bitemporal facts (valid time + transaction time) let us answer "what was true on Tuesday?" and "what did we believe on Tuesday?" — sometimes very different.

### Why git for identity

Identity is the most consequential category of memory. Git gives us:

- A reviewable history
- Atomic commits gated by consent
- Merge semantics for cross-device sync
- Cheap rollback if something goes wrong

The user can clone their identity repo, walk its history, see exactly what the agent learned about them and when.

### Why separate procedural from semantic

A how-to recipe ("when the user says X, do Y") is an executable artifact, not a fact about the world. Mixing it with semantic facts confuses retrieval and update semantics. Procedural memory is essentially the user's installed "skills"; we treat it as such.

## Consequences

### Per-layer surface

Each layer exposes a small, typed Cap'n Proto interface (see `MEMORY-FACADE.md`). The agent loop never queries a store directly; it goes through the facade.

### Consolidation flow

Recent activity flows downward over time:

```
Sensory ──▶ Working ──▶ Episodic ──▶ Semantic
                              │
                              └──▶ Procedural (when patterns recur)
                              └──▶ Identity   (with consent)
```

Consolidation runs in batches during quiet periods (see `DREAMING.md`); it is never on the agent's critical path.

### Read paths

A retrieval (see `RETRIEVAL.md`) typically hits:

1. Working (in-RAM, instant)
2. Identity files (small, always loaded)
3. Procedural recipes by relevance
4. Semantic graph for entity facts
5. Episodic search for past turns

Hybrid: vector + structured filters. Recall over precision.

### Multi-user

Per-user directory under `/var/lib/kiki/users/<user-id>/memory/`. Each layer is partitioned. Cross-user reads are denied by default; explicit grants per fact.

### Drift mitigation

Long-lived memories drift. We track:

- Recency
- Re-confirmation count
- Contradictions
- User corrections

See `DRIFT-MITIGATION.md`.

### Failure isolation

Each layer can degrade independently:

- Sensory unavailable: voice degrades but agent works
- Working capped: compaction more aggressive
- Episodic unavailable: no recall, but facts still queryable
- Semantic unavailable: facts fall back to raw episodic
- Procedural unavailable: recipes unavailable; agent reasons from scratch
- Identity unavailable: refuse high-stakes operations; surface error

The agent loop tolerates partial memory.

### Performance budget

| Layer        | Read p99 | Write p99 |
|--------------|----------|-----------|
| Sensory      | <100µs   | <100µs    |
| Working      | <500µs   | <1ms      |
| Episodic     | <50ms    | <100ms    |
| Semantic     | <20ms    | <50ms     |
| Procedural   | <10ms    | <20ms     |
| Identity     | <5ms     | (consent) |

Aggregate retrieval p99: <200ms.

### Storage budget

Default device profile:

```
Sensory     RAM only, ~16MB
Working     RAM, ~50MB
Episodic    disk, default cap 10GB; user-tunable
Semantic    disk, ~500MB typical
Procedural  disk, ~50MB
Identity    disk, ~10MB
```

Quotas enforced; eviction policy per `PRUNING.md`.

### Consent

Identity changes always go through `CONSENT-FLOW.md`. Other layers' writes are gated by capabilities (`agent.memory.write.episodic`, `.semantic`, `.procedural`).

## References

- `00-foundations/PRINCIPLES.md`
- `02-platform/STORAGE-LAYOUT.md`
- `04-memory/MEMORY-FACADE.md`
- `04-memory/SENSORY-BUFFER.md`
- `04-memory/WORKING-MEMORY.md`
- `04-memory/EPISODIC-MEMORY.md`
- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/PROCEDURAL-MEMORY.md`
- `04-memory/IDENTITY-FILES.md`
- `04-memory/CONSENT-FLOW.md`
- `04-memory/RETRIEVAL.md`
- `04-memory/DREAMING.md`
- `04-memory/DRIFT-MITIGATION.md`
