---
id: system-clients
title: System Clients
type: SPEC
status: draft
version: 0.0.0
implements: [system-clients]
depends_on:
  - sdk-overview
  - kernel-framework
  - capnp-rpc
  - capability-taxonomy
depended_on_by:
  - sdk-rust
last_updated: 2026-04-30
---
# System Clients

## Purpose

Specify the typed clients an app uses to call into Kiki's system surfaces: memory, inference, focus, tools, agents, mailbox, audit. System clients are the read-and-write side of the SDK; they front the Cap'n Proto interfaces with ergonomic Rust APIs.

## The clients

```
MemoryClient        memory facade
InferenceClient     route an inference request
FocusClient         publish or subscribe focus
ToolClient          dispatch a tool by id
AgentClient         talk to the agent (e.g., delegate a sub-task)
MailboxClient       enqueue notifications, read responses
AuditClient         read audit entries (if granted)
SettingsClient      read/write app-scoped settings
```

Each is a thin wrapper that:

- Connects to the right Cap'n Proto socket
- Adds the app's ActorRef binding (from the kernel)
- Maps results to typed Rust structs
- Maps errors to `ErrorPayload`

## MemoryClient

```rust
let memory = ctx.memory();
let hits = memory.search(&Query::text("trip Lisbon")).await?;
memory.write(&WriteOp::EpisodeAppend { ... }).await?;
```

Subject to `agent.memory.read.*` / `.write.*` capabilities. Identity-class writes always go through the consent flow regardless.

## InferenceClient

```rust
let inference = ctx.inference();
let stream = inference.run(InferenceRequest {
    prompt: ...,
    privacy_level: PrivacyLevel::Sensitive,
    latency_budget: LatencyBudget::Conversational,
    ...
}).await?;
```

The router decides where the request runs; the app cannot specify a remote provider directly. Apps that need a specific model can hint via `model_hint`.

## FocusClient

```rust
let focus = ctx.focus();
focus.publish(FocusContext { ... })?;

let mut stream = focus.subscribe();
while let Some((app_id, ctx)) = stream.next().await { ... }
```

Publishing requires the manifest's `[focus]` declaration; subscribing requires `focus.read.*` capability.

## ToolClient

```rust
let tools = ctx.tools();
let result = tools.dispatch("kiki:tools/calculator/add", &args!{ a: 2, b: 3 }).await?;
```

The capability gate runs at dispatch.

## AgentClient

```rust
let agent = ctx.agent();
let result = agent.delegate(SubAgentTask {
    description: "summarize this article",
    capabilities: ["web.read.host:*"],
}).await?;
```

Apps can ask the agent to do something on their behalf; the agent's gate ensures the app can only request what it can do itself.

## MailboxClient

```rust
let mailbox = ctx.mailbox();
mailbox.enqueue(Message {
    title: "Sync complete",
    body: "Imported 12 items.",
    importance: Importance::Hint,
})?;
```

## AuditClient

```rust
let audit = ctx.audit();
let recent = audit.tail(Filter::ForApp("self")).await?;
```

`audit.read.self` gates own-app entries; `audit.read` gates broader access (rare).

## SettingsClient

```rust
let settings = ctx.settings();
let prefs: AppPrefs = settings.get("prefs").unwrap_or_default();
settings.set("prefs", &updated).await?;
```

Settings are per-app; stored under `/var/lib/kiki/apps/<id>/settings/`.

## Connection management

Each client holds a Cap'n Proto session; the kernel manages the connection pool. On disconnect (agentd restart), the kernel re-establishes silently; in-flight calls return retryable errors.

## Errors

All clients return `Result<T, ErrorPayload>`. The error categories include `policy.denied` (the gate said no), `not_found.resource`, `network.timeout`, etc.

## Capability checks

The clients do not pre-check; they let the daemon's gate decide. Apps should *handle* `policy.denied` gracefully — the user may not have granted yet.

## Streaming

Streaming methods return `impl Stream<Item = T>`. The kernel handles backpressure.

## Testing

The kernel provides in-process mocks for system clients:

```rust
let ctx = TestContext::new()
    .with_memory(MockMemory::default())
    .with_focus(MockFocus::default());
```

Useful for unit-testing app logic without spinning up agentd.

## Acceptance criteria

- [ ] Each client wraps the right Cap'n Proto interface
- [ ] Capability errors surface clearly
- [ ] Streaming methods backpressure correctly
- [ ] Reconnect after daemon restart is automatic
- [ ] Mocks available for tests

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/KERNEL-FRAMEWORK.md`
- `06-sdk/SDK-RUST.md`
- `04-memory/MEMORY-FACADE.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/TOOL-DISPATCH.md`
- `03-runtime/MAILBOX.md`
- `05-protocol/FOCUSBUS.md`
- `05-protocol/CAPNP-RPC.md`
- `10-security/AUDIT-LOG.md`
## Graph links

[[SDK-OVERVIEW]]  [[KERNEL-FRAMEWORK]]  [[CAPNP-RPC]]  [[CAPABILITY-TAXONOMY]]
