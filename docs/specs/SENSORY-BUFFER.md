---
id: sensory-buffer
title: Sensory Buffer
type: SPEC
status: draft
version: 0.0.0
implements: [sensory-buffer]
depends_on:
  - memory-architecture
  - audio-stack
  - iceoryx-dataplane
depended_on_by: []
last_updated: 2026-04-30
---
# Sensory Buffer

## Purpose

The transient layer where raw sensor data lives for seconds to minutes before being summarized into working memory or dropped. Audio frames, partial transcripts, draft VAD activity. Bounded RAM; never written to disk.

## Why a separate layer

Without a bounded buffer, raw sensor data either floods working memory or vanishes immediately. Voice in particular needs a small window of history (e.g., "replay the last 1.5s into ASR after wake word") that is meaningless to keep beyond seconds.

## Design

### rtrb + memmap2

- **rtrb** (real-time ring buffer, lock-free, single-producer/single-consumer) for audio frame queues
- **memmap2** as the backing memory for shared-memory regions (the iceoryx2 services already use this; the sensory layer reuses the underlying frames in place)
- Bounded; oldest entries overwritten when full

No disk involvement. The buffer is RAM-only; on shutdown or crash, contents are gone.

### Channels

```
sensory.audio.mic.<session>      raw PCM frames (last ~5s)
sensory.audio.tts.<session>      synthesized TTS frames
sensory.transcript.partial       partial ASR text (last ~10 turns)
sensory.transcript.final         final ASR text awaiting save
sensory.vad.activity              voice-activity flags
sensory.environment              ambient sensor signals
                                 (optional, hardware-dependent)
```

Each channel has a fixed capacity declared at startup.

### Capacity

```
audio frames        ~5s history per session
transcripts          last 10 partial + 5 final
vad                  last 1000 events
environment          last 1000 events
```

Total RAM: ~16MB default, configurable.

### Access pattern

Producers (pipewire capture, ASR streamer, VAD) write at the wire rate. Consumers (wake-word detector, working memory consolidator, agent loop) read with their own pace. Late subscribers see history up to the buffer depth.

### Capability scoping

`agent.audio.observe` is required to read sensory.audio.* channels. Microphone kill switch zeroes producer output.

### Lifecycle

Per-session channels live as long as the voice session. Cross-session ambient channels (vad, environment) live for the daemon's lifetime.

## Interfaces

### Programmatic

```rust
struct Sensory {
    fn channel<T>(&self, name: &str) -> Result<Channel<T>>;
    fn list(&self) -> Vec<ChannelInfo>;
}
```

### CLI

```
kiki-sensory channels                # list active
kiki-sensory tail audio.mic --secs=1 # debug, requires grant
```

## State

In-memory only.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Buffer overflow                  | drop oldest; counter increments|
| Slow consumer                    | per-channel policy (drop)      |
| Memory pressure                  | shrink buffer; alert maintenance|

## Performance

- Frame push: <10µs
- Read: <50µs
- No syscalls on hot path

## Acceptance criteria

- [ ] No disk writes from sensory layer
- [ ] Audio history depth honored
- [ ] Microphone kill switch zeroes producer
- [ ] Late subscribers receive history within buffer

## References

- `02-platform/AUDIO-STACK.md`
- `05-protocol/ICEORYX-DATAPLANE.md`
- `08-voice/VOICE-CHANNELS.md`
- `04-memory/WORKING-MEMORY.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[AUDIO-STACK]]  [[ICEORYX-DATAPLANE]]
