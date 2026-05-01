---
id: 0006-centos-stream-bootc-upstream
title: CentOS Stream 10 bootc as Operational Upstream
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
  - 0002-oci-native-distribution
last_updated: 2026-04-29
depended_on_by:
  - 0007-mkosi-image-build
  - 0008-systemd-init
  - 0037-landlock-primary-apparmor-backstop
  - 0099-future-distribution-pivots
---
# ADR-0006: CentOS Stream 10 bootc as Operational Upstream

## Status

`accepted`

## Context

Kiki OS is composed from upstream Linux packages. The choice of upstream is operational (not exposed to the user) but affects tooling alignment, package freshness, hardware support, and predictable cadence.

Realistic upstream candidates: CentOS Stream 10, Fedora rawhide, Debian sid, openSUSE Tumbleweed, Arch.

## Decision

Use **CentOS Stream 10 bootc** as the operational upstream for Kiki OS in v0.

The upstream is invisible to the user. `/etc/os-release` reads `Kiki OS`, not `CentOS`.

## Consequences

### Positive

- bootc, OSTree, podman, crun, cosign, Sigstore, SELinux, Landlock all originated or matured in this ecosystem; alignment is best.
- Predictable release cadence as RHEL upstream.
- systemd 257+ default; kernel 6.12 LTS.
- bootc image-mode variant designed for atomic image-based deployment.
- x86_64 and arm64 first-class.

### Negative

- Smaller hardware breadth than Debian (especially riscv64 and exotic ARM SBCs).
- Volunteer-driven projects might prefer Debian's ethos.

## Alternatives considered

- **Fedora rawhide**: more current but more drift; not suitable for production cadence.
- **Debian sid (snapshotted)**: Plan B documented as `0099-future-distribution-pivots`; larger hardware breadth but bootc/OSTree tooling less mature.
- **openSUSE Tumbleweed**: rolling RPM; less alignment with bootc ecosystem.
- **Arch**: rolling pacman; conflicts with image-based atomic paradigm.
- **Custom from scratch (LFS, Yocto)**: rejected — we don't fork; we inherit.

## References

- `02-platform/UPSTREAM-CHOICE.md`
- `14-rfcs/0099-future-distribution-pivots.md`
