---
id: working-memory
title: Working Memory
type: SPEC
status: draft
version: 0.0.0
implements: [working-memory]
depends_on:
  - memory-architecture
  - context-engineering
  - agent-loop
depended_on_by:
  - agent-loop
  - compaction
last_updated: 2026-04-30
---
# Working Memory

## Purpose

Specify the in-process active context the agent loop reasons against: latches, recent turns, task state, identity-reserved tokens. The working memory is the "what's happening right now" layer; it bounds what the model sees on each cycle.

## Why a dedicated layer

The agent loop needs fast, structured access to its current context. A direct LanceDB query per turn is overkill; a giant in-memory blob has no structure. Working memory is the typed, partitioned, fast-path representation.

## Design

### Sections

```
[identity]            always-loaded identity facts (~1k tokens)
[latches]             sticky context (current task, deadline, mode)
[turns]               recent conversation turns
[tools]               tool descriptions for the current scope
[scratch]             agent-private notes between tool calls
```

Each section has its own token budget; the total fits within the model's context window minus a safety margin.

### Token budgets

Default for an 8k-context model:

```
identity   1,200 tokens
latches      500
tools      1,500
turns      4,000
scratch      400
margin       400
total      8,000
```

For larger models, the budgets scale; turns scale fastest, tools and identity stay small.

### Storage

Working memory lives in agentd's process memory (Rust structs). A redb-backed snapshot persists across daemon restarts so an interrupted session can resume.

```
/var/lib/kiki/users/<uid>/memory/working/snapshot.redb
```

The snapshot is updated on idle (every 5s typical) — never on the hot path.

### Latches

Latches are key/value-typed sticky state:

```rust
pub enum Latch {
    Task(TaskDescriptor),
    Mode(SessionMode),       // DND, child mode, focus mode
    Deadline(DateTime),
    Location(LocationHint),
    Custom(String, Value),
}
```

Latches are written by the agent loop, hooks, or explicit user commands. They expire by TTL or are explicitly cleared.

### Turns

Each turn is a typed structure:

```rust
struct Turn {
    role: TurnRole,           // User | Assistant | Tool
    content: TurnContent,
    timestamp: DateTime,
    tokens: u32,
    cache_pin: Option<CachePin>,
    audit_id: AuditId,
}
```

Turns are appended; never edited. Compaction (see `COMPACTION.md`) summarizes older turns into earlier sections.

### Identity-reserved tokens

The `identity` section is reserved for the user's identity facts loaded from the identity layer. The working memory never lets the identity section be evicted or compacted. If the budget is tight, the agent loop reduces `turns` first.

### Concurrency

Per-user, per-session working memories are isolated. A workspace (see `WORKSPACE-LIFECYCLE.md`) owns its working memory; switching workspaces swaps the in-process structure.

### Capability scoping

Reads/writes to working memory require `agent.memory.read.working` / `.write.working`. Most components have these; tools generally do not.

### Eviction policy

When budget pressure exceeds threshold:

1. Compact oldest turns into a summary block (tier-3)
2. If still tight, fold tier-3 into tier-4 (single archive summary)
3. Halve `turns` budget for the next cycle (emergency)

Identity, latches, and active task descriptions are never evicted.

## Interfaces

### Programmatic

```rust
struct Working {
    fn snapshot(&self) -> WorkingSnapshot;
    fn append_turn(&mut self, turn: Turn);
    fn set_latch(&mut self, latch: Latch);
    fn clear_latch(&mut self, kind: LatchKind);
    fn compact(&mut self) -> CompactionReport;
}
```

### CLI

```
kiki-memory working show           # the current snapshot
kiki-memory working latch list
kiki-memory working compact        # force a compaction
```

## State

### In-memory

The full working memory.

### Persistent

`snapshot.redb` for resume across restarts.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Budget exceeded                  | compact; if still over, refuse |
|                                  | the turn append                |
| Snapshot read fails on resume    | start fresh; log; user notified|
| Latch type mismatch              | reject set; log; report bug    |

## Performance

- Snapshot size: ~200KB typical
- Append turn: <500µs
- Set latch: <100µs
- Compact: <200ms (fires off-thread)

## Acceptance criteria

- [ ] Working memory stays within budget every cycle
- [ ] Identity section never evicted under pressure
- [ ] Snapshot resume works after daemon restart
- [ ] Multiple workspaces' working memories isolated

## References

- `03-runtime/AGENT-LOOP.md`
- `03-runtime/WORKSPACE-LIFECYCLE.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/COMPACTION.md`
- `04-memory/IDENTITY-FILES.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
