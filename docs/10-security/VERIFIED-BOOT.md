---
id: verified-boot
title: Verified Boot
type: SPEC
status: draft
version: 0.0.0
implements: [verified-boot]
depends_on:
  - boot-chain
  - cryptography
  - storage-encryption
depended_on_by:
  - device-provisioning
last_updated: 2026-04-30
---
# Verified Boot

## Purpose

Specify the chain of trust from hardware through the OS, the cryptographic signatures verified at each stage, the recovery mechanism on failure, and the boundary where verified boot stops.

## Behavior

### Chain of trust

```
Hardware Root of Trust (immutable in CPU/SoC, where present)
     │ verifies
     ▼
UEFI firmware (signed)
     │ verifies
     ▼
systemd-boot (signed PE binary)
     │ verifies
     ▼
UKI (signed: kernel + initramfs + cmdline)
     │ verifies (via dm-verity)
     ▼
Root filesystem (read-only, dm-verity Merkle tree)
     │ trust ends; user data follows
     ▼
Encrypted user volumes (different key model: TPM-sealed LUKS)
```

Each stage verifies the next. Failure at any step halts boot or activates recovery.

### Hardware Root of Trust

Where the SoC has a hardware-rooted trust anchor (Intel Boot Guard, AMD Secure Boot, Apple Silicon Secure Boot, ARM TrustZone-based):

- Only signed first-stage bootloaders execute.
- The signing key is fused into the chip.
- Unsigned code cannot run from cold-boot.

For platforms without HRoT, verified boot starts at the UEFI level. This is weaker but still meaningful (an attacker would need physical access to flash unsigned firmware).

### UEFI Secure Boot

Kiki ships systemd-boot signed by the Microsoft 3rd-party CA (or a Kiki-specific signing chain on hardware that supports custom keys). Secure Boot rejects unsigned bootloaders.

For developer mode, Secure Boot can be disabled by the user (with physical access). This drops to a weaker trust posture; the user is informed.

### UKI signing

Unified Kernel Images combine kernel, initramfs, and cmdline into one PE binary. The PE binary is signed with the Kiki release key. systemd-boot verifies the signature before loading.

`systemd-measure` pre-computes PCR11 values for the UKI at build time. The expected PCR is signed and embedded; this enables reliable TPM PCR sealing of disk keys that survives kernel updates.

### dm-verity for root filesystem

The root filesystem is read-only and protected by dm-verity:

- A Merkle tree over the rootfs blocks is built at image-composition time.
- The Merkle root hash is signed.
- The kernel verifies blocks on read.
- Any modification fails verification → kernel reports it.

This means tampering with the OS image, even after boot, is detected at next read. Combined with read-only mount, it makes the OS truly immutable in operation.

### TPM PCR-based key binding

When TPM 2.0 is present:

- Each boot stage extends a Platform Configuration Register (PCR) with its measurement.
- Encrypted partition keys are sealed against expected PCR values.
- A different boot chain → different PCRs → keys won't unseal.

Standard Linux TPM-backed verified-boot pattern (systemd-cryptenroll style).

### A/B partition rollback

Two root partitions:

- Active partition contains the running OS.
- Inactive partition contains the previous (or pending) OS.

Boot logic chooses based on boot count and "successful boot" markers. Verified boot applies to both.

This enables:

- OTA: write new image to inactive; verify; mark; reboot.
- Rollback: if new boot fails, fall back to previous.

### Boot success markers

After a successful boot, userspace marks the partition as known-good. After N attempts of the new partition without success, the bootloader falls back to the previous.

The marker is persisted in a small storage area visible to the bootloader (`/boot/loader/`).

### Where verified boot ends

Verified boot guarantees:

- Firmware is trusted (or HRoT-verified).
- Bootloader is signed.
- Kernel + initramfs are signed.
- Root FS is integrity-checked.

It does NOT cover:

- User data (which is encrypted but not signature-verified per file).
- Apps (verified by their cosign signatures, separately).
- Configuration files (validated at use, not at boot).

The trust ends at the platform binary surface; user data trust is via encryption + access control.

### Recovery mode

If verified boot fails on both A and B partitions:

- Recovery initramfs activates.
- A minimal busybox-class environment with diagnostic tools.
- The user (or a technician) can:
  - Re-flash a known-good image.
  - Inspect the device's state.
  - Wipe and re-provision.

Recovery itself is signed; it cannot be replaced without breaking verified boot.

### OTA and verified boot

The OTA flow respects verified boot:

```
1. Pull signed update artifact (cosign-verified OCI image).
2. Verify cosign signature.
3. Verify dm-verity Merkle root signature.
4. Write to inactive partition.
5. Verify dm-verity integrity of the written rootfs.
6. Mark boot order: try inactive next.
7. Reboot.
8. Bootloader: try the new partition.
9. If verified boot succeeds and userspace marker is written → mark active.
10. If fails → revert to old.
```

### Updating signing keys

Trusted keys can rotate:

- A new key is signed by the old key's signature.
- The new key is added to trusted-keys store via OTA.
- After grace period, old key is removed from trust.

The HRoT key (if hardware-fused) cannot rotate; only keys layered on top.

### Tamper response

A device that detects tampering at boot:

- Halts and requires user intervention (default).
- Boots to a degraded "alert" mode (configurable).
- Erases user data (configurable; default no — the user may recover).

Default is halt + alert.

### Platforms without TPM

Platforms without TPM 2.0 use:

- HRoT-only verification of firmware/bootloader.
- dm-verity for rootfs.
- LUKS encryption with passphrase-derived key (no TPM unseal).

Slightly weaker than TPM-backed but functional.

## Interfaces

### Internal

```rust
pub fn boot_state() -> BootState;
pub fn last_boot_failure() -> Option<Failure>;
```

### CLI

```
bootc status                       # current deployments
agentctl boot status               # high-level summary
agentctl boot pcr-list             # current PCRs (if TPM)
agentctl boot verify-now           # re-verify rootfs
agentctl boot last-fail            # last boot failure detail
```

## State

### Persistent

- Bootloader configuration in ESP.
- A/B partition state.
- TPM-sealed keys.
- Trusted keys.

### Per-boot

- PCR values in TPM.
- Boot success marker.

## Failure modes

| Failure | Response |
|---|---|
| Bootloader signature invalid | UEFI halts |
| UKI signature invalid | systemd-boot halts |
| dm-verity fails on rootfs | kernel panic; fall back to other slot |
| Boot count exceeded (A failed) | switch to B |
| Both A and B fail | recovery mode |
| TPM unsealing fails | passphrase prompt |
| Trusted-keys store corrupt | refuse to update kernel/rootfs |

## Performance contracts

- Boot signature verification: <500ms each stage.
- PCR extension: negligible.
- dm-verity at runtime: I/O bandwidth-bounded; typically imperceptible.

## Acceptance criteria

- [ ] All boot stages signed.
- [ ] dm-verity protects rootfs.
- [ ] A/B partitions enable rollback.
- [ ] Encrypted user data bound to verified boot via TPM where present.
- [ ] Recovery mode bootable.
- [ ] OTA respects verified boot.
- [ ] Tamper detection halts boot.
- [ ] Trusted keys can be rotated via OTA.

## References

- `02-platform/BOOT-CHAIN.md`
- `02-platform/IMAGE-COMPOSITION.md`
- `09-backend/OTA-DISTRIBUTION.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/STORAGE-ENCRYPTION.md`
