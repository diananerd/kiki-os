---
id: 0043-workspaces-model
title: Workspaces Model for Parallel Agentic Sessions
type: ADR
status: draft
version: 0.0.0
depends_on: [0014-rust-only-shell-stack]
last_updated: 2026-04-29
---
# ADR-0043: Workspaces Model for Parallel Agentic Sessions

## Status

`accepted`

## Context

Users routinely have multiple ongoing agentic tasks: drafting a document, planning a trip, monitoring a long process. Forcing them into a single linear conversation is wrong; spawning a fresh agent per click is wasteful. We want first-class parallel sessions that can be paused, resumed, and isolated, with cost predictable per session.

## Decision

Introduce **workspaces** as the unit of an agent session. Each workspace owns its conversation context, latches, working memory, tool grants snapshot, and (optionally) a worktree for files. Lifecycle states: **Active** (in front of the user), **Background** (running but not foreground), **Hibernated** (frozen via cgroup freezer; KV cache evicted; can be resumed), **Archived** (transcript persisted; KV gone). Workspaces are per-user; cross-user access requires explicit grants.

## Consequences

### Positive

- Users can parallelize without merging contexts.
- Hibernation via cgroup freezer reclaims memory cheaply; resume is fast.
- Cost is per-workspace; user can see and cap.
- Each workspace has its own audit subtree, simplifying review.
- The agent loop's cycle budget applies per workspace, so a runaway in one doesn't drain another.

### Negative

- More state to manage (lifecycle transitions, GC, per-workspace policies).
- Resume from hibernation requires re-loading context tokens; a small "warm-up" cost.
- UX must clearly show which workspace is active.

## Alternatives considered

- **Single linear conversation**: forces context contention; users routinely lose track.
- **One-off sessions per click**: cheap to start but no continuity; loses memory benefits.
- **Threads-as-data only**: stores transcripts but doesn't formalize the runtime resources around them.

## References

- `03-runtime/WORKSPACE-LIFECYCLE.md`
- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/LOOP-BUDGET.md`
- `11-agentic-engineering/COST-CONTROL.md`
## Graph links

[[0014-rust-only-shell-stack]]
