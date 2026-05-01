---
id: 0003-cosign-sigstore-trust
title: cosign + Sigstore for Signing and Trust
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0002-oci-native-distribution
last_updated: 2026-04-29
depended_on_by:
  - 0004-namespace-registry
---
# ADR-0003: cosign + Sigstore for Signing and Trust

## Status

`accepted`

## Context

Distributing signed OCI artifacts (per ADR-0002) requires choosing a signing tool and trust model. Multiple options exist:

- cosign (Sigstore)
- Notary v2 / notation
- minisign (simpler, but no transparency log integration)
- GPG (legacy, weaker UX)
- apt-secure (deb-only, ruled out by ADR-0002)

The trust model also has options:

- Single root of trust (centralized).
- Per-namespace keys (federated trust).
- Keyless signing via OIDC (Sigstore Fulcio).
- Web of trust (PGP-style).

## Decision

**Sign all OCI artifacts with cosign. Use per-namespace public keys as the trust unit. Make Sigstore witness submission optional (opt-in by maintainer).**

Specifically:

1. Each Kiki namespace has a registered cosign public key, recorded in the namespace registry.
2. Maintainers sign their artifacts with the corresponding private key (kept offline / in a hardware token / in a CI signing service).
3. Verification: every artifact pull goes through `cosign verify` against the namespace's registered key.
4. Witness: maintainers may optionally submit signatures to a Sigstore witness (Rekor or a sigsum witness) for transparency. The Kiki client respects the witness when present.
5. Key rotation: a maintainer rotates by issuing a new key signed by the old key. Clients accept the rotation on first sight after explicit user consent.
6. Revocation: maintainers publish a revocation in Sigstore Rekor; clients refuse signed-but-revoked artifacts.

## Consequences

### Positive

- Industry-standard tooling: cosign and Sigstore are widely adopted (Kubernetes, npm provenance, PyPI trusted publishing, GitHub Actions).
- One signing tool covers OCI images, OCI artifacts, and arbitrary blobs.
- Per-namespace keys give maintainers sovereignty over their content without a central authority.
- Transparency log support is opt-in but available, accommodating maintainers who want non-repudiation and those who don't.
- Keyless signing via OIDC is supported as a future option without protocol changes.

### Negative

- cosign is a separate tool maintainers must learn.
- Key management for maintainers is non-trivial (offline keys, hardware tokens, CI signing).
- Sigstore infrastructure dependency for witness submission (mitigated by being opt-in and supporting alternative witnesses like sigsum).
- Revocation propagation is eventually consistent.

## Alternatives considered

- **Notary v2 / notation.** Rejected because the ecosystem is significantly smaller than Sigstore and the trust model offers no advantage for our use case.
- **minisign.** Rejected because lack of transparency log integration weakens auditability for maintainers who want it.
- **GPG.** Rejected on UX grounds; key management with GPG has been a deterrent to adoption for decades.
- **Single root of trust (Kiki-signed).** Rejected because it creates a centralized authority inconsistent with the federated registry model.

## References

- `10-security/COSIGN-TRUST.md`
- `10-security/SIGSTORE-WITNESS.md`
- `12-distribution/OCI-WORKFLOWS.md`
- Sigstore documentation: https://docs.sigstore.dev
- cosign 2.x release notes
- sigsum project: https://sigsum.org
