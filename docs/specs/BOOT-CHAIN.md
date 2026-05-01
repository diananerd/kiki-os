---
id: boot-chain
title: Boot Chain
type: SPEC
status: draft
version: 0.0.0
implements: [boot-chain]
depends_on:
  - upstream-choice
  - init-system
  - image-composition
depended_on_by:
  - storage-encryption
  - storage-layout
  - verified-boot
last_updated: 2026-04-30
---
# Boot Chain

## Purpose

Specify the boot sequence from firmware to user session: bootloader, UKI (Unified Kernel Image), dm-verity verification, A/B image deployment, TPM PCR sealing, and rollback.

## Inputs

- A signed bootc OCI image deployed via `bootc switch` or `bootc upgrade`.
- The bootloader configuration in the EFI System Partition.
- TPM 2.0 (where present) for PCR sealing.
- The hardware root of trust (where supported).

## Outputs

- A booted system with verified integrity from firmware to userspace.
- Atomic A/B partition switching with automatic rollback on failure.
- Disk encryption keys released only when the boot chain is verified.

## Behavior

### Why systemd-boot + UKI

We use **systemd-boot** with **Unified Kernel Images** (UKIs) signed via **sd-stub**.

Reasons:

- UEFI-only (Kiki targets UEFI hardware; legacy BIOS not supported).
- UKIs combine kernel, initramfs, and cmdline into one signed PE binary.
- systemd-measure can pre-compute PCR11 values for the UKI, enabling TPM-sealed disk keys that survive kernel updates without re-enrollment.
- A/B partition selection comes free via `BootCounting` (since systemd 254).
- systemd-boot menu render is fast (~80ms vs GRUB's ~400ms).
- Aligns with the systemd ecosystem we are already in.

GRUB is the runner-up for cases requiring legacy BIOS or shim chain-of-trust for Microsoft 3rd-party CA Secure Boot. Not used in v0.

### Chain of trust

```
Hardware Root of Trust (immutable in CPU/SoC)
     │ verifies
     ▼
UEFI firmware (signed)
     │ verifies
     ▼
systemd-boot (signed PE binary in ESP)
     │ verifies UKI signature
     ▼
UKI (signed PE: kernel + initramfs + cmdline)
     │ kernel mounts root via dm-verity
     ▼
Root filesystem (read-only, dm-verity protected)
     │ trust ends; user data follows
     ▼
Encrypted user volumes (LUKS2; keys released by TPM)
```

Each stage verifies the next. Failure at any step halts boot or activates recovery.

### A/B deployments via bootc

Two slots:

```
slot A: ostree commit <hash-A>
slot B: ostree commit <hash-B>
```

`bootc switch <new-image>` writes the new image into the inactive slot and marks it for next boot. After successful boot (userspace marker), the slot becomes active. Failure rolls back.

systemd-boot reads:

```
loader.conf
   default kiki-bootc-A
   timeout 0
   editor 0

entries/kiki-bootc-A.conf
   title Kiki OS
   linux /EFI/Linux/kiki-A.efi
   options ...

entries/kiki-bootc-B.conf
   title Kiki OS (alt)
   linux /EFI/Linux/kiki-B.efi
   options ...
```

`BootCounting` decrements the counter on each attempt; on successful boot, userspace clears the counter. Repeated failures cause the bootloader to switch to the previous slot.

### dm-verity for root filesystem

The root filesystem is read-only and verified by dm-verity:

- A Merkle tree over the rootfs blocks is built at image-composition time.
- The Merkle root hash is signed.
- The kernel verifies blocks on read.
- Any tampering causes verification failure → kernel reports it.

This means any modification to the deployed OS is detected at next read. Combined with the read-only mount, it makes the OS image truly immutable in operation.

### TPM PCR sealing

Disk encryption keys are sealed against expected PCR values (where TPM 2.0 is present):

- PCR 7: Secure Boot policy.
- PCR 11: UKI measurements (covers kernel + initramfs + cmdline).
- PCR 12: kernel command line.
- PCR 15: systemd system extensions.

`systemd-cryptenroll` enrolls a TPM-sealed keyslot. At boot, the TPM releases the key only if PCR values match the expected (signed) values. A different boot chain (different OS, modified UKI) produces different PCRs; keys do not unseal; encrypted volumes are inaccessible.

### Boot success markers

After a successful boot, userspace marks the partition as known-good:

```
A successful kiki-runtime.target reach writes /var/lib/bootc/boot-state
After N attempts of the new partition without success, the bootloader
falls back to the previous.
```

The marker is persisted such that the bootloader can read it on next boot.

### Recovery mode

If both A and B partitions fail to boot:

- Recovery initramfs activates (separately signed, in ESP).
- Provides a minimal busybox-like environment.
- The user (or a technician) can:
  - Re-flash a known-good image via USB.
  - Inspect the device's state.
  - Wipe and re-provision.

Recovery itself is signed; it cannot be replaced without breaking verified boot.

### OTA flow integration

`bootc upgrade` orchestrates:

```
1. Pull new OCI image from registry.
2. Verify cosign signature against kiki:core key.
3. Verify dm-verity integrity of the staged image.
4. Write to inactive partition.
5. Update bootloader entries; mark new slot to try next.
6. Reboot.
7. Bootloader: try the new slot.
8. If kiki-runtime.target reaches successfully → mark new slot as active.
9. If fails → bootloader counts attempts; falls back to old.
```

### Updating signing keys

Trusted keys (sd-boot, dm-verity, cosign for image pulls) can rotate:

- New key signed by old key's signature.
- New key added to trusted-keys store via OTA.
- After grace period, old key removed from trust.

The HRoT key (hardware-fused) cannot rotate; only keys layered on top.

## Interfaces

### Internal

```rust
fn boot_state() -> BootState;          // active partition, verification status
fn last_boot_failure() -> Option<Failure>;
```

### CLI

```
bootc status                 # current deployments and pending changes
bootc switch <image>          # switch to a new image
bootc rollback                # explicit rollback
bootc upgrade                 # pull-and-switch
agentctl boot status          # higher-level summary
```

## State

### Persistent

- ESP: bootloader, UKIs, recovery initramfs.
- /boot or equivalent: deployment metadata.
- /var/lib/bootc/: deployment state.
- TPM: PCR-sealed keyslots.

### Per-boot

- PCR values in TPM.
- Boot success marker.

## Failure modes

| Failure | Response |
|---|---|
| Bootloader signature invalid | UEFI halts |
| UKI signature invalid | systemd-boot halts |
| dm-verity fails on rootfs | kernel panic; fall back to other slot |
| Boot counter exceeded | switch to other slot |
| Both slots fail | recovery mode |
| TPM unsealing fails | encrypted volumes inaccessible; user prompted (passphrase fallback or recovery) |
| Trusted-keys store corrupt | refuse new updates; alert |

## Performance contracts

- UEFI to bootloader: hardware-bounded (~100–500ms typical).
- Bootloader to kernel exec: <500ms.
- Kernel start to systemd PID 1: <2s.
- systemd PID 1 to ready: <15s on reference hardware.
- Total cold boot to graphical login: <30s.

## Acceptance criteria

- [ ] systemd-boot + UKI + sd-stub used.
- [ ] dm-verity protects rootfs.
- [ ] A/B partitions enable rollback.
- [ ] Encrypted user volumes bound to verified boot via TPM PCRs (where available).
- [ ] Recovery mode bootable.
- [ ] OTA respects verified boot (writes verified before activation).
- [ ] Tamper detection halts boot or falls back.
- [ ] Trusted keys can be rotated via OTA.

## Open questions

- Whether to ship a fallback for hardware lacking TPM (passphrase-only LUKS).
- Whether Secure Boot enrollment is on-by-default for OEM devices.

## References

- `02-platform/IMAGE-COMPOSITION.md`
- `02-platform/INIT-SYSTEM.md`
- `02-platform/STORAGE-LAYOUT.md`
- `10-security/VERIFIED-BOOT.md`
- `10-security/STORAGE-ENCRYPTION.md`
- `09-backend/OTA-DISTRIBUTION.md`
- `14-rfcs/0009-systemd-boot-uki-pcr.md`
