---
id: stt-local
title: Local STT
type: SPEC
status: draft
version: 0.0.0
implements: [stt-local]
depends_on:
  - voice-pipeline
  - vad
  - inference-models
  - inference-engine
depended_on_by: []
last_updated: 2026-04-30
---
# Local STT

## Purpose

Specify the on-device speech-to-text engine: Whisper Large-v3-turbo (default) and smaller variants for low-power tiers, served via whisper.cpp.

## Default model

**Whisper Large-v3-turbo** (810M params). High quality, multilingual, decent on a Pro tier with hardware acceleration. For Standard tier, **Whisper Medium**. For Low tier, **Whisper Small** or **Distil-Whisper**.

The model is selected at provisioning per the hardware manifest; the user can change in Settings.

## Engine

**whisper.cpp** — the C++ Whisper inference engine. Bound via Rust crate (`whisper-rs`). Backend selected at runtime: CPU, CUDA, ROCm, Metal, Vulkan, depending on hardware.

## Streaming

Whisper is fundamentally a chunk model, but whisper.cpp supports streaming via overlapping windows:

```
audio chunks (1-2s each, overlapping)
   │
   ▼
whisper inference per chunk
   │
   ▼
partial transcript (may be revised by next chunk)
   │
finalize at end-of-speech (VAD)
```

Partial transcripts are surfaced to the UI as they arrive; the final transcript is committed when VAD signals end-of-speech.

Latency:

- First partial: ~300-500ms after speech starts
- Final commit: end-of-speech + ~200ms

## Languages

Whisper supports ~99 languages. We ship with English, Spanish, French, German, Portuguese, Italian, Dutch as fully tested; others work but with less validation. The user picks language(s) at provisioning; auto-detect mode is available.

## Multilingual

Whisper handles code-switching (mixing two languages) natively for many pairs.

## Custom vocabulary

The model can be biased toward names and terms in the user's identity files (e.g., "Kiki", proper names, project names) via prompt-conditioning. Implementation: a fixed initial-prompt prefix passed to whisper.cpp at the start of each utterance, drawn from a per-user vocabulary list.

## Privacy

- Inference is on-device; audio never leaves
- The transcript is treated as Sensitive by default
- Audio is held in iceoryx2 RAM; not written to disk unless the user explicitly enables transcription archive

## Capability

`agent.voice.transcribe.local` — used internally by the voice daemon.

## Configuration

```toml
[stt.local]
model = "whisper-large-v3-turbo@1.0"
languages = ["en", "es"]
auto_detect = false
custom_vocab_enabled = true
backend = "auto"               # auto | cpu | cuda | rocm | metal | vulkan
```

## Resource budget

| Tier      | Model                | RAM    | First partial |
|-----------|----------------------|--------|---------------|
| Reference | Whisper Small        | 500MB  | ~200ms        |
| Standard  | Whisper Medium       | 1.5GB  | ~300ms        |
| Pro       | Large-v3-turbo       | 2.5GB  | ~250ms        |

GPU/accelerator memory budget is a separate concern; whisper.cpp uses what's declared in the model entry.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Model load fails                 | fall back to smaller variant   |
| Confidence very low              | request user repeat            |
| Accelerator OOM                  | fall back to CPU; warn         |
| Language detection wrong         | offer manual override          |

## Acceptance criteria

- [ ] Streaming works with overlapping windows
- [ ] First partial within 500ms
- [ ] Languages user has selected work end-to-end
- [ ] Custom vocab biases recognition toward known names
- [ ] No audio leaves the device

## References

- `03-runtime/INFERENCE-ENGINE.md`
- `03-runtime/INFERENCE-MODELS.md`
- `08-voice/VOICE-PIPELINE.md`
- `08-voice/STT-CLOUD.md`
- `08-voice/VAD.md`
## Graph links

[[VOICE-PIPELINE]]  [[VAD]]  [[INFERENCE-MODELS]]  [[INFERENCE-ENGINE]]
