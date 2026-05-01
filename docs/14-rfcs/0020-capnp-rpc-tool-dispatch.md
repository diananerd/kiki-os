---
id: 0020-capnp-rpc-tool-dispatch
title: Cap'n Proto RPC for Tool Dispatch
type: ADR
status: draft
version: 0.0.0
depends_on: [0014-rust-only-shell-stack]
last_updated: 2026-04-29
depended_on_by:
  - 0021-nats-service-bus
---
# ADR-0020: Cap'n Proto RPC for Tool Dispatch

## Status

`accepted`

## Context

Tool dispatch is the most security-sensitive IPC path in Kiki: every model-driven action passes through it. The wire layer must support typed methods, capability passing as live revocable handles (not opaque tokens), promise pipelining, schema evolution, and bidirectional RPC over a Unix socket. Candidates: gRPC, JSON-RPC, tarpc, custom, Cap'n Proto.

## Decision

Use **Cap'n Proto RPC** (via `capnp-rpc-rs`) as the IPC layer between agentd, the other Rust daemons, the tool registry, and tools. Schemas live under `/usr/share/kiki/capnp/`, generated bindings ship with the OS image, and capability binding is enforced at bootstrap from SO_PEERCRED-derived identity.

## Consequences

### Positive

- Capabilities as first-class wire references match our trust model directly.
- Zero-copy decode keeps tool result handling cheap.
- Promise pipelining lets the agent loop compose tool calls without round trips.
- Schema-driven evolution with stable 64-bit ids prevents drift across releases.
- Mature Rust libraries; no C dependency.

### Negative

- Less ubiquitous than gRPC for non-Rust tool authors; mitigated by Wassette + the typed boundary.
- Schema management overhead: id assignments, deprecation rules, version negotiation.
- Promise pipelining is powerful but adds debugging complexity; we keep stack traces as part of the trace context.

## Alternatives considered

- **gRPC**: adds HTTP/2 framing for no local benefit; tokens not capabilities.
- **JSON-RPC**: simple, but no capability typing; we'd reinvent it.
- **tarpc**: ergonomic Rust, but no schema-first discipline and no capability handles.
- **Custom**: too much rope; reinventing what Cap'n Proto already gets right.

## References

- `05-protocol/CAPNP-RPC.md`
- `05-protocol/CAPNP-SCHEMAS.md`
- `03-runtime/TOOL-DISPATCH.md`
