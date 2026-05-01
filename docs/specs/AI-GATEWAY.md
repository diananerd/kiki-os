---
id: ai-gateway
title: AI Gateway
type: SPEC
status: draft
version: 0.0.0
implements: [ai-gateway]
depends_on:
  - backend-contract
  - device-auth
  - inference-router
  - capability-gate
  - cost-control
depended_on_by:
  - self-hosting
last_updated: 2026-04-30
---
# AI Gateway

## Purpose

Specify the optional cloud-inference service: a thin proxy between the device's inference router and external AI providers. The gateway abstracts provider details, manages credentials, enforces budgets, and emits usage events. It is *not* required; everything works locally without it.

## Why a gateway, not direct provider calls

- **Credentials abstraction.** The user's account is at the gateway; provider-specific keys live there.
- **Budgets.** The gateway counts tokens and enforces caps at the source.
- **Privacy layer.** A user can choose which providers their account exposes; the gateway only routes to allowlisted ones.
- **Audit.** Every cloud call is logged at the gateway with the device's mTLS identity.
- **Failover.** Multiple providers configurable; gateway picks based on availability.

A user can still use direct provider keys (set in their config); the gateway is for users who prefer the abstraction.

## What the gateway does

```
device inference router
   │ HTTPS (mTLS) — request with provider hint, prompt, etc.
   ▼
gateway:
   ├── verify mTLS device cert
   ├── resolve user account
   ├── check budget
   ├── pick provider (per user policy + availability)
   ├── apply credential substitution (provider's API key)
   ├── proxy request (streaming)
   ├── record usage events
   ├── stream response back
   ▼
device
```

## What the gateway does NOT see

- Sensitive content (the router never sends Sensitive to cloud)
- Identity content (never leaves the device)
- Memory data unless the inference explicitly references it (the user is responsible for what they include in a prompt)

The gateway is a proxy for *what was asked*; it doesn't silently extract or store user state.

## Provider abstraction

Providers covered by the reference gateway:

- Anthropic Claude
- OpenAI / Azure OpenAI
- Google / Vertex
- Mistral
- Local-network providers (private clouds)

Each provider has an adapter in the gateway; the device's request is normalized; the gateway maps to provider-specific API. Streaming responses translate back to the device's expected format.

## Budget enforcement

```
GET /v1/budget                    (the device polls)
POST /v1/inference                 (a call; counts against budget)
GET /v1/usage?period=current        (history for UI)
```

The gateway maintains per-user period budgets:

```
{
  "period_start": "2026-04-01T...",
  "period_end": "2026-05-01T...",
  "tokens_in": 5400000,
  "tokens_out": 1200000,
  "limit_in": 10000000,
  "limit_out": 2500000
}
```

Exhausted budgets refuse new requests; the device falls back to local.

## User policy

A user account can enforce:

- Allowlist of providers
- Per-provider budgets
- Disabled-for-voice
- Disabled-for-Sensitive (forced; the device also enforces, but defense in depth)

## Security

- mTLS auth (per `DEVICE-AUTH.md`)
- TLS 1.3 to providers
- Provider keys encrypted at rest at the gateway
- Audit log replicated to device on request

## Streaming

Server-sent events / chunked HTTP for streaming. The gateway re-streams provider chunks to the device. Backpressure is honored via TCP-level controls.

## Failover

If a provider returns 5xx repeatedly, the gateway marks Degraded for a cool-down. The device's inference router sees Degraded and routes around (per `INFERENCE-ROUTER.md`).

## Cost transparency

The gateway exposes per-call cost in usage events. The device's `kiki-router budget` CLI surfaces it. Surprise bills are incompatible with the design.

## Self-hosted gateway

A reference open-source implementation ships in the Kiki repo:

```
docker run --rm -p 8443:8443 \
  -v /etc/kiki-gateway:/etc/kiki-gateway \
  kiki/gateway-reference:latest
```

Configure providers, allowlists, and CA root; it's a regular Rust service.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Gateway unreachable              | router falls back to local     |
| Provider 5xx                     | gateway marks Degraded;        |
|                                  | router avoids                  |
| Budget exhausted                 | refuse; device informs user    |
| TLS verification fails           | refuse                         |
| Auth fails                       | refuse; device prompts         |
|                                  | re-provisioning                |

## Acceptance criteria

- [ ] mTLS auth enforced
- [ ] Budgets enforced with sub-second latency
- [ ] Streaming works end-to-end
- [ ] Provider abstraction exposes a uniform request shape
- [ ] User can disable providers per their policy
- [ ] Reference self-hosted gateway runs

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/DEVICE-AUTH.md`
- `09-backend/SELF-HOSTING.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `11-agentic-engineering/COST-CONTROL.md`
- `08-voice/STT-CLOUD.md`
- `08-voice/TTS-CLOUD.md`
- `10-security/PRIVACY-MODEL.md`
- `10-security/CRYPTOGRAPHY.md`
## Graph links

[[BACKEND-CONTRACT]]  [[DEVICE-AUTH]]  [[INFERENCE-ROUTER]]  [[CAPABILITY-GATE]]  [[COST-CONTROL]]
