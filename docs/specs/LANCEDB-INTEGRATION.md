---
id: lancedb-integration
title: LanceDB Integration
type: SPEC
status: draft
version: 0.0.0
implements: [lancedb-integration]
depends_on:
  - memory-architecture
  - episodic-memory
  - storage-layout
depended_on_by:
  - episodic-memory
last_updated: 2026-04-30
---
# LanceDB Integration

## Purpose

Specify how LanceDB is configured, embedded, and operated as the episodic memory store: directory layout, version retention, index tuning, embedder integration, hash-column tamper-evidence, backup format.

## Why LanceDB

- Pure Rust client, no Python runtime needed
- Vector + scalar columns in one table
- Native versioning (each commit is a transaction; "time-travel queries" are first-class)
- Arrow-native storage; backups are file copies
- Index types we need (IVF_PQ, HNSW) are first-class

## Layout

```
/var/lib/kiki/users/<uid>/memory/episodic/
├── episodes.lance/                    table dir
├── summaries.lance/
├── _versions/                         LanceDB version metadata
└── config.toml                        per-user tuning
```

A LanceDB dataset is a directory; backups are recursive copies. Btrfs snapshots (per `FILESYSTEM-BTRFS.md`) cover this naturally.

## Configuration

```toml
# config.toml
[index.episodes]
type = "ivf_pq"
num_partitions = 256
num_sub_vectors = 16
metric = "cosine"

[index.summaries]
type = "ivf_pq"
num_partitions = 64
num_sub_vectors = 16
metric = "cosine"

[retention]
keep_versions = 30           # number of LanceDB versions retained
prune_after_days = 90        # pre-summary turns older than this

[ingest]
batch_size = 256
embedder = "bge-m3@1.5.0"
```

The embedder version is tracked: re-embedding old data after a model bump is a background task; queries against pre-bump data still work via the older index until reembed completes.

## Versioning

LanceDB writes each commit as a new version. We use this for:

- **Transaction time queries**: "what did we believe on Tuesday?"
- **Cheap rollback**: revert to a prior version if a bad ingest corrupts data
- **Audit linkage**: each version id is recorded in the audit log

`keep_versions` bounds disk; older versions are pruned by a maintenance task.

## Hash column

```
hash = sha256(prev_hash || canonical_bytes(row_minus_hash))
```

Where `prev_hash` is the previous row in the same session (or zero for the first). The episodic head is mirrored to the audit log every 100 inserts, giving tamper-evidence even if LanceDB itself is modified out-of-band.

`canonical_bytes` is the row encoded with sorted field names and a fixed timestamp format, so verification is deterministic across LanceDB versions.

## Indexes

- **Episodes embedding**: IVF_PQ (storage-efficient; recall sufficient for top-K=20).
- **Summaries embedding**: IVF_PQ.
- **Scalar B-tree**: on `session_id`, `user_id`, `timestamp`.

Indexes rebuild on schema migration or after large bulk writes; rebuilds run in the background and the search path falls back to a sequential scan during rebuild.

## Embedder

Default: bge-m3 (multilingual, 1024-dim). Embedder runs in inferenced; memoryd calls it via Cap'n Proto. Batched for efficiency; agent-path writes can flush early.

A re-embed CLI:

```
kiki-memory reembed --since=<date> --model=<id>
```

runs as a background job (rate-limited). Newly inserted rows always use the active embedder.

## Search API

```rust
struct Episodic {
    fn search(&self, q: &EpisodicQuery) -> Result<Vec<Hit>>;
    fn append(&self, row: EpisodeRow) -> Result<EpisodeId>;
    fn redact(&self, id: EpisodeId, reason: &str) -> Result<()>;
    fn time_travel(&self, ts: DateTime) -> Result<EpisodicView>;
}
```

`EpisodicQuery` carries scalar filters, vector, top-K, and optional time filter.

## Time travel

```rust
let view = episodic.time_travel(yesterday)?;
let hits = view.search(&query)?;
```

Internally, this opens the LanceDB dataset at the version active at `yesterday`. Queries against the view see the historical state.

## Backup

Btrfs snapshot of `/var/lib/kiki/users/<uid>/memory/episodic/`. The snapshot is consistent because LanceDB commits are atomic at the filesystem level. Restoring a snapshot just replaces the directory.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Index missing or corrupt         | rebuild background; scalar     |
|                                  | search in the meantime         |
| Embedder unavailable             | queue ingest; serve scalar     |
| LanceDB version pruning fails    | log; alert; do not block       |
|                                  | writes                         |
| Hash chain mismatch              | quarantine session; alert      |
|                                  | maintenance                    |

## Performance

- Vector search top-20 over 1M rows: <50ms p99
- Append + embed: <100ms p99
- Time-travel open: <50ms

## Acceptance criteria

- [ ] LanceDB dataset opens cleanly across reboots
- [ ] Versioning lets us run "as of" queries
- [ ] Hash chain holds and is verified by `kiki-memory verify`
- [ ] Embedder version is tracked per row
- [ ] Index rebuild runs in the background without blocking

## References

- `04-memory/EPISODIC-MEMORY.md`
- `04-memory/RETRIEVAL.md`
- `02-platform/STORAGE-LAYOUT.md`
- `02-platform/FILESYSTEM-BTRFS.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[EPISODIC-MEMORY]]  [[STORAGE-LAYOUT]]
