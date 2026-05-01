---
id: 0004-namespace-registry
title: Namespace Registry for Identity Resolution
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0002-oci-native-distribution
  - 0003-cosign-sigstore-trust
last_updated: 2026-04-29
---
# ADR-0004: Namespace Registry for Identity Resolution

## Status

`accepted`

## Context

OCI registries (per ADR-0002) provide artifact storage and distribution but not naming. We need a stable identity scheme that:

- Lets users say "install kiki:acme/notes" without knowing acme's registry URL.
- Gives maintainers control over where their content is hosted.
- Survives a maintainer changing their hosting provider.
- Anchors trust to per-namespace cosign keys (per ADR-0003).
- Supports semver version resolution.
- Permits federation: no single registry is required.

## Decision

**A namespace registry maps `kiki:<namespace>` to a tuple of `(canonical OCI registry URL, cosign public key fingerprint, metadata)`.**

Specifically:

1. Canonical identity: `kiki:<namespace>/<name>@<version>`.
2. The namespace registry exposes an HTTP API: `GET /namespaces/<ns>` returns the registration record (signed JSON).
3. Each registration is signed by the namespace registry's authority.
4. `agentctl install kiki:acme/notes@^1.2` performs:
   - Resolve `acme` via the namespace registry.
   - Pull artifact metadata from the canonical registry URL.
   - Resolve `^1.2` to a concrete version via OCI tag listing.
   - Pull the artifact.
   - Verify with cosign against the namespace's registered key.
5. Three reserved internal namespaces: `kiki:core/*` (official OS components), `kiki:dev/*` (developer tooling), `kiki:meta/*` (meta-packages and compositions).
6. Other namespaces are registered via a maintainer onboarding process (out of scope for this ADR).
7. Namespaces are stable identifiers. Renaming a namespace is structurally a new namespace; the old one continues to resolve to its last known content.

## Consequences

### Positive

- Stable user-facing identity that doesn't depend on hosting choices.
- Federation: any OCI registry hosts content; the namespace registry is the only centralized component, and even it can be mirrored or replaced.
- Trust anchoring: per-namespace cosign keys give maintainers cryptographic identity.
- Version resolution: semver matching at the OCI tag level, exact pinning via digest.
- Policy: namespace registrations carry metadata (reserved-for-system, KYC level, abuse history) that informs trust decisions.

### Negative

- The namespace registry is a centralized point in an otherwise federated system.
- Registry compromise allows malicious namespace registrations (mitigated by per-namespace cosign keys: even a compromised registry cannot mint signatures).
- Namespace squatting is possible without curation; mitigated by registration policy (out of scope).
- Maintainers depend on the registry being available; mitigated by mirroring and the ability for clients to cache resolutions.

## Alternatives considered

- **Direct OCI URL identity (no namespace abstraction).** Rejected because users would have to type `registry.acme.dev/notes:1.2.0` for every install; identity becomes tied to hosting choices.
- **DNS-based namespace identity (e.g., `acme.dev/notes`).** Considered. Rejected because it conflates DNS ownership with content authority and loses the ability to migrate hosting.
- **Decentralized identity (DID or similar).** Considered. Rejected as immature for OS distribution in 2026 and lacking tooling.
- **Federated namespace registries (multiple, peering).** Future consideration; v0 has one canonical registry, with federation as a v2 path.

## References

- `09-backend/REGISTRY-PROTOCOL.md`
- `09-backend/NAMESPACE-FEDERATION.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/OCI-WORKFLOWS.md`
