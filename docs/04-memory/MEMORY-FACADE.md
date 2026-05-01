---
id: memory-facade
title: Memory Facade
type: SPEC
status: draft
version: 0.0.0
implements: [memory-facade]
depends_on:
  - memory-architecture
  - capnp-rpc
  - capability-gate
depended_on_by:
  - retrieval
last_updated: 2026-04-30
---
# Memory Facade

## Purpose

Specify the single typed surface the agent loop and tools use to read and write memory. The facade is implemented by the memory daemon (memoryd) and exposed over Cap'n Proto. Behind it are the six layered stores; in front of it is one consistent API.

## Inputs

- Read or write requests with capability binding
- Optional layer hints (which layer to target)
- Optional time filters (valid time, transaction time)

## Outputs

- Typed results per layer
- Audit entries for sensitive operations
- Consent prompts for identity-class writes

## Behavior

### The MemoryStore trait

In Rust, the facade is a trait implemented by `kiki-memory`:

```rust
pub trait MemoryStore: Send + Sync {
    fn working(&self) -> &Working;
    fn episodic(&self) -> &Episodic;
    fn semantic(&self) -> &Semantic;
    fn procedural(&self) -> &Procedural;
    fn identity(&self) -> &Identity;

    fn search(&self, q: &Query) -> Result<RecallSet>;
    fn write(&self, op: &WriteOp) -> Result<WriteAck>;
    fn flush(&self) -> Result<()>;
}
```

Each layer trait is small and focused (see per-layer specs). The top-level `search` and `write` hide layer routing.

### Cap'n Proto interface

```capnp
# memoryd.capnp
interface MemoryRoot {
  working @0 () -> (w :Working);
  episodic @1 () -> (e :Episodic);
  semantic @2 () -> (s :Semantic);
  procedural @3 () -> (p :Procedural);
  identity @4 () -> (i :Identity);

  search @5 (q :Query) -> stream (hit :Hit);
  write @6 (op :WriteOp) -> (ack :WriteAck);
  flush @7 () -> ();
}
```

Each per-layer capability is itself an interface; the gate scopes them.

### Read path

```
agent loop
  └▶ memoryd.search(q)
        ├▶ working   (in-process, no IPC for the calling agent)
        ├▶ identity  (always-loaded, hot)
        ├▶ procedural (small, fast)
        ├▶ semantic  (graph traversal)
        └▶ episodic  (vector + scalar)
       merge, score, dedupe
       return ranked Hit stream
```

Search merges results across layers and returns a ranked stream. The caller can also target a specific layer.

### Write path

```
agent loop / hook
  └▶ memoryd.write(op)
        ├▶ gate (capability check, identity-class flag)
        ├▶ if identity: ConsentFlow → user prompts → commit
        ├▶ otherwise: layer.write
        └▶ audit log entry
```

Writes are gated. Identity writes are *non-bypassable*: they always go through the consent flow regardless of capability grant.

### Capability scoping

A query without `agent.memory.read.episodic` does not search episodic. A query without `agent.memory.read.identity` cannot retrieve identity facts. The capability gate filters at retrieval time, not at the per-layer level — so a malicious tool that bypasses the facade still hits the same gate via the underlying capability.

### Time filters

```capnp
struct TimeFilter {
  validAt @0 :UInt64;       # query the world as of this time
  knownAs @1 :UInt64;       # query our beliefs as of this time
}
```

Bitemporal: `validAt` filters facts by their valid range; `knownAs` filters by transaction time (when we wrote/learned them). Either may be omitted.

### Streaming semantics

`search` is a stream; the caller pulls hits as they arrive. The facade applies global limits (default 50 hits) and per-layer caps (e.g., max 20 from episodic) so a noisy layer can't dominate.

### Caching

A small per-session cache memoizes identical queries within a short window (default 30s). Invalidated on any write to a layer. The cache lives in memoryd, not the agent loop, so multiple callers benefit.

### Backpressure

Writers issue `write` and get an immediate ack with a queued status. Heavy writes (consolidation batches) flow through a separate dispatcher that doesn't block agent-path writes.

### Multi-user

The facade resolves the active user from the connection's ActorRef. Memory is per-user; cross-user reads require an explicit grant and an audit entry.

### Errors

All facade errors use the unified `ErrorPayload` (see `ERROR-MODEL.md`). Common codes:

```
not_found.resource           memory id doesn't exist
policy.denied                gate denied the read/write
conflict.version             concurrent identity change
validation.bad_argument      query shape invalid
internal.bug                 unexpected
```

## Interfaces

### Programmatic (Rust)

```rust
let memory = MemoryClient::connect()?;
let hits: Vec<Hit> = memory.search(&Query {
    text: "trip to Lisbon",
    layers: Layer::Episodic | Layer::Semantic,
    time: None,
    limit: 20,
}).collect();

memory.write(&WriteOp::EpisodeAppend {
    session: current_session(),
    turn: turn,
})?;
```

### CLI

```
kiki-memory search "trip to Lisbon"
kiki-memory write episodic --turn-file=...
kiki-memory dump episodic --since=1d
kiki-memory verify                    # tamper-evidence check
```

### Capabilities consumed

```
agent.memory.read.<layer>
agent.memory.write.<layer>
agent.memory.read.identity            # ElevatedConsent
agent.memory.write.identity           # always consent flow
```

## State

### Persistent

Per-layer; described in their specs.

### In-memory

- The session search cache
- The write dispatcher queue
- Per-connection capability scope

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Layer unavailable                | omit from search; surface in   |
|                                  | result metadata                |
| Write to identity without consent| refuse; log; no partial state  |
| Cache stale across writes        | invalidate; refetch            |
| Concurrent identity change       | conflict.version; user resolves|
| Audit log write fails            | refuse the memory write        |
|                                  | (audit is mandatory)           |

## Performance contracts

- search() across layers (small q): <200ms p99
- write() episodic append: <100ms p99
- write() identity (incl. consent prompt): bounded by user

## Acceptance criteria

- [ ] Single Cap'n Proto interface for all layers
- [ ] Capability gate consulted on every read/write
- [ ] Identity writes always go through consent flow
- [ ] Per-user isolation enforced
- [ ] Errors use the unified ErrorPayload
- [ ] CLI tools work for inspection and debugging

## Open questions

None.

## References

- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/CONSENT-FLOW.md`
- `05-protocol/CAPNP-RPC.md`
- `05-protocol/ERROR-MODEL.md`
- `10-security/CAPABILITY-TAXONOMY.md`
