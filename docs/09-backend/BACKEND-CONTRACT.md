---
id: backend-contract
title: Backend Contract
type: DESIGN
status: draft
version: 0.0.0
implements: [backend-contract]
depends_on:
  - principles
  - paradigm
  - cryptography
  - cosign-trust
depended_on_by:
  - ai-gateway
  - device-auth
  - device-provisioning
  - memory-sync
  - ota-distribution
  - registry-protocol
  - remote-architecture
  - remote-discovery
  - self-hosting
last_updated: 2026-04-30
---
# Backend Contract

## Problem

Some Kiki features benefit from a server: cross-device sync, OTA updates, optional cloud inference, namespace registry. We need backend services that *help* without becoming the architecture's center of gravity. The device must remain fully functional without any backend; backends are *optional* helpers, not the boss.

## Constraints

- **Local-first.** A device with no internet works.
- **No backend lock-in.** Any function with a backend service has either a public protocol (so users can self-host) or a clear local-only fallback.
- **Privacy by default.** Backends never see decrypted user data unless the user explicitly opts in (e.g., cloud inference).
- **Auditable.** Backend operations are recorded in the device's audit log and reflected in the user's view.
- **Self-hostable.** Every service has a published spec and a reference implementation.

## Decision

Five backend services, each with a clean protocol and an optional path:

```
1. Device auth + provisioning      mTLS + attestation; needed once at setup
2. OTA distribution                bootc + sysext + app channel mirror
3. AI gateway                      optional cloud inference + budgets
4. Memory sync                     optional cross-device E2E-encrypted sync
5. Namespace registry              public lookup; federated; cacheable
```

Each is self-hostable. The Kiki Foundation runs a default deployment; users and orgs can run their own.

## What backends do NOT do

- Run the agent loop (the device runs it)
- Hold user data in the clear (sync is E2E-encrypted; gateway is opt-in)
- Push commands to devices (devices pull; the only push channel is opt-in notifications)
- Make policy decisions (the device's gate is final)

## Service boundaries

```
┌──────────────────────────────────────────────────────┐
│                       Device                          │
│              (agent, capabilities, memory)           │
└──────────────────────────────────────────────────────┘
        │ mTLS device cert
        │
┌───────┴──────────┬──────────────┬─────────────┬───────┐
│ device-auth       │ ota          │ ai-gateway  │ sync  │
│ provisioning      │ distribution │  (optional) │ (opt) │
└───────────────────┴──────────────┴─────────────┴───────┘
        │
┌───────┴──────────┐
│ namespace        │
│ registry         │
└──────────────────┘
```

The device authenticates once via device-auth; subsequent service calls reuse the cert.

## Protocols

- **REST/JSON** for management endpoints (device-auth, registry, fleet)
- **gRPC over HTTPS** for high-volume paths (AI gateway streaming)
- **OCI Distribution** for OTA (existing standard)
- **Custom E2E-encrypted protocol** for memory sync (described in `MEMORY-SYNC.md`)

All over TLS 1.3 (rustls + aws-lc-rs).

## Multi-backend

A device can be configured with:

- Default backend (Kiki Foundation)
- Custom backends per service (e.g., self-hosted AI gateway, default for everything else)
- No backend (full local; some features unavailable)

Settings expose this; the user owns the topology.

## Authentication

mTLS device certificates issued at provisioning time bind a device to a user account on the chosen backend. Cert renewal happens before expiry; rotation is automatic.

User accounts live on the backend; the device's identity is anchored to its certificate. No username/password on the device.

## Privacy guarantees

- mTLS prevents eavesdropping
- Memory-sync content is encrypted client-side; backend stores ciphertext
- AI gateway is opt-in; the user sees what's sent
- OTA: the artifacts the device pulls reveal *what versions* the device runs (not its content); this metadata can be obscured via Tor or a relay if desired

## Failure modes (network)

If a backend is unreachable:

- Auth: existing cert continues working until expiry
- OTA: device runs current version; updates wait
- Gateway: routes fall back to local
- Sync: changes queue locally; flush when reachable
- Registry: cached records (24h default) keep the system functional

## Liveness and self-hosting

A user can run their own:

- harbor + zot for the registry
- A small reference AI gateway (`kiki-gateway-reference`)
- A small reference sync server
- A reference OTA mirror

The reference implementations are open source and small.

## References

- `00-foundations/PRINCIPLES.md`
- `09-backend/DEVICE-AUTH.md`
- `09-backend/DEVICE-PROVISIONING.md`
- `09-backend/OTA-DISTRIBUTION.md`
- `09-backend/AI-GATEWAY.md`
- `09-backend/MEMORY-SYNC.md`
- `09-backend/REGISTRY-PROTOCOL.md`
- `09-backend/NAMESPACE-FEDERATION.md`
- `09-backend/SELF-HOSTING.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/PRIVACY-MODEL.md`
- `12-distribution/NAMESPACE-MODEL.md`
