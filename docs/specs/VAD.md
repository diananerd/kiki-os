---
id: vad
title: Voice Activity Detection
type: SPEC
status: draft
version: 0.0.0
implements: [vad]
depends_on:
  - voice-pipeline
  - audio-io
depended_on_by:
  - barge-in
  - stt-local
last_updated: 2026-04-30
---
# Voice Activity Detection

## Purpose

Specify the VAD layer that distinguishes speech from silence. VAD makes ASR efficient (don't transcribe silence), enables turn-taking (speak/listen boundaries), and supports barge-in (detect user speech while TTS plays).

## Default model

**Silero VAD v5** — a small, accurate, multilingual VAD. ONNX or PyTorch model, ~2MB. Runs on CPU in real time with <5ms per 30ms window.

## Operation

```
audio frame (20-30ms)
   │
   ▼
Silero VAD
   │
 speech probability ∈ [0, 1]
   │
   ▼
state machine (configurable thresholds)
   │
emits: SpeechStart, SpeechContinue, SpeechEnd
```

The state machine has hysteresis: cross threshold for N frames to enter speech; cross opposite for M frames to exit. Defaults: enter at 0.6, exit at 0.4, N=2 frames, M=10 frames (~200-300ms of silence to end a turn).

## Modes

- **Streaming mode**: continuous; emits state events as they happen
- **One-shot mode**: returns "speech vs silence" for a fixed buffer

The pipeline uses streaming.

## Use cases

### After wake-word

VAD validates that the wake-word was followed by speech. If no speech for ~600ms, the wake-word trigger is treated as a false positive and discarded.

### During ASR

VAD bounds the ASR's input. End-of-utterance triggers the final ASR commit and ends the user's turn.

### During TTS (barge-in)

VAD runs on the *post-AEC* mic stream. If speech is detected while TTS is playing, the system cancels TTS and starts a new ASR stream. See `BARGE-IN.md`.

### In ambient mode

Some sessions want VAD without wake-word (push-to-talk, conversational mode). VAD's start/stop boundaries replace explicit user actions.

## Calibration

The user can fine-tune sensitivity (low / medium / high). The pipeline adjusts the thresholds:

- Low (less false positives, more missed): enter 0.7, exit 0.3
- Medium: 0.6 / 0.4
- High (more sensitive, more false positives): 0.5 / 0.45

## Multilingual

Silero VAD is language-agnostic; it works for the languages we support without per-language tuning.

## Capability

VAD runs in the voice daemon; no per-call capability needed beyond the daemon's privileged audio access.

## Configuration

```toml
[vad]
model = "silero-vad@5.0"
sensitivity = "medium"
end_of_speech_silence_ms = 300
window_ms = 30
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Model load fails                 | fall back to energy-based VAD  |
|                                  | (lower quality)                |
| Mic feed gaps                    | treat gap as silence           |
| AEC residual misclassified as    | barge-in suppressed during     |
| speech during TTS                | known TTS frames; logged       |

## Performance

- Inference per window: <5ms
- Memory: <8MB
- CPU on continuous stream: <3% on a small core

## Acceptance criteria

- [ ] Real-time streaming on default hardware
- [ ] Hysteresis prevents flickering
- [ ] Multilingual without retuning
- [ ] Sensitivity setting applies live
- [ ] Barge-in path uses post-AEC stream

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/AUDIO-IO.md`
- `08-voice/WAKE-WORD.md`
- `08-voice/STT-LOCAL.md`
- `08-voice/BARGE-IN.md`
## Graph links

[[VOICE-PIPELINE]]  [[AUDIO-IO]]
