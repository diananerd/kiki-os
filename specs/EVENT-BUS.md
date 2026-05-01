---
id: event-bus
title: Internal Event Bus
type: SPEC
status: draft
version: 0.0.0
implements: [internal-event-bus]
depends_on:
  - agentd-daemon
depended_on_by:
  - agent-loop
  - coordinator
last_updated: 2026-04-30
---
# Internal Event Bus

## Purpose

Specify the in-process event bus inside `agentd`: event types, priority ordering, inference hints, backpressure, and the producer/consumer contract.

This is internal to the `agentd` process; not the inter-process bus (which is NATS, see `05-protocol/NATS-BUS.md`).

## Behavior

### Event taxonomy

```rust
enum Event {
    // From the world
    PerceptionInput(PerceptionEvent),
    UserCommand(UserCommandEvent),
    HardwareEvent(HardwareEvent),
    PushEvent(PushEvent),

    // From within
    InferenceResult(InferenceResultEvent),
    ToolCallRequested(ToolCallEvent),
    ToolCallResult(ToolCallResultEvent),
    SubagentMessage(SubagentMessageEvent),
    HookTriggered(HookTriggerEvent),

    // System
    ConfigChanged(ConfigChangeEvent),
    HealthAnomaly(HealthEvent),
    ShutdownRequested(ShutdownEvent),
}

struct EventEnvelope {
    id: EventId,
    payload: Event,
    priority: Priority,
    inference_hint: InferenceHint,
    arrived_at: Instant,
    deadline: Option<Instant>,
    user_id: Option<UserId>,
    workspace_id: Option<WorkspaceId>,
    audit_tags: Vec<Tag>,
}
```

### Priorities

```
Critical    user voice command, barge-in, safety event
High        user touch, hardware alerts
Normal      service push, hooks, scheduled
Background  dreaming, pruning, telemetry
```

Critical processed before High before Normal before Background. FIFO within a level.

Critical can preempt the agent's current cycle (barge-in cancels inference).

### Inference hints

```rust
enum InferenceHint {
    TriggerNow,      // immediately infer; preempt if needed
    Accumulate,      // batch with related events in a window
    ContextOnly,     // update working memory; no inference
    IfIdle,          // infer only when no active inference
}
```

Coordinator honors hints.

### Bus structure

In-process bounded MPSC channels per priority + a selector task using `tokio::select!` with `biased`.

```rust
loop {
    tokio::select! {
        biased;
        evt = channel_critical.recv() => deliver(evt).await,
        evt = channel_high.recv() => deliver(evt).await,
        evt = channel_internal.recv() => deliver(evt).await,
        evt = channel_normal.recv() => deliver(evt).await,
        evt = channel_background.recv() => deliver(evt).await,
    }
}
```

`biased` ensures higher-priority channels checked first on every iteration.

### Backpressure

Channels are bounded:

| Channel | Capacity | Full behavior |
|---|---|---|
| Critical | 64 | block briefly; panic if still full |
| High | 256 | drop oldest with audit |
| Normal | 1024 | drop newest with audit |
| Background | 64 | drop newest silently |

Drops are logged with metadata for diagnostics.

### Producer contract

Producers must:
- Set sensible priority and inference hint.
- Honor bounded behavior.
- Provide useful audit_tag list.
- Set deadline if time-sensitive.

### Consumer contract

The coordinator (the consumer) must:
- Process in priority order.
- FIFO within a priority.
- Honor inference hints.
- Detect stale events; treat as expired.
- Not block the bus indefinitely.

### Subscription model

Hooks subscribe via the hook system, not directly. The bus delivers all events to the coordinator; the coordinator triggers relevant hooks.

For diagnostics, an observer can subscribe via a special "audit" subscription receiving copies of all events. Capability-gated and rate-limited.

## Interfaces

### Producer API

```rust
struct EventBusProducer {
    fn try_publish(&self, evt: Event, prio: Priority, hint: InferenceHint) -> Result<(), PublishErr>;
    fn publish_or_block(&self, evt: Event, prio: Priority, hint: InferenceHint, timeout: Duration) -> Result<(), PublishErr>;
}
```

### Consumer API

```rust
async fn recv(&self) -> EventEnvelope;
```

### Diagnostics

```
agentctl bus stats        # channel depths, drop counts, throughput
agentctl bus tail          # recent events (capability-gated)
```

## State

In-memory only. No persistence.

If `agentd` crashes with events in flight, those are lost. Events that must not be lost are persisted by the producer (the mailbox, for example).

## Failure modes

| Failure | Response |
|---|---|
| Critical channel full | brief block; panic if persistent |
| High channel full | drop oldest with audit |
| Normal/Background full | drop newest |
| Coordinator stuck | events accumulate; eventual drop pattern |
| Producer panics | bus continues |
| Selector panics | systemd restart |

## Performance contracts

- Publish latency: <100µs typical.
- Delivery latency: <1ms p99.
- Throughput: 10,000+ events/sec.
- Memory per event: ~256 bytes.

## Acceptance criteria

- [ ] Critical events preempt within 1ms.
- [ ] FIFO within priority observable.
- [ ] Drop counts recorded under overload.
- [ ] Channels bounded; no unbounded growth.
- [ ] Diagnostic subscription works with capability.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/COORDINATOR.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/HOOKS.md`
