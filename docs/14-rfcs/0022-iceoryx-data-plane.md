---
id: 0022-iceoryx-data-plane
title: iceoryx2 for Bulk Data Plane
type: ADR
status: draft
version: 0.0.0
depends_on: [0014-rust-only-shell-stack]
last_updated: 2026-04-29
---
# ADR-0022: iceoryx2 for Bulk Data Plane

## Status

`accepted`

## Context

Audio capture (48kHz 16-bit stereo ≈ 190KB/s) and TTS playback feed multiple consumers per stream — wake word, VAD, ASR, diagnostics. Sending these bytes through Cap'n Proto RPC means a memcpy per consumer. Tensor inputs and outputs at the inference engine boundary can be tens of MB. We want zero-copy, lock-free, bounded-latency local-shm transport. Candidates: POSIX shm directly, Lightning Memory-Mapped DB (LMDB), DDS implementations, eCAL, iceoryx (C++), iceoryx2 (Rust).

## Decision

Use **iceoryx2** as the local shared-memory data plane for audio, TTS, vision frames, and large inference tensors. Cap'n Proto carries the *control* (start/stop/parameter); iceoryx2 carries the *bytes*. Memory budget capped at 512MB across all services per device.

## Consequences

### Positive

- Zero-copy fanout: producer writes once, any number of consumers read in place.
- Lock-free queues; no syscalls on the hot path past setup.
- Pure Rust, integrates with our daemons.
- POSIX-shm-backed; AppArmor and Landlock can describe per-service reachability.
- History buffer (last N samples) supports "wake word triggered, replay last 1.5s into ASR".

### Negative

- One more transport in the system, with its own conventions.
- Crash recovery requires a janitor task in agentd to clean stale services.
- /dev/shm is global; we depend on per-service ACL via policyd callback rather than filesystem-only isolation.

## Alternatives considered

- **Cap'n Proto streams** for the bytes: works, but copies through serde and adds latency; wrong tool for ~200KB/s with three consumers.
- **Raw POSIX shm + custom protocol**: we'd rebuild iceoryx.
- **eCAL / DDS**: heavier protocol stack, mostly designed for cross-machine.
- **iceoryx (C++)**: introduces C++ runtime; iceoryx2 supersedes it for our case.

## References

- `05-protocol/ICEORYX-DATAPLANE.md`
- `02-platform/AUDIO-STACK.md`
- `08-voice/VOICE-CHANNELS.md`
## Graph links

[[0014-rust-only-shell-stack]]
