---
id: 0008-systemd-init
title: systemd as Init and Supervisor
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
  - 0006-centos-stream-bootc-upstream
last_updated: 2026-04-29
depended_on_by:
  - 0009-systemd-boot-uki-pcr
  - 0010-btrfs-var-subvolumes
  - 0012-podman-quadlet-app-runtime
---
# ADR-0008: systemd as Init and Supervisor

## Status

`accepted`

## Context

Kiki needs an init system and process supervisor. Options: systemd, s6 / s6-rc, dinit, runit, OpenRC.

## Decision

Use **systemd 257+** as the init and supervisor.

## Consequences

### Positive

- De facto standard for modern Linux distributions; CentOS Stream native.
- Tightly integrated with bootc, sysext, sysupdate, cryptenroll, homed, networkd, journald.
- Provides Landlock unit directives, RestrictNamespaces, sandbox primitives at the unit level.
- Quadlet integrates podman containers as systemd units (apps as containers).
- Soft-reboot, kexec, generators, timers all available.
- Watchdog and notify protocols mature.

### Negative

- systemd is criticized for scope and complexity; we accept this for ecosystem alignment.
- A single PID 1 is the supervisor; we depend on it being reliable. Service degradation tested.

## Alternatives considered

- **s6 / s6-rc**: technically elegant but loses sysext, sysupdate, cryptenroll, homed, soft-reboot, the entire systemd-adjacent ecosystem we use. Cost of going against the grain too high.
- **dinit / runit / OpenRC**: same loss; not viable for our integration goals.

## References

- `02-platform/INIT-SYSTEM.md`
- `01-architecture/PROCESS-MODEL.md`
