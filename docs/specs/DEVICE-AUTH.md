---
id: device-auth
title: Device Auth
type: SPEC
status: draft
version: 0.0.0
implements: [device-auth]
depends_on:
  - backend-contract
  - cryptography
  - cosign-trust
depended_on_by:
  - ai-gateway
  - device-pairing
  - device-provisioning
  - memory-sync
  - ota-distribution
  - self-hosting
last_updated: 2026-04-30
---
# Device Auth

## Purpose

Specify how a Kiki device authenticates to backend services: mTLS device certificates, certificate lifecycle, renewal, revocation. The device's identity is its cert; user accounts on the backend bind to that cert.

## Why mTLS

- Strong mutual auth without passwords on the device
- Standard, widely supported
- Works for any HTTPS-based service
- Fits the local-first model: the cert is the only credential

API tokens were considered; they have weaker rotation semantics and risk leakage. mTLS with short-lived certs is cleaner.

## Cert lifecycle

```
Provisioning ──▶ CSR ──▶ Backend CA ──▶ Cert (valid 1 year)
                                          │
                                       deployed on device
                                          │
                              ~30d before expiry
                                          │
                                          ▼
                                       renewal request
                                          │
                                          ▼
                                    new cert (1 year)
```

If a renewal fails (network out, CA reachable but says no), the device keeps the current cert until expiry; user is alerted to investigate.

## CA structure

```
Backend root CA
  └── Backend issuing CA (intermediate)
        └── Device cert
```

Root CA is offline-signed and pinned in the device image (only renewed when the OS image is). Issuing CA is online; rotates more frequently.

## Cert contents

Standard X.509:

- Subject CN: `device:<device-id>`
- Subject alternative names: `device-id`, `user-account`
- Extensions:
  - Extended key usage: client auth
  - Custom: device profile, hardware attestation digest

Devices identify themselves with their cert; backends can implement per-user, per-device policy.

## Hardware attestation

When a device has a TPM or equivalent secure element:

- The CSR includes a TPM-quote attestation
- The CA verifies attestation before issuing
- The cert encodes the attestation digest

Devices without TPM can still get certs, but at lower trust tier.

## Renewal

Renewal request:

- Device generates a new key pair
- CSR signed with the new key
- Posted to the CA endpoint over the existing mTLS session
- CA verifies session, optionally re-attests, issues
- Device replaces cert atomically

We rotate keys on renewal; the long-lived secret is the device's enrollment binding, not the per-cert key.

## Revocation

Backends maintain a CRL (Certificate Revocation List) or use OCSP:

- A user can revoke a device cert via Settings on another paired device or via the backend's web UI
- Revoked certs reject within minutes (CRL polled by services)

Revocation reasons logged: user request, suspected compromise, decommission.

## Compromise

If the device's cert key is suspected compromised:

- User revokes via another device or backend portal
- Device's existing connections terminate
- The device must re-provision (which generates a new key + cert)
- The user should also rotate any backend credentials the device knew

## Capability binding

The cert identifies the device; what the device is *allowed* to do at the backend is controlled by the user account it's bound to. Different services may grant different scopes:

- AI gateway: budget, providers, hosts allowed
- Memory sync: which sync corpora
- OTA: which channels

## Multiple devices per user

A user can have many devices; each has its own cert. Backends keep per-device records.

## Self-hosting

A self-hosted backend runs its own CA. Devices can be enrolled against any CA the user trusts. Multiple CAs allowed (one device may talk to multiple backends).

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Cert expired                     | service refuses; device re-    |
|                                  | provisions or alerts user      |
| CA unreachable for renewal       | use existing cert until expiry |
| Revocation list pull fails       | services use cached CRL with   |
|                                  | bounded staleness              |
| TPM attestation fails            | refuse issuance; alert user    |

## Acceptance criteria

- [ ] Cert issuance via CSR + attestation
- [ ] Renewal before expiry
- [ ] Revocation reflected within minutes
- [ ] Multiple devices per user
- [ ] Multiple CAs (multi-backend)

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/DEVICE-PROVISIONING.md`
- `09-backend/SELF-HOSTING.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/STORAGE-ENCRYPTION.md`
## Graph links

[[BACKEND-CONTRACT]]  [[CRYPTOGRAPHY]]  [[COSIGN-TRUST]]
