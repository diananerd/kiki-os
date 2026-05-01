---
id: paradigm
title: Paradigm — Appliance OS for Agentic Computing
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - vision
depended_on_by:
  - anti-patterns
  - appliance-model
  - backend-contract
  - design-philosophy
  - hardware-abstraction
  - image-composition
  - oci-native-model
  - principles
  - privacy-model
  - roadmap
  - sdk-overview
  - system-overview
  - upstream-choice
last_updated: 2026-04-30
---
# Paradigm

## Problem

A general-purpose Linux distribution with an agent application bolted on is a category mismatch. The agent fights the host's lifecycle, cannot enforce its own contract, and exposes a surface area that contradicts its own promises (privacy, safety, predictability).

Without a paradigm declaration, every technical decision becomes a re-litigation of the same trade-offs. Engineers default to whatever the local Linux convention is, even when the convention contradicts the system's purpose.

## Constraints

- The paradigm must be irreducible: stated in one sentence, supported by a small set of properties.
- It must be testable: any decision can be checked against the paradigm.
- It must be exclusionary: it must rule out wide classes of decisions, not just suggest them.
- It must be honest about lineage: Kiki is not the first appliance OS, and the paradigm should acknowledge ancestors.

## Decision

Kiki OS is an **appliance operating system for agentic computing**.

This places Kiki in the lineage of:

- **ChromiumOS** (2009) — appliance for browser-based productivity.
- **CoreOS** (2013) and its descendants **Flatcar Linux** (2018), **Fedora CoreOS** (2018), **Bottlerocket** (2020), **Talos Linux** (2018) — appliances for containerized workloads.
- **SteamOS 3** (2022) — appliance for gaming.
- **Universal Blue / bluefin / aurora** (2023+) — desktop appliances built on Fedora atomic.

Kiki extends this lineage to the agentic domain. The OS exists to run an agent and its shell. Everything else is implementation detail.

## Five irreducible properties

The paradigm is supported by five properties. None is negotiable.

### 1. Single-purpose

The OS exists to run the agent and its shell. It is not a generalist Linux that can also host an agent. It is not configurable into a different kind of OS. It is not a base on which the user can build their own desktop environment. The single purpose is agentic computing.

### 2. Opaque to user

The user does not interact with "Linux". They interact with Kiki. Package managers, configuration files, services, units, mount points, kernel parameters, init scripts — these are detail of the implementation and never emerge in the experience. The user interacts with the agent shell and the agent.

### 3. Image-based atomic

The OS is a signed image, indistinct, atomic. The user does not install packages into the OS; they deploy a new OS image. Rollback is a flip of the boot pointer. State that must survive lives in `/var` and `/home` with declarative merge semantics. The image is content-addressed and tamper-evident.

### 4. Signed end-to-end

Every artifact (kernel, base image, system extension, app, component, tool, profile, model, skill, agent bundle) carries a verifiable cryptographic signature. Trust is per-namespace, scoped, rotatable, and revocable. There is no implicit trust anywhere in the system.

### 5. Declarative state

Everything that matters about the system is declared in signed artifacts. Runtime state is derivable from artifacts plus explicit user interaction. Drift — accidental state divergence from the declared shape — is detected and reconciled, never tolerated.

## Lineage and what we inherit conceptually

| Ancestor | Concept Kiki inherits |
|---|---|
| ChromiumOS | The user-facing OS is opaque about Linux underneath. Single-purpose appliance. Atomic update. |
| CoreOS / Fedora CoreOS | Image-based atomic OS, A/B partition rollback, automatic updates. Container-native. |
| Bottlerocket | Minimal base, container-first, signed image, API-only access. |
| Talos Linux | No SSH, no shell access, API-only configuration. The OS is not a thing you log into; it is a thing that runs. |
| Flatcar Linux | Container Linux philosophy: the OS is just enough to run containers. |
| Fedora atomic family | bootc, OSTree, podman, cosign, Sigstore — the modern toolchain for atomic image-based Linux. |
| SteamOS 3 | Appliance shape applied to a consumer desktop product. |
| Universal Blue / bluefin | Community-driven desktop appliances built on Fedora atomic with bootc. |

Kiki's own contribution is to apply the appliance pattern to **agentic computing**: the agent harness as system substrate, memory as system service, the canvas as the only user surface, OCI distribution for everything (not just containers). The contribution is also a research one — Kiki is built and refined in public so that the resulting interaction model can be studied, contested, and built upon by anyone, not only used.

## Lineage and what we reject

What we explicitly do **not** inherit from its lineage of ancestors, even where adjacent:

- **From ChromiumOS**: vendor lock-in to a single ecosystem (Google account, ChromeOS apps).
- **From Fedora atomic family**: GNOME/KDE assumed as default desktop. Kiki has its own shell, not a desktop environment.
- **From Bottlerocket / Talos / CoreOS**: server-shape orientation. Kiki is for personal computing, not container hosting.
- **From SteamOS**: a single-vendor app store. Kiki's distribution is federated.

## What the paradigm demands

A decision must satisfy the paradigm to be acceptable. A test for any technical proposal:

1. Does it preserve single-purpose? A feature that turns Kiki into a generalist Linux fails this.
2. Does it preserve opacity to the user? A feature that exposes Linux internals to the user fails this.
3. Does it preserve image-based atomic semantics? A feature that lets the user mutate the base outside the image flow fails this.
4. Does it preserve signed end-to-end? A feature that introduces an unsigned trust path fails this.
5. Does it preserve declarative state? A feature that depends on imperative drift fails this.

If the answer to any of these is no, the proposal is rejected or reshaped until it complies.

## What the paradigm rejects

Several common Linux decisions are rejected by paradigm:

- A user-facing package manager (apt, dnf, pacman). Apps come as OCI artifacts.
- A traditional desktop environment (GNOME, KDE, Xfce). The shell is the agent's canvas.
- SSH access by default. The OS is operated through the agent and `agentctl`.
- A writable root filesystem. `/usr` is read-only and tied to the image.
- Manual configuration files maintained by the user. Configuration is declarative and versioned.
- Forking upstream packages. We consume upstream as inputs to image composition; we do not maintain a parallel copy.

## Consequences

- The choice of upstream Linux distribution becomes operational, not contractual. Whichever distribution gives us the best inputs to compose our image is acceptable.
- Distribution is OCI-native. There is no parallel apt/dnf/pacman track for end users.
- Apps run as containers (podman quadlet) rather than native installations.
- The OS image and its components carry cosign signatures verifiable end-to-end.
- The user-facing experience does not expose Linux details. The agent and its shell are the entire surface area.
- Updates are atomic across the entire system. There is no concept of "update one package."

## References

- `00-foundations/VISION.md`
- `00-foundations/PRINCIPLES.md`
- `01-architecture/APPLIANCE-MODEL.md`
- `02-platform/UPSTREAM-CHOICE.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `14-rfcs/0001-appliance-os-paradigm.md`
## Graph links

[[VISION]]
