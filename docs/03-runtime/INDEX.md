---
id: runtime-index
title: Runtime — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Runtime

The agent harness layer: five daemons, agent loop, capability gate, hooks, mailbox, subagents, workspaces.

## Daemons

- `../specs/AGENTD-DAEMON.md` — central daemon: process structure, startup, supervision.
- `../specs/INFERENCE-ROUTER.md` and `../specs/INFERENCE-ENGINE.md` — `inferenced` internals.
- `../specs/MODEL-REGISTRY.md` and `INFERENCE-MODELS.md` — model catalog and routing.
- `../specs/TOOL-DISPATCH.md` and `../specs/TOOLREGISTRY.md` — tool dispatch + registry.
- `../specs/CAPABILITY-GATE.md` and `../specs/ARBITER-CLASSIFIER.md` — `policyd` internals.

## Agent execution

- `../specs/AGENT-LOOP.md` — 10-step inference cycle.
- `../specs/COORDINATOR.md` — rule-based event triage.
- `../specs/EVENT-BUS.md` — internal tokio mpsc bus.
- `../specs/LOOP-BUDGET.md` — circuit breaker per task.
- `../specs/HOOKS.md` — 18+ hook points × 3 modes.
- `../specs/MAILBOX.md` — durable async messaging.
- `../specs/SUBAGENTS.md` — Fork / Teammate / Worktree.

## Lifecycle

- `../specs/WORKSPACE-LIFECYCLE.md` — parallel sessions, hibernation, concurrency.
- `../specs/UPDATE-ORCHESTRATOR.md` — bootc / sysext / app update coordination.
