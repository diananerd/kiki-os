---
id: semantic-graph
title: Semantic Graph
type: SPEC
status: draft
version: 0.0.0
implements: [semantic-graph]
depends_on:
  - memory-architecture
  - cozodb-integration
  - bitemporal-facts
depended_on_by:
  - bitemporal-facts
  - contradiction-resolution
  - cozodb-integration
  - dreaming
  - pruning
  - retrieval
last_updated: 2026-04-30
---
# Semantic Graph

## Purpose

Specify the layer that holds structured facts about entities — people, places, projects, preferences — as a Datalog graph with bitemporal validity. Semantic memory answers "where does the user live?", "what does Maria prefer?", "who is on this project?", and the same questions with a time qualifier.

## Storage

CozoDB. See `COZODB-INTEGRATION.md`.

## Why CozoDB

- Datalog query language: expressive over graph traversal.
- Native `Validity` type for bitemporal facts (valid time + transaction time + supersession).
- Pure Rust embedded library; in-process, no IPC.
- Multiple backend stores; we use the rocksdb backend on disk.

## Conceptual model

Entities have ids and properties. Relationships are edges. Both are facts; both are bitemporal.

```
Entity      (id, kind, name)
Property    (entity_id, name, value, validity)
Relation    (subject, predicate, object, validity)
```

Examples:

```
Entity("user-1", "user", "Diana")
Entity("city-3", "city", "Lisbon")
Property("user-1", "lives_in", "city-3",
         valid=[2024-06-01..now], known=[2024-06-02..now])
Relation("user-1", "knows", "user-7",
         valid=[2025-01-15..now], known=[2025-01-15..now])
```

A property like `lives_in` can be modeled as a Relation if it's an entity link, or as a Property if it's a scalar.

## Bitemporal model

Every fact has:

- **valid_from / valid_to**: the time range during which the fact is true in the world
- **known_from / known_to**: the time range during which we believed it
- **supersedes**: a chain pointer for explicit replacements

See `BITEMPORAL-FACTS.md` for full semantics.

## Schemas (Datalog)

```
:create entity {id: String => kind: String, name: String}

:create property {entity: String, name: String =>
                  value: Json, validity: Validity}

:create relation {subject: String, predicate: String, object: String =>
                  validity: Validity, weight: Float?}
```

Validity is CozoDB's native type:

```
v = #VALIDITY {
  ts: 12345.67,
  retracted: false,
}
```

We extend with our own metadata stored alongside (audit_id, source).

## Sources

Facts come from:

- Episodic summarizer: extracts entities and relations from session summaries
- Explicit user statements: "remember that I prefer X"
- Tool outputs: the calendar tool reports events as relations
- Dreaming consolidation: aggregates patterns into stable facts

Each source records itself; `provenance` queries are first-class.

## Confidence

Each fact carries an optional confidence ∈ [0,1]. Patterns:

- Direct user statement: 1.0
- Repeated implicit pattern: rises with frequency, capped at 0.85
- Single inference from one episode: 0.5
- Conflicting facts: confidence drops; surfaces a contradiction (see `CONTRADICTION-RESOLUTION.md`)

Confidence affects ranking but not visibility; low-confidence facts are still searchable.

## Capability scoping

- `agent.memory.read.semantic`
- `agent.memory.write.semantic`
- `agent.memory.read.identity_facts` — for facts that reach into identity territory (e.g., name, contact info)

The boundary between semantic and identity is by category: factual relationships (Project X has members A, B) are semantic; first-person identity assertions ("I am ...") are identity.

## Read paths

```rust
struct Semantic {
    fn entity(&self, id: &EntityId) -> Result<Entity>;
    fn properties(&self, entity: &EntityId) -> Result<Vec<Property>>;
    fn relations(&self, subject: &EntityId,
                 predicate: Option<&str>) -> Result<Vec<Relation>>;
    fn datalog(&self, query: &str,
               params: &Params) -> Result<RowSet>;
    fn at(&self, valid_at: DateTime, known_at: DateTime)
          -> Result<SemanticView>;
}
```

`datalog` exposes the raw query language for advanced traversal; the typed methods are wrappers around common patterns.

## Write paths

```rust
struct SemanticWriter {
    fn assert_property(&self, entity: &EntityId, name: &str,
                       value: Value, validity: Validity);
    fn assert_relation(&self, subj: &EntityId, pred: &str,
                       obj: &EntityId, validity: Validity);
    fn supersede(&self, fact: &FactId, by: FactCandidate);
    fn retract(&self, fact: &FactId, reason: &str);
}
```

Asserts happen via memoryd's writer task; the agent loop only enqueues. Retractions are recorded; the underlying fact is not deleted (bitemporal: it has a `known_to`).

## Indexes

- B-tree on `entity.id`, `relation.subject`, `relation.object`
- Predicate-grouped indexes for common predicates (`lives_in`, `knows`, `prefers`)
- Free-text index on `entity.name` for lexical lookup
- Per-entity vector embedding (small) for similarity queries

## Sync

Per-user; not synced across users. Cross-device sync is a separate concern (see `09-backend/MEMORY-SYNC.md`).

## Interfaces

### CLI

```
kiki-memory facts list <entity>
kiki-memory facts at <entity> --time=<ts>
kiki-memory facts assert "user-1 lives_in city-3 valid=2025-..."
kiki-memory facts retract <fact-id>
```

### Datalog example

```
?[city, since] := *property{entity: 'user-1', name: 'lives_in',
                            value: city, validity: v},
                   since = ts(v)
```

Returns the cities the user has lived in with the start times.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Conflicting facts                | mark contradiction; surface;   |
|                                  | resolution flow (see           |
|                                  | CONTRADICTION-RESOLUTION.md)   |
| Backend store corrupt            | refuse writes; restore from    |
|                                  | snapshot                       |
| Datalog query error              | return validation.bad_argument |
| Cap exceeded                     | apply pruning; alert           |

## Performance

- Single entity property fetch: <1ms p99
- Datalog traversal (bounded): <20ms p99
- Time-travel view open: <10ms
- Bulk assert (1k facts): <500ms (off the hot path)

## Acceptance criteria

- [ ] Bitemporal queries return correct results across
      `valid_at` and `known_at`
- [ ] Confidence is stored and used in ranking
- [ ] Provenance is queryable
- [ ] Contradictions are detected on assert
- [ ] Per-user partition enforced
- [ ] CLI tools work for inspection

## References

- `04-memory/COZODB-INTEGRATION.md`
- `04-memory/BITEMPORAL-FACTS.md`
- `04-memory/CONTRADICTION-RESOLUTION.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/RETRIEVAL.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[COZODB-INTEGRATION]]  [[BITEMPORAL-FACTS]]
