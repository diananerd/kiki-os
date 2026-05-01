---
id: 0001-appliance-os-paradigm
title: Appliance OS for Agentic Computing
type: ADR
status: draft
version: 0.0.0
depends_on: []
last_updated: 2026-04-29
depended_on_by:
  - 0002-oci-native-distribution
  - 0005-no-package-manager-user-facing
  - 0006-centos-stream-bootc-upstream
  - 0008-systemd-init
  - 0012-podman-quadlet-app-runtime
  - 0013-cage-kiosk-compositor
  - 0038-camel-trifecta-isolation
---
# ADR-0001: Appliance OS for Agentic Computing

## Status

`accepted`

## Context

Kiki must decide its OS-level identity. Two broad shapes are available:

- A general-purpose Linux distribution (Debian-, Fedora-, Arch-derivative) with the agent and its shell as components installed alongside conventional Linux software.
- A single-purpose appliance OS in the lineage of ChromiumOS, Fedora CoreOS, Bottlerocket, Talos, SteamOS — where the entire OS exists for one purpose and Linux is an implementation detail invisible to the user.

The first shape produces compromises at every layer: the agent fights the host's lifecycle, package management duplicates concerns, security boundaries are optional rather than structural, and the user is exposed to Linux internals that contradict the agent's promises (predictability, safety, simplicity).

The second shape constrains the design space sharply but lets every layer align with the same purpose.

## Decision

Kiki OS is an **appliance operating system for agentic computing**.

Five irreducible properties define this shape:

1. **Single-purpose.** The OS exists to run the agent and its shell. It is not configurable into a generalist Linux.
2. **Opaque to user.** Linux internals (package managers, services, files, units) never emerge in the user experience.
3. **Image-based atomic.** The OS is a signed, content-addressed image. Updates and rollbacks are atomic.
4. **Signed end-to-end.** Every artifact carries a verifiable cryptographic signature.
5. **Declarative state.** Everything that matters is declared in signed artifacts; runtime state is derivable.

The lineage is explicit: ChromiumOS, CoreOS family (Flatcar, Fedora CoreOS, Bottlerocket, Talos), SteamOS 3, Universal Blue. Kiki extends this lineage to the agentic domain.

## Consequences

### Positive

- Every other technical decision has a clear test: does it preserve the five properties?
- Wide classes of decisions are ruled out (generalist Linux conventions, user-facing package managers, writable root, manual configuration).
- The system's behavior is predictable and verifiable end-to-end.
- Maintenance burden is bounded: we maintain only what we publish.
- Security and safety are structural rather than aspirational.

### Negative

- We cannot serve users who want a general-purpose Linux. They must use a different OS.
- We cannot ship features that compromise the appliance shape, even when they would be convenient.
- Users with deep Linux expertise find Kiki opaque by design. The OS is not a hacker's playground.
- Some decisions feel rigid because they are structural rather than configurable.

## Alternatives considered

- **General-purpose Linux distribution with agent application.** Rejected because the resulting compromises (lifecycle, security, predictability) contradict the agent's promises.
- **Custom-built minimal Linux from scratch (LFS-style).** Rejected because it requires us to maintain everything, contradicting the principle of inheriting upstream support.
- **Build on Flatpak/Snap/AppImage as primary distribution.** Rejected because their compromise (cross-distro portability) is irrelevant when the OS is single-purpose, and adds runtime layers we don't need.
- **Pure NixOS-style declarative OS.** Rejected because the Nix paradigm conflicts with OCI/container distribution we want to standardize on.

## References

- `00-foundations/PARADIGM.md`
- `00-foundations/VISION.md`
- `00-foundations/PRINCIPLES.md`
- `01-architecture/APPLIANCE-MODEL.md`
- ChromiumOS architecture docs
- Fedora CoreOS / bootc documentation
- Talos Linux design rationale
