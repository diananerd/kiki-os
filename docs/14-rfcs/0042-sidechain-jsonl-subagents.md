---
id: 0042-sidechain-jsonl-subagents
title: Sidechain JSONL for Subagent Transcripts
type: ADR
status: draft
version: 0.0.0
depends_on: [0041-coordinator-worker-isolation]
last_updated: 2026-04-29
---
# ADR-0042: Sidechain JSONL for Subagent Transcripts

## Status

`accepted`

## Context

Subagent transcripts can be long. If they live in the parent's context, they bloat tokens and break cache discipline. If they vanish, audits and debugging suffer. We need a place to put subagent intermediate steps that is durable, queryable, and out of the parent's context.

## Decision

Persist each subagent's full transcript as a **JSONL file in a sidechain directory**: `/var/lib/kiki/sidechains/<session-id>/<subagent-id>.jsonl`. Each line is one event (turn, tool call, tool result, decision). The parent context contains only the subagent's *result* (typed via Cap'n Proto), not the trace. The audit log records a pointer to the sidechain file. Sidechains are GC'd per retention policy (default 30 days; longer if linked from an audit entry under investigation).

## Consequences

### Positive

- Parent context stays small; cache hit rate preserved.
- Auditors can review full subagent traces independently of parent.
- JSONL is easy to grep, replay, and feed back into evaluation.
- Cheap: append-only file writes; no extra DB engine.
- Retention policy keeps disk bounded.

### Negative

- One more directory tree to manage; we keep the path discipline strict.
- JSONL is line-oriented but tool results may be large; we cap per-line size and reference larger blobs by content hash.
- Sidechains are not a queryable store — for cross-session search we use the audit log and memory.

## Alternatives considered

- **Inline subagent traces in parent context**: blows the cache and wastes tokens.
- **Database for subagent transcripts**: heavier than needed; JSONL is sufficient.
- **No persistence**: blind audits.
- **Persist only outcomes**: loses the diagnosis trail when something goes wrong.

## References

- `03-runtime/SUBAGENTS.md`
- `11-agentic-engineering/MULTI-AGENT-POLICY.md`
- `10-security/AUDIT-LOG.md`
