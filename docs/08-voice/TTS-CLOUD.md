---
id: tts-cloud
title: Cloud TTS
type: SPEC
status: draft
version: 0.0.0
implements: [tts-cloud]
depends_on:
  - voice-pipeline
  - inference-router
  - capability-gate
  - cryptography
depended_on_by: []
last_updated: 2026-04-30
---
# Cloud TTS

## Purpose

Specify the optional cloud-based text-to-speech path used in hybrid mode. Some users prefer cloud-quality voices for richer prosody and emotion; the cloud path is opt-in and never carries Sensitive content.

## Why cloud TTS exists

High-end cloud TTS providers offer voices that are noticeably more expressive than what fits on-device. Where the user values that and accepts the privacy and cost, we support it.

## Privacy guarantees

- Off by default
- The router never sends Sensitive text to cloud TTS
- The user must opt in (`agent.voice.cloud_tts` capability)
- TLS 1.3 in transit
- A user-visible indicator when cloud TTS is in use
- Provider-side data retention is the provider's; we surface their policy at opt-in

## Routing

```
agent text response
   │
   ▼
[router check]
   ├── privacy = Sensitive → use local TTS
   ├── network unavailable → use local TTS
   ├── budget exhausted → use local TTS
   └── otherwise → cloud TTS
```

Same fallback discipline as cloud STT.

## Streaming

Cloud TTS providers support streaming PCM/Opus output. We negotiate a streaming session and pipe the audio into the iceoryx2 sink as it arrives.

Latency:

- LAN-to-cloud RTT: ~50ms
- First audio: ~200-400ms (provider-dependent)

## Voices

Provider-specific. The user picks a voice from the provider's catalog; the choice is stored in the per-user voice preferences.

## Cost

Metered per character or per minute. Router enforces budget; falls back to local on exhaustion.

## Capability

`agent.voice.cloud_tts` — required to send any text to cloud TTS.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Provider 5xx                     | retry once; fall back to local |
| Network drop                     | fall back to local             |
| Budget exhausted                 | fall back to local             |
| TLS verification fails           | refuse; alert                  |
| Audio truncated                  | log; continue from local TTS   |

## Configuration

```toml
[tts.cloud]
enabled = false
provider = "<provider-id>"
voice = "<voice-id>"
endpoint = "https://..."
```

## Acceptance criteria

- [ ] Off by default; opt-in only
- [ ] Sensitive text never sent
- [ ] Fallback to local on failure or budget
- [ ] User-visible indicator
- [ ] TLS verification mandatory
- [ ] Streaming output integrates with iceoryx2 sink

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/TTS-LOCAL.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/CAPABILITY-GATE.md`
- `09-backend/AI-GATEWAY.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/PRIVACY-MODEL.md`
