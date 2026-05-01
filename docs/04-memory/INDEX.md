---
id: memory-index
title: Memory — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Memory

Six memory layers, bitemporal facts, dreaming, drift mitigation.

## Architecture

- `MEMORY-ARCHITECTURE.md` — the six layers and consolidation flow.
- `MEMORY-FACADE.md` — the `kiki-memory` Rust crate, `MemoryStore` trait.

## Per-layer SPECs

- `SENSORY-BUFFER.md` — RAM-only ring buffer (rtrb + memmap2).
- `WORKING-MEMORY.md` — current context, identity-reserved tokens.
- `EPISODIC-MEMORY.md` — LanceDB native versioning as transaction time.
- `LANCEDB-INTEGRATION.md` — episodic specifics, hash column for tamper-evidence.
- `SEMANTIC-GRAPH.md` — CozoDB Datalog + bitemporal Validity.
- `COZODB-INTEGRATION.md` — Datalog patterns and integration.
- `BITEMPORAL-FACTS.md` — valid time + transaction time + supersession.
- `PROCEDURAL-MEMORY.md` — TOML+Markdown files + sqlite-vec sidecar.
- `IDENTITY-FILES.md` — SOUL, IDENTITY, USER as Markdown in git.

## Cross-cutting

- `COMPACTION.md` — five-tier compaction with cache pinning and L3 background notes.
- `RETRIEVAL.md` — hybrid search, recall over precision.
- `DREAMING.md` — LIGHT, REM, DEEP phases.
- `PRUNING.md` — retention policy.
- `CONSENT-FLOW.md` — non-bypassable identity changes.
- `CONTRADICTION-RESOLUTION.md` — classifier + user prompts.
- `DRIFT-MITIGATION.md` — four categories of drift, signals, recovery.
