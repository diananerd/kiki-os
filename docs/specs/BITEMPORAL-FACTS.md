---
id: bitemporal-facts
title: Bitemporal Facts
type: SPEC
status: draft
version: 0.0.0
implements: [bitemporal-facts]
depends_on:
  - memory-architecture
  - semantic-graph
depended_on_by:
  - contradiction-resolution
  - drift-mitigation
  - memory-sync
  - semantic-graph
last_updated: 2026-04-30
---
# Bitemporal Facts

## Purpose

Specify the time semantics for facts in semantic memory. The model is bitemporal: every fact has both a *valid time* (when it is true in the world) and a *transaction time* (when we believed it). This matters whenever:

- A fact changes (the user moves, divorces, switches jobs)
- We learn a fact retroactively (we hear about an event after the fact)
- We need to answer "what was true on T?" or "what did we believe on T?"
- We correct a mistaken belief without losing the trail

## Model

```
Fact:
  id              UUID
  entity_id       String
  attribute       (name, value) | (predicate, object)
  valid_from      Timestamp     # may be -infinity
  valid_to        Timestamp     # may be +infinity (open-ended)
  known_from      Timestamp     # transaction time start
  known_to        Timestamp     # transaction time end
                                # (+inf if currently believed)
  confidence      Float in [0,1]
  source          String        # provenance
  audit_id        String        # link to audit log
  supersedes      Option<UUID>  # explicit predecessor
```

A fact is "currently believed and currently true" if `known_to == +inf` and `valid_from <= now <= valid_to`.

## Operations

### Assert

```
assert(entity, attr, value, valid_range, source) =>
  fact_id =
    new fact (
      valid = valid_range,
      known_from = now(),
      known_to = +inf,
      confidence = source.default_confidence,
      ...
    )
  store fact
  audit("fact_asserted", fact_id)
  detect_contradictions(entity, attr, fact_id)
```

The assert is a *new fact*, not an update. We never edit existing facts.

### Supersede

```
supersede(old_fact_id, new_value, valid_range) =>
  close old: known_to = now()
  insert new fact with valid range and supersedes = old_fact_id
  audit("fact_superseded", old_fact_id, new_fact_id)
```

The old fact is *closed* in transaction time (we no longer believe it from now on) but remains queryable historically.

### Retract

```
retract(fact_id, reason) =>
  close: known_to = now()
  audit("fact_retracted", fact_id, reason)
```

A retraction means "we no longer believe this." The fact's valid range is unchanged (it may still have been true once, we just stop asserting it).

### Query

```
query(entity, attr, valid_at?, known_at?) =>
  match facts where:
    fact.entity = entity AND fact.attribute = attr
    AND (valid_at is None OR (fact.valid_from <= valid_at <= fact.valid_to))
    AND (known_at is None OR (fact.known_from <= known_at <= fact.known_to))
```

Common shorthands:

- `query(entity, attr)` — currently believed and currently true
- `query(entity, attr, valid_at=T)` — what is true at T per current beliefs
- `query(entity, attr, known_at=T)` — what we believed at T (about whatever times)

## Worked examples

### Move

```
2024-06-01: assert(user-1, lives_in, "Lisbon",
                   valid=[2024-06-01, +inf])
       known: [2024-06-01, +inf]

2025-09-15: supersede(prev, "Berlin", valid=[2025-09-15, +inf])
   old fact's valid stays [2024-06-01, +inf];
       its known closes at 2025-09-15 — we no longer believe
       it's true from 2025-09-15 onwards.
   new fact: valid=[2025-09-15, +inf], known=[2025-09-15, +inf]
```

Now:

- "where does the user live?" — Berlin
- "where did the user live in July 2025?" — Lisbon
- "what did we believe in July 2025 about where the user lives?" — Lisbon (we hadn't heard about the move yet)
- "what do we now believe about where the user lived in July 2025?" — Lisbon (confirmed by historical fact)

The facts agree because we didn't have to revise valid time, only transaction time.

### Retroactive correction

```
2025-01-10: assert(user-1, age, 32, valid=[2025-01-01, +inf])

2025-02-01: supersede(prev, 33, valid=[2024-12-15, +inf])
   The user's actual birthday was 2024-12-15, not 2025-01-01.
   We close the old record's known at 2025-02-01;
   new fact has valid_from = 2024-12-15 (retroactive) and known_from = 2025-02-01.
```

Now:

- "what is the user's age now?" — 33
- "what did we believe in mid-January?" — 32 (we hadn't corrected yet)
- "what is true (per current belief) in mid-January?" — 33

The first answers historical belief; the second answers historical truth (per current understanding).

## Contradictions

Two facts conflict if their valid ranges overlap and they assert incompatible values for the same (entity, attribute):

```
fact_A: lives_in=Lisbon, valid=[2024-06-01, +inf], known=[2024-06-01, +inf]
fact_B: lives_in=Berlin, valid=[2025-01-01, +inf], known=[2025-09-15, +inf]
```

Both are currently believed (`known_to = +inf`); valid ranges overlap from 2025-01-01.

The system detects this on assert and either:

1. Auto-supersedes if the new fact has higher confidence
2. Surfaces a contradiction to the user via the consent flow (see `CONTRADICTION-RESOLUTION.md`)

## Provenance

Every fact records `source` and `audit_id`. `source` includes:

- `user:<uid>:explicit` — direct user statement
- `tool:<id>` — derived from a tool's output
- `episodic:<session>:summarized` — from session summary
- `dreaming:consolidation` — from background pattern detection

Provenance affects confidence and is shown in UI when relevant.

## Long-running facts

Some facts have no clear `valid_to`. We use `+inf` until evidence ends them. An "ends" event (move, divorce, job change) closes the prior fact and opens a new one.

## Time precision

Timestamps are stored at millisecond precision. Intervals can be finer than the data justifies; the user-facing UI rounds to day or hour as appropriate.

## Time zones

All stored times are UTC. Display rendering uses the user's preferred zone.

## Garbage collection

Closed facts (`known_to < now() - retention_window`) can be GC'd if not linked from audit. By default, retention for closed facts is unlimited unless the user requests pruning.

## Acceptance criteria

- [ ] Assert / supersede / retract behave per the model
- [ ] Time-travel queries are correct on both axes
- [ ] Contradictions are detected on assert
- [ ] Provenance is recorded and queryable
- [ ] Edge cases (`+inf`, retroactive) work in tests

## References

- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/COZODB-INTEGRATION.md`
- `04-memory/CONTRADICTION-RESOLUTION.md`
- `04-memory/DRIFT-MITIGATION.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[SEMANTIC-GRAPH]]
