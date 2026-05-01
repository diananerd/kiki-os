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
- `../../specs/MEMORY-FACADE.md` — the `kiki-memory` Rust crate, `MemoryStore` trait.

## Per-layer SPECs

- `../../specs/SENSORY-BUFFER.md` — RAM-only ring buffer (rtrb + memmap2).
- `../../specs/WORKING-MEMORY.md` — current context, identity-reserved tokens.
- `../../specs/EPISODIC-MEMORY.md` — LanceDB native versioning as transaction time.
- `../../specs/LANCEDB-INTEGRATION.md` — episodic specifics, hash column for tamper-evidence.
- `../../specs/SEMANTIC-GRAPH.md` — CozoDB Datalog + bitemporal Validity.
- `../../specs/COZODB-INTEGRATION.md` — Datalog patterns and integration.
- `../../specs/BITEMPORAL-FACTS.md` — valid time + transaction time + supersession.
- `../../specs/PROCEDURAL-MEMORY.md` — TOML+Markdown files + sqlite-vec sidecar.
- `../../specs/IDENTITY-FILES.md` — SOUL, IDENTITY, USER as Markdown in git.

## Cross-cutting

- `../../specs/COMPACTION.md` — five-tier compaction with cache pinning and L3 background notes.
- `../../specs/RETRIEVAL.md` — hybrid search, recall over precision.
- `../../specs/DREAMING.md` — LIGHT, REM, DEEP phases.
- `../../specs/PRUNING.md` — retention policy.
- `../../specs/CONSENT-FLOW.md` — non-bypassable identity changes.
- `../../specs/CONTRADICTION-RESOLUTION.md` — classifier + user prompts.
- `../../specs/DRIFT-MITIGATION.md` — four categories of drift, signals, recovery.
