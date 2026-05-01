---
id: 0036-ct-merkle-audit-chain
title: ct-merkle for Audit Log Hash Chain
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0035-rustls-aws-lc-rs
last_updated: 2026-04-29
---
# ADR-0036: ct-merkle for Audit Log Hash Chain

## Status

`accepted`

## Context

The audit log requires a tamper-evident hash chain plus periodic Merkle tree heads suitable for transparency log submission. We need an RFC 9162 (Certificate Transparency v2) compatible binary Merkle implementation.

## Decision

Use **`ct-merkle` Rust crate** for RFC 9162 binary Merkle tree, plus per-entry hash chain (custom, ~100 lines) using **sha2** from RustCrypto.

## Consequences

### Positive

- ct-merkle implements RFC 6962/9162 semantics correctly (domain separation `0x00` for leaves, `0x01` for nodes).
- Audit logs can be submitted to Sigstore Rekor or sigsum witnesses without custom format mediation.
- Pure Rust; modular dependencies.

### Negative

- ct-merkle is less starred than alternatives like rs-merkle; smaller community but correct for our use.

## Alternatives considered

- **rs-merkle**: most-popular Rust Merkle crate, but does not enforce RFC 9162 domain separation by default; would need careful config.
- **Custom over sha2**: ~150 lines, no extra dependency, easy to audit. Reasonable runner-up if we want minimum supply chain.
- **Trillian/Rekor as full transparency log**: overkill at OS scale.

## References

- `10-security/AUDIT-LOG.md`
- `10-security/AUDIT-MERKLE-CHAIN.md`
- `10-security/SIGSTORE-WITNESS.md`
- RFC 9162
## Graph links

[[0035-rustls-aws-lc-rs]]
