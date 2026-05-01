---
id: loop-budget
title: Loop Budget
type: SPEC
status: draft
version: 0.0.0
implements: [loop-budget]
depends_on:
  - agentd-daemon
  - agent-loop
  - subagents
depended_on_by:
  - coordinator
  - cost-control
  - subagents
last_updated: 2026-04-29
---
# Loop Budget

## Purpose

Specify the mechanism that prevents the agent (and subagents) from looping indefinitely on a task: caps consecutive inference cycles per task, signals wrap-up as the cap nears, stops the loop hard if the cap is reached.

## Behavior

### Why this is needed

Agentic systems have an emergent failure mode: the agent reasons, calls a tool, gets a result that doesn't quite satisfy, reasons again, calls another tool, indefinitely. Without a hard cap:

- The user waits for a reply that never comes.
- Battery drains.
- Tool calls accumulate audit entries with no progress.
- Cost budgets burn.

The LoopBudget solves this by:

- Hard cap (default 25 cycles for primary agent).
- Wrap-up signal at 80% so the agent can produce a natural wrap-up.
- Forced stop at 100%.

### Budget allocation

| Context | Default budget |
|---|---|
| Primary agent task | 25 cycles |
| Fork subagent | 15 cycles |
| Teammate (per turn) | 10 cycles |
| Worktree session | 50 cycles |
| Proactive cycle | 5 cycles |
| Hook-initiated | 10 cycles |

Configurable via agentd config.

### Lifecycle

```
1. Task starts (user command, proactive trigger, etc.).
   Coordinator allocates LoopBudget(N).
2. Agent enters inference cycle. At cycle start: budget.consume_step().
3. If remaining = 0: budget exhausted. Agent loop must stop.
   Final action: produce "I had to stop before finishing" if no final response yet.
4. If remaining ≤ 20% of original:
   Inject "WrapUpHint" into next inference's context:
     "You have N cycles remaining for this task. If you can conclude with what you have, do so."
5. On final response: budget released. Audit log: task_completed with cycles_used.
```

### WrapUpHint integration

The hint is added to the system frame for cycles in the wind-down zone:

```
[task budget hint]
- You have used X of Y allotted reasoning cycles.
- N cycles remain.
- Prefer producing a final answer over additional tool calls.
- If genuinely blocked, say so honestly rather than continue.
```

Soft signal. The agent can ignore and continue, but will eventually hit zero.

### Exhaustion handling

```
exhaustion_action(state):
  if state.has_partial_response:
    deliver partial_response with note: "I had to stop before finishing. Here's what I have."
  else:
    deliver: "I worked on this but couldn't reach a resolution within my reasoning budget."
  audit_log: task_budget_exhausted
  release budget
```

### Per-subagent budgets

Subagents have independent budgets. Subagent exhaustion does not exhaust parent's. When Fork exhausts, parent receives partial result and decides whether to spawn follow-up Fork or wrap up.

### Budget reset

Budget resets at task boundaries:

- New user command → new budget.
- New proactive event → new budget.
- Subagent spawn → new sub-budget.

A budget does NOT reset within a multi-turn dialogue if it's the same task. Coordinator decides task boundaries based on:

- Time since last inference (>5 minutes → new task).
- Topic shift (heuristic; agent's own assessment).
- Explicit "new task" markers.

### Tunability

Per-app or per-subagent budgets can be larger or smaller via Profile:

```yaml
subagent_budget_override:
  fork_default: 20
  teammate_default: 5
```

Privileged apps (KikiSigned) can request larger budgets; user-installed apps can only lower theirs.

### Manual extension

User can extend mid-task:

- "Kiki, keep working on that" → +25 cycles for primary task.
- Recorded in audit log.

Rare but user's prerogative.

### Cost integration

LoopBudget independent of cost budget (inference router's cost cap):

- LoopBudget: how many cycles.
- Cost budget: how many tokens / dollars.

Either can stop a task; both must permit progress to continue.

### Diminishing returns detection

In addition to the cycle cap, the loop tracks productive output:

- If 3 consecutive cycles produce <500 tokens of new content → halt early.
- Suggests the agent is stuck rather than progressing.

## Interfaces

### Programmatic

```rust
pub struct LoopBudget {
    pub fn new(initial: u32) -> Self;
    pub fn consume_step(&mut self) -> RemainingCount;
    pub fn remaining(&self) -> u32;
    pub fn is_in_wrap_up_zone(&self) -> bool;
    pub fn is_exhausted(&self) -> bool;
    pub fn extend(&mut self, additional: u32);
}

pub struct RemainingCount {
    pub used: u32,
    pub remaining: u32,
    pub in_wrap_up: bool,
    pub exhausted: bool,
}
```

The agent loop calls `consume_step()` at start of each cycle. Remaining count added to context when in wrap-up zone.

### CLI

```
agentctl coord budgets         # active budgets
agentctl coord budget <task-id> # one task detail
```

## State

In-memory per-task. Released when task completes or canceled.

Coordinator keeps a small ring buffer of recently-completed tasks with budget usage in DuckDB:

```
task_id, kind, allocated, used, exhausted, completed_at
```

## Failure modes

| Failure | Response |
|---|---|
| Negative remaining detected | log; treat as exhausted |
| Budget consumed without cycle running | bug; log diagnostic |
| Extension request denied | log; ignore; continue toward exhaustion |

## Performance contracts

- Budget operations: <1µs.
- Negligible memory footprint per budget (~32 bytes).

## Acceptance criteria

- [ ] Primary agent budget defaults to 25 cycles.
- [ ] WrapUpHint appears when remaining ≤ 20%.
- [ ] Exhaustion produces clean stop with partial result.
- [ ] Subagent budgets independent from parent.
- [ ] User can extend when authorized.
- [ ] Budget exhaustion in audit log.
- [ ] New task boundaries get fresh budgets.
- [ ] Diminishing returns detection halts unproductive loops.

## Open questions

- Whether to support adaptive budgets based on task complexity. Not in v1.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/COORDINATOR.md`
- `03-runtime/SUBAGENTS.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `11-agentic-engineering/COST-CONTROL.md`
## Graph links

[[AGENTD-DAEMON]]  [[AGENT-LOOP]]  [[SUBAGENTS]]
