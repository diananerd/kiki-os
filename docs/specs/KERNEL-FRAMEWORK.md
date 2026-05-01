---
id: kernel-framework
title: Kernel Framework
type: SPEC
status: draft
version: 0.0.0
implements: [kernel-framework]
depends_on:
  - sdk-overview
  - capnp-rpc
  - capnp-schemas
depended_on_by:
  - blocks-api
  - sdk-rust
  - system-clients
last_updated: 2026-04-30
---
# Kernel Framework

## Purpose

Specify the Kernel contract: the small, ergonomic Rust framework that lets an app expose state, register commands, and contribute tools to the agent. The Kernel is the heart of every Kiki app — everything else (Blocks, Render, System) is built around it.

## Conceptual model

```
struct AppKernel<S: AppState> {
    state: S,
    commands: Vec<Box<dyn Command<S>>>,
    tools: Vec<Box<dyn Tool>>,
    views: Vec<View>,
    focus: Option<FocusContext>,
}
```

An app:

1. Defines a state type
2. Registers commands (mutations) and queries (reads) over that state
3. Optionally declares tools that the agent can call
4. Declares UI views that emit blocks
5. Optionally publishes focus context

The framework provides the plumbing for Cap'n Proto, capability checks, lifecycle, hibernation, and event integration.

## State

State is owned by the app. The framework requires:

```rust
trait AppState: Serialize + Deserialize + Clone + Send {
    fn version(&self) -> u32;
}
```

State is checkpointed periodically so a crash or pause/resume restores cleanly. The version field migrates state across app updates.

## Commands

Commands are state mutations:

```rust
#[command]
async fn play_track(state: &mut MyState, track: TrackId) -> Result<()> {
    state.queue.push_front(track);
    Ok(())
}
```

The macro registers the command, generates a Cap'n Proto schema, and wires capability checks. Commands are dispatched by the agent (or directly by user actions on UI views).

## Queries

Queries are read-only and may stream:

```rust
#[query]
fn now_playing(state: &MyState) -> Option<Track> {
    state.queue.front().cloned()
}

#[query(stream)]
fn track_progress(state: &MyState) -> impl Stream<Item = Progress> {
    // ...
}
```

Streamed queries map to Cap'n Proto streaming methods.

## Auto-MCP

Tools registered with the kernel are auto-published in an MCP-like surface (using `rmcp` patterns):

```rust
#[tool(risk = "safe")]
async fn search(state: &MyState, q: String) -> Result<Vec<Hit>> {
    // ...
}
```

The framework derives:

- Cap'n Proto schema for the tool
- Tool registry registration
- Capability declarations
- MCP-compatible JSON schema for legacy interop

Tool authors don't write the schema by hand.

## Lifecycle hooks

```rust
impl App for MyApp {
    fn on_init(&mut self, ctx: &AppContext) -> Result<()> { ... }
    fn on_pause(&mut self) -> Result<()> { ... }
    fn on_resume(&mut self) -> Result<()> { ... }
    fn on_terminate(&mut self) -> Result<()> { ... }
}
```

The framework calls these at the right times. Defaults are no-ops.

## Event subscriptions

Apps can subscribe to system or app events:

```rust
#[event_handler("focus.changed")]
fn on_focus_change(state: &mut MyState, evt: FocusEvent) {
    // ...
}
```

Subscriptions are scoped to the app's namespace + system events the app's manifest declares.

## Capability awareness

Commands and tools are gated by capability annotations:

```rust
#[command(requires = "audio.play")]
async fn play(...) { ... }
```

The framework consults the gate on every call.

## Persistence

State is persisted to `/var/lib/kiki/apps/<id>/state.bin` (encrypted at rest). Restoration is automatic on launch.

## Concurrency

The kernel runs on a tokio executor; commands are async. State is wrapped in an `RwLock` (or finer-grained locks per the app); the framework provides macros that avoid common lock-misuse patterns.

## Errors

All command and tool errors map to `ErrorPayload` (see `ERROR-MODEL.md`). The framework provides convenience constructors.

## Testing

```rust
#[test]
async fn play_track_works() {
    let mut state = MyState::default();
    play_track(&mut state, TrackId::new("...")).await.unwrap();
    assert_eq!(state.queue.len(), 1);
}
```

The framework provides an in-process harness for unit tests; integration tests use a sandboxed runtime.

## Acceptance criteria

- [ ] Commands and queries auto-publish via Cap'n Proto
- [ ] Tools auto-publish via auto-MCP
- [ ] Capability annotations enforced at every call
- [ ] State persistence + version migration works
- [ ] Lifecycle hooks called correctly
- [ ] Event subscriptions scoped properly

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/BLOCKS-API.md`
- `06-sdk/RENDER-API.md`
- `06-sdk/SYSTEM-CLIENTS.md`
- `06-sdk/SDK-RUST.md`
- `05-protocol/CAPNP-RPC.md`
- `05-protocol/ERROR-MODEL.md`
- `03-runtime/TOOLREGISTRY.md`
## Graph links

[[SDK-OVERVIEW]]  [[CAPNP-RPC]]  [[CAPNP-SCHEMAS]]
