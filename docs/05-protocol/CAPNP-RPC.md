---
id: capnp-rpc
title: Cap'n Proto RPC
type: SPEC
status: draft
version: 0.0.0
implements: [capnp-rpc]
depends_on:
  - agentd-daemon
  - capability-gate
  - transport-unix-socket
  - capnp-schemas
depended_on_by:
  - agentui
  - capnp-schemas
  - error-model
  - ipc-patterns
  - kernel-framework
  - memory-facade
  - remote-protocol
  - system-clients
  - tool-dispatch
  - toolregistry
  - voice-channels
last_updated: 2026-04-30
---
# Cap'n Proto RPC

## Purpose

Specify the RPC layer used between agentd, the other Rust
daemons (policyd, inferenced, memoryd, toolregistry), tools,
and clients on the same machine. Cap'n Proto RPC carries
tool calls, capability handles, and structured responses with
zero-copy decoding and capability-typed references.

This is the *primary* in-machine IPC. NATS handles loosely
coupled events; iceoryx2 handles bulk audio/video; DBus
handles desktop integration. Cap'n Proto is the workhorse for
typed request/response and streaming with capabilities.

## Why Cap'n Proto

- **Capabilities are first-class.** A `Capability` reference
  in a Cap'n Proto interface is a live, revocable handle, not
  just a token string. The wire format and runtime track
  ownership, drop, and revocation. This matches our trust
  model directly.
- **Schema evolution.** Field tags with version numbers; old
  clients keep working as fields are added. Required during
  the multi-year life of an installed device.
- **Zero-copy.** Decoder reads the wire buffer in place. Tool
  payloads (vector embeddings, large structured prompts) are
  not memcpy'd through serde.
- **Promise pipelining.** Tools that compose other tools can
  pass capability promises forward without round trips.
- **No code generation surprises.** `capnp-rust` and
  `capnp-rpc` are mature and the generated code is plain
  Rust.

JSON-RPC, gRPC, and tarpc were considered. JSON-RPC has no
capability typing; gRPC needs HTTP/2 framing for nothing in
return; tarpc is fine for ad-hoc but lacks the schema-first
discipline we want.

## Transport

Cap'n Proto RPC runs over the local Unix-socket transport
specified in `TRANSPORT-UNIX-SOCKET.md`. Sockets live under
`/run/kiki/`:

```
/run/kiki/agentd.sock       agentd public RPC
/run/kiki/policyd.sock       policyd RPC (capability gate, grants)
/run/kiki/inferenced.sock    inference engine RPC
/run/kiki/memoryd.sock       memory daemon RPC
/run/kiki/toolregistry.sock  tool registry RPC
/run/kiki/tools/<id>.sock    per-tool sockets (when persistent)
```

Each socket is owned `kiki:kiki` mode 0660. SO_PEERCRED
authenticates the peer's UID, GID, and PID. Per-user paths
add a user component:

```
/run/kiki/users/<uid>/agentd.sock
```

## Connection lifecycle

```
1. Client opens AF_UNIX SOCK_STREAM to the socket.
2. Server accepts; reads SO_PEERCRED.
3. Both sides perform Cap'n Proto RPC handshake (bootstrap
   capability exchange).
4. Server returns a Bootstrap interface scoped to the peer's
   identity (an "actor token" — see Capability binding).
5. Client uses the Bootstrap to fetch typed sub-capabilities.
6. Either side may close the connection at any time; the
   server drops outstanding capabilities held by the client.
```

The Bootstrap returned at step 4 is *the* authority delegation
point. A client cannot self-promote. Whatever Bootstrap they
get is the ceiling.

## Capability binding

When a client connects, the server constructs a Bootstrap
capability bound to:

- **Actor**: the kind of caller (system component, app id,
  user, remote pairing)
- **User**: the active user, when applicable
- **Pairing**: the remote pairing id, when applicable
- **Scope**: the scope ceiling for this connection

Every method call through that Bootstrap (and its derived
capabilities) carries this binding implicitly. The capability
gate (`policyd`) consults the binding when checking grants.

A capability handed back to the client (e.g., a
`MemorySearchCap`) is itself bound — narrower than the
Bootstrap. Drop-on-disconnect ensures held capabilities die
when the client disconnects.

## Schema layout

Schemas live in `/usr/share/kiki/capnp/`:

```
common.capnp                 shared types: Time, Bytes, Hash,
                             ActorRef, AuditTag
agentd.capnp                 agentd public bootstrap
policyd.capnp                capability gate, grants
inferenced.capnp             inference engine, model registry
memoryd.capnp                memory layers and search
toolregistry.capnp           tool list, manifest, dispatch
tool.capnp                   the trait every tool implements
audit.capnp                  audit log writers
mailbox.capnp                mailbox messages
focus.capnp                  focusbus contracts (DBus-shaped)
```

Schemas are versioned; see `CAPNP-SCHEMAS.md` for evolution
rules. Daemons load the schema at startup and reject calls
with unknown method ids beyond what their schema knows.

## The bootstrap interface

Each daemon exposes a small Bootstrap interface. Example
(agentd):

```capnp
interface AgentdBootstrap {
  # Get a session for the current actor.
  session @0 () -> (s :Session);

  # Get the audit reader (capability-gated).
  auditReader @1 () -> (r :AuditReader);

  # Subscribe to coordinator events for which the actor
  # has audit.read.
  events @2 () -> (e :EventStream);
}

interface Session {
  send @0 (msg :UserMessage) -> stream (chunk :AssistantChunk);
  cancel @1 () -> ();
  context @2 () -> (ctx :ContextSnapshot);
}
```

Every interface is documented inline in the .capnp file.

## Method conventions

- Methods are named in lowerCamelCase verbs.
- Streaming uses Cap'n Proto's `stream` keyword (server pushes
  chunks; client backpressures by not pumping its end).
- Long-running methods return a "handle" capability that
  exposes `cancel`, `progress`, `await`.
- Idempotency: methods marked `# idempotent` in their schema
  doc-comment must be safely retriable; clients may retry on
  transient errors.
- Errors: the framework's exception channel carries an
  `ErrorPayload` (see `ERROR-MODEL.md`). Schemas do not redefine
  per-method error enums.

## Capability passing

A method may return a capability:

```capnp
interface MemoryRoot {
  episodic @0 () -> (e :EpisodicLayer);
}

interface EpisodicLayer {
  search @0 (q :Query) -> stream (hit :Hit);
  open @1 (id :EpisodeId) -> (ep :EpisodeView);
}
```

A method may take a capability:

```capnp
interface ToolHost {
  install @0 (manifest :ToolManifest, signer :SignerCap) -> ();
}
```

Passing capabilities is how privilege flows in the system.
The arbiter classifier delegates a narrow `ToolDispatchCap`
to a planner subagent; the planner cannot escalate it.

## Promise pipelining

A client can chain calls without waiting for round trips:

```rust
let session = bootstrap.session_request().send().pipeline.get_s();
let chunk_stream = session.send_request(msg).send();
```

Both calls go out together. The agent loop uses this to issue
a model call and a memory write in parallel when they don't
depend on each other.

## Backpressure

Cap'n Proto RPC's `stream` keyword (the new "streaming" RPC
flavor) gives flow-control: the server `await`s its yield;
the client paces its read. We use it for:

- Token streaming from the model
- Audio chunks (control plane only — bulk audio is iceoryx2)
- Memory search results
- Audit log tailing

Non-streaming methods are bounded in their response size by
schema (max field sizes); requests larger than the schema
permits are rejected at decode.

## Concurrency

The server uses a thread-per-core pool with `tokio` and
`capnp-rpc-rs`. Each connection runs on a single executor;
capability calls are serialized per-capability to avoid
within-connection reorderings. Cross-connection concurrency
is unrestricted.

A capability that holds long-lived state (e.g., a
subscription) is `Send + Sync` only when the underlying
state is. Most capabilities are `!Send` and bound to a
single executor task; that's fine because each connection's
work is local.

## Bidirectional RPC

Cap'n Proto RPC is bidirectional. After bootstrap, the server
can call back into capabilities the client provided. We use
this for:

- The mailbox subscriber: client passes a `MessageSink`; the
  server pushes mailbox messages by calling the sink
- Model output streaming: client passes a `ChunkSink`
- Hook callbacks: agentd holds capabilities to client-side
  hook handlers

## Logging and tracing

Each call is logged at trace level with method id, caller,
and a content-addressed digest of arguments (for replay). The
audit log stores only calls that crossed the capability gate
with sensitive capability; trace logs are local-only and
rotated.

## Testing

`capnp-rpc-test` provides an in-process RPC harness without
sockets. Daemons in tests use this. Integration tests use
real sockets in a tmpfs.

## Wire format and codecs

- Cap'n Proto canonical wire format (little-endian)
- No compression (frames are small; bulk data goes via
  iceoryx2)
- Frame size: 1 segment per message recommended; multi-segment
  messages are decoded but a warning is logged

## Versioning

Each schema has a `# version: <semver>` doc comment. Major
bumps require a coordinated daemon update; sysext channels
(see `UPDATE-ORCHESTRATOR.md`) gate this.

A daemon serving an old client is responsible for backwards
compatibility (old method ids continue to work; obsolete ones
are removed only on major bumps with deprecation windows
declared).

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Schema mismatch                  | reject at handshake; client    |
|                                  | gets ProtocolMismatch          |
| Peer cred lookup fails           | refuse connection              |
| Capability-gate denies a call    | exception with                 |
|                                  | PolicyDenied + reason          |
| Stream backpressure exceeded     | server pauses; client must     |
|                                  | drain                          |
| Connection drop mid-call         | outstanding promises rejected; |
|                                  | server drops capabilities      |
| Encoded message exceeds schema   | reject at decode; log; close   |
| max size                         | connection                     |

## Performance contracts

- Bootstrap handshake: <5ms p99 on the local machine
- Request/response (small): <1ms p99
- Streaming first chunk: <5ms p99 after method call
- Capability passing: <100µs added per cap

## Acceptance criteria

- [ ] All five Rust daemons expose Cap'n Proto RPC bootstraps
- [ ] Schemas under `/usr/share/kiki/capnp/` versioned and
      shipped with the OS image
- [ ] Capability binding survives across pipelined calls
- [ ] Drop-on-disconnect verified: holding a cap, killing the
      client, the server tears down associated state
- [ ] Streaming methods backpressure correctly under slow
      consumers
- [ ] Schema-mismatch rejection exercised in tests

## Open questions

None.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/TOOL-DISPATCH.md`
- `05-protocol/CAPNP-SCHEMAS.md`
- `05-protocol/TRANSPORT-UNIX-SOCKET.md`
- `05-protocol/IPC-PATTERNS.md`
- `05-protocol/ERROR-MODEL.md`
- `10-security/CAPABILITY-TAXONOMY.md`
