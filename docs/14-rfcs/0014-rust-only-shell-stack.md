---
id: 0014-rust-only-shell-stack
title: Rust-Only Shell and Daemon Stack
type: ADR
status: draft
version: 0.0.0
depends_on: []
last_updated: 2026-04-29
depended_on_by:
  - 0020-capnp-rpc-tool-dispatch
  - 0022-iceoryx-data-plane
  - 0023-zbus-dbus-integration
  - 0024-llamacpp-inference-engine
  - 0043-workspaces-model
---
# ADR-0014: Rust-Only Shell and Daemon Stack

## Status

`accepted`

## Context

The user-space components of Kiki — the agent daemon, policy daemon, inference daemon, memory daemon, tool registry, the compositor wrapper, the on-device GUI — could be written in C, C++, Rust, Go, or a mix. Each daemon owns sensitive code paths (capability gating, audit chain, crypto, IPC). We want a single primary language to minimize FFI surface, simplify code review, and unify the build system.

## Decision

All Kiki-owned daemons, the agent shell, the GUI stack glue (Slint + Servo + wgpu + AccessKit + libinput-rs), the SDK, and the tool host are written in **Rust**. C dependencies are limited to upstream system libraries already on the bootc base (kernel, glibc, llama.cpp via `llama-cpp-2`, pipewire, dbus-broker). Tools may be written in any language but the runtime hosts them through Wassette (WASM) or a sandboxed binary contract — the *boundary* into Kiki is always typed Cap'n Proto.

## Consequences

### Positive

- Memory safety and data-race safety by default for all sensitive code.
- One language for daemons reduces context-switching cost for contributors.
- Cap'n Proto, zbus, async-nats, iceoryx2, llama-cpp-2, ndarray, candle, serde, tokio — all first-class in Rust.
- Single build system (cargo workspaces) for the whole shell stack.
- No GC pauses; predictable latency for the agent loop.
- Same binaries across all hardware variants (aarch64, x86_64) without language-runtime variance.

### Negative

- Some ecosystem maturity gaps remain (e.g., ML library breadth lags Python). We mitigate via FFI to llama.cpp and selective use of candle.
- Compile times are higher than Go's; mitigated by sccache and incremental builds.
- Onboarding friction for contributors who don't know Rust.

## Alternatives considered

- **C/C++**: more libraries, but memory-safety risk on capability-critical code is unacceptable.
- **Go**: faster builds, GC pauses are unfriendly to real-time voice loops; no real cap'n proto capability story.
- **Mixed (Rust + Python)**: tempting for ML; introduces a runtime split and a packaging headache; we stay Rust and call into native ML libs.

## References

- `00-foundations/PRINCIPLES.md`
- `01-architecture/PROCESS-MODEL.md`
- `03-runtime/AGENTD-DAEMON.md`
- `05-protocol/CAPNP-RPC.md`
