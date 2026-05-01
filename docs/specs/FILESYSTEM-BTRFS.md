---
id: filesystem-btrfs
title: Filesystem (btrfs for /var)
type: SPEC
status: draft
version: 0.0.0
implements: [btrfs-var]
depends_on:
  - kernel-config
  - storage-layout
depended_on_by:
  - storage-layout
  - workspace-lifecycle
last_updated: 2026-04-30
---
# Filesystem (btrfs for /var)

## Purpose

Specify btrfs as the filesystem for `/var` and `/home`, the subvolume layout for workspaces, snapshot policy, and compression configuration.

## Inputs

- A LUKS2-encrypted block device.
- The kernel with btrfs enabled (per `02-platform/KERNEL-CONFIG.md`).

## Outputs

- A btrfs filesystem mounted at `/var` (and another at `/home`).
- Subvolumes created for workspaces and other logical units.
- Snapshots usable for rollback and export.

## Behavior

### Why btrfs

- **Subvolumes** give logical separation without partition overhead. Each workspace can be its own subvolume with its own snapshot history.
- **Snapshots** are constant-time (CoW). Useful for atomic operations, rollback, and `btrfs send/receive` for export.
- **Compression** (zstd:3) saves 30–45% on databases, logs, embeddings without significant CPU cost.
- **Single-device boring-correct** in 2026. RAID5/6 still have caveats; we don't use them.
- **Mature in mainline** since 2014; in 2026 the rough edges are well-mapped.

bcachefs is the runner-up; we may revisit when 6.x stabilizes it further. ext4 is rejected because subvolumes/snapshots are essential for our workspace model and we don't want to re-implement them.

### /var layout

Mounted at `/var` after LUKS2 unlock. Subvolumes:

```
@root                                 the top-level subvolume
@kiki                                 mounted as /var/lib/kiki
   @containers                        mounted as /var/lib/containers
   @journal                           mounted as /var/log/journal
   @bootc                             mounted as /var/lib/bootc
@workspaces                           parent for per-workspace subvolumes
   workspace-<ulid>                   per workspace, created on workspace creation
```

### /home layout

Per-user `/home/<user>` is its own filesystem (managed by systemd-homed via LUKS-on-loopback). Inside, btrfs subvolumes can be used by user-installed tools but are not Kiki-mandated.

### Workspace subvolumes

Each workspace creates a subvolume:

```rust
btrfs subvolume create /var/lib/kiki/users/<user>/workspaces/<ws-id>
```

The subvolume contains:

- Canvas ops log database (SQLite).
- Per-workspace memory namespace (when in Scoped mode).
- Per-workspace policy overlay.
- Per-workspace snapshots taken before risky agent actions.

When a workspace is archived, its subvolume is snapshotted and the live subvolume is destroyed (or renamed for retention).

### Snapshot policy

Snapshots are taken at:

- Workspace creation (baseline).
- Before each agent action with `risk_class: irreversible` (rollback target).
- On user request (manual snapshot).
- Periodically per workspace policy (defaults: never; user opt-in).

Snapshots are stored in `<workspace>/.snapshots/` as read-only btrfs snapshots. Pruning policy: keep the last N snapshots per workspace (default 10), plus any user-pinned ones.

### Send/receive for export

A user exporting their workspace runs:

```
btrfs send /var/lib/kiki/users/<user>/workspaces/<ws-id> | gzip > workspace.btrfs.gz
```

The output can be imported on another Kiki device:

```
gunzip < workspace.btrfs.gz | btrfs receive /var/lib/kiki/users/<user>/workspaces/
```

This preserves the entire subvolume contents efficiently.

`agentctl workspace export <ws-id>` wraps this with cosign signing for integrity.

### Compression

`compress=zstd:3` on mount:

```
mount -o compress=zstd:3,ssd,noatime /dev/mapper/var-decrypted /var
```

Tradeoff: ~5% CPU overhead for ~35% disk savings on average Kiki workloads (databases, embeddings, logs).

### Quota

btrfs qgroups can enforce per-subvolume quotas. v0 does not enable qgroups by default (performance cost). Future: opt-in per-workspace quota for users wanting strict bounds.

### Maintenance

Periodic background tasks (via systemd timers):

- `btrfs scrub` weekly: validates checksums.
- `btrfs balance` quarterly: redistributes data to recover from fragmentation.

These run during idle windows, with reduced I/O priority.

### Tooling

```
btrfs subvolume list /var
btrfs subvolume snapshot ...
btrfs send/receive ...
btrfs filesystem df /var
btrfs scrub start /var
```

Most users never run these directly; agentctl wraps the operations they need.

## Interfaces

### Programmatic

```rust
pub fn create_workspace_subvolume(user: &UserId, ws: &WorkspaceId) -> Result<PathBuf>;
pub fn snapshot_workspace(user: &UserId, ws: &WorkspaceId, label: &str) -> Result<SnapshotId>;
pub fn rollback_workspace(user: &UserId, ws: &WorkspaceId, snap: &SnapshotId) -> Result<()>;
pub fn export_workspace(user: &UserId, ws: &WorkspaceId) -> Result<ExportStream>;
```

The agentd workspace lifecycle uses these via the `libbtrfsutil-rs` crate.

### CLI

```
agentctl workspace snapshot <ws-id>
agentctl workspace rollback <ws-id> --to <snap>
agentctl workspace export <ws-id> --output <file>
agentctl storage scrub               # manual scrub trigger
```

## State

The filesystem and subvolumes are the persistent state.

## Failure modes

| Failure | Response |
|---|---|
| btrfs corruption (CRC mismatch) | scrub repairs from second copy if RAID; otherwise alert |
| Subvolume creation fails | log; abort the operation that needed it |
| Snapshot rollback fails | recovery mode; user-driven repair |
| Quota exceeded (when enabled) | refuse new writes to that workspace; alert |
| Free space critical | refuse new writes globally; agent prompts user to clean |

## Performance contracts

- Subvolume creation: <5ms.
- Snapshot creation: <5ms (constant-time CoW).
- Snapshot rollback: <30ms typical.
- send/receive throughput: bounded by IO bandwidth (~500 MB/s on NVMe).
- Compression overhead: ~5% CPU.

## Acceptance criteria

- [ ] /var mounted with btrfs + compress=zstd:3.
- [ ] Per-workspace subvolumes created.
- [ ] Snapshots before risky agent actions.
- [ ] Export via btrfs send works.
- [ ] Periodic scrub schedule in place.
- [ ] Per-user /home managed by systemd-homed (separate from /var).

## Open questions

- When to evaluate bcachefs as default replacement (2027+ likely).
- Whether to enable qgroups by default (performance vs UX tradeoff).

## References

- `02-platform/STORAGE-LAYOUT.md`
- `02-platform/KERNEL-CONFIG.md`
- `10-security/STORAGE-ENCRYPTION.md`
- `03-runtime/WORKSPACE-LIFECYCLE.md`
## Graph links

[[KERNEL-CONFIG]]  [[STORAGE-LAYOUT]]
