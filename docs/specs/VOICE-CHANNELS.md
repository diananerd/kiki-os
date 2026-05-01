---
id: voice-channels
title: Voice Channels
type: SPEC
status: draft
version: 0.0.0
implements: [voice-channels]
depends_on:
  - voice-pipeline
  - iceoryx-dataplane
  - capnp-rpc
depended_on_by:
  - remote-architecture
last_updated: 2026-04-30
---
# Voice Channels

## Purpose

Specify the three voice transports: Native (local pipewire + iceoryx2), WebRTC (for paired remote clients), and Bridge (legacy/RTP). Each carries audio between the device's pipeline and a counterparty.

## The three channels

### Native

Local on-device. PipeWire captures and plays; iceoryx2 fans the bytes; agentd's voice control plane uses Cap'n Proto.

```
mic → pipewire capture node → iceoryx2 audio.mic.<session>
                              ↓
              [wake, VAD, AEC, ASR, agent, TTS] (local components)
                              ↑
       speaker ← pipewire sink ← iceoryx2 audio.tts.<session>
```

Used for: in-front-of-device voice with the on-device agent.

### WebRTC

For voice from a paired remote client (a phone, a laptop). The remote client opens a WebRTC session against the device; audio flows directly (LAN) or via a TURN/relay (WAN).

```
remote mic → WebRTC → kiki-voice-rtc daemon → iceoryx2 service
                                           ↓
                       same pipeline as Native
                                           ↑
       remote speaker ← WebRTC ← TTS audio
```

Used for: voice control of the device from a paired client without putting bytes through a backend cloud.

WebRTC is the right tool for low-latency bidirectional audio across the network. We do not use it locally where iceoryx2 is faster and direct.

### Bridge

For legacy or special scenarios: SIP/RTP bridges, telephony integrations, hardware bridges that present an RTP stream. agentd receives an RTP feed and translates to an iceoryx2 service.

Used rarely; opt-in per device profile.

## Capability scoping

- `voice.session.local` — initiate a local voice session
- `voice.session.remote` — accept a WebRTC session from a paired remote
- `voice.bridge.rtp` — accept a bridge stream (privileged)

The capability gate enforces these at session-start.

## Channel selection

A voice session declares its channel at start; the device's voice loop is channel-agnostic past the first stage. The same agent loop, ASR, TTS run regardless of channel. The differences are:

- Native: zero-copy via iceoryx2; AEC on local hardware
- WebRTC: jitter buffer; codec negotiation (Opus); RTP stack
- Bridge: codec depends on bridge

## Codecs

- Native: PCM 16-bit 48kHz mono (per audio stack)
- WebRTC: Opus 16kHz / 24kHz / 48kHz negotiated
- Bridge: Opus or G.711, depending on bridge

Conversion happens at the edge; downstream sees uniform PCM.

## Multi-session

Multiple voice sessions can run concurrently:

- One Native session in front of the device
- One or more WebRTC sessions from paired remotes

Each session has its own iceoryx2 service path and its own agent loop binding. The user can be in front while a paired remote sends a separate question; the device prioritizes per the user's preference (default: serialize, foreground first).

## Latency budgets per channel

| Channel  | Capture-to-ASR delay | TTS-to-speaker delay |
|----------|----------------------|----------------------|
| Native   | <30ms                | <50ms                |
| WebRTC   | <120ms (LAN)         | <120ms               |
| WebRTC   | <250ms (WAN)         | <250ms               |
| Bridge   | varies               | varies               |

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| WebRTC session drops             | end voice session; surface to  |
|                                  | remote client                  |
| iceoryx2 service unavailable     | refuse session; alert          |
| Codec mismatch                   | renegotiate; if fail, refuse   |
| Bridge stream invalid            | drop; log                      |

## Privacy

Native: bytes never leave the device.
WebRTC: bytes traverse the LAN (encrypted via DTLS-SRTP) or the WAN (same encryption + TURN). Backend never sees decrypted audio.
Bridge: privacy depends on bridge configuration; declared at install.

## Acceptance criteria

- [ ] All three channels deliver audio to the same pipeline interface
- [ ] Capability gate enforces session start
- [ ] Multi-session works with isolation
- [ ] Latency budgets met
- [ ] WebRTC encryption verified (DTLS-SRTP)

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/AUDIO-IO.md`
- `02-platform/AUDIO-STACK.md`
- `05-protocol/ICEORYX-DATAPLANE.md`
- `13-remotes/REMOTE-PROTOCOL.md`
## Graph links

[[VOICE-PIPELINE]]  [[ICEORYX-DATAPLANE]]  [[CAPNP-RPC]]
