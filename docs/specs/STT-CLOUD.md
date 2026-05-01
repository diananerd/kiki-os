---
id: stt-cloud
title: Cloud STT
type: SPEC
status: draft
version: 0.0.0
implements: [stt-cloud]
depends_on:
  - voice-pipeline
  - inference-router
  - capability-gate
  - cryptography
depended_on_by: []
last_updated: 2026-04-30
---
# Cloud STT

## Purpose

Specify the optional cloud-based speech-to-text path used in hybrid mode. The cloud path is opt-in; it only handles content the router classifies as non-Sensitive; it never receives audio for Sensitive content.

## Why cloud STT exists

For some users and devices, cloud STT is faster, more accurate, or supports languages we don't ship locally. We support it as a *secondary* option; local is the default and the always-available baseline.

## Providers

The router supports multiple cloud providers behind a uniform interface:

- Provider-specific accounts (user supplies API key) or
- Backend gateway (per `09-backend/AI-GATEWAY.md`)

The user chooses a provider at provisioning or in Settings. None is "default"; cloud STT is off unless turned on.

## Privacy guarantees

- The router never sends Sensitive audio to a cloud provider
- The user must opt in (`agent.voice.cloud_asr` capability)
- The audio that *is* sent is encrypted in transit (TLS 1.3, rustls + aws-lc-rs)
- The audio is *not* stored by us; storage by the provider depends on the provider's policy
- A clear indicator shows when cloud STT is in use ("Cloud transcription enabled" badge)

## Routing

```
audio chunk
   │
   ▼
[router check]
   ├── privacy = Sensitive → use local STT
   ├── network unavailable → use local STT
   ├── budget exhausted → use local STT
   └── otherwise → cloud STT
```

The router checks per chunk; a session may switch mid-flow if conditions change.

## Streaming

Cloud STT providers offer WebSocket or HTTP/2 streaming. We use the streaming API where available; partial transcripts surface to the UI.

## Latency

Cloud STT is sometimes faster than local on low-tier hardware:

- LAN-to-cloud RTT: ~50ms
- First partial: ~200-300ms (provider-dependent)

## Cost

Cloud STT is metered. The router enforces the user's budget; if exhausted, falls back to local.

## Configuration

```toml
[stt.cloud]
enabled = false
provider = "<provider-id>"
languages = ["en", "es"]
endpoint = "https://..."

[stt.cloud.privacy]
disable_for_voice_session = false
```

## Capability

`agent.voice.cloud_asr` — required to send any audio to cloud STT.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Provider 5xx                     | retry once; fall back to local |
| Network drop                     | fall back to local             |
| Budget exhausted                 | fall back to local             |
| TLS verification fails           | refuse; alert                  |
| Audio quality too low            | provider returns error;        |
|                                  | surface to user                |

## Acceptance criteria

- [ ] Off by default; opt-in only
- [ ] Sensitive audio never sent to cloud
- [ ] Fallback to local on any failure or budget
- [ ] User-visible indicator when active
- [ ] TLS verification mandatory

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/STT-LOCAL.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/CAPABILITY-GATE.md`
- `09-backend/AI-GATEWAY.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/PRIVACY-MODEL.md`
