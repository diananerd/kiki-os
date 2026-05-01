---
id: barge-in
title: Barge-In
type: SPEC
status: draft
version: 0.0.0
implements: [barge-in]
depends_on:
  - voice-pipeline
  - audio-io
  - vad
  - tts-local
depended_on_by: []
last_updated: 2026-04-30
---
# Barge-In

## Purpose

Specify how the system detects user speech while TTS is playing and yields the floor within 100ms. Barge-in is the difference between "this thing actually feels conversational" and "this thing won't shut up."

## Setup

Barge-in requires:

- AEC (acoustic echo cancellation) suppressing the device's own TTS from the mic capture
- VAD running on the post-AEC mic stream
- A TTS engine that can stop within ~100ms when asked
- A control plane that can fire a Cancel message to TTS the moment VAD signals user speech

All four are present in the default pipeline.

## Sequence

```
TTS playing
   │
mic captures TTS + (possibly) user speech
   │
AEC removes the TTS portion
   │
post-AEC stream → VAD
   │
VAD: SpeechStart event
   │
control plane: Cancel TTS
   │
TTS: drain pending buffer → silence
   │
ASR: receive new user audio (already buffered from VAD start)
   │
agent loop: new turn begins
```

## Timing

- Speech start to VAD detection: ~30-50ms (one or two windows)
- VAD detection to Cancel TTS: <10ms
- TTS Cancel to silence at speaker: <50ms (depends on PipeWire buffer)
- Total: <100ms, often <70ms

## Semantics

- The interrupted TTS is *cancelled*, not paused. The agent's response that was speaking is considered superseded by the new user input.
- If the user starts speaking and then stops mid-utterance (false positive), the agent has already cancelled; it then waits for ASR; if no real input arrives, the agent may resume or not depending on context.
- The interrupted assistant turn is recorded as truncated in episodic memory ("agent was responding to ..., user interrupted").

## Tunable thresholds

```toml
[barge_in]
enabled = true
vad_sensitivity = "medium"
ignore_below_ms = 80          # ignore very short blips
require_speech_after_ms = 600 # if VAD trigger not followed by
                              # real speech, suppress next time
```

The "ignore below" guards against background noise spikes; the "require speech after" implements a learning loop that quiets aggressive false positives.

## Multi-speaker scenes

When multiple speakers are present and one is the primary user:

- Speaker id (see `SPEAKER-ID.md`) gates barge-in
- A non-primary user's speech does not interrupt the agent's response to the primary user
- The user can override (e.g., a child interrupting a parent's session must be allowed when the parent permits)

## TTS state-machine

The TTS engine exposes a Cancel method that:

1. Stops feeding new audio into the iceoryx2 sink
2. Drains any frames already in PipeWire's playback buffer (or zeros them, depending on the latency budget)
3. Emits an event so subscribers can update UI ("interrupted")

## Capability

`agent.audio.barge_in` — internal to the voice daemon. Apps cannot disable barge-in; users can in Settings.

## Anti-patterns

- TTS without barge-in capability
- AEC turned off by default; barge-in works but with frequent false positives from speaker bleed
- TTS that finishes the current sentence before yielding (annoying)

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| AEC disabled or failing          | barge-in still works but with  |
|                                  | many false positives; warn     |
| VAD too sensitive                | learning loop reduces          |
|                                  | sensitivity; surface to user   |
| TTS cancel too slow              | log; investigate engine        |
|                                  | configuration                  |
| Multi-speaker confusion          | speaker id gates; user can     |
|                                  | adjust                         |

## Acceptance criteria

- [ ] User speech mid-TTS cancels TTS within 100ms
- [ ] AEC suppresses TTS from mic before VAD
- [ ] False positives below 1 per minute on quiet rooms
- [ ] Speaker id gates correctly
- [ ] User can disable barge-in if desired

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/AUDIO-IO.md`
- `08-voice/VAD.md`
- `08-voice/TTS-LOCAL.md`
- `08-voice/SPEAKER-ID.md`
