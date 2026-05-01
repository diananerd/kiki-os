---
id: 0011-luks2-cryptenroll-homed
title: LUKS2 + cryptenroll + systemd-homed for Encryption
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0009-systemd-boot-uki-pcr
last_updated: 2026-04-29
---
# ADR-0011: LUKS2 + cryptenroll + systemd-homed for Encryption

## Status

`accepted`

## Context

`/var` and `/home` must be encrypted. We need TPM-sealed keys for unattended boot, recovery passphrases, and per-user home isolation on multi-user devices.

## Decision

Use **LUKS2** for `/var`, **systemd-cryptenroll** for TPM PCR-sealed keyslots, and **systemd-homed** for per-user encrypted home directories.

PCR sealing against PCRs 7 (Secure Boot policy), 11 (UKI measurements), 12 (cmdline), 15 (sysext).

## Consequences

### Positive

- LUKS2 is the Linux standard; AES-XTS-256 mature.
- TPM-sealed key enables unattended boot when PCRs match; recovery passphrase fallback.
- systemd-cryptenroll provides clean TPM enrollment.
- systemd-homed gives per-user home with separate LUKS volume; structural multi-user privacy.
- Hardware change detection: PCR mismatch surfaces as recovery passphrase prompt.

### Negative

- Hardware without TPM falls back to passphrase-only; weaker but functional.
- Kernel updates that change PCR 11 require rotation; mitigated by signed expected PCR in UKI.
- systemd-homed is relatively new in production deployments.

## Alternatives considered

- **Clevis + tang**: network-bound encryption; overkill for desktop.
- **Plain dm-crypt without LUKS2**: loses keyslot management; rejected.
- **Single shared encrypted home**: rejected for multi-user privacy reasons.

## References

- `10-security/STORAGE-ENCRYPTION.md`
- `10-security/VERIFIED-BOOT.md`
- `02-platform/STORAGE-LAYOUT.md`
## Graph links

[[0009-systemd-boot-uki-pcr]]
