---
id: kernel-config
title: Kernel Configuration
type: SPEC
status: draft
version: 0.0.0
implements: [kernel-feature-set]
depends_on:
  - upstream-choice
  - sandbox
depended_on_by:
  - drm-display
  - filesystem-btrfs
  - hal-contract
  - sandbox
last_updated: 2026-04-30
---
# Kernel Configuration

## Purpose

Specify the kernel features Kiki OS requires, the kernel version baseline, and the configuration we maintain on top of the upstream CentOS Stream kernel.

## Inputs

- The CentOS Stream 10 kernel (6.12 LTS baseline) with our applied configuration.
- Hardware feature requirements (Landlock, namespaces, cgroups v2, etc.).

## Outputs

- A bootable kernel image embedded in the UKI.
- A signed kernel-config artifact for verification.

## Behavior

### Kernel version baseline

CentOS Stream 10 ships kernel 6.12 LTS. Kiki tracks this baseline. Kernel updates flow with bootc image updates; the kernel inside the UKI is replaced atomically.

### Required kernel features

These features must be enabled (CONFIG entries set) for Kiki to function:

```
CONFIG_BPF=y
CONFIG_BPF_LSM=y
CONFIG_LSM=...,landlock,bpf
CONFIG_SECURITY_LANDLOCK=y
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_USER_NS=y
CONFIG_NETWORK_NAMESPACE=y
CONFIG_PID_NS=y
CONFIG_MOUNT_NAMESPACE=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_CGROUPS=y
CONFIG_CGROUP_FREEZER=y
CONFIG_CGROUP_DEVICE=y
CONFIG_BLK_CGROUP=y
CONFIG_MEMCG=y
CONFIG_CGROUP_PIDS=y
CONFIG_CPU_FREQ=y
CONFIG_CRYPTO_AEAD=y
CONFIG_DM_VERITY=y
CONFIG_DM_CRYPT=y
CONFIG_DM_INTEGRITY=y
CONFIG_TPM_TIS=y
CONFIG_TRUSTED_KEYS=y
CONFIG_ENCRYPTED_KEYS=y
CONFIG_BTRFS_FS=y
CONFIG_BTRFS_FS_POSIX_ACL=y
CONFIG_BCACHEFS_FS=m              # available, not default
CONFIG_DRM=y
CONFIG_DRM_AMDGPU=y
CONFIG_DRM_I915=y
CONFIG_DRM_NOUVEAU=y
CONFIG_DRM_NVK=y
CONFIG_FB_SIMPLE=y
CONFIG_USB_HID=y
CONFIG_INPUT_EVDEV=y
CONFIG_NETFILTER=y
CONFIG_NF_TABLES=y
CONFIG_BRIDGE=y
CONFIG_VETH=y
CONFIG_NET_NS=y
```

These are non-negotiable. Disabling any breaks Kiki functionality.

### Disabled features

Some features are disabled to reduce attack surface:

```
CONFIG_KEXEC=y                    # required for kexec; soft-reboot uses
CONFIG_KEXEC_FILE=y
CONFIG_KPROBES=n                  # not needed in production
CONFIG_FTRACE=n                   # disabled in production
CONFIG_KGDB=n                     # debugger disabled in production
CONFIG_PROC_KCORE=n               # kernel memory not exposed
CONFIG_DEBUG_KERNEL=n             # disabled in production
```

Development builds may enable debugging features. Production builds disable them.

### Kernel cmdline

The UKI bakes in the kernel cmdline:

```
root=UUID=<rootfs-uuid>
ro
quiet
splash
audit=1
audit_backlog_limit=8192
lockdown=integrity
slab_nomerge
init_on_alloc=1
init_on_free=1
```

`lockdown=integrity` activates kernel lockdown mode, restricting userspace ability to write kernel memory or load unsigned modules.

`slab_nomerge`, `init_on_alloc`, `init_on_free` are hardening options that have minor performance cost but reduce exploit primitives.

### Kernel modules

Most drivers compiled built-in (`=y`). Some compiled as modules (`=m`) for hardware that may or may not be present:

- bcachefs (alternative filesystem; not default).
- nvidia kernel modules (when NVIDIA hardware detected).
- Specific WiFi/Bluetooth drivers per hardware.

Modules sign with the kernel signing key; loading unsigned modules is rejected (kernel lockdown).

### Real-time

Real-time patches are NOT applied in v0. Kiki targets desktop, where soft-real-time is sufficient. PREEMPT_VOLUNTARY is the default (CentOS Stream 10 default). Hard real-time would be a future hardware-class consideration.

### Kernel signing

The kernel binary is signed with the Kiki release key (same as for the OS image). Signed kernels are required because:

- The UKI containing the kernel is signed.
- dm-verity hashes are computed against the signed kernel.
- TPM PCRs measure the signed kernel.

### Updates

Kernel updates ship with bootc image updates. The kernel inside the UKI is replaced atomically. There is no "update only the kernel" path. This is by design: the OS image is the unit of deployment.

Live kernel patching (kpatch) is not used in v0. Kernel CVEs are handled through bootc image updates with reboot. Reboots are aceptable per the appliance paradigm.

### Compatibility

CentOS Stream 10 kernel covers:

- x86_64 Intel/AMD desktop and server.
- aarch64 ARM (Apple Silicon, Ampere, AWS Graviton).
- riscv64 (early support; v1 target).

Hardware support breadth follows CentOS Stream's kernel coverage.

## Interfaces

### Build-time

The kernel-config file is part of the mkosi build pipeline. Changes to kernel config require a CI rebuild and re-test.

### Runtime

```
uname -r                        # kernel version
cat /proc/cmdline               # active cmdline
cat /sys/kernel/security/lsm    # active LSMs
```

## State

### Persistent

- Kernel image inside the UKI in the ESP.
- Kernel config artifact archived alongside the build for audit.

## Failure modes

| Failure | Response |
|---|---|
| Required kernel feature missing | image build aborts; cannot deploy |
| Kernel signature invalid | bootloader refuses to load |
| Kernel modules signature invalid | kernel refuses to load module |
| Kernel panic | bootloader counts attempts; rollback to alt slot |

## Acceptance criteria

- [ ] Kernel 6.12+ with required features enabled.
- [ ] Lockdown mode active in production builds.
- [ ] Audit subsystem active.
- [ ] Hardening options applied.
- [ ] Modules signed with the kernel signing key.
- [ ] Multi-arch builds produce kernels for x86_64 and arm64.

## Open questions

- When to enable bcachefs as default for /var (currently btrfs).
- Whether to backport specific kernel features past CentOS Stream's release line.

## References

- `02-platform/UPSTREAM-CHOICE.md`
- `02-platform/SANDBOX.md`
- `02-platform/BOOT-CHAIN.md`
- `10-security/VERIFIED-BOOT.md`
