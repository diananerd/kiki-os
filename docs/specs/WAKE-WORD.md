---
id: wake-word
title: Wake Word
type: SPEC
status: draft
version: 0.0.0
implements: [wake-word]
depends_on:
  - voice-pipeline
  - audio-io
  - inference-engine
depended_on_by: []
last_updated: 2026-04-30
---
# Wake Word

## Purpose

Specify the always-on wake-word detector. The detector listens continuously to the mic stream, triggers the rest of the voice pipeline on detection, and replays the last ~1.5s of audio so context is preserved.

## Default model

**microWakeWord** — a tiny on-device model designed for keyword spotting on low-power microcontrollers and SBCs. Footprint <2MB; CPU <2% on a small core.

We ship default phrases:

- "Hey Kiki"
- "OK Kiki"

The user can record a custom phrase via Settings; the model retrains on-device using the user's enrollment samples.

## Architecture

```
mic stream (16kHz mono)
       │
       ▼
ring buffer (last ~3s)
       │
       ▼
microWakeWord (sliding window)
       │
   confidence > threshold?
       │
       ▼ yes
trigger event
   + replay last 1.5s into ASR
```

The ring buffer keeps a short history so on detection we can prepend audio that came *before* the trigger phrase reached high confidence — important for "Hey Kiki, what time is it?" where the question follows the trigger by a fraction of a second.

## Sensitivity tuning

The user picks one of three sensitivities (low / medium / high). Higher sensitivity means more false triggers but fewer missed wakes. The default is medium.

A separate "no-wake-word" mode (push-to-talk via gesture or hardware button) exists for users who don't want the always-on listening; the model is then unloaded.

## Privacy

- The wake-word model runs entirely locally
- Audio before a trigger is in the ring buffer (RAM only); never written to disk
- After a trigger, audio enters the standard pipeline (privacy = Sensitive)
- Mic kill switch zeroes the source; the detector sees silence
- A subtle indicator on the status bar shows "listening" continuously when the detector is active

## Multi-user

Each user can enroll their own custom phrase; the model dispatches to a per-user pipeline based on speaker id (see `SPEAKER-ID.md`). When phrases differ, the right user is woken.

If the same default phrase is shared, the device wakes the foreground user; the agent disambiguates if speaker id is uncertain.

## Capability

`agent.audio.wakeword` — the daemon-internal capability for the wake-word listener. Apps cannot register custom wake words (would be a confused-deputy mess).

## Configuration

```toml
[wakeword]
enabled = true
sensitivity = "medium"
phrases = ["Hey Kiki", "OK Kiki"]
ring_buffer_seconds = 3.0
replay_seconds = 1.5
```

User-level overrides per `~/.config/kiki/wakeword.toml`.

## Enrollment

Custom phrase enrollment:

1. User picks a phrase (3+ syllables recommended)
2. Records 3-5 samples in different rooms / tones
3. Local fine-tune on the recordings
4. Test prompt; confirm

The training stays on-device; samples are kept under
`/var/lib/kiki/users/<uid>/voice/wakeword/` and used for retraining.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| False positive                   | VAD rejects (no speech follows)|
| False negative                   | user must repeat or use        |
|                                  | gesture                        |
| Model unloaded (no-wake mode)    | gesture / button required      |
| Detector crashes                 | restart; if persistent, fall   |
|                                  | back to push-to-talk           |

## Performance

- Inference: <5ms per window
- Memory: <2MB
- CPU: <2% on a small core (continuous)

## Acceptance criteria

- [ ] Default phrases work out of the box
- [ ] Custom phrase enrollment works on-device
- [ ] Replay buffer feeds ASR with pre-trigger context
- [ ] Sensitivity setting is respected
- [ ] Mic kill switch zeroes detection
- [ ] No audio leaves the device

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/VAD.md`
- `08-voice/SPEAKER-ID.md`
- `08-voice/AUDIO-IO.md`
- `02-platform/HARDWARE-KILL-SWITCHES.md`
## Graph links

[[VOICE-PIPELINE]]  [[AUDIO-IO]]  [[INFERENCE-ENGINE]]
