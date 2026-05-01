---
id: 0012-podman-quadlet-app-runtime
title: podman + crun + quadlet for App Runtime
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
  - 0002-oci-native-distribution
  - 0008-systemd-init
last_updated: 2026-04-29
---
# ADR-0012: podman + crun + quadlet for App Runtime

## Status

`accepted`

## Context

Apps in Kiki are signed OCI containers (per ADR-0002). They need a runtime that integrates with systemd, applies sandbox primitives, and runs rootless. Options: podman+crun, podman+youki, Docker, containerd directly, runc.

## Decision

Use **podman + crun** as the OCI runtime, integrated via **systemd quadlet**. Apps are launched as systemd-supervised containers.

## Consequences

### Positive

- podman is rootless, daemonless; no central daemon to compromise.
- crun is C, fast (~60ms cold start vs runc ~95ms).
- Quadlet integrates podman with systemd: app units are first-class systemd units.
- The container runtime's default sandbox (namespaces, cgroups, seccomp) provides our per-app isolation.
- OCI-standard; portable.

### Negative

- crun is C, not Rust. We accept this for ecosystem maturity; revisit youki when its podman integration settles.
- Quadlet is relatively new; some edge cases in development.
- podman has its own learning curve for maintainers more familiar with Docker.

## Alternatives considered

- **podman + youki (Rust OCI runtime)**: pure-Rust appeal, ~45ms cold start. Revisit when integration with podman matures.
- **Docker Engine**: requires daemon; conflicts with rootless model.
- **containerd directly**: lower-level than needed; podman provides the right abstraction layer.
- **runc**: slower than crun, similar features.
- **bubblewrap as primary sandbox** (without OCI): loses OCI distribution alignment; ad hoc.

## References

- `02-platform/CONTAINER-RUNTIME.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `06-sdk/APP-RUNTIME-MODES.md`
