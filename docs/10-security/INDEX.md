---
id: security-index
title: Security — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Security

Security model, capability taxonomy, audit log, encryption, anti-patterns.

## Models

- `PRIVACY-MODEL.md` — four privacy tiers, propagation, invariants.
- `ANTI-PATTERNS.md` — lethal trifecta, cross-agent escalation, others.
- `HARDCODED-RESTRICTIONS.md` — nine immutable restrictions.

## Capabilities

- `CAPABILITY-TAXONOMY.md` — nine namespaces, seven grant levels.

## Audit

- `AUDIT-LOG.md` — append-only with hash chain, retention.
- `AUDIT-MERKLE-CHAIN.md` — RFC 9162 binary Merkle, opt-in sigsum.

## Cryptography

- `CRYPTOGRAPHY.md` — rustls + aws-lc-rs + RustCrypto.
- `COSIGN-TRUST.md` — per-namespace keys, rotation, revocation.
- `SIGSTORE-WITNESS.md` — opt-in transparency log.
- `STORAGE-ENCRYPTION.md` — LUKS2 + cryptenroll + homed + TPM PCR sealing.
- `VERIFIED-BOOT.md` — systemd-boot + UKI + dm-verity.

## Defenses against agentic threats

- `CAMEL-PATTERN.md` — split planner/parser for trifecta-touching tools.

## Process

- `VULNERABILITY-DISCLOSURE.md` — responsible disclosure.
