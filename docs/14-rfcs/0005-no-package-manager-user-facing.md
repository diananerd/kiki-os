---
id: 0005-no-package-manager-user-facing
title: No Package Manager User-Facing
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
  - 0002-oci-native-distribution
last_updated: 2026-04-29
---
# ADR-0005: No Package Manager User-Facing

## Status

`accepted`

## Context

Linux distributions traditionally expose a package manager (apt, dnf, pacman, zypper) to users. Users install software via this tool. Maintainers publish packages to repositories.

Kiki's appliance paradigm (ADR-0001) states that Linux internals are opaque to the user. OCI-native distribution (ADR-0002) provides the actual distribution mechanism. The question is whether to expose any package management surface to users at all.

## Decision

**No package manager is user-facing in Kiki OS.**

Specifically:

1. The user does not run `apt`, `dnf`, `pacman`, or any equivalent.
2. The user does not edit `sources.list`, `repos.d/`, or equivalent configuration.
3. The user does not interact with package repositories directly.
4. App and content management is performed through the agent ("install the molecule viewer from acme") or, for advanced users, through `agentctl` (a thin OCI client wrapper).
5. Internally, the OS may use a package manager during the build pipeline (mkosi composes the base image from upstream packages). This is a build-time detail, never user-facing.
6. The user cannot install upstream Linux packages into the running system. The system is immutable; changes require a new image.
7. The OS exposes no `/etc/apt/`, `/etc/yum.repos.d/`, or similar directories for user editing.

## Consequences

### Positive

- The user surface is minimal and consistent: agent + `agentctl` + system settings.
- Maintainers don't compete with Linux conventions for installation flow.
- The system is harder to break: no "I accidentally apt-removed libc" failure modes.
- Reproducibility is preserved: the running system equals the deployed image.
- Security: no path for user-installed software to escape the appliance shape.
- Documentation is simpler: one way to install things, not several.

### Negative

- Users who want to install arbitrary Linux packages cannot. They must publish them as Kiki apps or use a different OS.
- Workflows assuming `apt-get update && apt-get install` do not work.
- Some power-user expectations are violated by design.
- For development, there is no quick "install this thing temporarily" path. Developers use container images.

## Alternatives considered

- **Hidden but available package manager (e.g., `dnf` exists but is undocumented).** Rejected because hidden means accessible to skilled users who would then accidentally break the appliance shape; better to forbid structurally.
- **`agentctl install-package` as a thin wrapper around apt/dnf.** Rejected because it would surface upstream package conventions, contradicting opacity.
- **Sysext-based user-installed extensions.** Rejected for general user use, though sysext is used internally for the runtime; user-installed sysexts are an attack surface we don't want.

## References

- `00-foundations/PARADIGM.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `02-platform/IMAGE-COMPOSITION.md`
## Graph links

[[0001-appliance-os-paradigm]]  [[0002-oci-native-distribution]]
