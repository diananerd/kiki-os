---
id: backend-index
title: Backend — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Backend

Optional cloud services. The device is fully functional without any backend; backends add cross-device features.

## Contract

- `BACKEND-CONTRACT.md` — five services, multi-backend, self-hostable.

## Services

- `../../specs/DEVICE-AUTH.md` — mTLS device certificates.
- `../../specs/DEVICE-PROVISIONING.md` — first-boot enrollment, attestation.
- `../../specs/OTA-DISTRIBUTION.md` — bootc image distribution and sysext refresh.
- `../../specs/AI-GATEWAY.md` — credential substitution, budgets, provider abstraction.
- `../../specs/MEMORY-SYNC.md` — E2E encrypted, bitemporal-aware.
- `../../specs/REGISTRY-PROTOCOL.md` — namespace registry HTTP API.
- `../../specs/NAMESPACE-FEDERATION.md` — federation among OCI registries and namespace registries.

## Self-hosting

- `SELF-HOSTING.md` — running backend services on LAN or private cloud.
