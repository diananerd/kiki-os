---
id: storage-encryption
title: Storage Encryption
type: SPEC
status: draft
version: 0.0.0
implements: [storage-encryption]
depends_on:
  - cryptography
  - boot-chain
  - storage-layout
depended_on_by:
  - audit-log
  - verified-boot
last_updated: 2026-04-30
---
# Storage Encryption

## Purpose

Specify how on-disk data is encrypted: LUKS2 for `/var`, systemd-homed for `/home`, TPM PCR sealing of keys, recovery passphrases, and the relationship to verified boot.

## Behavior

### LUKS2 for /var

`/var` is encrypted with LUKS2:

- AES-XTS-256 cipher.
- Argon2id key derivation for passphrase keyslots (rare, for recovery).
- TPM-sealed primary keyslot (default boot path).

The keyslot is sealed against PCRs 7 (Secure Boot policy), 11 (UKI measurements), 12 (kernel cmdline), 15 (systemd extensions). At boot, systemd-cryptenroll asks the TPM to unseal; if PCRs match, the key is released and `/var` mounts.

A boot from a different OS image (different PCRs) cannot unseal the key. `/var` is inaccessible without the recovery passphrase.

### systemd-homed for /home

Each user has their own encrypted home directory via systemd-homed:

- LUKS-on-loopback file in `/var/lib/homes/<user>.home`.
- Per-user key derived from the user's password and (optionally) TPM-sealed.
- Home directory is mounted only when the user is active; unmounted on logout.

Multi-user privacy is structural: User A cannot read User B's home because the LUKS volume is unmounted and the key is unavailable when not logged in as B.

### Recovery passphrase

Users set a recovery passphrase at provisioning. This passphrase enrolls a separate keyslot in the LUKS2 volume:

- TPM keyslot: default boot path.
- Recovery passphrase keyslot: fallback for TPM unavailability or hardware change.

The passphrase is presented to the user as a long random string at provisioning. The user is encouraged to store it securely (paper, password manager). Without it, a hardware change that breaks PCR sealing makes the disk inaccessible.

### Per-blob encryption for high-sensitivity content

Some content is encrypted with a per-blob key on top of LUKS:

- **Voice prints**: ChaCha20-Poly1305 with a per-user key derived from the user's TPM-sealed identity.
- **Identity files (SOUL, USER)**: optionally age-encrypted at rest, with key derived from user identity.

This is defense in depth: LUKS protects against offline disk access; per-blob encryption protects against in-OS access by a misconfigured component.

### Provisioning flow

```
1. First boot: device generates random LUKS key.
2. Key sealed against expected PCRs (computed from the booted UKI).
3. User sets recovery passphrase; second keyslot enrolled.
4. systemd-homed creates per-user home with user's password + TPM-sealed key.
```

### Key rotation

LUKS2 supports key rotation:

```
agentctl storage rotate-key
```

This re-seals against current PCRs (e.g., after a kernel update changed PCR 11 measurements; usually not needed because PCRs are pre-computed from the signed UKI).

User can rotate recovery passphrase.

### What encryption protects against

- Stolen device (offline attack on disk): protected by TPM + Secure Boot.
- Modified OS image (different boot chain): protected; PCRs don't match, key not unsealed.
- One user reading another user's home: protected by per-user systemd-homed.
- Malicious app reading other apps' data: protected by sandbox + per-container bind mounts (not encryption).

### What encryption does NOT protect against

- Running adversary with root (a compromised system service can read mounted volumes).
- Cold boot attacks on RAM (mitigation: fast boot, lock screen, RAM clear on suspend).
- Hardware bus snooping (hardware-level threat; out of scope).

### Hardware without TPM

Devices lacking TPM 2.0 fall back to:

- LUKS2 with passphrase-only keyslot (no automatic unseal).
- User enters passphrase at boot.
- Per-user systemd-homed still encrypted with user password.

This is weaker but functional. The hardware manifest declares TPM presence; provisioning adapts.

## Interfaces

### Programmatic

`tpm-rs` for TPM operations. `cryptsetup` (via shell-out) for LUKS operations during install/recovery; not used at runtime hot paths.

### CLI

```
agentctl storage status                # encryption status
agentctl storage rotate-key            # re-seal against current PCRs
agentctl storage set-recovery-passphrase
```

### systemd integration

`systemd-cryptenroll` for TPM-sealed keyslot enrollment. `systemd-homed` for per-user home management. These are upstream tools; we configure them.

## State

### Persistent

- LUKS2 metadata in the partition header.
- TPM-sealed keys (in TPM NVRAM).
- systemd-homed user records in `/var/lib/systemd/home/`.

### In-memory

- LUKS volume key (only after unsealing; held by kernel).
- User home volume keys (only when user is active).

## Failure modes

| Failure | Response |
|---|---|
| TPM unsealing fails (PCR mismatch) | recovery passphrase prompt; if user enters, mount continues |
| Recovery passphrase forgotten | data unrecoverable; recovery mode for re-provisioning |
| TPM corruption | recovery passphrase fallback |
| systemd-homed user record corrupt | per-user; affects only that user |

## Performance contracts

- LUKS2 read overhead: ~5–10% on modern hardware with AES-NI / ARM AES.
- TPM unseal at boot: <1s.
- systemd-homed mount on login: <2s typical.

## Acceptance criteria

- [ ] /var encrypted with LUKS2 + TPM-sealed key.
- [ ] /home encrypted per user via systemd-homed.
- [ ] PCRs 7, 11, 12, 15 used for sealing.
- [ ] Recovery passphrase enrolled at provisioning.
- [ ] Voice prints additionally encrypted with per-blob keys.
- [ ] Identity files optionally age-encrypted.
- [ ] Hardware without TPM has passphrase fallback.

## References

- `10-security/CRYPTOGRAPHY.md`
- `10-security/VERIFIED-BOOT.md`
- `02-platform/BOOT-CHAIN.md`
- `02-platform/STORAGE-LAYOUT.md`
- `14-rfcs/0011-luks2-cryptenroll-homed.md`
