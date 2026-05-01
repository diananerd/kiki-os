---
id: audio-stack
title: Audio Stack
type: SPEC
status: draft
version: 0.0.0
implements: [audio-stack]
depends_on:
  - hal-contract
  - init-system
depended_on_by:
  - audio-io
  - iceoryx-dataplane
  - sensory-buffer
  - voice-pipeline
last_updated: 2026-04-30
---
# Audio Stack

## Purpose

Specify the audio stack: PipeWire as the system audio service, AEC integration for barge-in, multi-stream routing, and the interface exposed to the voice pipeline and apps.

## Behavior

### PipeWire as system audio

PipeWire 1.4+ is the system audio service. It replaces both PulseAudio and JACK with a unified low-latency model that handles consumer audio, professional audio, and video routing.

Why PipeWire:

- Mainline default in 2026 across CentOS Stream, Fedora, Debian, Arch.
- Sub-5ms round-trip latency at 48kHz/256-frame on reference hardware.
- JACK and PulseAudio compatibility shims for legacy applications.
- Wayland-friendly (avoids X11-era assumptions).
- `module-echo-cancel` provides AEC built in.

`wireplumber` is the session manager (default in PipeWire deployments). It handles policy: which streams go where, default device selection.

### Process layout

```
pipewire           system audio service
wireplumber        session manager
pipewire-pulse     compatibility shim for PulseAudio clients
pipewire-jack      compatibility shim for JACK clients (rare in Kiki)
```

PipeWire and wireplumber run as system services (Category B). User-mode pipewire daemons may also run for per-user audio scopes.

### AEC for barge-in

The voice pipeline needs AEC (Acoustic Echo Cancellation) to support barge-in: the user can interrupt the agent while it is speaking, and the wake word / VAD must distinguish the user's voice from the TTS playback.

PipeWire's `module-echo-cancel` with `aec_method=webrtc` provides this:

```
context.modules = [
  { name = libpipewire-module-echo-cancel
    args = {
      monitor.mode = true
      capture.props = { node.name = "echo-cancel-source" }
      playback.props = { node.name = "echo-cancel-sink" }
      aec.method = "webrtc"
      library.name = "aec/libspa-aec-webrtc"
    }
  }
]
```

WebRTC AEC3 is the underlying algorithm. RNNoise is layered on top for residual noise suppression.

### Stream routing

PipeWire routes:

- Microphone input through AEC-cancel source → kiki-voiced (for VAD, STT).
- TTS output from kiki-voiced → speaker (with echo-cancel monitoring playback).
- App audio (e.g., music player) → speaker via standard pipewire pulse compatibility.
- Notification sounds → speaker.

When the agent speaks (TTS), the playback signal is fed back into the echo-cancel module's monitor input so the microphone signal is cancelled accordingly.

### Multiple speakers / microphones

Devices with multiple audio devices (built-in + USB headset, e.g.):

- wireplumber default policy follows user preference.
- Voice pipeline can request a specific device per Profile.
- Apps follow the system default unless explicitly routed.

### Per-app audio access

Apps in containers reach PipeWire through:

- Bind-mount of `/run/user/<uid>/pipewire-0` (or system socket).
- The app's Profile declares `device.audio.input` or `device.audio.output` capability.
- Without the capability, the bind mount is not provided; the app cannot reach PipeWire.

### Hardware kill switch (microphone)

When the hardware microphone kill switch is engaged:

- The kernel reports the microphone as unavailable.
- PipeWire sees the source disappear.
- Voice pipeline falls back to "voice unavailable" mode.
- agentd surfaces a status indicator.

The kill switch is HAL-enforced; software cannot override. See `02-platform/HARDWARE-KILL-SWITCHES.md`.

### Latency tuning

Default quantum: 256 samples at 48kHz = ~5.3ms.

For voice pipeline (low latency required for barge-in detection): same quantum is sufficient.

For audio production apps (rare): can request smaller quantum (e.g., 128) for ~2.7ms latency.

### Audio formats

PipeWire handles format conversion automatically. Common formats:

- 48kHz, 16-bit, mono: voice
- 48kHz, 16/24-bit, stereo: music, system audio
- Higher sample rates supported but rare for our use case.

### Multi-user audio

On multi-user devices, the active user's session has audio routing. When users switch (via speaker ID or explicit switch), wireplumber re-routes default streams to the new user's session.

## Interfaces

### PipeWire DBus

The standard PipeWire DBus interface is exposed under `org.pipewire.*`. agentd uses zbus.

### CLI

```
wpctl status                       # wireplumber status (developer mode)
agentctl audio devices             # user-friendly listing
agentctl audio set-default <name>  # change default audio output
```

## State

### Persistent

- wireplumber configuration in /etc/wireplumber/.
- User audio preferences.

### In-memory

- Active audio streams.
- Echo-cancel state.

## Failure modes

| Failure | Response |
|---|---|
| PipeWire crash | systemd restarts; brief audio gap; voice pipeline reconnects |
| Hardware kill switch engaged | mic source disappears; voice features degrade gracefully |
| Audio device unplug | streams migrate to next default; user notified |
| AEC module fails to load | warn; barge-in performance degraded |
| Sample format mismatch | PipeWire converts; small CPU cost |

## Performance contracts

- Round-trip latency at default quantum: 5–10ms at 48kHz.
- AEC processing overhead: ~3–5% CPU on one core.
- Stream switch latency on device change: <100ms.

## Acceptance criteria

- [ ] PipeWire 1.4+ with wireplumber.
- [ ] module-echo-cancel active with WebRTC AEC3.
- [ ] Voice pipeline reaches PipeWire via dedicated socket.
- [ ] Apps reach PipeWire only with capability.
- [ ] Hardware kill switch reflected.
- [ ] Multi-stream routing works (TTS + music + notification simultaneously).

## Open questions

- Whether to add per-app volume control as agentui block.

## References

- `02-platform/HAL-CONTRACT.md`
- `02-platform/HARDWARE-KILL-SWITCHES.md`
- `08-voice/VOICE-PIPELINE.md`
- `08-voice/AUDIO-IO.md`
- `08-voice/BARGE-IN.md`
