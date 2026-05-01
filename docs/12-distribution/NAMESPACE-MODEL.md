---
id: namespace-model
title: Namespace Model
type: SPEC
status: draft
version: 0.0.0
implements: [namespace-model]
depends_on:
  - oci-native-model
  - cosign-trust
depended_on_by:
  - artifact-catalog
  - cosign-trust
  - maintainer-guide
  - namespace-federation
  - registry-operations
  - registry-protocol
last_updated: 2026-04-30
---
# Namespace Model

## Purpose

Specify the universal identifier scheme `kiki:<namespace>/<name>@<version>` and the namespace registry that resolves it to a concrete OCI registry URL with verification keys.

## Why this scheme

We need:

- A stable identifier independent of where the artifact is hosted today
- Decentralized publishing — anyone with a namespace can ship
- Verifiable identity — the namespace owner is bound to specific signing keys / OIDC identities
- Renames possible without breaking installed devices

A registry-URL-only identifier (`ghcr.io/acme/...`) breaks when hosting moves; a fully decentralized DNS-like scheme reinvents the wheel. The namespace registry is a small lookup that maps `kiki:<namespace>` → registry URL + pubkeys.

## Identifier shape

```
kiki:<namespace>/<name>@<version>
```

- `<namespace>`: lowercase, alphanumeric + dash; reserved namespaces: `kiki`, `system`, `apps`, `components`, `profiles`, `models`, `tools`, `skills`, `agents`
- `<name>`: lowercase, alphanumeric + dash; arbitrary
- `<version>`: semver, possibly with prerelease (`1.0.0-rc1`)

Examples:

```
kiki:apps/example-music@1.2.0
kiki:components/voice-waveform@1.0.0
kiki:profiles/kid-friendly@2.1.0
kiki:tools/markdown-render@0.9.5
kiki:models/llama-3.3-8b-q4@1.0.0
```

## Namespace registry

A small public registry mapping namespaces to OCI registries:

```toml
# in the registry's data store, conceptually:
[namespaces."acme"]
registry = "ghcr.io/acme/kiki"
sigstore_identity_regex = "^https://github.com/acme/.*"
sigstore_oidc_issuer = "https://token.actions.githubusercontent.com"
maintainer_pubkeys = [
    "...",
]
verified_at = "2026-04-30T..."
```

The Kiki device caches namespace records; refreshes daily.

A namespace can be:

- **Verified by Sigstore identity** (preferred): the bound OIDC identity is the canonical signer
- **Keyed**: the bound public keys are the canonical signers
- **Mixed**: both supported, either accepted

## Reserved namespaces

```
kiki         official Kiki Foundation publishing
system       OS-internal artifacts (base, sysext)
apps         apps under official curation
components   components under official curation
profiles     profiles under official curation
models       models under official curation
tools        tools under official curation
skills       skills under official curation
agents       agents under official curation
```

Other namespaces are arbitrary. Reserved namespaces' records are pinned in the OS image so a compromise of the namespace registry doesn't subvert system updates.

## Registry registration

Anyone can register a namespace by:

1. Pushing a record with the namespace, registry URL, and signing identity
2. Verifying ownership of the namespace name (e.g., a DNS TXT record on a related domain, a Sigstore-bound identity)
3. The record becomes queryable

Renaming or transferring a namespace requires a signed delegation by the prior owner.

## Resolution

```
kiki install kiki:apps/example-music@1.2.0
   │
   ▼
look up namespace "apps" → ghcr.io/kiki/apps/...
   │
   ▼
pull manifest for example-music:1.2.0
   │
   ▼
verify signature (must match namespace's identity)
   │
   ▼
install
```

If the signature does not match, the install is refused.

## Caching and TTL

Namespace records are cached locally with a TTL (default 24h). Stale records still work; refreshed in the background. A namespace record cannot be silently changed — when a fetch detects a different value, the user is prompted.

## Security

The namespace registry is a lookup; not a trust anchor. Trust comes from the signing identity bound to each namespace. The registry can be replicated (federation); compromise of a single replica doesn't compromise users with already-cached records.

For top-criticality content (system base, sysext), namespace records are baked into the bootc image and refresh only via signed updates of the image itself. This prevents a registry compromise from subverting the OS.

## Federation

Multiple namespace registry mirrors can coexist. The Kiki device queries them in priority order; the first valid response wins. Conflicts surface to the user.

## Removing or deprecating

A namespace can mark itself deprecated:

- Records still resolve
- Installs include a deprecation warning
- Users can unsubscribe from the namespace

## Anti-patterns

- Hardcoding registry URLs in app manifests (use `kiki:` IDs)
- Skipping signature verification "for testing"
- Manually editing namespace records on a device

## Acceptance criteria

- [ ] Identifier scheme parsed and validated
- [ ] Namespace registry lookup works
- [ ] Sigstore + keyed identity both supported
- [ ] Reserved namespaces pinned in OS image
- [ ] TTL + refresh logic
- [ ] Renaming/delegation supported

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/MAINTAINER-GUIDE.md`
- `12-distribution/REGISTRY-OPERATIONS.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/SIGSTORE-WITNESS.md`
- `14-rfcs/0004-namespace-registry.md`
