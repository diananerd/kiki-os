---
id: tts-local
title: Local TTS
type: SPEC
status: draft
version: 0.0.0
implements: [tts-local]
depends_on:
  - voice-pipeline
  - audio-io
  - inference-models
  - inference-engine
depended_on_by:
  - barge-in
last_updated: 2026-04-30
---
# Local TTS

## Purpose

Specify the on-device text-to-speech engine: Kokoro-82M as default, with smaller variants for low-power tiers. Local TTS keeps responses on-device, supports multilingual output, and integrates with barge-in for snappy turn-taking.

## Default model

**Kokoro-82M** — a small, fast, high-quality multilingual TTS model. ~80MB on disk. Fast on CPU, very fast on accelerator.

For low-tier devices, **Piper TTS** is an alternate baseline. Both produce intelligible speech; Kokoro produces more natural prosody.

## Engine

Models run via candle (Rust ML framework) for Kokoro, or via Piper's native engine. Either way, the output is 22kHz/16-bit PCM streamed to the iceoryx2 service `audio.tts.<session>`.

## Streaming

Text-to-speech runs on chunked input. As the agent's response streams in, TTS begins synthesizing the first sentence while later tokens arrive:

```
agent token stream → sentence chunker → TTS synthesis → audio stream
```

Latency:

- First audio: ~300ms after first sentence is complete
- Continuous: TTS keeps up with token rate on most hardware

## Voices

Kokoro ships with multiple voices per language. The user picks a default voice; the agent or apps may request a specific voice via the synthesis call.

```
voices/
├── en/
│   ├── kiki-default
│   ├── narrator-warm
│   └── narrator-bright
├── es/
│   ├── kiki-default
│   └── narrator-natural
└── ...
```

A user can record samples to bias voice selection toward styles they prefer; we do not clone arbitrary voices on-device (a future feature with strong consent gates).

## Prosody control

The TTS API accepts SSML-like markup for:

- Pauses
- Emphasis
- Pace
- Pitch (limited; voice-dependent)

The agent uses these sparingly. Identity files can declare default pace and warmth.

## Multilingual

Same model supports multiple languages; the agent picks language from context (the latch language; the user's identity language; the question's language). Code-switching mid-sentence is supported on a best-effort basis.

## Capability

`agent.voice.synthesize.local` — used internally by the voice daemon.

## Configuration

```toml
[tts.local]
model = "kokoro-82m@1.0"
default_voice = "kiki-default"
default_pace = 1.0
sample_rate = 22050
backend = "auto"
```

## Resource budget

| Tier      | Model        | RAM    | First audio |
|-----------|--------------|--------|-------------|
| Reference | Piper        | 200MB  | ~400ms      |
| Standard  | Kokoro-82M   | 350MB  | ~300ms      |
| Pro       | Kokoro-82M   | 350MB  | ~200ms      |

## Privacy

- All synthesis on-device; no text leaves
- No telemetry on what is spoken
- TTS audio in iceoryx2 RAM only; not written to disk

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Model load fails                 | fall back to Piper             |
| Voice not available              | use default voice              |
| Synthesis lags token rate        | buffer; on persistent lag,     |
|                                  | switch to faster voice         |
| Output sample rate mismatch      | resample at output             |

## Acceptance criteria

- [ ] First audio within 300ms (Standard / Pro)
- [ ] Multilingual output works
- [ ] Streaming keeps up with token rate
- [ ] No text or audio leaves the device
- [ ] User can pick voice in Settings

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/TTS-CLOUD.md`
- `08-voice/AUDIO-IO.md`
- `08-voice/BARGE-IN.md`
- `03-runtime/INFERENCE-MODELS.md`
- `03-runtime/INFERENCE-ENGINE.md`
## Graph links

[[VOICE-PIPELINE]]  [[AUDIO-IO]]  [[INFERENCE-MODELS]]  [[INFERENCE-ENGINE]]
