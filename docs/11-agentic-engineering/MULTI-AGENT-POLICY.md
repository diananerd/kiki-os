---
id: multi-agent-policy
title: Multi-Agent Policy
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - subagents
  - harness-patterns
  - cost-control
last_updated: 2026-04-29
---
# Multi-Agent Policy

## Purpose

Decide when to spawn subagents and when not to.
Multi-agent setups are often the right answer; just as
often they add latency, cost, and confusion without
helping. This document captures Kiki's policy and the
reasoning behind it.

## The temptation

Multi-agent architectures are seductive: a "researcher"
that searches, a "writer" that drafts, a "critic" that
reviews. In practice, much of the time:

- Two agents in sequence are slower than one strong agent
  doing both
- Two agents in parallel coordinate badly without explicit
  protocol
- Each subagent duplicates context loading, which is
  expensive
- The handoff format becomes its own surface for bugs

Empirical findings (Anthropic Cookbook, AnyAgent, Multi-
Agent-Experiments, internal eval): single-agent baselines
beat poorly-designed multi-agent systems in most tasks
under 10 minutes. Multi-agent wins clearly when:

- Sub-tasks are genuinely independent and parallelizable
- A single agent's context would blow up under the union
  of tasks
- Sub-tasks need different tool sets or different
  capability scopes
- The orchestrator is small and the workers are
  specialized (not the other way around)

## Kiki's policy

### Default: single agent

Run the agent loop. Do not spawn subagents unless one of
the triggers below applies.

### Triggers for subagent dispatch

1. **Independent parallelism**: the planner identifies ≥3
   sub-tasks with no dependencies between them. Fork-join
   pattern: dispatch them to subagents in parallel,
   collect results.
2. **Capability isolation**: a sub-task needs capabilities
   the parent shouldn't have. Spawn a worker with a
   narrow capability scope. Coordinator/Worker pattern.
3. **Context isolation**: the sub-task processes
   untrusted data and we don't want it polluting the
   parent's context. CaMeL pattern's quarantined parser
   is a special case.
4. **Workspace isolation**: a sub-task may make changes
   to files; do them in a worktree so the parent can
   diff and accept/reject.
5. **Budget partitioning**: a sub-task is allowed to
   spend up to N tokens; bound it explicitly.

### Triggers against

- The sub-task is small (<5 cycles in the agent loop).
  Just do it inline.
- The sub-task depends sequentially on the parent's
  thinking. Subagent overhead is pure waste.
- The orchestration logic itself is complex. If the
  orchestrator's prompt is bigger than the workers',
  reconsider.

## Patterns

### Fork

```
Parent   ─┬──▶ Subagent A ──▶ result A
          ├──▶ Subagent B ──▶ result B
          └──▶ Subagent C ──▶ result C
                                 │
                Parent collects results, continues
```

Use for: parallel independent searches, parallel file
analyses, A/B comparisons.

Constraints: each subagent inherits a snapshot of the
parent's context (or a curated subset). Results flow
back as structured data, not free-form continuations.

### Teammate

```
Parent  ◀──messages──▶  Teammate (long-lived, own context)
```

A teammate has its own session, its own memory, its own
specialty. The parent communicates via structured
messages.

Use for: ongoing collaborations with a specialized agent
(e.g., a domain expert agent the user keeps).

Cost: high. Each teammate is a long-running session.
Justified only when the specialty is consistently useful.

### Worktree

```
Parent  ──spawn(workspace)──▶  Worker on isolated branch
                                 │
                            Worker makes changes, returns
                            diff
Parent  ◀──diff──             Parent reviews, accepts or
                              rejects
```

Use for: code changes, document edits, configuration
changes that should be reviewable.

The worktree pattern matches what `WORKSPACE-LIFECYCLE.md`
describes for parallel agentic sessions.

### Coordinator/Worker

```
Coordinator  ──plan──▶  Worker 1 (capability X)
             ──plan──▶  Worker 2 (capability Y)
             ◀──results──
```

Coordinator has reasoning + planning capabilities but no
direct tool dispatch. Workers have narrow capabilities
each. Defends against an injected coordinator escalating
to broad action.

Used heavily in injection-prone domains (reading email,
browsing the web).

### Sidechain JSONL

Subagent transcripts are persisted as JSONL files in a
sidechain directory. The parent's context only contains
the result, not the subagent's intermediate steps. The
audit log links to the sidechain for traceability.

Benefits:

- Parent context stays small
- Auditability preserved
- Subagent transcripts can be reviewed independently

Used by all subagent patterns above.

## Coordination protocols

When subagents need to coordinate:

- **Structured handoff**: subagent returns a typed
  result (Cap'n Proto schema). The parent doesn't
  read free-form text.
- **Explicit lifecycle**: the parent knows when each
  subagent starts, runs, and ends. No fire-and-forget.
- **Error propagation**: subagent errors flow back as
  `ErrorPayload`; the parent decides whether to retry,
  reroute, or surface.
- **Capability scoping**: each subagent's capability
  scope is set at spawn time and cannot be widened.

## Context budget for multi-agent

A subagent's context is *not free*. Each spawn:

- Allocates a fresh KV cache
- May replicate sticky latches and identity facts
- Adds latency for the first inference
- Adds tokens to the parent's context (the result + any
  metadata)

The parent's loop budget (`LOOP-BUDGET.md`) accounts for
this: a subagent dispatch costs N cycles' worth of
budget, decided per pattern.

## Cost considerations

Spawn cost vs. inline cost:

- Inline tool call: ~1 turn
- Subagent (Fork): ~3-5 turns equivalent (spawn, exec,
  result handling)
- Teammate: ~10+ turns (sustained session)
- Worktree: variable, depends on the work; minimum ~5

The harness should prefer inline unless the parallel or
isolation benefit clearly exceeds the spawn cost.

## Anti-patterns

- **Mandatory subagents**: "every task goes through a
  planner that delegates to a worker." Adds latency on
  every task; only justified for narrow domains.
- **Hierarchical agents that aren't really independent**:
  the parent waits on the child anyway. Just inline.
- **Subagents that share mutable state**: race
  conditions, hard to debug. Pass results, not state.
- **Subagents with unbounded budget**: cost blow-up
  from one bad task.
- **Result aggregation by another LLM call**: parent uses
  a third agent just to merge results. Often a sign the
  partition was wrong.

## When the user spawns

The user can spawn explicit subagents (Skills,
Subagents directory in `~/.kiki/subagents/`). These have
their own scope and are governed by the same patterns.

The harness should respect user-spawned subagents as
peers; the agent loop calls them when appropriate but
doesn't manage their lifecycle beyond the current
invocation.

## Evaluation

Multi-agent designs are evaluated against single-agent
baselines on the same task:

- Time to completion
- Quality (judged by reference or LLM-as-judge with care)
- Token cost
- Capability surface (smaller is better when equal)

A multi-agent design that doesn't beat the baseline on at
least two of these is rejected.

## References

- `00-foundations/PRINCIPLES.md`
- `03-runtime/SUBAGENTS.md`
- `03-runtime/WORKSPACE-LIFECYCLE.md`
- `03-runtime/LOOP-BUDGET.md`
- `10-security/CAMEL-PATTERN.md`
- `11-agentic-engineering/HARNESS-PATTERNS.md`
- `11-agentic-engineering/COST-CONTROL.md`
- `11-agentic-engineering/EVALUATION.md`
- Anthropic Cookbook (multi-agent systems)
- "Multi-Agent Hidden Costs" (research)
