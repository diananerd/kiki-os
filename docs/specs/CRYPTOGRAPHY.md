---
id: cryptography
title: Cryptography
type: SPEC
status: draft
version: 0.0.0
implements: [crypto-stack]
depends_on:
  - principles
depended_on_by:
  - audit-merkle-chain
  - backend-contract
  - cosign-trust
  - device-auth
  - device-pairing
  - memory-sync
  - remote-protocol
  - storage-encryption
  - stt-cloud
  - tts-cloud
  - verified-boot
last_updated: 2026-04-30
---
# Cryptography

## Purpose

Specify the cryptography stack: TLS provider, AEAD/signing/hash primitives, key management, FIPS posture, and the conventions for using crypto in Kiki code.

## Behavior

### Library choices

```
TLS:                rustls + aws-lc-rs provider
AEAD/sign/hash:     RustCrypto suite
Code signing:       cosign + Sigstore
Merkle:             ct-merkle (RFC 9162)
TPM:                tpm-rs (pure Rust)
```

### rustls + aws-lc-rs

rustls is the canonical Rust TLS implementation. We use it everywhere TLS is needed: backend connections, OCI registry pulls, optional cloud routes.

The `CryptoProvider` API in rustls 0.23+ pluggable. Two production providers exist:

- `ring` — default; legacy.
- `aws-lc-rs` — FIPS 140-3 validated, AWS-maintained, faster on aarch64/x86_64 via assembly.

We standardize on **aws-lc-rs** for the speed and the FIPS path.

### RustCrypto for primitives

For AEAD (authenticated encryption), signing, hashing outside TLS:

- `aes-gcm` and `chacha20poly1305` for AEAD.
- `ed25519-dalek` for Ed25519 signing.
- `sha2` and `blake3` for hashing.
- `hkdf` for key derivation.

RustCrypto crates are pure Rust, modular (pull only what you use), and audited (NCC Group audit of `aes-gcm`, `chacha20poly1305`).

### Algorithm choices

Default algorithms:

| Use | Algorithm |
|---|---|
| TLS handshake | TLS 1.3, X25519, AES-128-GCM or ChaCha20-Poly1305 |
| File AEAD (e.g., voice prints) | ChaCha20-Poly1305 |
| Disk encryption | AES-XTS-256 (LUKS2 default) |
| Identity signing | Ed25519 (cosign default) |
| OCI image signing | cosign with Ed25519 |
| Hash chain (audit log) | SHA-256 (RFC 9162 binary Merkle) |
| Key derivation | HKDF-SHA-256 |
| Password hashing (rare) | Argon2id |
| Memory snapshot integrity | Blake3 (faster than SHA for large blobs) |

### Key management

Keys live in:

- **TPM-sealed** for disk encryption keys (LUKS2 keyslots; PCR-bound).
- **systemd-creds** with TPM for credentials accessed by services (e.g., backend mTLS keys).
- **Per-user encrypted home** for user-level keys (managed by systemd-homed).
- **age-encrypted files** for identity files (SOUL/USER) at rest, with the key derived from the user's TPM.

Private keys never appear unencrypted on disk after first provisioning.

### TPM integration

`tpm-rs` is the pure-Rust binding for TPM 2.0 operations:

- PCR extension and reading.
- Sealing and unsealing.
- Quote generation for attestation.
- Key creation in TPM-protected slots.

We prefer `tpm-rs` over the C-binding `tss-esapi` for new code; TPM is too security-critical to use FFI when a pure-Rust alternative exists.

### FIPS posture

The aws-lc-rs provider is FIPS 140-3 validated as of late 2024. For deployments requiring FIPS:

- Enable the FIPS feature flag in rustls + aws-lc-rs.
- Restrict algorithms to FIPS-approved list.
- Use `aes-gcm` (not `chacha20poly1305`) for AEAD.

v0 ships non-FIPS by default for performance; FIPS mode is a build flag.

### Convention: errors are first-class

Crypto operations return `Result`. They never panic on attacker-controlled input. Bad signatures, malformed certificates, decryption failures all return errors that the caller handles.

### Convention: constant-time where it matters

Comparing secrets uses constant-time comparison (`subtle` crate). Side-channel resistance is a property of the algorithms (AES-NI on x86, hardware AES on ARM).

### Convention: no rolling our own

We do not implement crypto primitives ourselves. We use audited libraries. Code review for crypto changes requires an additional reviewer.

### Random number generation

`rand::rngs::OsRng` for all key generation, nonces, and salts. This wraps `getrandom(2)` on Linux.

We do not use deterministic RNGs for cryptographic operations.

## Interfaces

### Library APIs

Crates and conventions:

```rust
// TLS
use rustls::{ClientConfig, ServerConfig};
use aws_lc_rs::default_provider;

// Primitives
use aes_gcm::{Aes256Gcm, KeyInit, aead::Aead};
use chacha20poly1305::ChaCha20Poly1305;
use ed25519_dalek::{SigningKey, VerifyingKey};
use sha2::Sha256;
use blake3::Hasher;
use hkdf::Hkdf;

// TPM
use tpm_rs::context::Context;
```

### CLI

```
agentctl crypto verify <file>          # verify a signature on a file
agentctl crypto fingerprint <key>      # show key fingerprint
```

For most operations, crypto is invoked indirectly (cosign for OCI signing, systemd-cryptenroll for TPM enrollment).

## State

### Persistent

- Keys (TPM-sealed, age-encrypted, or in systemd-creds).
- Trusted public keys (cosign keys for namespaces).
- LUKS keyslot data.

### In-memory

- Active TLS sessions.
- Loaded private keys (only for the duration of the operation).

## Failure modes

| Failure | Response |
|---|---|
| TLS handshake fails | error to caller; retry policy upstream |
| Signature verification fails | error; never falls back |
| Decryption fails | error; data unavailable until key resolved |
| TPM unavailable | fallback to passphrase where supported (LUKS2); else hard fail |
| RNG failure | abort; do not generate keys with weak entropy |

## Performance contracts

- AES-GCM encrypt/decrypt: ~3 GB/s on modern x86 with AES-NI.
- Ed25519 sign: ~50,000 ops/s.
- Ed25519 verify: ~17,000 ops/s.
- TLS handshake: ~1.2M/s server-side on 16-core ARM (rustls + aws-lc-rs).
- TPM seal/unseal: ~50ms typical.

## Acceptance criteria

- [ ] rustls + aws-lc-rs is the TLS stack.
- [ ] RustCrypto crates are used for primitives outside TLS.
- [ ] cosign signs all OCI artifacts.
- [ ] ct-merkle implements the audit log hash chain.
- [ ] TPM keys backed by `tpm-rs`.
- [ ] FIPS mode buildable.
- [ ] No custom crypto implementations.
- [ ] Constant-time comparison for secrets.

## Open questions

- Whether to ship FIPS mode as a separate channel or build flag.

## References

- `10-security/STORAGE-ENCRYPTION.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/AUDIT-MERKLE-CHAIN.md`
- `10-security/VERIFIED-BOOT.md`
- `09-backend/DEVICE-AUTH.md`
- `14-rfcs/0035-rustls-aws-lc-rs.md`
