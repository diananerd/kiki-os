---
id: 0010-btrfs-var-subvolumes
title: btrfs for /var with Workspace Subvolumes
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0008-systemd-init
last_updated: 2026-04-29
---
# ADR-0010: btrfs for /var with Workspace Subvolumes

## Status

`accepted`

## Context

`/var` holds all mutable Kiki state, including per-workspace data. We need: subvolumes for logical separation, snapshots for rollback and export, compression for space efficiency, and stable mainline behavior.

Filesystem options: ext4, btrfs, bcachefs, ZFS.

## Decision

Use **btrfs** for `/var` with per-workspace subvolumes and zstd:3 compression.

## Consequences

### Positive

- Subvolumes give logical separation per workspace.
- Snapshots are constant-time (CoW) — useful for atomic operations and export.
- send/receive enables workspace export.
- zstd:3 saves 30–45% disk on databases, embeddings, logs.
- Boring-correct in 2026 for single-device setups.
- libbtrfsutil-rs provides Rust integration.

### Negative

- btrfs RAID5/6 still has caveats; we don't use them (single-device only).
- Maintenance overhead: periodic scrub and balance.
- ~1.15x write amplification with CoW + zstd:3.

## Alternatives considered

- **ext4**: regret no snapshots once agents start mutating workspace state.
- **bcachefs**: mainline since 6.13; less tooling, fewer recovery resources. Revisit in 2027.
- **ZFS**: license incompatible with Linux mainline.

## References

- `02-platform/FILESYSTEM-BTRFS.md`
- `02-platform/STORAGE-LAYOUT.md`
- `03-runtime/WORKSPACE-LIFECYCLE.md`
## Graph links

[[0008-systemd-init]]
