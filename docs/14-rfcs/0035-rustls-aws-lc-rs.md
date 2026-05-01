---
id: 0035-rustls-aws-lc-rs
title: rustls + aws-lc-rs as TLS and Crypto Provider
type: ADR
status: draft
version: 0.0.0
depends_on: []
last_updated: 2026-04-29
depended_on_by:
  - 0036-ct-merkle-audit-chain
---
# ADR-0035: rustls + aws-lc-rs as TLS and Crypto Provider

## Status

`accepted`

## Context

We need a TLS implementation and a cryptographic primitives provider. Options: rustls (Rust-native), openssl (mature C, FFI), boringssl, aws-lc-rs.

## Decision

Use **rustls 0.23+** as the TLS implementation, with **aws-lc-rs** as the `CryptoProvider` backend. Use **RustCrypto** suite (modular Rust crates) for AEAD/signing/hash primitives outside TLS.

## Consequences

### Positive

- rustls is the canonical Rust TLS; modern protocols (TLS 1.3), no FFI for protocol logic.
- aws-lc-rs provider: FIPS 140-3 validated (late 2024); ~15–30% faster than ring on aarch64/x86_64.
- AWS-maintained provider with good cadence.
- RustCrypto is modular: pull only `aes-gcm`, `ed25519-dalek`, etc. as needed; pure Rust; audited.

### Negative

- aws-lc-rs is newer than ring; some migration friction.
- FIPS mode requires specific build flags; not default in v0 for performance.

## Alternatives considered

- **rustls + ring**: ring is legacy, no FIPS path, slower on ARM.
- **openssl/boringssl via FFI**: C, FFI overhead, harder to audit.
- **RustCrypto-only stack**: simpler dependency tree, but no FIPS path and slower AES on platforms without proper intrinsics tuning.

## References

- `10-security/CRYPTOGRAPHY.md`
- `09-backend/DEVICE-AUTH.md`
