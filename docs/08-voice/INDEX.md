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
- `VOICE-CHANNELS.md` — Native, WebRTC, Bridge.
- `AUDIO-IO.md` — PipeWire integration and AEC configuration.

## Components

- `WAKE-WORD.md` — microWakeWord, context replay.
- `VAD.md` — Silero VAD v5.
- `STT-LOCAL.md` — Whisper Large-v3-turbo via whisper.cpp.
- `STT-CLOUD.md` — cloud routing.
- `TTS-LOCAL.md` — Kokoro-82M.
- `TTS-CLOUD.md` — cloud routing.
- `BARGE-IN.md` — AEC and interrupt within 100ms.
- `SPEAKER-ID.md` — local-only voice prints.
