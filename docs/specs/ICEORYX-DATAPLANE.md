---
id: iceoryx-dataplane
title: iceoryx2 Data Plane
type: SPEC
status: draft
version: 0.0.0
implements: [iceoryx-dataplane]
depends_on:
  - agentd-daemon
  - hardware-abstraction
  - audio-stack
depended_on_by:
  - audio-io
  - ipc-patterns
  - sensory-buffer
  - voice-channels
last_updated: 2026-04-30
---
# iceoryx2 Data Plane

## Purpose

Specify the zero-copy shared-memory transport used for bulk,
latency-sensitive data: microphone audio, TTS audio, model
input tensors at the edge of the inference engine, vision
frames from accessory cameras when applicable. Cap'n Proto
RPC carries the *control* for these flows; iceoryx2 carries
the *bytes*.

## Why iceoryx2

- **Zero-copy.** Producers write into a shared-memory buffer;
  consumers read in place. No `memcpy` between processes.
  Audio at 48kHz/16-bit/2-channel is ~190KB/s per stream;
  multiple consumers (the wake-word detector, the VAD, the
  ASR streamer) without per-consumer copies matters.
- **Pure Rust.** iceoryx2 is a Rust rewrite of iceoryx. No
  C/C++ build dependencies, integrates with our daemons.
- **Bounded latency.** Lock-free queues; no GC pauses; no
  syscalls on the hot path beyond initial setup.
- **POSIX shm.** Uses `/dev/shm`, which AppArmor and Landlock
  understand, so we can sandbox per-service shared regions.
- **Publish/subscribe with history.** Late subscribers can
  receive the most recent N samples — useful for "wake word
  triggered, replay last 1.5s into ASR".

## What does NOT go through iceoryx2

- Anything below ~10KB and not on the hot path: use Cap'n
  Proto.
- Anything that crosses the device/remote boundary: WebRTC
  for media, Cap'n-Proto-over-mTLS for control. iceoryx2 is
  local-shm-only.
- Anything that needs durability: shm is volatile.

## Topology

```
┌──────────────┐        ┌──────────────────────────────────┐
│ pipewire     │  audio │  iceoryx2 service "audio.mic"    │
│ capture node │───────▶│  history=N samples                │
└──────────────┘        └─────────┬────────────────────────┘
                                  │ shm read
       ┌──────────┬───────────────┼─────────────┬───────────┐
       ▼          ▼               ▼             ▼           ▼
   wake-word    VAD          ASR streamer   audio dump   diagnostics
   detector                                  (debug)
```

Each subscriber reads in place. The producer writes once.

## Service taxonomy

```
audio.mic.<session>            mic capture, raw PCM
audio.tts.<session>             synthesized audio
inference.tensor.<model>        model input/output tensors
                                (large)
vision.frame.<source>           camera frames (if applicable)
```

A "service" in iceoryx2 is a named pub/sub channel with a
fixed payload type. Names are kebab-case under fixed
prefixes; agentd reserves `audio.`, `vision.`, `inference.`.

## Sample shape

Each service declares a fixed payload struct:

```rust
#[repr(C)]
struct AudioPcmSample {
    capture_ns: u64,           // monotonic
    seq: u64,                  // sequence number
    samples: [i16; FRAME_LEN],
    actual_len: u32,           // <= FRAME_LEN
}
```

Reasoning for fixed-size: iceoryx2 publishes into a
pre-allocated pool. Variable-size payloads use the "blob"
pattern with a length prefix and a max bound.

## Capability gating

A service has an ACL controlled by policyd:

- **Producer**: which actor may publish (typically a single
  daemon)
- **Consumer ACL**: which actors may subscribe; based on
  capabilities

For example, `audio.mic.*` requires `agent.audio.observe` to
subscribe; only the wake-word detector, VAD, ASR streamer,
and (optionally) an attacker-class debug tool with explicit
grant can connect.

The gate is consulted at subscribe time. iceoryx2's runtime
calls into a Kiki-provided callback to authorize.

## Lifecycle

```
1. agentd publishes service registration over NATS
   ("system.iceoryx.service.created").
2. The producer (e.g., pipewire capture worker) opens the
   service in publish mode; allocates the shm pool.
3. Subscribers open the service; the gate authorizes.
4. The producer writes samples; subscribers iterate.
5. On producer shutdown: subscribers see EOF; service is
   removed.
6. On subscriber drop: refcount decrements; pool freed when
   all subscribers and the publisher are gone.
```

Crashes are detected via heartbeat + lifeline FDs; stale
services are cleaned up by a janitor task in agentd.

## Memory budget

```
audio.mic           ~4MB (history of ~5s @ 48kHz 16-bit mono)
audio.tts           ~4MB
inference.tensor    up to 256MB per model (rare; large LLM
                    KV scratch lives off-heap)
vision.frame        sized per device; default 16MB
```

Total iceoryx2 reservations are capped at 512MB per device by
default; agentd refuses to register a new service that would
exceed the cap.

## Performance characteristics

- Publish a 20ms audio frame to N subscribers: <50µs total
  on commodity hardware
- No syscalls on the hot path (only on register/drop)
- Memory bandwidth-bound, not CPU-bound

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Slow subscriber                  | per-service policy: drop       |
|                                  | oldest (audio) or block        |
|                                  | producer (rare; unsafe for     |
|                                  | real-time streams)             |
| Producer crash                   | subscribers see EOF; service   |
|                                  | removed                        |
| Subscriber crash                 | refcount drops; pool not       |
|                                  | freed if other subscribers     |
|                                  | still hold                     |
| /dev/shm full                    | refuse register; alert         |
| Schema mismatch                  | iceoryx2 rejects connect;      |
|                                  | logged                         |
| ACL deny                         | subscribe() returns            |
|                                  | PolicyDenied                   |

## Sandbox interaction

- iceoryx2 uses `/dev/shm/iox2_*` files. The sandbox profile
  for a service producer permits create + write on its
  prefix; subscribers permit read.
- File names encode the service name; the namespace is
  effectively flat in /dev/shm but logical isolation is via
  the gate.
- Cleanup uses `shm_unlink` from the daemon that created the
  region.

## Interfaces

### Programmatic

```rust
struct DataPlane {
    fn publish<T>(&self, service: &str) -> Result<Publisher<T>>;
    fn subscribe<T>(&self, service: &str) -> Result<Subscriber<T>>;
    fn list(&self) -> Vec<ServiceInfo>;
}

trait Publisher<T> {
    fn loan(&self) -> Result<Sample<T>>;
    fn publish(&self, sample: Sample<T>) -> Result<()>;
}

trait Subscriber<T> {
    fn receive(&self) -> Result<Option<&T>>;
}
```

### CLI

```
kiki-shm services                      # list active
kiki-shm peers <service>                # producer + subscribers
kiki-shm tap <service> --frames=10      # debug; requires
                                        # appropriate grant
```

### NATS announcements

iceoryx2 service lifecycle is announced on NATS:

```
system.iceoryx.service.created  payload: ServiceInfo
system.iceoryx.service.removed  payload: ServiceName
```

so subscribers can wait for late-creation services without
polling.

## Acceptance criteria

- [ ] Audio mic stream goes through iceoryx2 without
      per-consumer copies
- [ ] Subscribe-time ACL enforced via policyd callback
- [ ] Memory budget cap enforced; new services refused if
      total exceeds
- [ ] Lifecycle events published on NATS
- [ ] Janitor cleans up after producer crashes

## Open questions

None.

## References

- `02-platform/AUDIO-STACK.md`
- `01-architecture/HARDWARE-ABSTRACTION.md`
- `03-runtime/INFERENCE-ENGINE.md`
- `05-protocol/CAPNP-RPC.md`
- `05-protocol/IPC-PATTERNS.md`
- `08-voice/VOICE-CHANNELS.md`
## Graph links

[[AGENTD-DAEMON]]  [[HARDWARE-ABSTRACTION]]  [[AUDIO-STACK]]
