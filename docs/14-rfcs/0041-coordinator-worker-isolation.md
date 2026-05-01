---
id: 0041-coordinator-worker-isolation
title: Coordinator/Worker Isolation for Subagents
type: ADR
status: draft
version: 0.0.0
depends_on: [0038-camel-trifecta-isolation, 0040-arbiter-classifier-two-stage]
last_updated: 2026-04-29
depended_on_by:
  - 0042-sidechain-jsonl-subagents
---
# ADR-0041: Coordinator/Worker Isolation for Subagents

## Status

`accepted`

## Context

Some agent tasks naturally split into reasoning (the coordinator) and action (workers that execute narrow sub-tasks). If the coordinator has both reasoning and broad tool capabilities, an injection that hijacks the coordinator's context can take broad action. Restricting the coordinator's capabilities while delegating action to narrowly-scoped workers contains the blast radius.

## Decision

For subagent dispatch in trifecta-prone domains (web browsing, email reading, document processing), use the **Coordinator/Worker** pattern: the coordinator has reasoning + planning tools but **no direct external-effect tools**. Workers are spawned per sub-task with **narrow, sub-task-specific capability scopes** that cannot be widened. Workers return structured results to the coordinator via Cap'n Proto schemas. The capability gate enforces the worker's scope at every call.

## Consequences

### Positive

- An injection that lands on the coordinator cannot directly exfiltrate or send.
- Workers are bounded; their capability scope is proven minimal at spawn time.
- Audit log captures the parent/child relationship and each worker's scope.
- Composable with CaMeL: workers themselves can adopt the planner/parser split when they touch untrusted content.

### Negative

- More subagent spawns = more inference cost; the planner/orchestrator overhead is real.
- Structured handoff schemas must be maintained per worker type.
- Designing the coordinator to be useful without effectful tools requires care.

## Alternatives considered

- **Flat agent with broad capabilities**: simplest, most vulnerable.
- **Capability dampening on the planner**: drop a tool's effect after-the-fact based on context; brittle.
- **Per-call capability prompts only**: prompts fatigue users; doesn't catch sophisticated injection that crafts plausible-looking calls.

## References

- `03-runtime/SUBAGENTS.md`
- `11-agentic-engineering/MULTI-AGENT-POLICY.md`
- `10-security/CAMEL-PATTERN.md`
- `03-runtime/CAPABILITY-GATE.md`
