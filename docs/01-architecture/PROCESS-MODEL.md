---
id: process-model
title: Process Model
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - system-overview
  - appliance-model
  - principles
depended_on_by:
  - agentd-daemon
  - data-flow
  - hal-contract
  - init-system
  - sandbox
  - shell-overview
  - transport-unix-socket
  - trust-boundaries
last_updated: 2026-04-30
---
# Process Model

## Problem

Kiki OS runs many processes. Their relationships, privileges, supervision strategy, and crash semantics need to be defined precisely so that:

- Each subsystem is implementable independently.
- Crash containment is verifiable.
- Privilege escalation paths are auditable.
- Boot ordering is unambiguous.

## Constraints

- Use Linux process primitives: pid, uid, gid, namespaces, cgroups.
- Integrate with systemd as supervisor.
- Enforce least privilege: no process runs as root after initialization.
- Support dynamic process spawning (apps, subagents, ephemeral tools).
- Apps run as containers (podman quadlet); the process model accommodates this.

## Decision

Kiki OS organizes processes into **five categories** with distinct privilege levels and supervision strategies.

```
┌───────────────────────────────────────────────────────────────┐
│  CATEGORY A — KERNEL                                          │
│  pid 0, ring 0; not a process in userspace sense              │
├───────────────────────────────────────────────────────────────┤
│  CATEGORY B — SYSTEM SERVICES (root or system uid)            │
│  systemd (PID 1), NetworkManager, PipeWire, HAL daemons,      │
│  udev, journald, podman service, voice service                │
├───────────────────────────────────────────────────────────────┤
│  CATEGORY C — AGENT HARNESS (kiki-runtime uid)                │
│  agentd, policyd, inferenced, memoryd, toolregistry           │
├───────────────────────────────────────────────────────────────┤
│  CATEGORY D — APPS (per-app uid, sandboxed via podman)         │
│  CLI tools, headless services, interactive ephemeral,         │
│  interactive services                                          │
├───────────────────────────────────────────────────────────────┤
│  CATEGORY E — UI (kiki-ui uid)                                │
│  cage compositor, agentui shell                                │
└───────────────────────────────────────────────────────────────┘
```

## Category A — Kernel

The Linux kernel. Not a userspace process. Mentioned for completeness.

## Category B — System services

Run as root or dedicated system uids (e.g., `network`, `_pipewire`, `_voice`, `kiki-hal`). Started by systemd at boot. Supervised: restarted on crash.

Examples:

- `systemd` — pid 1, init.
- `NetworkManager` — network configuration.
- `systemd-resolved` — DNS resolution.
- `PipeWire` + `wireplumber` — audio.
- `kiki-hald-*` — HAL daemons (one per major hardware domain).
- `kiki-voiced` — voice pipeline service.
- `podman.service` — container engine (rootless mode user-scoped, but the system service is at category B).
- `journald` — log aggregation.

System services do not run user code. They expose interfaces (DBus over Unix sockets, NATS subjects, or Cap'n Proto) to higher layers.

## Category C — Agent harness

Five processes running as the dedicated `kiki-runtime` system uid:

- `agentd` — supervisor and orchestrator.
- `policyd` — capability gate and arbiter classifier.
- `inferenced` — L7 inference proxy.
- `memoryd` — memory facade.
- `toolregistry` — tool dispatch registry.

Distributed as a sysext OCI artifact. systemd-sysext refresh on update.

Supervised by systemd with restart policy. If `agentd` crashes more than 3 times in 5 minutes, the system enters maintenance mode and surfaces the issue.

Internally, each daemon is a single Linux process running a tokio async runtime with many tasks. They are not process trees.

## Category D — Apps

Each app runs as a podman container.

- The container has its own user namespace.
- Inside the container, the app may run as any uid; from the host, it runs as a per-app subordinate uid (`app_<ns>-<name>` mapped to a range).
- The container is launched via systemd quadlet (a `.container` file in `/etc/containers/systemd/`).
- The container's sandbox is configured by the app's Profile and the runtime's quadlet generator.
- Per-user isolation: multi-user devices launch separate container instances per user with bind-mounted user data directories.

Four runtime modes (defined in `06-sdk/APP-RUNTIME-MODES.md`):

- **CLI tool** — process spawned per tool call (transient quadlet); reads stdin, writes stdout, exits.
- **Headless service** — long-running container; exposes a Cap'n Proto socket.
- **Interactive ephemeral** — like CLI tool but has bind-mount to `agentui` socket for block emission.
- **Interactive service** — long-running with UI surfaces.

Apps cannot communicate directly with each other. All app-to-app data flow goes through `agentd` (via tool calls and the memory subsystem) or through explicit shared resources granted by capability.

## Category E — UI

Two processes:

- `cage` — kiosk Wayland compositor. Runs as `kiki-ui` uid. Has access to display hardware (DRM, input devices).
- `agentui` — the single GUI app. Runs as `kiki-ui` uid. Embedded within cage's Wayland session.

`agentui` is not a system service in the systemd sense; it is the user-mode session. cage and `agentui` start together as part of the user's graphical session, supervised by systemd-user.

## Privilege escalation

The privilege gradient is one-directional: lower categories cannot acquire higher privileges through any defined path.

```
A (kernel)
   ↑ syscalls (kernel-mediated)
B (system services)
   ↑ system service RPC (capability-gated)
C (agent harness)
   ↑ Cap'n Proto requests (capability-gated)
D, E (apps, UI)
```

Apps cannot directly invoke system service RPCs. They request operations through `agentd`, which decides whether to dispatch them based on the capability gate. System services enforce their own access checks against `agentd`'s identity, not the requesting app's.

## Supervision strategy

systemd is the supervisor. Each service has:

- **A type:** `Type=notify` for daemons that signal readiness, `Type=oneshot` for one-shot tasks, `Type=exec` for simple processes.
- **Dependencies:** what must be ready before this starts (`Requires=`, `After=`).
- **Restart policy:** `Restart=on-failure` with backoff, `StartLimitBurst=` to give up after N failures.
- **Logger:** journald per service, structured logging via `tracing` crate.

Kiki-specific service definitions live in the runtime sysext under `/usr/lib/systemd/system/kiki-*.service`.

Apps are not directly supervised by systemd at the service level; they are supervised by their quadlet-generated unit (which systemd manages). Quadlet declares restart policy per app per its Profile.

UI processes are managed by systemd-user with similar policy.

## Boot order

```
1. Bootloader (systemd-boot) → kernel + UKI
2. Kernel → mount root (read-only, dm-verity), /dev, /proc, /sys
3. Kernel → execute systemd as PID 1
4. systemd brings up dependency tree:
   a. systemd-cryptenroll → unseal LUKS keys via TPM PCRs
   b. /var, /home mount with decryption
   c. journald
   d. systemd-networkd / NetworkManager (async)
   e. systemd-resolved
   f. PipeWire system service
   g. kiki-hald-* daemons
   h. systemd-sysext refresh (mounts kiki-runtime sysext)
   i. kiki-runtime.target → starts memoryd, inferenced, toolregistry, policyd, agentd in dependency order
   j. kiki-voiced (if voice enabled)
   k. user session via systemd-user (cage + agentui)
5. agentd discovers apps, registers tools, starts headless service apps per their Profile
6. cage launches agentui as its single Wayland client
7. System ready
```

Each step has a timeout. A failed step does not abort boot if its dependents can run without it (e.g., network failure does not block agentd; agentd starts and operates in offline mode).

Total boot time target on reference hardware: under 30 seconds cold.

## Crash semantics

Failure of one process does not cascade except along documented dependencies.

- **Kernel panic.** Forces reboot. bootc A/B rollback applies if repeated boot-time.
- **System service crash (Category B).** systemd restarts. Repeated crashes trigger maintenance mode.
- **`agentd` crash.** systemd restarts. State recovered from disk (memory subsystem, audit log, mailbox). Apps see Cap'n Proto connection drop and retry. Repeated crashes (4 in 60s) trigger maintenance mode.
- **Other Category C daemon crash (`policyd`, `inferenced`, etc.).** systemd restarts. `agentd` reports degraded mode for affected capability.
- **App service crash (Category D).** podman/systemd restarts per its Profile policy. After threshold, marked unavailable; agent treats tool as missing.
- **Ephemeral tool crash.** `agentd` treats it as a tool failure, returns the failure to the agent. Agent decides next action.
- **`agentui` crash (Category E).** cage detects, restarts agentui. Workspace state recovered from journal.
- **cage crash.** systemd-user restarts. Display session re-established.

## User scoping

Multi-user devices have per-user app instances:

- Each user has their own per-app data directory at `/var/lib/kiki/apps/<ns>/<name>/data-<user>/`.
- Container runtime instantiates separate containers per user per app (where the Profile declares per-user scoping; some apps opt into shared mode).
- `agentd` tracks the active user. Per-user state in working memory.

Single-user devices have one user logically; the same scoping mechanisms apply but the user count is one.

## Consequences

- Adding a new system service requires a new system uid and a systemd unit definition.
- Adding a new app does not require system changes; the install process generates the quadlet and assigns a per-app uid range.
- The number of processes scales with active apps and live agent tasks, not with installed apps.
- Process counts are measurable: `systemctl list-units` and `podman ps` give the full picture.
- Crash isolation is testable: induce a crash in one process, verify others continue.
- Privilege boundaries are enforceable: every process has a known uid and sandbox profile.

## References

- `01-architecture/SYSTEM-OVERVIEW.md`
- `01-architecture/APPLIANCE-MODEL.md`
- `02-platform/INIT-SYSTEM.md`
- `02-platform/SANDBOX.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `03-runtime/AGENTD-DAEMON.md`
- `06-sdk/APP-RUNTIME-MODES.md`
## Graph links

[[SYSTEM-OVERVIEW]]  [[APPLIANCE-MODEL]]  [[PRINCIPLES]]
