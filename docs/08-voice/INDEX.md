---
id: voice-index
title: Voice — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Voice

End-to-end voice pipeline: wake word, VAD, STT, TTS, AEC, speaker ID.

## Pipeline

- `VOICE-PIPELINE.md` — end-to-end, three modes (hybrid, local-only, realtime).
- `../../specs/VOICE-CHANNELS.md` — Native, WebRTC, Bridge.
- `../../specs/AUDIO-IO.md` — PipeWire integration and AEC configuration.

## Components

- `../../specs/WAKE-WORD.md` — microWakeWord, context replay.
- `../../specs/VAD.md` — Silero VAD v5.
- `../../specs/STT-LOCAL.md` — Whisper Large-v3-turbo via whisper.cpp.
- `../../specs/STT-CLOUD.md` — cloud routing.
- `../../specs/TTS-LOCAL.md` — Kokoro-82M.
- `../../specs/TTS-CLOUD.md` — cloud routing.
- `../../specs/BARGE-IN.md` — AEC and interrupt within 100ms.
- `../../specs/SPEAKER-ID.md` — local-only voice prints.
