---
id: registry-protocol
title: Registry Protocol
type: SPEC
status: draft
version: 0.0.0
implements: [registry-protocol]
depends_on:
  - backend-contract
  - namespace-model
depended_on_by:
  - namespace-federation
  - self-hosting
last_updated: 2026-04-30
---
# Registry Protocol

## Purpose

Specify the HTTP API of the namespace registry: the lookup service that maps `kiki:<namespace>` to a concrete OCI registry URL plus signing identity. The registry is *not* an OCI registry — it's a small lookup layer that points at OCI registries.

## Endpoints

### GET /v1/namespaces/{namespace}

Fetch the record for a namespace.

```
GET /v1/namespaces/acme

200 OK
{
  "namespace": "acme",
  "registry": "ghcr.io/acme/kiki",
  "sigstore_identity_regex": "^https://github.com/acme/.*",
  "sigstore_oidc_issuer": "https://token.actions.githubusercontent.com",
  "maintainer_pubkeys": [
    "-----BEGIN PUBLIC KEY-----\n..."
  ],
  "verified_at": "2026-04-30T...",
  "deprecated": false,
  "etag": "...",
  "ttl_seconds": 86400
}
```

Cacheable per `Cache-Control` and `ETag`.

### POST /v1/namespaces

Register a new namespace (requires authentication and ownership proof).

```
POST /v1/namespaces
{
  "namespace": "acme",
  "registry": "ghcr.io/acme/kiki",
  "sigstore_identity_regex": "...",
  "ownership_proof": {
    "kind": "dns",
    "domain": "acme.example",
    "txt_record_value": "kiki-namespace=acme"
  }
}

201 Created
```

Ownership proofs supported:

- DNS TXT record at a related domain
- Sigstore-bound identity (the requester's OIDC identity is verified)
- Pre-shared admin token (for federated registries)

### PUT /v1/namespaces/{namespace}

Update an existing record (only by current owner).

### POST /v1/namespaces/{namespace}/transfer

Transfer ownership; requires signed delegation by current owner.

### POST /v1/namespaces/{namespace}/deprecate

Mark deprecated; provide replacement pointer.

### GET /v1/namespaces

List public namespaces; paginated; for discovery.

### GET /v1/health

Health check.

## Authentication

Read endpoints: public.
Write endpoints: per-registry-policy. Public Foundation registry uses Sigstore-bound identity; private registries can use any auth.

## Caching

- Records are immutable per ETag; clients cache aggressively
- `Cache-Control: public, max-age=86400` default
- Devices refresh in the background once a day
- `If-None-Match` supported

## Federation

Multiple registries can mirror each other. See `NAMESPACE-FEDERATION.md`.

## Verification

When a device receives a record, it verifies:

- Signature on the record (the registry signs records with its own key)
- `verified_at` timestamp not too far in the past
- TLS chain up to a CA trusted by the device

The registry's signing key is pinned in the device image; rotation via OS updates.

## Schemas

We use the standard OpenAPI spec (machine-readable) for the API. Generators produce Rust, TypeScript, Python clients.

## Anti-patterns

- Letting records change silently
- Not signing records
- Trusting a single registry mirror without verification
- Long-lived caches without TTL

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Registry unreachable             | use cached records             |
| TTL expired but registry down    | warn; continue with stale     |
|                                  | (audit logs the staleness)     |
| Record signature invalid         | refuse to use; alert            |
| Ownership proof fails            | reject registration            |

## Acceptance criteria

- [ ] All listed endpoints implemented
- [ ] Records signed by the registry
- [ ] Devices cache and refresh per TTL
- [ ] Ownership proofs validated
- [ ] Federation flag in records
- [ ] OpenAPI spec published

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/NAMESPACE-FEDERATION.md`
- `09-backend/SELF-HOSTING.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/MAINTAINER-GUIDE.md`
