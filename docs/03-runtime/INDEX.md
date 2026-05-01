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

- `AGENTD-DAEMON.md` — central daemon: process structure, startup, supervision.
- `INFERENCE-ROUTER.md` and `INFERENCE-ENGINE.md` — `inferenced` internals.
- `MODEL-REGISTRY.md` and `INFERENCE-MODELS.md` — model catalog and routing.
- `TOOL-DISPATCH.md` and `TOOLREGISTRY.md` — tool dispatch + registry.
- `CAPABILITY-GATE.md` and `ARBITER-CLASSIFIER.md` — `policyd` internals.

## Agent execution

- `AGENT-LOOP.md` — 10-step inference cycle.
- `COORDINATOR.md` — rule-based event triage.
- `EVENT-BUS.md` — internal tokio mpsc bus.
- `LOOP-BUDGET.md` — circuit breaker per task.
- `HOOKS.md` — 18+ hook points × 3 modes.
- `MAILBOX.md` — durable async messaging.
- `SUBAGENTS.md` — Fork / Teammate / Worktree.

## Lifecycle

- `WORKSPACE-LIFECYCLE.md` — parallel sessions, hibernation, concurrency.
- `UPDATE-ORCHESTRATOR.md` — bootc / sysext / app update coordination.
