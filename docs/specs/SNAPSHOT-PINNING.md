---
id: snapshot-pinning
title: Snapshot Pinning
type: SPEC
status: draft
version: 0.0.0
implements: [snapshot-pinning]
depends_on:
  - upstream-choice
  - build-system
depended_on_by: []
last_updated: 2026-04-30
---
# Snapshot Pinning

## Purpose

Specify how Kiki pins upstream package snapshots to ensure reproducible builds. CentOS Stream 10 (the operational upstream) is a moving target; mkosi's package source must point to a *frozen* snapshot for any given Kiki release.

## Why pin

A reproducible build means: same source + same recipes → same digest. An `apt-get install foo` against a live mirror returns whatever's in the mirror today. That's not reproducible.

Pinning means: every release of Kiki points to a specific snapshot of every upstream repo. CI verifies the pin works; the snapshot lives long enough to allow re-builds.

## Snapshot service

We use a content-addressable mirror for upstream:

```
snapshots/
├── centos-stream-10/
│   ├── 2026-03-01/
│   │   ├── Packages/...
│   │   └── repodata/...
│   ├── 2026-04-01/
│   └── 2026-04-15/
└── epel-10/
    └── ...
```

Each timestamp is a frozen snapshot. The Kiki build references a specific snapshot by date or content hash.

The mirror is operated by the Kiki Foundation (or a community provider) with public read access; backed by S3-compatible storage for durability.

## Pin format

In mkosi config:

```ini
[Distribution]
Distribution=centos
Release=stream10
Repositories=https://snapshots.kiki.example/centos-stream-10/2026-04-01/

[Content]
Packages=
    bootc
    podman
    crun
    rustls
    cosign
    ...
```

For Rust crates: `Cargo.lock` is committed; `cargo build --offline --frozen` enforces.

## Snapshot rollover

A snapshot is taken at a defined cadence:

- Weekly snapshots for nightlies
- Monthly snapshots for stable releases
- Ad-hoc snapshots for security advisories

A snapshot stays available for at least 1 year (longer for releases that ship to long-term-support tiers).

## Security updates

When CentOS Stream 10 ships a security update, we:

1. Take an out-of-band snapshot
2. Build a Kiki release against it
3. Push to the security stream

The pinned snapshot for old releases still works; users on those releases can update via the security stream.

## Reproducibility chain

```
Kiki release v1.4.2
   │
   pinned snapshot 2026-04-01
   │
   ▼
mkosi build using snapshot
   │
   ▼
artifacts produced; digests recorded
```

Anyone with the source + the pinned snapshot can rebuild the artifacts and verify digests match. The snapshot is therefore part of the supply chain.

## Mirror redundancy

We maintain at least two mirrors of the snapshot service. Build configs can list both for failover. Mirror integrity verified via SHA256 file lists.

## Air-gapped builds

For air-gapped environments, a snapshot bundle can be downloaded once and used offline:

```
kiki-snapshot fetch 2026-04-01 --to=/local/path
```

Build configs point at the local path.

## Anti-patterns

- Pointing builds at live mirrors
- Letting `Cargo.lock` drift across CI runs
- Snapshots without fixed retention
- Mirror redundancy without integrity checks

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Snapshot mirror unavailable      | failover to alternate mirror   |
| Pinned snapshot deleted          | block release; restore from    |
|                                  | archive                         |
| Hash mismatch                    | refuse build                   |
| Cargo.lock drift                 | CI blocks                      |

## Acceptance criteria

- [ ] Every release pins a specific snapshot
- [ ] Snapshots retained per policy
- [ ] Security stream produces snapshots out-of-band
- [ ] Mirror redundancy + integrity verification
- [ ] Air-gapped builds supported
- [ ] Reproducibility verified from snapshot

## References

- `12-distribution/BUILD-SYSTEM.md`
- `02-platform/UPSTREAM-CHOICE.md`
- `02-platform/IMAGE-COMPOSITION.md`
- `14-rfcs/0006-centos-stream-bootc-upstream.md`
## Graph links

[[UPSTREAM-CHOICE]]  [[BUILD-SYSTEM]]
