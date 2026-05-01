---
id: agent-loop
title: Agent Loop
type: SPEC
status: draft
version: 0.0.0
implements: [agent-inference-cycle]
depends_on:
  - agentd-daemon
  - event-bus
  - coordinator
  - inference-router
  - tool-dispatch
  - capability-gate
  - working-memory
depended_on_by:
  - context-engineering
  - coordinator
  - harness-patterns
  - hooks
  - loop-budget
  - subagents
  - working-memory
last_updated: 2026-04-30
---
# Agent Loop

## Purpose

Specify the inference cycle: how the agent processes one event, builds context, runs inference, dispatches tool calls, integrates results, and produces output.

## Behavior

### High-level

```
event arrives → coordinator decides → infer or dispatch directly
                                         │
                                         ▼
                                   build context
                                   run inference
                                   parse tool calls
                                   for each tool call:
                                       gate check
                                       dispatch
                                       integrate result
                                       loop back if needed
                                   final response
                                   record episode
                                   audit
```

### The 10-step cycle

```
1. Acquire LoopBudget step (abort if exhausted).
2. Pre-inference hooks (Observe / Intercept / Transform).
3. Build context:
   - Identity frame (SOUL, IDENTITY, USER) — never compacted.
   - Tool digests (subset, per workspace).
   - Recent thread.
   - Retrieved memories (memoryd hybrid retrieval).
   - Active perception slice.
   - Subagent integrations pending.
   - System context (time, hardware, battery).
   - Current event.
4. Inference router decides (privacy, latency, caps, route).
5. Run inference (streaming).
6. Post-inference hooks.
7. Parse output: tool calls, final response, uncertainty.
8. For each tool call:
   - Pre-tool-call hooks.
   - Capability gate check (deny → terminal; agent receives blocked).
   - Mailbox approval if risky.
   - Dispatch via Cap'n Proto to toolregistry.
   - Receive result (or timeout).
   - Post-tool-call hooks.
   - Add result to context.
   - Re-enter cycle (back to step 1).
9. If output is final response:
   - Pre-output hooks.
   - Send to output channel (voice/canvas/message).
   - Record episode in episodic memory.
   - Update working memory.
   - Audit log.
10. If LoopBudget exhausted before final response:
    - Wrap-up response.
    - Inform user.
    - Stop.
```

### Streaming and barge-in

Inference streams tokens. TTS begins as soon as final response tokens arrive (first-token-to-speech). Barge-in cancels mid-stream within 100ms.

### Tool call parallelism

Model can emit multiple tool calls in one inference. Dispatch worker pool handles concurrently (cap 8 per agent). Results returned in any order; coordinator collects all before re-entering inference.

### Context budget

- working_max_tokens default 32000.
- Identity reserved: ~4000 tokens.
- Tool digests: 2000–8000 tokens.
- Remaining for thread + retrieved + perception.

When budget exceeded, compaction tiers run (see `04-memory/COMPACTION.md`).

### Privacy classification

Strictest of any input wins. A Sensitive turn forces the entire inference Sensitive. Inference router enforces routing.

### Failure handling

| Step | Failure | Response |
|---|---|---|
| Hook denial | early return; user informed |
| Context build fails | abort cycle |
| Routing returns Refuse | abort cycle |
| Inference timeout | cancel; treat as failure |
| Inference engine crash | cancel; engine restarts |
| Output parse fail | best-effort response |
| Tool dispatch timeout | tool result = timeout error |
| Tool capability denied | terminal denial returned |
| Mailbox approval rejected | denial returned |
| LoopBudget exhausted | wrap-up |

## Interfaces

### Coordinator → loop

```rust
async fn run_inference_cycle(
    user_state: &mut UserState,
    request: InferenceRequest,
    budget: &mut LoopBudget,
) -> Result<CycleOutcome>;
```

Outcomes: `Completed(response, episode)`, `BudgetExhausted(partial)`, `Refused(reason)`, `HookDenied(hook_id, reason)`, `InferenceFailed(error)`.

### Hooks

Registered with agentd. Loop calls them at documented points. See `03-runtime/HOOKS.md`.

### Memory

Loop reads at context-build time, writes at end-of-cycle. See `04-memory/MEMORY-ARCHITECTURE.md`.

## State

Mostly stateless; state lives in `UserState` (held by coordinator), memory subsystem, mailbox, audit log.

Reentrant: can call itself for tool-result re-entry.

## Failure modes

| Failure | Response |
|---|---|
| Hook denial (intercept) | early return; user informed |
| Hook timeout | log; continue with default |
| Context build fails | abort cycle; surface error |
| Routing returns Refuse | abort cycle; surface reason |
| Inference timeout | cancel; treat as failure |
| Tool dispatch timeout | tool result is timeout error |
| LoopBudget exhausted | wrap-up; safe stop |
| OOM during inference | engine crash; cancel and report |
| Memory write fails | log; agent state may be inconsistent |

## Performance contracts

- Pre-inference (hooks + context build): <100ms typical.
- Tool dispatch + result (warm service): <100ms.
- Post-inference + output: <50ms.
- Total cycle for simple voice command: <1.2s end to end (hybrid mode).

## Acceptance criteria

- [ ] Voice command produces a voice response in under 1.5s.
- [ ] Tool calls execute through capability gate.
- [ ] Loop budget terminates runaway agents.
- [ ] Hooks fire at all documented points.
- [ ] Per-user state isolated.
- [ ] Crash and restart preserves memory.
- [ ] Audit log covers every cycle.
- [ ] Barge-in cancels within 100ms.

## References

- `03-runtime/COORDINATOR.md`
- `03-runtime/EVENT-BUS.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/TOOL-DISPATCH.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/HOOKS.md`
- `03-runtime/LOOP-BUDGET.md`
- `04-memory/WORKING-MEMORY.md`
- `04-memory/RETRIEVAL.md`
## Graph links

[[AGENTD-DAEMON]]  [[EVENT-BUS]]  [[COORDINATOR]]  [[INFERENCE-ROUTER]]  [[TOOL-DISPATCH]]  [[CAPABILITY-GATE]]  [[WORKING-MEMORY]]
