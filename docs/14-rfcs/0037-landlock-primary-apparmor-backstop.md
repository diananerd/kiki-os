---
id: 0037-landlock-primary-apparmor-backstop
title: Landlock Primary, AppArmor Backstop
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0006-centos-stream-bootc-upstream
last_updated: 2026-04-29
---
# ADR-0037: Landlock Primary, AppArmor Backstop

## Status

`accepted`

## Context

Linux Security Module (LSM) options for capability enforcement: Landlock, SELinux, AppArmor, bpf-lsm. The container runtime already provides namespace and seccomp isolation; the question is the primary LSM for filesystem and network policy.

## Decision

Use **Landlock** as the primary per-app capability enforcement layer, with **AppArmor** as a host-level backstop covering Kiki system services and daemons (defense in depth at the OS layer).

SELinux is not used. bpf-lsm is not used in v0.

## Consequences

### Positive

- Landlock is unprivileged; apps can sandbox themselves further if they want.
- Landlock 6 (kernel 6.7+) has TCP/UDP scoping and refer rules; sufficient for our needs.
- AppArmor is Debian-friendly and CentOS Stream-supported; provides MAC for system services.
- Combined: kernel sandbox + capability gate at runtime → defense in depth.

### Negative

- SELinux's policy model is more powerful but heavyweight; we don't use it.
- AppArmor profiles are an additional artifact to maintain (small set, for system services only).

## Alternatives considered

- **SELinux as primary**: heavyweight; policy authoring is significant work; rejected for our scope.
- **AppArmor as primary**: profile churn per binary change; per-app profiles harder to scale than Landlock's unprivileged composition.
- **bpf-lsm as primary**: powerful, but operational complexity high for systemd-supervised apps. Useful for telemetry hooks only.

## References

- `02-platform/SANDBOX.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `02-platform/KERNEL-CONFIG.md`
## Graph links

[[0006-centos-stream-bootc-upstream]]
