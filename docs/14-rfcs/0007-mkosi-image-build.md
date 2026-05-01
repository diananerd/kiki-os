---
id: 0007-mkosi-image-build
title: mkosi as Image Build Tool
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0006-centos-stream-bootc-upstream
last_updated: 2026-04-29
depended_on_by:
  - build-system
---
# ADR-0007: mkosi as Image Build Tool

## Status

`accepted`

## Context

We need a build tool to compose Kiki OS images from upstream packages. Options include mkosi, mmdebstrap, debos, buildah, custom scripts.

## Decision

Use **mkosi 25+** as the image build tool.

## Consequences

### Positive

- systemd-native (maintained alongside systemd; integrates with sd-stub, sd-boot, sd-cryptenroll, sd-measure).
- Multi-distro source: accepts Fedora, CentOS, Debian, Arch, openSUSE — preserves migration optionality.
- Reproducible: SOURCE_DATE_EPOCH support, deterministic file ordering.
- Multi-format output: bootc OCI directly, or disk images, or directories.
- Fast iteration: warm builds in <25s.
- Active maintenance.

### Negative

- mkosi is Python (not Rust). The build pipeline depends on it; not a runtime dependency on devices.
- mkosi 25+ is recent; some edge cases in the bootc workflow may need upstream contributions.

## Alternatives considered

- **mmdebstrap**: pure Debian-native; would tie us to deb format. Rejected as we may move between upstreams.
- **debos**: YAML-driven; Go + Fakemachine; extra moving parts.
- **buildah**: container-native; designed for OCI but lacks the OS-image-build ergonomics of mkosi.
- **Custom scripts**: opportunity cost of reinventing; rejected.

## References

- `02-platform/IMAGE-COMPOSITION.md`
- `12-distribution/BUILD-SYSTEM.md`
