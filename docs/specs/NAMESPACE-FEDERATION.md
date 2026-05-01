---
id: namespace-federation
title: Namespace Federation
type: SPEC
status: draft
version: 0.0.0
implements: [namespace-federation]
depends_on:
  - registry-protocol
  - namespace-model
depended_on_by:
  - self-hosting
last_updated: 2026-04-30
---
# Namespace Federation

## Purpose

Specify federation among namespace registries. A user's device queries a primary registry; alternate registries can mirror or be queried as fallbacks. Federation prevents a single registry from being the only point of failure (or control).

## Federation kinds

### Read-replica mirror

A registry mirrors another registry's records:

- Periodic pull of all namespaces
- Records re-signed by the mirror with its own key (so the mirror's signature is verifiable)
- The original signature is preserved alongside

The device can verify either signature; trust comes from the device's pinned root keys.

### Federation by namespace

A registry hosts authoritative records for some namespaces and federates queries for others:

- "We host `kiki:acme/*` here; for `kiki:other/*`, ask <upstream>"
- Recursive resolution allowed up to a small depth (default 3)

### Independent registries

Two registries operate independently with no overlap; users may query both. Conflicts (same namespace defined differently) trigger a user-visible warning.

## Discovery

A device's config lists registries by URL and trust priority:

```toml
[namespace_registries]
primary = "https://registry.kiki.example"
mirrors = [
    "https://mirror.kiki-foundation.example",
    "https://acme-mirror.example",
]

[namespace_registries.policy]
on_conflict = "primary_wins"          # primary_wins | newest | manual
```

Devices try primary; on miss or unreachable, try mirrors in order.

## Conflict resolution

When two registries return different records for the same namespace:

- **primary_wins**: trust primary; ignore mirrors for that namespace
- **newest**: use the record with the most recent `verified_at`
- **manual**: surface to user; user picks

Default is `primary_wins` for known namespaces; `newest` for newly seen.

## Verification

Each record is signed by the originating registry. The device:

1. Verifies signature against the registry's pinned key
2. Validates `verified_at` is recent enough
3. Checks the maintainer pubkeys (or sigstore identity) the record advertises
4. Uses these to verify subsequent OCI artifact pulls

A federated mirror cannot forge a record without the original registry's key.

## Trust roots

A device trusts a small set of registry roots (pinned in its image). Adding new roots:

- User can add via Settings (becomes a root for that user only)
- Profile can pin additional roots
- Untrusted registries can serve, but the device warns and uses lower trust

## DNS-based federation

For name resolution before federation: a registry advertises its presence via DNS:

```
_kiki-namespace._tcp.acme.example  IN SRV 0 0 443 registry.acme.example
```

Devices can opt to discover via DNS in addition to configured URLs.

## Replication topology

Recommended:

- One authoritative registry per organization
- One geo-distributed mirror per region for performance
- Optional: third-party mirrors for resilience

Replication interval: hourly for most; minutes for popular namespaces.

## Anti-patterns

- Letting a federation member create authoritative records for namespaces it doesn't own
- Trusting any registry the user adds without surfacing the trust change
- Federation cycles (A federates from B, B from A)

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Mirror sig invalid               | drop that mirror; alert        |
| Conflict (primary_wins)          | use primary; log               |
| Conflict (newest)                | use newer; log                 |
| Conflict (manual)                | block install; user resolves   |
| All registries down              | use cached records             |

## Acceptance criteria

- [ ] Mirror replication works with re-signing
- [ ] Conflict resolution per policy
- [ ] DNS-based discovery optional and functional
- [ ] Trust roots pinned and overridable per user
- [ ] Federation cycles detected and refused

## References

- `09-backend/REGISTRY-PROTOCOL.md`
- `09-backend/SELF-HOSTING.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/REGISTRY-OPERATIONS.md`
