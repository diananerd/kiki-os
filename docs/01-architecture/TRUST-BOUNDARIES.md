---
id: trust-boundaries
title: Trust Boundaries
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - system-overview
  - process-model
  - data-flow
  - principles
depended_on_by:
  - remote-architecture
  - threat-model
last_updated: 2026-04-30
---
# Trust Boundaries

## Problem

Every meaningful security property of Kiki OS depends on knowing where data is trusted and where it is not. Without explicit boundaries, validation logic gets repeated, missed, or weakened. Each boundary is a place where unverified data crosses from one trust level to another and must be checked.

## Constraints

- Each boundary must have one enforcement point, not many. Multiple enforcement points create coverage gaps when they disagree.
- Each boundary must be auditable: the check happened or not.
- Each boundary must be testable in isolation.
- The total number of boundaries must be small enough to remember.

## Decision

Kiki OS has **eight trust boundaries**. Every cross-boundary data flow goes through a defined check at exactly one point. The boundaries are listed in the order data typically crosses them on its way into the system, then on its way out.

```
    outside world
        │
    [BOUNDARY 8] outside content → inside trust
        │
    [BOUNDARY 6] device ↔ backend
        │
    [BOUNDARY 5] device ↔ network
        │
    ┌───┴────────────────────────────┐
    │                                 │
    │  [BOUNDARY 1] hardware ↔ kernel │
    │  [BOUNDARY 2] kernel ↔ userspace│
    │  [BOUNDARY 3] agentd ↔ apps     │
    │  [BOUNDARY 4] app ↔ app         │
    │  [BOUNDARY 7] user ↔ device     │
    │                                 │
    └─────────────────────────────────┘
```

## Boundary 1 — Hardware to kernel

**What crosses.** Device firmware blobs. Sensor readings. Hardware events. Boot keys.

**Trust assumption.** Hardware is trusted to the extent that verified boot succeeded and tamper detection (where present) shows no tampering.

**Enforcement point.** The boot chain (verified boot via systemd-boot + UKI + dm-verity) plus the hardware manifest signature check at boot.

**What can fail.** Compromised silicon, modified firmware in transit, broken tamper seals. We accept that we cannot defend against arbitrarily compromised hardware; we make tampering visible where possible via TPM PCR sealing.

See: `02-platform/BOOT-CHAIN.md`, `10-security/VERIFIED-BOOT.md`, `02-platform/HARDWARE-MANIFEST.md`.

## Boundary 2 — Kernel to userspace

**What crosses.** System calls from userspace processes.

**Trust assumption.** Userspace is partially trusted. Privileged services (Category B and C) more so, apps (Category D) less so.

**Enforcement point.** The Linux kernel sandbox: Landlock for filesystem, seccomp for syscalls, namespaces for network and processes, cgroups for resources. For apps, this is provided by the container runtime (podman + crun) automatically.

**What can fail.** Kernel CVEs. We mitigate with prompt patching (atomic OCI updates make this fast), selective kernel feature inclusion, and the capability gate as a second defensive layer (defense in depth).

See: `02-platform/SANDBOX.md`, `02-platform/KERNEL-CONFIG.md`, `02-platform/CONTAINER-RUNTIME.md`.

## Boundary 3 — agentd to apps

**What crosses.** Tool calls and tool results encoded in Cap'n Proto over Unix sockets.

**Trust assumption.** `agentd` is privileged (Category C); apps (Category D) are not.

**Enforcement point.** The capability gate inside `policyd`. Every tool call is checked against the calling context's granted capabilities. Schema validation is performed by Cap'n Proto at the protocol boundary; semantic validation by the gate.

**What can fail.** A capability gate bug. A schema validation bypass. Cap'n Proto deserialization vulnerability. We test these adversarially, fuzz the parsers, and audit the gate's decisions in the audit log.

See: `03-runtime/CAPABILITY-GATE.md`, `05-protocol/CAPNP-RPC.md`.

## Boundary 4 — App to app

**What crosses.** Nothing, directly.

**Trust assumption.** Apps do not trust each other.

**Enforcement point.** Architectural: there is no shared memory between apps, no service bus where they can find each other directly, no filesystem access to each other's directories. App-to-app data flow goes through `agentd` (one app's tool calls another, mediated by the agent and the gate) or through explicit shared resources granted by capability.

Each app runs in its own container with its own user namespace, network namespace, and bind-mounted data directory. The container runtime enforces the isolation.

**What can fail.** A side-channel through a shared resource that both apps were granted access to. We mitigate by making shared grants explicit and audited.

See: `02-platform/CONTAINER-RUNTIME.md`, `06-sdk/APP-RUNTIME-MODES.md`.

## Boundary 5 — Device to network

**What crosses.** All outbound and (rarely) inbound network traffic.

**Trust assumption.** The network is hostile.

**Enforcement point.** Two layers:

1. The container's network namespace per app, configured at sandbox creation. An app can only connect to hosts in its declared network capability list.
2. The capability gate, which checks `network.outbound.host` at the time of the call (for system services not in containers; apps' network is enforced by the namespace alone).

**What can fail.** Misconfigured netns. A whitelist that's too permissive. We mitigate with explicit per-host grants (no broad wildcards by default) and audit logging of every connection initiation.

See: `02-platform/NETWORK-STACK.md`, `02-platform/CONTAINER-RUNTIME.md`, `10-security/CAPABILITY-TAXONOMY.md` (network.* section).

## Boundary 6 — Device to backend

**What crosses.** Backend protocol traffic: provisioning, OTA, AI Gateway, registry, optional memory sync.

**Trust assumption.** The backend is partially trusted. We assume its operator (whoever runs it) is honest. We do not assume:

- That a specific backend service has not been compromised.
- That an upstream provider (LLM provider for AI Gateway) is uncompromised.
- That the backend has access to data it does not need.

**Enforcement point.** mTLS device authentication for every connection. The inference router's privacy classification before any data is sent. Audit log records what was sent. cosign verification of all OCI artifacts pulled (independent of TLS).

**What can fail.** A compromised backend could refuse service, log requests, or deliver malicious updates. We mitigate with:

- cosign signatures on all artifacts (compromised backend cannot forge).
- Privacy classification preventing Sensitive data from reaching the backend.
- Audit log for inspection.
- The option to use an alternative backend or no backend.

See: `09-backend/DEVICE-AUTH.md`, `09-backend/BACKEND-CONTRACT.md`, `03-runtime/INFERENCE-ROUTER.md`.

## Boundary 7 — User to device

**What crosses.** User commands (voice, touch, gesture, messaging).

**Trust assumption.** The user is fully trusted in the normal case.

**Enforcement point.** Confirmation flows for sensitive actions. Speaker identification for multi-user. Hardware kill switches that the user can verify physically. The consent flow for identity changes (non-bypassable).

**What can fail.** User can be deceived (social engineering), coerced, or make mistakes. We mitigate with:

- Clear confirmation prompts (the `Confirm` component shows what is being granted).
- Audit visibility (the user can review what happened).
- Reversible-by-default actions (most actions can be undone).
- Hardcoded restrictions (some actions cannot be approved by anyone).

See: `04-memory/CONSENT-FLOW.md`, `08-voice/SPEAKER-ID.md`, `02-platform/HARDWARE-KILL-SWITCHES.md`.

## Boundary 8 — Outside content to inside

**What crosses.** Content from outside the system that the agent processes: voice transcripts, web pages, file contents, app descriptions, perception data, tool results from external services.

**Trust assumption.** Content is data, not commands. Instructions embedded in content are not authoritative.

**Enforcement point.** The agent's hardcoded behaviors cannot be overridden by content it processes. Capability gate denies any tool call that wasn't authorized regardless of who suggested it. Source provenance is tracked in memory. The arbiter classifier sees only the user's literal request and the proposed tool call (input minimization), never the agent's reasoning prose, so prompt injection in agent prose cannot reach the gate.

**What can fail.** Prompt injection that succeeds in influencing the agent's reasoning. The capability gate is the backstop: even an influenced agent cannot do what its capabilities don't permit. The CaMeL pattern (split planner/parser) is applied for tools touching the lethal trifecta.

See: `03-runtime/CAPABILITY-GATE.md`, `03-runtime/ARBITER-CLASSIFIER.md`, `04-memory/DRIFT-MITIGATION.md`, `10-security/HARDCODED-RESTRICTIONS.md`, `10-security/CAMEL-PATTERN.md`.

## Properties guaranteed by the boundaries

When all eight boundaries are correctly enforced:

1. **An app cannot exceed its declared capabilities** even if its code is malicious. The kernel sandbox limits what's possible; the capability gate enforces what's permitted.

2. **Sensitive data does not leave the device without authorization.** The inference router enforces privacy levels at boundary 6; the capability gate enforces network egress at boundary 5; the sandbox enforces filesystem boundaries at boundary 2.

3. **A compromise of one app does not compromise others.** Boundary 4 prevents direct app-to-app communication; the capability gate (boundary 3) prevents indirect compromise via shared resources.

4. **A compromise of the backend does not compromise the device's local data.** Boundary 6 limits what the backend can do to the device. Local data and identity remain on-device. cosign signatures prevent the backend from forging artifacts.

5. **Adversarial content does not gain agent capabilities.** Boundary 8 enforces that processed content is data; the capability gate enforces that tool calls require declared capabilities; identity invariants cannot be overridden.

## Consequences

- Every cross-boundary call has one defined enforcement point. Adding a second enforcement point would create a coverage gap if the second point disagrees with the first.
- The audit log records boundary crossings of interest. The audit log itself crosses no trust boundary (it is append-only, hash-chained, kept on the local device).
- Any change to a boundary requires an RFC. Boundaries change rarely.
- New components must declare which boundaries they sit on. A component that sits on a boundary is responsible for the enforcement at that point.

## References

- `01-architecture/SYSTEM-OVERVIEW.md`
- `01-architecture/PROCESS-MODEL.md`
- `01-architecture/THREAT-MODEL.md`
- `03-runtime/CAPABILITY-GATE.md`
- `02-platform/SANDBOX.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/PRIVACY-MODEL.md`
## Graph links

[[SYSTEM-OVERVIEW]]  [[PROCESS-MODEL]]  [[DATA-FLOW]]  [[PRINCIPLES]]
