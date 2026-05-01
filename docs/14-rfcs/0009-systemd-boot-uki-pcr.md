---
id: 0009-systemd-boot-uki-pcr
title: systemd-boot + UKI + TPM PCR Sealing
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0008-systemd-init
last_updated: 2026-04-29
depended_on_by:
  - 0011-luks2-cryptenroll-homed
---
# ADR-0009: systemd-boot + UKI + TPM PCR Sealing

## Status

`accepted`

## Context

The boot chain must support verified boot, A/B atomic deployment, and TPM-sealed disk encryption. Bootloader options: systemd-boot, GRUB 2, others.

## Decision

Use **systemd-boot** with **Unified Kernel Images (UKIs)** signed via **sd-stub**, with **TPM PCR sealing** for disk encryption keys.

## Consequences

### Positive

- UEFI-only (Kiki targets UEFI hardware; legacy BIOS unsupported).
- UKIs combine kernel, initramfs, and cmdline as one signed PE binary; one signature, one verification step.
- systemd-measure pre-computes PCR11 values; TPM-sealed disk keys survive kernel updates.
- A/B selection via BootCounting (systemd 254+).
- Faster bootloader render (~80ms vs GRUB ~400ms).
- Aligns with the systemd ecosystem.

### Negative

- No legacy BIOS support; not a concern for our target hardware.
- For Microsoft 3rd-party CA Secure Boot chains, GRUB still has wider support; we use Microsoft 3rd-party for our shim if needed.
- TPM-sealed keys require recovery passphrase fallback for hardware changes.

## Alternatives considered

- **GRUB 2**: more flexible (BIOS support, more architectures), but slower, weaker verified-boot integration, harder PCR sealing through GRUB.

## References

- `02-platform/BOOT-CHAIN.md`
- `10-security/VERIFIED-BOOT.md`
- `10-security/STORAGE-ENCRYPTION.md`
## Graph links

[[0008-systemd-init]]
