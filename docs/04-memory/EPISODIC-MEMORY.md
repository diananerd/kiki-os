---
id: episodic-memory
title: Episodic Memory
type: SPEC
status: draft
version: 0.0.0
implements: [episodic-memory]
depends_on:
  - memory-architecture
  - lancedb-integration
  - audit-log
depended_on_by:
  - dreaming
  - lancedb-integration
  - pruning
  - retrieval
last_updated: 2026-04-30
---
# Episodic Memory

## Purpose

Specify the layer that holds the autobiography of past sessions: turns, summaries, and the embeddings that make them recallable. Episodic memory answers "what did we say last week?" and "find the conversation about X."

## Storage

LanceDB. See `LANCEDB-INTEGRATION.md` for table schemas and configuration.

## Why LanceDB

- Native versioning gives transaction time for free.
- Vector and scalar columns in the same table; hybrid search without joins to a separate vector store.
- Columnar Arrow storage: cheap to scan, easy to back up.
- Pure Rust client for tight integration with memoryd.

## Schema

```
table: episodes
  id              UUID
  session_id      UUID
  user_id         Text
  turn_index      Int
  role            Text          # user | assistant | tool
  content         Text
  embedding       FixedSizeList<Float32, 1024>   # bge-m3
  timestamp       Timestamp
  task_id         Text          (nullable)
  audit_id        Text          (link to audit log)
  hash            FixedSizeBinary<32>            # tamper-evidence
  redacted        Bool

table: summaries
  id              UUID
  session_id      UUID
  user_id         Text
  range_start     Timestamp
  range_end       Timestamp
  summary         Text
  embedding       FixedSizeList<Float32, 1024>
  generated_by    Text          # model id + version
  hash            FixedSizeBinary<32>
```

`hash` is `sha256(prev_hash || row_canonical_bytes)`, chained per session. Tamper-evident; the audit log mirrors the head.

## Lifecycle

```
1. A turn lands in working memory.
2. Working memory promotes the turn to episodic asynchronously
   (next idle quantum) — the agent loop is never blocked by ingest.
3. Embedder (bge-m3) computes the vector.
4. Row is inserted into the episodes table with a hash linking
   to the previous row in the same session.
5. The audit log records the insert.
6. The summarizer runs at session end, producing a row in
   summaries; old turns may be pruned per retention.
```

## Read paths

- **Vector search**: top-K nearest by embedding within filters
- **Scalar filter**: by session_id, task_id, time range
- **Hybrid**: vector ranked + scalar pre-filter
- **Time travel**: query "as of" via LanceDB's native versioning

The retrieval layer (`RETRIEVAL.md`) composes these.

## Write controls

`agent.memory.write.episodic` required. Ingestion runs in memoryd's writer task; the agent loop only enqueues.

## Per-user partition

Each user has their own LanceDB dataset under
`/var/lib/kiki/users/<uid>/memory/episodic/`.

## Tamper-evidence

Each row's hash chains the previous. The audit log mirrors the head every N inserts; tampering invalidates a chain segment that the audit log can detect.

```
kiki-memory verify episodic --user=<uid>
```

## Retention

Configurable per user; default cap 10GB. When the cap is hit:

- Pre-summary turns older than 90 days: dropped (summary remains)
- Post-summary period: keep summaries indefinitely
- User-pinned episodes: never pruned

See `PRUNING.md`.

## Redaction

A user can redact specific episodes:

- Mark `redacted = true`
- The content field is replaced with a placeholder
- The hash chain is updated with a redaction-aware variant
  (the rewrite is itself audited)

The audit log shows the redaction event; the previous content
is *not* recoverable from the episodic store after redaction.

## Capabilities

```
agent.memory.read.episodic
agent.memory.write.episodic
agent.memory.redact.episodic     ElevatedConsent
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Vector index corrupt             | rebuild; degrade to scalar     |
|                                  | search until ready             |
| Embedding model unavailable      | queue ingestion; serve scalar  |
| Tamper detected                  | quarantine session; alert      |
| Cap exceeded                     | apply pruning; if still over,  |
|                                  | refuse new writes              |

## Performance

- Vector search top-20: <50ms p99 on Pro hardware
- Insert: <100ms p99 (off the hot path anyway)
- Time-travel query: <200ms p99

## Acceptance criteria

- [ ] Per-user dataset isolation
- [ ] Hash chain enforced; verify CLI works
- [ ] Vector + scalar hybrid search supported
- [ ] Time-travel queries return historical rows
- [ ] Redaction is audited and irreversible
- [ ] Retention cap enforced

## References

- `04-memory/LANCEDB-INTEGRATION.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/RETRIEVAL.md`
- `04-memory/PRUNING.md`
- `10-security/AUDIT-LOG.md`
