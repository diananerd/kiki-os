---
id: ipc-patterns
title: IPC Patterns
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - capnp-rpc
  - nats-bus
  - dbus-integration
  - iceoryx-dataplane
  - error-model
last_updated: 2026-04-29
---
# IPC Patterns

## Purpose

Give writers of daemons, tools, and apps clear guidance on
which transport to use for which kind of interaction, and
how to compose them. Kiki uses four transports — Cap'n Proto,
NATS, DBus, iceoryx2 — each with a clear job. Picking the
right one keeps the system coherent.

## Choosing a transport

```
                      ┌─────────────────────────────────────┐
                      │ Need typed request/response with    │
                      │ capabilities, possibly streaming?   │
                      │                                     │
                      │  → Cap'n Proto RPC                   │
                      └─────────────────────────────────────┘
                      ┌─────────────────────────────────────┐
                      │ Need loosely coupled events that    │
                      │ many subscribers may observe?       │
                      │                                     │
                      │  → NATS (or JetStream if            │
                      │     at-least-once)                  │
                      └─────────────────────────────────────┘
                      ┌─────────────────────────────────────┐
                      │ Talking to or from the wider        │
                      │ Linux desktop ecosystem             │
                      │ (logind, NetworkManager, portals)?  │
                      │                                     │
                      │  → DBus                              │
                      └─────────────────────────────────────┘
                      ┌─────────────────────────────────────┐
                      │ Bulk media or tensor data on the    │
                      │ hot path within one machine?        │
                      │                                     │
                      │  → iceoryx2                          │
                      └─────────────────────────────────────┘
```

Defaults:

- A daemon's "front door" is Cap'n Proto on a Unix socket.
- A daemon's "side channel" for ambient events is NATS.
- A daemon that participates in desktop UX exposes a small
  DBus interface mapped from its Cap'n Proto API.
- Audio, video, tensors stream via iceoryx2; the control
  plane is Cap'n Proto.

## Common patterns

### Request/response with a typed capability

For: every tool call, every memory query, every grant lookup.

```
Client → CapnpRPC.method() → Daemon
Daemon ← CapnpRPC.response ← Client
```

- Define the method on a typed interface in `*.capnp`.
- Carry actor identity via the bootstrap binding, not in the
  message.
- Errors via `ErrorPayload` (see `ERROR-MODEL.md`).

### Streaming response

For: token streaming, search result paging, audio control
events.

```
Client → CapnpRPC.method() → Daemon
Daemon ← chunk ← chunk ← chunk ← ... ← Client (drains)
```

- Use Cap'n Proto's `stream` keyword.
- Apply backpressure: server `await`s its yield; client
  paces its read.
- For *bulk* audio, do not stream over Cap'n Proto — use
  iceoryx2 for the bytes and Cap'n Proto for the events.

### Event broadcast (best-effort)

For: hooks, mailbox arrival notifications, focus changes.

```
Producer publishes "agent.cycle.start" payload.
Subscribers (hook handlers, observers, audit reader) receive.
Producer never waits for subscribers.
```

- NATS Core (best-effort fanout).
- Drop policy on slow consumer.
- Schema known via `kiki-schema` header.

### Event broadcast (durable)

For: mailbox delivery, audit log tail.

```
Producer publishes to a JetStream-backed subject.
Subscribers ack messages; pending counts visible.
On consumer reconnect, replay from last ack.
```

- JetStream stream with bounded retention.
- Producer treats it like a queue; consumers durables.

### Long-running operation with progress

For: model warm-up, large memory ingest, app install.

```
Client → start(...) → Daemon → returns Handle capability
Client polls Handle.progress() or subscribes to NATS subject.
On completion, Handle.result() returns final value.
```

- Cap'n Proto for the handle; NATS optionally for progress
  fanout.

### Hook-style intercept

For: capability decisions, pre-tool-dispatch transforms.

```
Tool dispatch invokes hook synchronously over Cap'n Proto.
Hook returns Continue | Allow | Deny | Transform.
Dispatch proceeds based on result.
```

- Cap'n Proto only (synchronous; NATS would be wrong here
  because we need a return value within a deadline).
- Deadline enforced by dispatcher; hook timeouts treated
  per the safer-default policy in `HOOKS.md`.

### Cross-app coordination

For: focus changes, "who is the current music player?".

```
App publishes its focus to org.kiki.Focus1 (DBus) /
focus.changed (NATS mirror).
Other apps and the agent subscribe.
```

- DBus is the well-known surface; NATS mirrors for
  daemon-internal use.

### Audio/voice flow

```
Mic capture (pipewire) → iceoryx2 service "audio.mic.<sid>"
                                   │
        ┌──────────────┬───────────┼───────────┬─────────┐
        ▼              ▼           ▼           ▼         ▼
   wake-word        VAD       ASR streamer   diag      ...
        │
       triggers ───── Cap'n Proto event ─────▶ agentd
                                                       │
                                                  agent loop
                                                       │
                                            TTS request
                                                       │
                                                       ▼
                                          inferenced (Cap'n Proto)
                                                       │
                                            audio out (iceoryx2)
                                                       │
                                                  pipewire sink
```

Control events on Cap'n Proto and DBus; bytes on iceoryx2.

### Pairing handshake (remote)

For: a paired remote client connecting from LAN or WAN.

```
Client → mTLS connect → Kiki remote proxy
Proxy → CapnpRPC over the mTLS tunnel
Proxy attaches pairing-bound ActorRef to the connection.
```

- Cap'n Proto over mTLS for the wire; the bootstrap is
  scoped by the pairing scope. NATS does not federate
  over the boundary.

## Anti-patterns

### Using NATS for request/response

Tempting because subjects are flexible, but you give up:

- Capability typing (NATS scopes are subject-based, not
  capability-based)
- Bidirectional capability passing
- Promise pipelining

If you find yourself writing reply-subjects on NATS, you
want Cap'n Proto.

### Using Cap'n Proto for ambient broadcasts

Each subscriber is an explicit capability holder; fanout to
many ad-hoc observers is awkward and bookkeeping-heavy. Use
NATS.

### Using DBus for high-frequency calls

DBus has more overhead than Cap'n Proto and isn't designed
for streaming. Use it for the surface that Linux components
expect, not as your daemon's primary RPC.

### Sending bulk audio over Cap'n Proto

Works, but copies the bytes through serde. Use iceoryx2.

### Mixing transports in a single API

A daemon's public surface should pick one front-door (Cap'n
Proto) and a small set of side channels (NATS for events,
DBus for ecosystem integration). Don't sprinkle different
transports randomly.

## Composing multiple transports

Common: a method that publishes a side-effect.

```
Client → CapnpRPC.create_grant(...) → policyd
policyd inserts grant in DB
policyd publishes NATS "policy.grant.created"
policyd returns success on Cap'n Proto
Subscribers (audit, app reactors) receive on NATS
DBus signal mirrored from NATS
```

Common: a stream that needs ACL on subscribe.

```
Client → CapnpRPC.subscribe_audio(scope) → agentd
agentd checks gate
agentd issues an iceoryx2 token (file-mode bit; or
                                  named-server cookie)
Client opens iceoryx2 service with the token
```

The Cap'n Proto layer authorizes; the iceoryx2 layer carries
the bytes.

## Tracing and observability

Every cross-boundary call carries a `trace-id`:

- Cap'n Proto: in the bootstrap; propagated in headers
- NATS: in `kiki-trace-id` header
- DBus: in the message header (via standard
  `org.freedesktop.DBus.Peer` extensions)
- iceoryx2: in the sample header struct field

agentd's tracing collector ingests these and renders them in
`kiki-trace` for debugging.

## Versioning across transports

- Cap'n Proto schema version negotiated at bootstrap
- NATS payloads carry `kiki-schema: name@version` header;
  consumers reject unknown major versions
- DBus introspection XML carries an `Annotation` for
  version; clients can read it
- iceoryx2 sample structs are versioned by their `service`
  name suffix when needed (rare)

## Migration patterns

When introducing a new transport for an existing path:

1. Add the new path; both run in parallel for one release.
2. Migrate clients; flag legacy users with deprecation
   warnings.
3. Remove the old path on the next major release.

The audit log records use of deprecated paths; the
`UPDATE-ORCHESTRATOR.md` ties this to release cadence.

## References

- `05-protocol/CAPNP-RPC.md`
- `05-protocol/NATS-BUS.md`
- `05-protocol/DBUS-INTEGRATION.md`
- `05-protocol/ICEORYX-DATAPLANE.md`
- `05-protocol/ERROR-MODEL.md`
- `03-runtime/HOOKS.md`
- `03-runtime/EVENT-BUS.md`
## Graph links

[[CAPNP-RPC]]  [[NATS-BUS]]  [[DBUS-INTEGRATION]]  [[ICEORYX-DATAPLANE]]  [[ERROR-MODEL]]
