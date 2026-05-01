---
id: 0099-future-distribution-pivots
title: Future Distribution Pivots
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0006-centos-stream-bootc-upstream
last_updated: 2026-04-29
---
# ADR-0099: Future Distribution Pivots

## Status

`accepted` (this ADR records future contingency, not present action)

## Context

Operational decisions about upstream and tooling may need to change as the ecosystem evolves. Rather than re-litigate from scratch, we pre-document the realistic pivot paths and what would trigger each.

## Decision

Document three pivot paths and the triggers that would activate each. None is in effect; all three remain options.

### Pivot A: CentOS Stream → Debian sid (snapshotted)

**Trigger**: CentOS Stream license change, project disruption, or a hardware breadth gap (e.g., we need riscv64 SBC support that Stream lacks).

**Path**:
1. Verify mkosi supports Debian as a source for our Packages list.
2. Pin a snapshot.debian.org timestamp.
3. Adjust kiki-runtime sysext to be deb-package-shaped where it currently consumes RPM-shaped files.
4. Re-sign the OS image.
5. CI dual-builds during transition.

**Cost**: ~1 quarter of focused work to migrate the build pipeline; user-facing changes minimal.

### Pivot B: deb/rpm replaced by something else

**Trigger**: Neither rpm nor deb is suitable for a future hardware class.

**Path**: For specific hardware classes only, a custom mkosi profile that uses a different upstream source. Identity of Kiki OS unchanged.

### Pivot C: bootc replaced

**Trigger**: bootc development stalls or a clearly superior atomic OS deployment mechanism emerges.

**Path**: mkosi can produce other formats; sysext continues to work; we re-target the deployment artifact format. Distribution model (OCI everywhere) unchanged.

## Consequences

### Positive

- We do not lock ourselves into CentOS Stream irrevocably.
- Migration paths are pre-thought; not panic responses.
- Maintainer-facing identity (`kiki:<ns>/<name>@<version>`) is stable across pivots.

### Negative

- Maintaining migration paths is itself work; we may never use them.
- Some abstraction overhead in the build pipeline to stay portable.

## Alternatives considered

- **Refusing to plan for pivots**: brittle; if upstream changes, we scramble.
- **Active maintenance of multiple upstreams**: cost-prohibitive; pick one and pivot if necessary.

## References

- `02-platform/UPSTREAM-CHOICE.md`
- `12-distribution/SNAPSHOT-PINNING.md`
- `14-rfcs/0006-centos-stream-bootc-upstream.md`
