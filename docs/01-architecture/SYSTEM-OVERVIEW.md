---
id: system-overview
title: System Overview
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - vision
  - paradigm
  - principles
depended_on_by:
  - appliance-model
  - data-flow
  - hardware-abstraction
  - process-model
  - threat-model
  - trust-boundaries
last_updated: 2026-04-30
---
# System Overview

## Problem

A new contributor or reasoning system needs a single document that explains how Kiki OS fits together at the macro level. Without it, each subsystem document is read in isolation and the relationships between subsystems must be inferred from the corpus.

## Constraints

- Must explain the whole system in one read.
- Must reference (not duplicate) the SPECs that detail each layer.
- Must be stable: layer boundaries change rarely.
- Must reflect the appliance OS paradigm: layers exist for the agentic purpose, not for general-purpose Linux.

## Decision

Kiki OS is organized into **ten layers**. Each layer depends only on the layers below it. Each has a clear purpose and a small set of responsibilities.

```
┌────────────────────────────────────────────────────────────────┐
│  LAYER 10  COMPOSITOR + SHELL                                  │
│            cage (Wayland) + agentui (Slint + Servo + wgpu)     │
├────────────────────────────────────────────────────────────────┤
│  LAYER 9   AGENT HARNESS                                       │
│            agentd, policyd, inferenced, memoryd, toolregistry  │
├────────────────────────────────────────────────────────────────┤
│  LAYER 8   APPS                                                │
│            OCI containers (podman quadlet), capability-gated    │
├────────────────────────────────────────────────────────────────┤
│  LAYER 7   MEMORY SUBSYSTEM                                    │
│            sensory / working / episodic / semantic /            │
│            procedural / identity                                │
├────────────────────────────────────────────────────────────────┤
│  LAYER 6   IPC + CAPABILITY GATE                               │
│            Cap'n Proto RPC + NATS + iceoryx2 + DBus + gate     │
├────────────────────────────────────────────────────────────────┤
│  LAYER 5   SANDBOX                                             │
│            Landlock / seccomp / namespaces / cgroups / podman  │
├────────────────────────────────────────────────────────────────┤
│  LAYER 4   SYSTEM SERVICES                                     │
│            systemd / NetworkManager / PipeWire / HAL daemons   │
├────────────────────────────────────────────────────────────────┤
│  LAYER 3   KERNEL                                              │
│            Linux + Landlock + seccomp + namespaces + cgroups   │
├────────────────────────────────────────────────────────────────┤
│  LAYER 2   BOOT CHAIN                                          │
│            systemd-boot + UKI + sd-stub + bootc + dm-verity    │
├────────────────────────────────────────────────────────────────┤
│  LAYER 1   HARDWARE                                            │
│            described by a signed hardware manifest             │
└────────────────────────────────────────────────────────────────┘
```

## Rationale

### Why ten layers, not fewer

Fewer layers conflate concerns that need to be reasoned about separately. Treating "kernel + system services" as one layer hides the fact that system services are userspace processes with different update and crash semantics than the kernel. Treating "agent + apps" as one layer hides that apps are sandboxed and the agent is not.

### Why this ordering

Each layer must be operable without any layer above it.

- The kernel runs without `agentd`.
- `agentd` runs without the compositor.
- The compositor runs without apps.

This makes failures contained: a crash in layer N cannot prevent layer N−1 from operating.

### Why memory is its own layer

Memory is shared across the agent and apps with permission. It is not a feature of `agentd`; it is infrastructure. Treating it as a layer makes its lifecycle (boot-time start, OTA-survivable, inspectable) explicit.

### Why the capability gate is layered with IPC

Every cross-app and app-to-`agentd` call goes through both. Combining them into one layer makes the enforcement point unambiguous: there is no path that crosses IPC without crossing the gate.

### Why the agent harness sits between memory and apps

The agent harness reads memory to construct context and dispatches to apps to execute tools. Apps cannot reach memory directly. This routes all memory access through a gate.

### Why the compositor + shell is one layer

Cage and `agentui` together provide the user surface. They are configured to act as a unit (cage launches `agentui` as its sole client). Treating them as separate layers obscures that one is unusable without the other.

## Layer responsibilities

Each layer has a SPEC document or set of SPECs that fully define its behavior. This overview gives the responsibility; the SPECs give the contract.

### Layer 1 — Hardware

Real silicon. Described to the rest of the system through:

- A device tree in the kernel.
- A signed hardware manifest at `/etc/kiki/hardware-manifest.toml`.
- The HAL contract for driver interfaces.

See: `02-platform/HARDWARE-MANIFEST.md`, `02-platform/HAL-CONTRACT.md`.

### Layer 2 — Boot chain

Verified boot from a hardware-rooted trust anchor where supported. A/B image deployment via bootc with rollback. UKI (Unified Kernel Images) signed; PCR sealing of disk encryption keys.

See: `02-platform/BOOT-CHAIN.md`, `10-security/VERIFIED-BOOT.md`.

### Layer 3 — Kernel

Linux kernel with specific features enabled: Landlock LSM, seccomp, namespaces, cgroups v2. Patches go upstream where possible; we do not maintain a fork.

See: `02-platform/KERNEL-CONFIG.md`.

### Layer 4 — System services

Userspace services managing OS lifecycle:

- `systemd` for init and supervision.
- `NetworkManager` for connectivity.
- `PipeWire` for audio.
- HAL daemons exposing hardware to apps.

See: `02-platform/INIT-SYSTEM.md`, `02-platform/NETWORK-STACK.md`, `02-platform/AUDIO-STACK.md`, `02-platform/HAL-CONTRACT.md`.

### Layer 5 — Sandbox

Kernel-level isolation. Each app runs in a podman container with crun as the OCI runtime. The container's default sandbox already provides Landlock filesystem rules, seccomp syscall filters, network namespace, and cgroup limits. The agent harness configures additional restrictions per the app's Profile.

See: `02-platform/SANDBOX.md`, `02-platform/CONTAINER-RUNTIME.md`.

### Layer 6 — IPC + capability gate

The protocol layer.

- **Cap'n Proto RPC** is the binary protocol for tool dispatch and cross-app communication.
- **NATS embedded** is the service bus with pub/sub and request/reply.
- **iceoryx2** is the zero-copy data plane for bulk transfers (audio frames, video frames).
- **DBus (zbus)** is the integration surface for `org.kiki.*` services.
- **The capability gate** runs in `policyd` and checks every sensitive call.

See: `05-protocol/CAPNP-RPC.md`, `05-protocol/NATS-BUS.md`, `05-protocol/ICEORYX-DATAPLANE.md`, `05-protocol/DBUS-INTEGRATION.md`, `03-runtime/CAPABILITY-GATE.md`.

### Layer 7 — Memory subsystem

Six layers of memory: sensory, working, episodic, semantic, procedural, identity. Different storage backends, different lifetimes, different protections. Accessed by `agentd` and by apps with appropriate capability via `memoryd`.

See: `04-memory/MEMORY-ARCHITECTURE.md` and the per-layer SPECs.

### Layer 8 — Apps

Sandboxed OCI containers exposing tools through Cap'n Proto. Four runtime modes: CLI tool (per-call), headless service (long-running), interactive ephemeral (per-call with UI), interactive service (long-running with UI). Apps cannot communicate directly with each other.

See: `06-sdk/APP-CONTAINER-FORMAT.md`, `06-sdk/APP-RUNTIME-MODES.md`.

### Layer 9 — Agent harness

Five daemons in Rust, distributed as a sysext OCI artifact:

- `agentd` — supervisor, lifecycle, journal, workspace orchestrator.
- `policyd` — capability gate, arbiter classifier, drift mitigation.
- `inferenced` — L7 inference proxy, credential substitution, routing, cost ledger.
- `memoryd` — memory facade over the six layers.
- `toolregistry` — MCP, WASM, container tool dispatch.

See: `03-runtime/AGENTD-DAEMON.md` and the rest of `03-runtime/`.

### Layer 10 — Compositor + shell

Cage runs as a kiosk Wayland compositor. Its only client is `agentui`, the single GUI app of Kiki OS. `agentui` hosts the canvas, status bar, command bar, task manager, voice pipeline, and integrates with the rest of the runtime via Cap'n Proto and DBus.

See: `07-ui/COMPOSITOR.md`, `07-ui/AGENTUI.md`, `07-ui/SHELL-OVERVIEW.md`.

## Cross-cutting concerns

Some concerns do not fit neatly in one layer.

### Identity

Three files: `SOUL.md` (agent voice), `IDENTITY.md` (device, signed at build), `USER.md` (per-user). Stored in the memory subsystem, read by `agentd` at every inference, modified only through the consent flow. Versioned in git via `gix`.

See: `04-memory/IDENTITY-FILES.md`, `04-memory/CONSENT-FLOW.md`.

### Hardware adaptation

The same OS runs on multiple hardware classes. Adaptation has three mechanisms: build-time profiles (which subsystems are included), the hardware manifest (what is actually present), and runtime adaptation (responding to dynamic state).

See: `01-architecture/HARDWARE-ABSTRACTION.md`.

### Privacy

Enforced architecturally: capability gate, inference router privacy levels, audit log, memory subsystem protections, kernel sandbox. No single layer is responsible; the property emerges from the combination.

See: `10-security/PRIVACY-MODEL.md`.

### Observability

Audit log records capability decisions and significant actions. Local telemetry tracks system health (DuckDB-backed). External telemetry is opt-in.

See: `10-security/AUDIT-LOG.md`, `11-agentic-engineering/EVALUATION.md`.

### Distribution

OCI everywhere. The base OS, the runtime sysext, apps, components, tools, profiles, models, skills, and bundles are all signed OCI artifacts. Distribution is federated; trust is per-namespace.

See: `12-distribution/OCI-NATIVE-MODEL.md`.

## Boot order

The boot order follows the layers, with optional layers conditional:

```
1. Bootloader → kernel
2. Kernel → mount root, /dev, /proc, /sys
3. Kernel → execute systemd (PID 1)
4. systemd brings up dependency tree:
   a. Storage (mount /var, /home, decrypt with TPM-sealed keys)
   b. Logging (journald)
   c. Network (NetworkManager) — async, does not block
   d. Audio (PipeWire) — async
   e. HAL daemons
   f. Memory subsystem databases (LanceDB, CozoDB integrity check)
   g. Voice service (kiki-voiced) if enabled
   h. agentd (with the rest of the runtime sysext)
   i. cage as user session, which launches agentui
5. agentd → discover apps, register tools, start service apps
6. cage + agentui ready; user can interact
7. System ready
```

Total boot time target on reference hardware: under 30 seconds cold.

## Consequences

- A new subsystem must declare which layer it belongs to. Adding a feature that spans layers requires explicit cross-layer design (RFC).
- Each layer has independent failure semantics. Subsystems within a layer can crash without taking down adjacent layers.
- Cross-layer calls go through defined interfaces. Apps do not call kernel APIs directly; they call Cap'n Proto which calls `agentd` which uses the kernel.
- The dependency graph is acyclic by construction. A doc in layer N may not declare `depends_on` to a doc in layer M > N.

## References

- `00-foundations/PARADIGM.md`
- `01-architecture/PROCESS-MODEL.md`
- `01-architecture/TRUST-BOUNDARIES.md`
- `01-architecture/THREAT-MODEL.md`
- `01-architecture/DATA-FLOW.md`
- `01-architecture/APPLIANCE-MODEL.md`
