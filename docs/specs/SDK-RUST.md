---
id: sdk-rust
title: Rust SDK
type: SPEC
status: draft
version: 0.0.0
implements: [sdk-rust]
depends_on:
  - sdk-overview
  - kernel-framework
  - blocks-api
  - render-api
  - system-clients
depended_on_by:
  - sdk-bindings-c
  - sdk-bindings-go
  - sdk-bindings-python
  - sdk-bindings-typescript
  - sdk-codegen
last_updated: 2026-04-30
---
# Rust SDK

## Purpose

Specify the canonical Rust SDK that ships the four contracts (Kernel, Blocks, Render, System) as ergonomic crates. This is the SDK other languages bind to; everything else is a wrapper.

## Crates

```
kiki-sdk            top-level re-exports + macros
├── kiki-kernel     state, commands, tools, lifecycle
├── kiki-blocks      view DSL, components, reactivity
├── kiki-render      DMA-BUF surface (optional)
├── kiki-system      MemoryClient, InferenceClient, ...
├── kiki-capnp       generated Cap'n Proto bindings
└── kiki-test        in-process mocks + harness
```

## Hello world

```rust
use kiki_sdk::prelude::*;

#[derive(Default, Serialize, Deserialize, Clone)]
struct State {
    counter: u32,
}

impl AppState for State {
    fn version(&self) -> u32 { 1 }
}

#[command]
async fn increment(state: &mut State) -> Result<()> {
    state.counter += 1;
    Ok(())
}

#[view("home")]
fn home(state: &State) -> View {
    view! {
        <Card title="Counter">
            <Text content=format!("Count: {}", state.counter) />
            <Button label="Increment" intent={cmd!(increment())} />
        </Card>
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    KikiApp::new::<State>()
        .with_view::<home>()
        .with_command::<increment>()
        .run()
        .await
}
```

That's a complete Kiki app: state, command, view, lifecycle.

## Macros

- `#[command]` — registers a command and generates Cap'n Proto schema
- `#[query]` — read-only queries
- `#[query(stream)]` — streaming
- `#[tool(...)]` — tool registration with risk class
- `#[view("id"[, intent = "..."])]` — view registration
- `#[event_handler(...)]` — subscribe to events

The macros emit Cap'n Proto schemas, capability metadata, and registration code at build time. No reflection, no surprise dispatch.

## View DSL

JSX-like Rust macros (similar to leptos / dioxus):

```rust
view! {
    <Card title="...">
        <Text content="..." />
        if condition {
            <Button label="Yes" intent={cmd!(yes())} />
        }
        for item in &state.items {
            <ListItem key=item.id>
                {item.label.clone()}
            </ListItem>
        }
    </Card>
}
```

Type-checked at compile time.

## Reactivity

Fine-grained subscriptions: views read fields; the framework tracks reads; only views whose subscriptions are dirtied re-render.

## Async

All I/O is async; tokio is the runtime. The framework integrates cleanly with `async-trait`, `futures`, etc.

## Errors

Returns `kiki::Result<T>` (which is `Result<T, ErrorPayload>`). Convenience constructors:

```rust
err!(policy_denied("user.email", "needs grant"))
err!(not_found("track", id))
```

## Logging and tracing

Standard `tracing` crate. Each call gets a span automatically; the framework attaches the actor and trace ids.

## Build

```
[package]
name = "my-app"
version = "1.2.0"

[dependencies]
kiki-sdk = "1"
tokio = { version = "1", features = ["full"] }

[package.metadata.kiki]
id = "kiki:apps/my-app"
```

`cargo build --release` produces the binary; `kiki-pkg build` packages it as a Kiki container.

## Cross-arch

The SDK supports aarch64 and x86_64 first-class. Cross-compile via standard cargo cross-targets.

## MSRV

The SDK's MSRV (minimum supported Rust version) is the most recent two stable releases. We avoid nightly-only features.

## Feature flags

```toml
default = ["blocks", "system"]
blocks = []
render = ["dep:wgpu", ...]
system = []
test = []
```

cli_tool apps can leave out blocks/render to shrink binary size.

## Acceptance criteria

- [ ] Hello-world app builds and runs
- [ ] All four contracts available behind feature flags
- [ ] View DSL type-checks at compile
- [ ] Reactivity updates only affected views
- [ ] Capability annotations enforce gate calls
- [ ] kiki-test mocks let unit tests run without daemons

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/KERNEL-FRAMEWORK.md`
- `06-sdk/BLOCKS-API.md`
- `06-sdk/RENDER-API.md`
- `06-sdk/SYSTEM-CLIENTS.md`
- `06-sdk/SDK-CODEGEN.md`
- `05-protocol/CAPNP-RPC.md`
- `05-protocol/ERROR-MODEL.md`
## Graph links

[[SDK-OVERVIEW]]  [[KERNEL-FRAMEWORK]]  [[BLOCKS-API]]  [[RENDER-API]]  [[SYSTEM-CLIENTS]]
