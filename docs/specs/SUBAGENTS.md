---
id: subagents
title: Subagents
type: SPEC
status: draft
version: 0.0.0
implements: [subagent-system]
depends_on:
  - agentd-daemon
  - agent-loop
  - capability-gate
  - mailbox
  - loop-budget
depended_on_by:
  - agent-bundle
  - loop-budget
  - multi-agent-policy
last_updated: 2026-04-30
---
# Subagents

## Purpose

Specify how the primary agent spawns subagents to handle isolated or parallel reasoning, with three distinct patterns: Fork (isolated context), Teammate (parallel coordinated), Worktree (persistent domain-scoped).

## Behavior

### The three patterns

```
FORK
   one-shot
   isolated context (no shared working memory)
   returns a result and ends
   use: speculative reasoning, what-if exploration

TEAMMATE
   parallel to primary agent
   shares some context (per declaration)
   may persist for a session
   use: coordinated multi-perspective tasks, code review, fact-checking

WORKTREE
   persistent across sessions
   scoped to a domain (e.g., one project, one client)
   has its own memory subset
   use: long-running projects with bounded context, domain experts
```

### Spawn flow

```
1. Caller emits SpawnSubagent (kind, task_description, context, capability_scope, model_pref, budget).
2. Capability check: caller has agent.subagent.spawn? scope is subset of caller's grants?
3. SubagentManager creates task; allocates SubagentId; builds initial context per kind; configures inference router scope; configures memory access.
4. Subagent task starts with own LoopBudget; runs own agent loop; tools dispatched through gate, checked against subagent's capability scope.
5. Communication:
   - Fork: returns result via channel; parent awaits.
   - Teammate: shares mailbox with parent; bidirectional.
   - Worktree: persists; messages routed via mailbox.
```

### Coordinator/Worker isolation

Crucial pattern for safety: when a subagent is spawned in Coordinator/Worker mode, the **Coordinator does not execute tools directly**. Coordinator's role is orchestration only:

- Spawns workers per subtask.
- Reads worker summaries.
- Synthesizes final response.

Workers do the actual tool execution. Each worker's journal is sidechain JSONL — never merged into Coordinator's context. This prevents prompt injection in worker output from manipulating the Coordinator.

### Capability scoping

Subagents inherit a subset of parent capabilities:

```toml
[fork.caps]
allow = ["data.calendar.read", "agent.tool.invoke.web_search"]
deny = ["network.outbound.host:*", "agent.memory.write.*"]
```

The capability gate checks subagent calls against this subset. Parent capabilities are not directly available; subagent has only what was scoped.

Subagents are safer than parent: a manipulated subagent has bounded blast radius.

### Memory access

| Kind | Memory access |
|---|---|
| Fork | read-only of provided context; no writes |
| Teammate | own working memory; reads parent's via msg pass |
| Worktree | subset of episodic + semantic per scope; writes to its own subset |

Forks cannot write to memory. Teammates write to their own working memory only; promoting to episodic happens only when parent integrates result. Worktrees can write to their scoped memory subset.

### Budgets

Per subagent:

| Kind | Default LoopBudget |
|---|---|
| Fork | 15 cycles |
| Teammate | 10 per turn |
| Worktree session | 50 cycles |
| Proactive cycle | 5 cycles |
| Hook-initiated | 10 cycles |

Time budget:

| Kind | Default |
|---|---|
| Fork | 30s |
| Teammate | session-bounded |
| Worktree | unbounded session |

Memory budget per subagent. Exceeding terminates with partial result.

### Lifecycle

```
Fork:        spawn → run → return result → done
Teammate:    spawn → message exchange → end-of-session → done
Worktree:    create → load → message exchange → unload (later reload) → indefinite
```

Forks and teammates are reaped at end. Worktrees persist state to disk.

### Concurrency limits

- Per-user max concurrent: 4.
- Per-task max nested depth: 2 (a subagent can spawn one more, no further).
- Per-app rate limits on `agent.subagent.spawn`.

These prevent runaway expansion.

### Audit

Every subagent operation audited:

```json
{"event": "subagent_spawned", "kind": "Fork", "id": "sub-abc",
 "parent": "primary", "user": "user-1", "caps_inherited": [...], "budget": {...}}

{"event": "subagent_message", "from": "sub-abc", "to": "primary", "size_bytes": 1234}

{"event": "subagent_completed", "id": "sub-abc", "outcome": "Success",
 "elapsed_ms": 4231, "loop_steps_used": 11}
```

### Sidechain JSONL pattern

For Workers in Coordinator/Worker mode:

```
/var/lib/kiki/users/<user>/agents/<worker_id>/sidechain.jsonl
```

Each line is one event (tool call, tool result, observation). Coordinator never reads this file; only the final summary. Replay possible by auditing sidechains.

This is the Claude Code pattern; documented in `14-rfcs/0042-sidechain-jsonl-subagents.md`.

## Interfaces

### Programmatic

```rust
struct SubagentManager {
    async fn fork(&self, req: ForkRequest) -> Result<ForkResult>;
    async fn spawn_teammate(&self, req: TeammateRequest) -> Result<TeammateId>;
    async fn create_worktree(&self, req: WorktreeRequest) -> Result<WorktreeId>;
    async fn send_to(&self, id: SubagentId, msg: Message) -> Result<()>;
    async fn recv_from(&self, id: SubagentId) -> Result<Message>;
    async fn terminate(&self, id: SubagentId) -> Result<()>;
    fn list_active(&self) -> Vec<SubagentInfo>;
    fn list_worktrees(&self, user: UserId) -> Vec<WorktreeInfo>;
}
```

### CLI

```
agentctl subagents list
agentctl subagents worktrees <user>
agentctl subagents kill <id>
agentctl subagents history <user>
```

## State

### In-memory

- Active subagent registry.
- Per-subagent task handles, channels, budgets.

### Persistent

- Worktree state at /var/lib/kiki/users/<user>/worktrees/<name>/:
  - manifest.toml (name, domain, caps, soul extension).
  - memory/ (scoped subset of memory).
  - state.toml (last activity).
- Subagent telemetry in DuckDB.

## Failure modes

| Failure | Response |
|---|---|
| Capability scope invalid | spawn denied |
| Budget exhausted | terminate; partial result; parent informed |
| Subagent crashes | terminate; parent receives error |
| Subagent attempts unauthorized tool | gate denies; logged; agent sees error |
| Worktree state corrupt | mark unloadable; user prompt to reset |
| Concurrency limit exceeded | spawn denied; queue or refuse |
| Recursive spawn beyond depth | spawn denied |
| Teammate mailbox full | drop message or block per policy |

## Performance contracts

- Fork spawn overhead: <100ms.
- Teammate spawn overhead: <200ms.
- Worktree load (cached): <500ms.
- Worktree load (cold): <2s.
- Per-subagent memory: ~50MB (loop state + working memory).
- Concurrent subagents: up to 4 per user on reference hardware.

## Acceptance criteria

- [ ] All three patterns work end-to-end.
- [ ] Capability scope enforced.
- [ ] Budgets terminate runaway subagents.
- [ ] Worktree state persists across agentd restart.
- [ ] Subagent crash does not affect parent.
- [ ] Audit log records spawn/message/completion.
- [ ] Concurrency limits enforced.
- [ ] Coordinator/Worker isolation: Coordinator cannot execute tools directly.
- [ ] Sidechain JSONL not merged into Coordinator context.

## Open questions

- Whether worktrees should support multi-user collaboration. Roadmap; not v1.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/MAILBOX.md`
- `03-runtime/LOOP-BUDGET.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `14-rfcs/0041-coordinator-worker-isolation.md`
- `14-rfcs/0042-sidechain-jsonl-subagents.md`
## Graph links

[[AGENTD-DAEMON]]  [[AGENT-LOOP]]  [[CAPABILITY-GATE]]  [[MAILBOX]]  [[LOOP-BUDGET]]
