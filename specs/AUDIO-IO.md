---
id: audio-io
title: Audio IO
type: SPEC
status: draft
version: 0.0.0
implements: [audio-io]
depends_on:
  - audio-stack
  - voice-pipeline
  - iceoryx-dataplane
depended_on_by:
  - barge-in
  - speaker-id
  - tts-local
  - vad
  - wake-word
last_updated: 2026-04-30
---
# Audio IO

## Purpose

Specify how voice connects to PipeWire: capture nodes, sinks, AEC chain, device selection, and per-session routing. AUDIO-IO is the bridge between the platform's audio stack (`02-platform/AUDIO-STACK.md`) and the voice pipeline.

## Capture chain

```
hardware mic → PipeWire input device
              → AEC node (echo cancel + denoise)
              → resample to 16kHz mono
              → iceoryx2 service "audio.mic.<session>"
```

Each voice session has its own iceoryx2 service so multiple sessions don't mix audio.

## Playback chain

```
agent TTS → iceoryx2 service "audio.tts.<session>"
          → PipeWire sink (resampled if needed)
          → device output
```

The TTS sink is paired with the AEC node feeding capture so playback can be canceled from the mic before reaching downstream.

## AEC

AEC is provided by PipeWire's built-in `webrtc-audio-processing` chain or platform equivalent:

- Echo cancellation: removes playback from mic
- Noise suppression: filters background hum
- AGC: gentle automatic gain

AEC is on by default; it is the difference between conversational and unusable.

## Device selection

The hardware manifest declares mic and speaker preferences. PipeWire is configured via the manifest at boot:

```toml
[audio]
default_input = "<device-id>"
default_output = "<device-id>"
aec_enabled = true
denoise_enabled = true
agc_enabled = true
```

The user can override via `kiki-audio device set`. Hot-pluggable headsets (USB / Bluetooth) automatically reconfigure.

## Sample format

- Capture: 48kHz 16-bit linear PCM stereo (then downsampled to 16kHz mono for the pipeline)
- Playback: 48kHz 16-bit linear PCM mono or stereo depending on the sink
- Frame size: 20ms (960 samples at 48kHz, 320 at 16kHz)

## Multi-channel (multi-mic arrays)

A device with a mic array uses beamforming via PipeWire/PulseAudio modules. The output of the array is a single mono stream feeding the pipeline.

## Volume and mixer

Voice TTS and other audio share a mixer:

- Voice TTS volume independent of music/alarm
- Ducking: when voice TTS plays, music ducks by ~12dB
- DND mode silences notifications but not the agent's voice

## Mic kill switch

When the hardware kill switch is engaged, capture is zeroed at the PipeWire node level (not the application). The voice pipeline sees silence and times out gracefully. See `02-platform/HARDWARE-KILL-SWITCHES.md`.

## Capability scoping

- `audio.read` — read mic capture
- `audio.write` — write to a sink
- `audio.observe` — read mic with AEC + denoise (the privileged
  voice path)
- `audio.metadata` — read device names, mixer state

The voice daemon holds `audio.observe`; apps may have `audio.read` for narrow uses (recording).

## Configuration

`/etc/kiki/audio.toml`:

```toml
[capture]
sample_rate = 48000
frame_ms = 20

[playback]
ducking_db = 12

[aec]
mode = "webrtc"               # webrtc | speex | off
denoise = true
agc = true

[mic_array]
beamforming = "auto"
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| AEC node fails                   | continue without AEC; warn     |
| Device unplugged mid-session     | switch to next preferred       |
|                                  | device or end session          |
| Sample rate not supported        | resample in software           |
| iceoryx2 service unavailable     | refuse session                 |

## Performance

- Capture-to-iceoryx2 publish: <5ms
- TTS-to-speaker: <50ms
- AEC overhead: <10ms

## Acceptance criteria

- [ ] AEC chain on by default; user can disable
- [ ] Per-session iceoryx2 services
- [ ] Hardware kill switch zeroes capture
- [ ] Hot-plug reconfigures correctly
- [ ] Ducking applied during TTS

## References

- `02-platform/AUDIO-STACK.md`
- `02-platform/HARDWARE-KILL-SWITCHES.md`
- `08-voice/VOICE-PIPELINE.md`
- `08-voice/VOICE-CHANNELS.md`
- `08-voice/BARGE-IN.md`
- `05-protocol/ICEORYX-DATAPLANE.md`
