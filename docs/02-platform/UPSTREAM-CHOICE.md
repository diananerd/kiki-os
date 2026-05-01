---
id: upstream-choice
title: Upstream Choice
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - paradigm
  - appliance-model
  - hardware-abstraction
depended_on_by:
  - boot-chain
  - image-composition
  - init-system
  - kernel-config
  - snapshot-pinning
last_updated: 2026-04-30
---
# Upstream Choice

## Problem

Kiki OS is composed from upstream Linux packages (kernel, glibc, mesa, drivers, firmware, system libraries). The choice of upstream is operational, not contractual: the user never sees which upstream supplies the binaries. But the choice still matters for tooling alignment, package freshness, hardware support breadth, and predictable cadence.

## Constraints

- The user must not see the upstream identity. `/etc/os-release` reads `Kiki OS`, not the upstream's name.
- The upstream must support the chosen stack (systemd 257+, kernel 6.7+, bootc, mkosi, podman, cosign, Landlock).
- The upstream must have a predictable release cadence.
- The upstream must support our target architectures (x86_64, arm64; future riscv64).
- We must never fork upstream packages. Fixes are contributed upstream.

## Decision

**CentOS Stream 10 bootc** is the operational upstream for Kiki OS in v0.

Rationale:

- **bootc-native ecosystem.** bootc, OSTree, podman, crun, cosign, Sigstore, SELinux, Landlock — all originated or matured in the Red Hat ecosystem. CentOS Stream is the upstream of RHEL with first-class support for all these tools.
- **Predictable cadence.** CentOS Stream releases follow a known schedule. Stream 10 is the upstream for RHEL 10.
- **systemd freshness.** Stream 10 ships systemd 257 with sysext, sysupdate, soft-reboot, cryptenroll PCR sealing, Landlock unit directives.
- **Kernel freshness.** Stream 10 ships kernel 6.12 LTS with Landlock 6 (TCP/UDP scoping, refer rules), bcachefs available, btrfs mature.
- **bootc image-mode.** Stream 10 has a first-class bootc-image-mode variant designed for atomic image-based deployment.
- **Multi-arch.** x86_64 and arm64 are first-class; riscv64 is in early support.

## Plan B: Debian sid (snapshotted)

If CentOS Stream becomes unsuitable (license change, project disruption, hardware breadth gap for specific deployments), Debian sid is the documented alternative:

- Larger hardware breadth (more ARM SBCs, riscv64 first-class earlier).
- Volunteer-driven (philosophical alignment with open-source ethos).
- Slower bootc/OSTree maturity, but functional.
- Snapshot pinning via snapshot.debian.org for reproducibility.

A migration to Debian sid changes the build pipeline (mkosi accepts Debian as a source) but does not change the user-facing OS or app distribution model. Documented as `14-rfcs/0099-future-distribution-pivots.md`.

## What we consume from upstream

The base OS image composes the following from CentOS Stream 10:

- Linux kernel (with our kernel config — see `02-platform/KERNEL-CONFIG.md`).
- glibc and base userspace (coreutils, util-linux).
- systemd 257+.
- systemd-boot, sd-stub, ukify (UKI tooling).
- bootc.
- podman + crun (rootless container runtime).
- mesa (GPU drivers including NVK, RadeonSI, Iris).
- nvidia-open kernel modules (when NVIDIA hardware present).
- PipeWire 1.4+ + wireplumber.
- NetworkManager.
- systemd-resolved.
- LUKS2 + cryptsetup + tpm2-tools.
- btrfs-progs.
- Standard runtime libraries (openssl-libs, ncurses, libxml2, etc.) as needed.

## What we do NOT consume from upstream

The following are explicitly excluded from the base image:

- GNOME, KDE, Xfce, or any desktop environment.
- X11 server (we are Wayland-only).
- bash as the user's default shell (no shell-access user surface).
- Traditional dnf/yum tooling for user use (image-mode-fedora-style).
- Documentation packages (man pages, info pages) for user-facing tools.
- Locales beyond English and Spanish (other locales installed by user opt-in).
- Compilers and build tools (containers handle build for apps).
- System monitoring TUIs (htop, top, etc.) — diagnostics through `agentctl`.

## Snapshot pinning

To make builds reproducible, mkosi pins to a specific CentOS Stream 10 build timestamp. The pinned snapshot is part of the build pipeline configuration. Promoting to a newer snapshot is a deliberate operation, not a side effect of "rolling" updates.

Details in `12-distribution/SNAPSHOT-PINNING.md`.

## What we never modify

- Upstream package binaries.
- Upstream package manager metadata.
- Upstream signing keys.

If we need a fix, we contribute to CentOS Stream upstream. If the fix is too slow or rejected, we document the gap and consider migration paths rather than maintaining a fork.

## Consequences

- We benefit from Red Hat's hardware enablement, kernel maintenance, and security backporting.
- We do not maintain glibc, kernel, mesa, or any base userspace.
- Our build pipeline depends on CentOS Stream 10 being available. We mirror upstream content for resilience.
- Migration to Debian sid is a documented path but a significant operational change. We do not optimize for it; we keep it open.
- The user does not see "CentOS" anywhere. `/etc/os-release` says Kiki OS. The bootloader says Kiki OS. The system identity is Kiki OS.

## References

- `00-foundations/PARADIGM.md`
- `02-platform/IMAGE-COMPOSITION.md`
- `02-platform/KERNEL-CONFIG.md`
- `12-distribution/SNAPSHOT-PINNING.md`
- `14-rfcs/0006-centos-stream-bootc-upstream.md`
- `14-rfcs/0099-future-distribution-pivots.md`
