---
id: vision
title: Vision
type: DESIGN
status: draft
version: 0.0.0
depends_on: []
depended_on_by:
  - deterministic-vs-agentic
  - paradigm
  - principles
  - roadmap
  - system-overview
last_updated: 2026-04-30
---
# Vision

## Problem

Operating systems in widespread use today were designed before the agentic shift in computing. Their assumptions are no longer correct for devices where:

- An agent observes continuously and acts autonomously on behalf of the user.
- Applications are tools the agent orchestrates, not destinations the user navigates to.
- Intelligence runs locally on the device where possible, and across cloud routes when necessary.
- Permission models govern autonomous actions, not just user clicks.
- Memory persists across sessions and reasons about its own state.

Bolting an agent onto Linux, Android, iOS, Windows, or macOS produces a layer of compromises. Background processes fight the host lifecycle. Permission dialogs were built for explicit user authorization, not for autonomous agents acting within bounds. Memory is per-app, not per-system. The user interface assumes the user knows which application solves their problem.

These are not bugs in the host operating systems. They are correct choices for what those systems were designed to be. They are wrong for an agent-native operating system.

## Constraints

- Open source under permissive licenses where compatible with our paradigm; copyleft only where required.
- Run on commodity Linux-capable desktop hardware with future extensibility to other classes.
- Function fully without network connectivity. Cloud is enhancement, not foundation.
- No hard dependency on a specific cloud backend. The protocols are open.
- Privacy enforced by architecture, not by policy.
- Implementation language for system code is Rust.
- The OS is single-purpose. Generalist Linux assumptions are out of scope.
- The work is conducted as **open research, in public**: design, decisions, and code are shared as they evolve, and the system must reach a level of stability and functionality real enough that an external community can run it, study its interaction model, and contribute back.

## What kind of project this is

Kiki OS is a research project on **agentic computing**, with a particular emphasis on **human–computer interaction and UX**. Its purpose is to investigate how far modern agentic systems — when integrated at the OS level rather than bolted on as applications — can change the way people interact with computers and mobile devices. The intended outputs are twofold: a working operating system, and observations about agentic interaction that the community can replicate, contest, and build upon. This shapes the corpus: it is sized to be a serious technical contract, because vague specifications cannot host a public conversation, and because a research result is only as useful as the artifact people can actually run. Kiki is not a commercial product; the success criterion is whether the experiment yields a system worth using and lessons worth keeping.

## Decision

Kiki OS is an **appliance operating system for agentic computing**. Specifically:

1. **The agent is the substrate**, not an application. The agent harness is a privileged system service that mediates every action between the user and the system, and between apps and the system.

2. **Applications are sandboxed services** the agent orchestrates. They expose tools through a binary protocol. Users do not navigate to them.

3. **Memory is a system service** with structured layers, drift defenses, and explicit consent for identity changes.

4. **Capabilities gate every sensitive action**, enforced at both the kernel sandbox and the runtime gate.

5. **The user interface is a single canvas** rendered by the agent. Surfaces appear when relevant, not because the user navigated to them.

6. **The base operating system is image-based, atomically deployed, and signed end-to-end**. Updates are atomic; rollback is automatic on failure.

7. **All distribution is OCI-native**. Apps, components, tools, profiles, models, and the base image are signed OCI artifacts in federated registries.

8. **The cloud is optional**. Devices are fully functional without network connectivity. Backend protocols are open standards.

## Rationale

**Linux as the kernel.** Reusing Linux gives us hardware support, security primitives (Landlock, seccomp, namespaces, cgroups), upstream maintenance, and a mature ecosystem. Innovation belongs at higher layers.

**Rust as the implementation language.** Memory safety is not optional in privileged code that runs in users' homes and devices. Rust is the only mainstream language that gives us this without runtime garbage collection.

**Agent as substrate, not application.** If the agent is just an app, every other app needs to integrate with it ad-hoc. If the agent is the substrate, integration is structural: every app exposes tools, every tool goes through the agent, every action is visible to the user.

**Capability-based security with two layers.** The kernel sandbox catches escape attempts at the OS level. The capability gate catches policy violations at the runtime level. Together: defense in depth — a single layer's failure does not compromise the system.

**Memory as system service.** A long-running agent needs persistent, structured memory. Per-app memory produces idiosyncratic systems that cannot be inspected or audited. System-level memory is inspectable, editable, exportable, and survives agent restarts and model changes.

**Local-first with optional cloud.** Edge inference, edge memory, edge UI. The cloud adds capabilities (cross-device sync, larger models, fleet management) but is never required. Disconnected devices remain functional.

**OCI everywhere.** A single distribution format, a single signing model, a single trust mechanism. Industry-standard, federated, mirror-friendly, vendor-neutral.

**Appliance shape.** Kiki is single-purpose. The OS exists to run the agent and its shell. The user does not interact with package managers, files, services, or units. They interact with the agent. Linux underneath is an implementation detail.

## Consequences

- The capability taxonomy is large and explicit. Every sensitive action has a named capability. See `10-security/CAPABILITY-TAXONOMY.md`.
- The agent harness is the most security-critical userspace component. See `03-runtime/AGENTD-DAEMON.md`.
- Apps cannot communicate directly with each other. App-to-app data flow goes through the agent or through explicit shared resources. See `01-architecture/TRUST-BOUNDARIES.md`.
- The memory subsystem has six distinct layers with different storage backends and protection levels. See `04-memory/MEMORY-ARCHITECTURE.md`.
- The UI is a single canvas with reactive composition, not windows. See `07-ui/CANVAS-MODEL.md`.
- Cloud backends are optional and replaceable. The protocol is open. See `09-backend/BACKEND-CONTRACT.md`.
- Identity is three Markdown files (SOUL, IDENTITY, USER) with versioning and consent flow. See `04-memory/IDENTITY-FILES.md`.
- All artifacts are OCI-distributed and signed. See `12-distribution/OCI-NATIVE-MODEL.md`.

## References

- `00-foundations/PARADIGM.md`
- `00-foundations/PRINCIPLES.md`
- `01-architecture/SYSTEM-OVERVIEW.md`
- `01-architecture/THREAT-MODEL.md`
