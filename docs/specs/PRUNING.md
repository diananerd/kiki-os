---
id: pruning
title: Pruning
type: SPEC
status: draft
version: 0.0.0
implements: [pruning]
depends_on:
  - memory-architecture
  - episodic-memory
  - semantic-graph
  - procedural-memory
  - audit-log
depended_on_by: []
last_updated: 2026-04-30
---
# Pruning

## Purpose

Specify retention and pruning rules across the six layers: what gets dropped, what gets kept, who decides, and how the user controls the policy. Pruning is the offset to consolidation; without it, episodic memory grows unbounded.

## Defaults per layer

```
Sensory     bounded RAM ring; oldest discarded automatically
Working     compaction-driven; never disk-pruned
Episodic    cap 10GB by default; 90 days raw + summaries indefinite
Semantic    indefinite; closed facts retained unless user requests
Procedural  indefinite; user-managed
Identity    indefinite; never auto-pruned
Audit       indefinite; tamper-evident
```

These are defaults; users can tighten or relax via Settings.

## Episodic pruning

The most active pruner. Triggers:

- Disk cap reached (default 10GB)
- Per-row age policy
- Explicit user request

Order of operations:

1. **Drop pre-summary turns** older than `prune_after_days` (default 90). Their session summary is kept.
2. **Drop summaries** older than `summary_retention_days` (default unlimited; user can set).
3. **Drop low-relevance** sessions (e.g., zero retrieval hits in 6 months) before high-relevance ones, when budget pressure persists.

Pinned episodes (user-marked "remember") are never pruned.

Each prune emits an audit event with the row count and the rationale.

## Semantic pruning

Semantic facts are bitemporal; we don't *delete* facts, we close them in transaction time. Pruning means:

- Garbage-collect closed facts whose `known_to` is older than `closed_retention_days` AND that are not linked from audit
- Reduce confidence on stale facts (this is technically dreaming's job; pruning is just storage)

Active facts are never auto-pruned; the user can retract explicitly.

## Procedural pruning

Recipes are user-owned; we don't auto-prune them. We may flag unused recipes ("haven't been used in 6 months") for user review. The user decides.

## Identity pruning

Never auto-pruned. Reset is explicit (`kiki-memory identity reset`) and archives the prior state under `archived/`.

## Audit log pruning

Audit log entries are part of the Merkle chain. We don't *prune* in the conventional sense; we *roll over* segments after a year (default) and keep them, but on-device the active chain is cleared at rollover. Rollover writes the head hash; the rolled segment is archived (filesystem move, optionally exported).

See `AUDIT-LOG.md`.

## Quotas

Per layer:

```
Episodic    10 GB (configurable up to disk free)
Semantic    no quota by default; warn at 5 GB
Procedural  100 MB warn
Identity    10 MB warn
```

When a quota is hit, pruning runs. If pruning can't free enough, writes to that layer are refused with `budget.cost_exhausted` and the user is notified.

## User policies

The user can set:

```toml
# /var/lib/kiki/users/<uid>/memory/policy.toml
[episodic]
cap_gb = 10
prune_after_days = 90
summary_retention_days = 0          # 0 = indefinite

[semantic]
prune_closed_after_days = 365

[redaction]
on_redact_drop_embeddings = true
```

Policy hot-reloads; effective immediately.

## Right-to-erasure

A user can request "erase everything from before date T" or "erase everything about entity E":

```
kiki-memory erase --before=2024-01-01 --confirm
kiki-memory erase --entity=user-7 --confirm
```

These run as a careful, audited operation:

- Mark target rows for deletion in episodic
- Close target facts in semantic
- Remove relevant procedural recipes (with diff for review)
- Audit log records the erasure event with the user as actor

The audit Merkle chain remains; we audit the deletion.

## Restore

Snapshots (btrfs) provide restore points. Within snapshot retention:

```
kiki-memory restore --from-snapshot=<name>
```

Restores the memory directory to that snapshot. Used for accidental erases.

## Capability

```
agent.memory.prune                  ElevatedConsent
agent.memory.erase                  ElevatedConsent
```

System-initiated pruning under default policy needs no per-call grant; it runs as memoryd's housekeeping with audit. User-initiated erase always requires confirmation.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Disk full mid-prune              | back off; alert user           |
| Pinned row hits prune attempt    | skip; log; never delete        |
| Audit write fails                | abort the prune; preserve data |
| Quota hit but nothing prunable   | refuse new writes; notify user |

## Performance

- Episodic prune (10k rows): <30s, off the hot path
- Semantic close + GC: <10s typical
- Audit rollover: <60s once a year

## Acceptance criteria

- [ ] Pruning honors retention configuration
- [ ] Pinned rows are never deleted
- [ ] User-initiated erase is confirmed and audited
- [ ] Restore from snapshot works
- [ ] Quotas are enforced; user notified at threshold
- [ ] Right-to-erasure removes targeted data

## References

- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/EPISODIC-MEMORY.md`
- `04-memory/SEMANTIC-GRAPH.md`
- `02-platform/FILESYSTEM-BTRFS.md`
- `10-security/AUDIT-LOG.md`
