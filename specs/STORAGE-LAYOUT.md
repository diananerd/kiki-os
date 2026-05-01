---
id: storage-layout
title: Storage Layout
type: SPEC
status: draft
version: 0.0.0
implements: [filesystem-layout]
depends_on:
  - boot-chain
  - filesystem-btrfs
depended_on_by:
  - container-runtime
  - cozodb-integration
  - filesystem-btrfs
  - lancedb-integration
  - memory-architecture
  - storage-encryption
last_updated: 2026-04-30
---
# Storage Layout

## Purpose

Specify the on-disk layout of a Kiki OS device: partitions, mount points, what is read-only, what is mutable, what is encrypted, and where each subsystem keeps its data.

## Inputs

- A bootc-deployed OS image.
- LUKS2 keys sealed by TPM.
- Per-user systemd-homed encrypted home directories.

## Outputs

- A booted system with the storage layout described.

## Behavior

### Partition layout

A typical Kiki device has the following partitions on its primary storage:

```
ESP (EFI System Partition)        FAT32, ~512 MB
   bootloader, UKIs, recovery initramfs
boot                              ext4, ~1 GB (optional; can co-locate with rootfs)
   kernel measurement metadata, deployment state
rootfs-A                          ext4 + dm-verity, ~2 GB (read-only OS image)
rootfs-B                          ext4 + dm-verity, ~2 GB (alternate OS image; A/B)
var                               btrfs, remaining (LUKS2 encrypted)
   /var subvolumes per below
home                              btrfs (LUKS2 encrypted, per-user homed)
   per-user subvolumes
```

Two rootfs partitions enable A/B atomic deployment via bootc.

### Mount points

```
/                                 rootfs (read-only, dm-verity)
/usr                              same as / (FHS standard, sealed)
/etc                              overlay (read-only base + writable layer for system config)
/var                              btrfs, mutable, encrypted
/home                             btrfs, mutable, encrypted, per-user via systemd-homed
/run                              tmpfs, ephemeral
/tmp                              tmpfs, ephemeral
/proc, /sys, /dev                 kernel-provided
```

`/usr` is read-only after boot. Any write to `/usr` fails with EROFS. `/etc` is mostly read-only with a small writable overlay for runtime configuration (e.g., NetworkManager state, systemd machine-id).

### `/var` layout

`/var` holds all mutable Kiki state. btrfs provides subvolumes for logical separation:

```
/var
├── lib/
│   ├── kiki/
│   │   ├── identity/                SOUL.md, IDENTITY.md (signed at build)
│   │   ├── users/<user-id>/         per-user data
│   │   │   ├── USER.md              user identity
│   │   │   ├── workspaces/<ws-id>/  workspace state (subvolume per workspace)
│   │   │   ├── memory/              episodic, semantic, procedural memory DBs
│   │   │   ├── voiceprints/         encrypted voice prints
│   │   │   ├── audit.sqlite         audit log
│   │   │   └── caps.redb            capability grants
│   │   ├── components/<ns>/<name>/<v>/  installed components
│   │   ├── tools/wasm/<ns>/<name>/<v>/  installed WASM tools
│   │   ├── profiles/<ns>/<name>/<v>/    installed profiles
│   │   ├── models/<ns>/<name>/<v>/      installed models (GGUF blobs)
│   │   ├── apps/<ns>/<name>/data-<user-or-workspace>/  app data dirs (bind volumes)
│   │   └── system.sqlite            tool registry, model catalog
│   ├── containers/                  podman image storage
│   ├── systemd/                     systemd state
│   ├── journal/                     journald logs
│   └── bootc/                       bootc deployment state
├── log/                             system logs (mostly journald binary)
├── cache/                           regenerable caches
└── tmp/                             persistent tmp (rare; usually /tmp)
```

### `/home` layout

```
/home/<user>/
├── .config/                         user preferences (small TOML files)
└── (anything the user creates via apps)
```

`/home/<user>/` is encrypted via systemd-homed with the user's TPM-sealed key. Each user has their own LUKS-on-loopback file.

The user does not see Kiki internals from `/home/`. Identity files (USER.md), workspace state, memory DBs all live under `/var/lib/kiki/users/<user-id>/`, not in the home directory.

### Subvolumes for workspaces

Each workspace gets its own btrfs subvolume:

```
/var/lib/kiki/users/<user-id>/workspaces/<ws-id>/
```

This enables:

- Snapshots (e.g., before risky agent action).
- Send/receive for export.
- Quota per workspace.

See `02-platform/FILESYSTEM-BTRFS.md` for subvolume details.

### Encryption boundaries

- ESP, boot, rootfs-{A,B}: not encrypted (signed and verified, but readable).
- `/var`: encrypted (LUKS2, TPM-sealed key).
- `/home`: encrypted per user (systemd-homed, per-user key).
- Voice prints: per-blob ChaCha20-Poly1305 on top of `/var` encryption.
- Identity files: encrypted by `/var` encryption + git-side signing.

### Bind mounts for apps

Each app container receives a bind mount of its data directory:

```
host: /var/lib/kiki/apps/<ns>/<name>/data-<scope>/
container: /data
```

`<scope>` is the workspace id for tier-full apps with `workspace_scope: per_workspace`, the user id for `shared_singleton`, etc.

The container has no other access to the host filesystem.

### Mount options

```
/var               compress=zstd:3, ssd, noatime
/home              compress=zstd:3, ssd, noatime
/                  ro, dm-verity
/etc overlay       defaults
/run, /tmp         tmpfs, defaults
```

`compress=zstd:3` reduces storage usage ~30–45% on agent logs and cached embeddings.

`noatime` reduces unnecessary writes (atime tracking is not needed for our access patterns).

### Disk usage estimates

A typical desktop deployment:

```
ESP                           ~50 MB used
rootfs-A                      ~600 MB
rootfs-B                      ~600 MB
/var (after fresh install)    ~2 GB (databases, caches)
/var (after months of use)    ~5–20 GB depending on usage
/home (per user)              user-determined
Models (when installed)       3.5–9 GB depending on selection
```

A 256 GB SSD comfortably hosts a Kiki desktop with multiple users and workspaces.

## Interfaces

### CLI

```
agentctl storage status      # disk usage per subsystem
agentctl storage gc          # cleanup unused container images, stale archives
```

## State

The storage layout is the persistent state.

## Failure modes

| Failure | Response |
|---|---|
| Disk full on /var | refuse new writes; alert; agent prompts user to clean |
| Disk full on /home | per-user; affects only that user |
| /var corrupt | recovery mode; fsck; restore from snapshot if available |
| /home corrupt | systemd-homed handles per-user; recovery prompt |
| Encrypted volume unsealing fails | recovery mode; passphrase fallback |

## Performance contracts

- /var read latency (cached): <100µs.
- /var write latency (committed): <10ms typical for SQLite WAL.
- btrfs snapshot creation: ~2ms.
- btrfs subvolume rollback: <30ms.

## Acceptance criteria

- [ ] /usr read-only and dm-verity-protected.
- [ ] /var encrypted with TPM-sealed key.
- [ ] /home encrypted per user via systemd-homed.
- [ ] btrfs subvolumes created per workspace.
- [ ] zstd compression active on /var.
- [ ] Bind mounts isolate per-app data.

## Open questions

- Whether to default to bcachefs for /var when stable in 6.x kernel.

## References

- `02-platform/BOOT-CHAIN.md`
- `02-platform/FILESYSTEM-BTRFS.md`
- `10-security/STORAGE-ENCRYPTION.md`
- `02-platform/CONTAINER-RUNTIME.md`
