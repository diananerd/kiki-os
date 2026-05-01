---
id: coordinator
title: Coordinator
type: SPEC
status: draft
version: 0.0.0
implements: [coordinator]
depends_on:
  - agentd-daemon
  - event-bus
  - agent-loop
  - mailbox
  - loop-budget
depended_on_by:
  - agent-loop
last_updated: 2026-04-30
---
# Coordinator

## Purpose

Specify the rule-based event triage component that decides what to do with each event: ignore, update context, infer, dispatch tool, process mailbox, spawn subagent. The coordinator is the deterministic dispatcher; the agent loop is its primary tool but not its only response.

One coordinator instance per active user.

## Behavior

### Decision table

| Event kind | Inference hint | Default action |
|---|---|---|
| UserCommand (voice) | TriggerNow | infer |
| UserCommand (touch) | TriggerNow | infer |
| UserCommand (message) | TriggerNow | infer |
| PerceptionInput | depends | promote; infer if attention warrants |
| HardwareEvent | ContextOnly | update context; infer if safety/critical |
| PushEvent | IfIdle | defer; infer when idle if attention permits |
| InferenceResult | (internal) | parse + dispatch tools or emit response |
| ToolCallResult | (internal) | re-enter inference |
| SubagentMessage | depends | route to recipient or inject |
| HookTriggered | (internal) | run hook |
| MailboxResponse | (internal) | resume blocked work |
| ConfigChanged | (internal) | reload |
| HealthAnomaly | (internal) | log; possibly notify |
| ShutdownRequested | (internal) | drain in-flight; shut down |

The coordinator is rule-based for triage. The agent itself runs only when triage decides "infer."

### Algorithm

```
process(event, user_state):
   user_state.last_event_at = now()
   if event.user != user_state.user: handle_user_switch(event.user)
   if event.deadline < now(): drop as stale
   hook_decision = run_hooks(BeforePushEvent, event)
   if hook_decision.is_deny(): return
   match classify(event):
     UserInitiated:
       if currently_inferring and event.is_critical: cancel current
       kick_off_inference(event)
     PerceptionPromotion:
       working_memory.note(event.summary)
       if attention_classifier.warrants(event):
         enqueue_or_infer(event)
     HardwareSafetyCritical:
       kick_off_inference_priority_critical(event)
     HardwareNonSafety:
       working_memory.note(event.summary)
       maybe_render_surface(event)
     PushEventIfIdle:
       if currently_inferring: defer
       elif user_in_dnd and event.severity < threshold: defer_to_post_dnd
       else: kick_off_inference(event)
     Internal:
       route_internal(event)
     System:
       handle_system_event(event)
```

### Attention model

For PerceptionInput / PushEvent, the coordinator classifies whether the event warrants inference:

```
warrants(event) =
   weighted(novelty, recent_attention_decay, topic_relevance,
            user_engagement, severity) > THRESHOLD
```

v1 is rule-based with thresholds. Future: learned model via a hook.

### User switching

```
handle_user_switch(new_user):
   if currently_inferring: cancel_or_finish_per_policy
   save_per_user_state(current_user)
   load_per_user_state(new_user)
   emit "user_switched" for hooks
   audit_log
```

Reloads: USER.md, working memory, active thread, LoopBudget, grant subset.

### Concurrency rules

- One inference at a time per primary agent.
- Subagents are concurrent.
- TriggerNow can preempt current inference.
- Per-user state locked during mutation.

### Idle handling

When idle:
- Process deferred events.
- Run scheduled background work (memory consolidation, dreaming).

### Shutdown

```
1. Mark coordinator as shutting down.
2. Cancel in-flight inferences with budget warning.
3. Drain mailbox of in-flight responses.
4. Persist user state.
5. Persist pending memory writes.
6. Exit.
```

## Interfaces

### Internal

```rust
struct Coordinator {
    fn run(self) -> impl Future<Output = ()>;
}
```

The coordinator pulls from the event bus and dispatches.

### Diagnostics

```
agentctl coord state <user>
agentctl coord deferred <user>
agentctl coord recent <user>
```

## State

Per-user state persisted at `/var/lib/kiki/users/<user-id>/state.toml`. Periodic flush (every 5s of activity).

```rust
struct UserState {
    user_id: UserId,
    user_md: UserIdentity,
    working_memory: WorkingMemory,
    active_thread: Option<ThreadId>,
    loop_budget: LoopBudget,
    last_event_at: Instant,
    last_inference_at: Option<Instant>,
    in_flight: Option<RequestId>,
    deferred: Vec<Event>,
    attention_state: AttentionState,
}
```

## Failure modes

| Failure | Response |
|---|---|
| Event classification fails | log; treat as Normal |
| Agent loop returns error | record; user notified per policy |
| User state load fails | start with defaults; alert |
| Concurrent state mutation | locking serializes |
| Deferred queue overflow | drop oldest; audit |
| Hook denies coordinator action | log; do nothing |
| Coordinator task panics | systemd restart |

## Performance contracts

- Event-to-decision latency: <1ms typical.
- TriggerNow preemption: <50ms from arrival to inference cancel.
- Per-user state save: <20ms.

## Acceptance criteria

- [ ] User commands trigger inference within 50ms of arrival.
- [ ] PerceptionInput updates working memory; may trigger inference.
- [ ] PushEvent IfIdle defers when busy.
- [ ] User switching reloads cleanly.
- [ ] DND honored for non-critical events.
- [ ] Per-user state isolation enforced.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/EVENT-BUS.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/MAILBOX.md`
- `03-runtime/LOOP-BUDGET.md`
- `04-memory/DREAMING.md`
