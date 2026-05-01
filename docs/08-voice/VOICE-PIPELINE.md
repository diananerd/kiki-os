---
id: voice-pipeline
title: Voice Pipeline
type: DESIGN
status: draft
version: 0.0.0
implements: [voice-pipeline]
depends_on:
  - audio-stack
  - inference-router
  - inference-models
  - capability-gate
depended_on_by:
  - audio-io
  - barge-in
  - speaker-id
  - stt-cloud
  - stt-local
  - tts-cloud
  - tts-local
  - vad
  - voice-channels
  - wake-word
last_updated: 2026-04-30
---
# Voice Pipeline

## Problem

A useful voice loop must wake on the right phrase, ignore noise, transcribe quickly, route through the agent, speak the result, and yield instantly when the user interrupts. It must do this with privacy guarantees (most users do not want their voice in someone's cloud) and predictable latency (slower than 700ms first-token barge-in is "broken").

## Constraints

- **Privacy by default.** Voice is treated as Sensitive privacy level by the inference router.
- **Local-first.** Wake word, VAD, ASR, TTS all run on-device by default.
- **Bounded latency.** Wake-to-first-token <700ms (barge-in), <2s (normal).
- **Hands-free etiquette.** Mute via gesture and physical kill switch; clear voice-state indicator.
- **Multi-user.** Speaker id keeps users separate; never sent off-device.

## Decision

A modular pipeline of small components, each replaceable; three modes (local-only, hybrid, realtime) selectable per session.

```
mic → AEC → VAD → wake word → STT → agent → TTS → AEC → speaker
                                       ▲
                                  barge-in cancels TTS
```

## Modes

### local-only

All components on-device. Lowest privacy risk. Default for Sensitive contexts (anything per the router's privacy rules).

- Wake word: microWakeWord
- VAD: Silero VAD
- ASR: Whisper Large-v3-turbo via whisper.cpp (smaller variants for low-power tiers)
- LLM: local model via inference router
- TTS: Kokoro-82M

### hybrid

Local wake/VAD; ASR may use cloud for non-Sensitive content (per the router); LLM per the router; TTS may be cloud for higher-quality voices the user opts into.

- The user opts in at provisioning or in Settings
- The router never escalates Sensitive to cloud regardless of the mode

### realtime

For voice-API-style providers that handle ASR/LLM/TTS in one stream. Requires user opt-in. Privacy and budget caveats apply. Used in narrow cases where ultra-low-latency conversational flow matters and the user accepts the tradeoffs.

## Pipeline stages

### Capture

PipeWire captures from the user's preferred mic source. AEC (acoustic echo cancellation) cancels playback before sending to downstream. Capture goes to an iceoryx2 service `audio.mic.<session>` for fanout.

### Wake word

A tiny model (microWakeWord, ~1MB) listens 100% of the time. On detection it triggers the rest of the pipeline. Replays the last ~1.5s of audio into ASR (so the agent hears the trigger phrase context).

### VAD

Silero VAD partitions speech vs. silence. Speech segments are sent to ASR; silence ends a turn.

### ASR

Streaming ASR. Partial transcripts surface in the UI as they arrive; final transcript is committed at end-of-utterance.

### Routing

The transcript is delivered to agentd as a `voice.user_message` event. The agent loop processes it; tool calls and reasoning happen in the standard path.

### TTS

The agent's response is streamed to TTS as it generates. TTS audio plays via PipeWire; AEC removes it from the mic capture.

### Barge-in

If the user starts speaking while TTS is playing, AEC + VAD detect; the system cancels TTS within 100ms; the new user input becomes a fresh ASR stream.

## Capability scoping

```
agent.audio.observe          read mic stream
agent.audio.respond           emit TTS
agent.voice.session            initiate a voice session
agent.voice.cloud_asr          opt-in for cloud ASR
agent.voice.cloud_tts          opt-in for cloud TTS
agent.voice.realtime           opt-in for realtime providers
```

## Sessions and presence

A voice session begins on wake-word and ends on:

- Final-answer + silence
- Explicit "stop" / mute
- Timeout (no user input for 10s)
- Mic kill switch toggle

The agent loop tracks session state separately from text sessions.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Wake word false positive         | VAD rejects; no transcript     |
|                                  | sent                            |
| ASR confidence low               | request user repeat            |
| TTS unavailable                  | render text on screen          |
| AEC failure                      | duplex audio degrades; warn    |
| Network drop in hybrid           | fall back to local             |
| Mic kill switch on               | suspend pipeline; no audio     |

## Performance

- Wake word detection: <200ms
- Wake word → ASR partial: <100ms
- ASR partial latency: ~300ms
- Agent first token (Realtime budget): <700ms
- TTS first audio: <300ms after first token
- Barge-in cancel: <100ms

## Acceptance criteria

- [ ] All three modes work end-to-end
- [ ] Sensitive content cannot reach cloud regardless of mode
- [ ] Barge-in cancels TTS within 100ms
- [ ] Mic kill switch suspends the pipeline immediately
- [ ] Speaker id keeps users distinct without leaving device

## References

- `02-platform/AUDIO-STACK.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/INFERENCE-MODELS.md`
- `08-voice/VOICE-CHANNELS.md`
- `08-voice/WAKE-WORD.md`
- `08-voice/VAD.md`
- `08-voice/STT-LOCAL.md`
- `08-voice/STT-CLOUD.md`
- `08-voice/TTS-LOCAL.md`
- `08-voice/TTS-CLOUD.md`
- `08-voice/BARGE-IN.md`
- `08-voice/SPEAKER-ID.md`
