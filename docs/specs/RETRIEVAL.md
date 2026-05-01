---
id: retrieval
title: Retrieval
type: SPEC
status: draft
version: 0.0.0
implements: [retrieval]
depends_on:
  - memory-architecture
  - memory-facade
  - episodic-memory
  - semantic-graph
  - procedural-memory
  - identity-files
depended_on_by: []
last_updated: 2026-04-30
---
# Retrieval

## Purpose

Specify the cross-layer search strategy: hybrid vector + structured filters, layer routing, ranking, deduplication, recall over precision. Retrieval is what makes the layered memory feel like one memory.

## Inputs

- A query (text + optional structured fields)
- Layer hints (which layers to consult)
- Time filters (valid_at, known_at)
- Capability binding (what the actor is allowed to read)
- Top-K

## Outputs

- A ranked, deduplicated stream of `Hit` records
- Per-hit metadata (layer, score, provenance)

## Algorithm

```
search(q):
  candidates = []

  for layer in q.layers:
    if not capability.allows_read(layer): continue

    layer_hits = layer.search(q, top_k=q.top_k * layer.factor)
    for hit in layer_hits:
      candidates.append((layer, hit))

  candidates = dedupe(candidates, strategy=q.dedupe)

  ranked = rank(candidates, q)
  return ranked[:q.top_k]
```

The simplest description hides several decisions; the rest of this doc fleshes them out.

## Layer routing

Default order (highest priority first):

1. **Working memory** — instant, always considered
2. **Identity files** — small, always loaded
3. **Procedural** — recipe match (trigger + semantic)
4. **Semantic graph** — entity facts
5. **Episodic** — past turns and summaries

A query can hint specific layers; absent hints, the router consults all five and merges.

## Hybrid search per layer

### Episodic

- Vector similarity (bge-m3) over `embedding`
- Scalar filter (session, time range, redacted)
- Optional time-travel via LanceDB version

Example: `search("trip Lisbon", time={valid_at: 2025-09})` searches episodes embedded near "trip Lisbon" within the time window.

### Semantic

- Datalog query over `entity`, `property`, `relation`
- Or vector similarity on `entity_embedding` for entity disambiguation

Example: "where does the user live?" → resolve `user-1`, fetch `lives_in` property at current valid time.

### Procedural

- Trigger match (intent / phrase)
- Vector similarity over recipe descriptions

Example: "make me coffee" → match on phrase, then load the recipe into working memory.

### Identity

- Direct file read; no search needed (small enough to keep loaded)

### Working

- In-process scan of recent turns and latches; vectorize on demand if budget permits

## Deduplication

Same fact can appear across layers (e.g., the user's name in identity and as a semantic property). Dedupe strategies:

- **id-based**: same entity_id + attribute
- **content-based**: high similarity score (cosine > 0.95)
- **layer-priority**: identity > semantic > episodic > procedural > working for the same fact

The default is layer-priority with content-based fallback.

## Ranking

Score = layer_weight × layer_score × confidence × time_decay

- `layer_weight`: identity 1.0, working 0.95, semantic 0.9, procedural 0.85, episodic 0.8 (illustrative)
- `layer_score`: per-layer relevance (vector similarity, lexical match)
- `confidence`: from semantic facts; 1.0 elsewhere
- `time_decay`: gentle decay for older episodic hits; none for facts

These weights are tunable; we err on the side of recall over precision.

## Recall over precision

For an agent, missing a relevant fact is usually worse than including a marginally relevant one. The model can ignore noise; it cannot recover from absence. So we:

- Use larger top-K than strictly needed
- Include semantic neighbors in graph traversal
- Prefer broader queries over narrow ones when the budget allows

The agent loop trims further if context budget is tight.

## Time filters

```rust
struct Query {
    text: String,
    layers: LayerSet,
    time: Option<TimeFilter>,
    confidence_floor: Option<f32>,
    top_k: usize,
}
```

Time filters apply differently per layer:

- Episodic: time range filters `timestamp`; optional time-travel via version
- Semantic: bitemporal `valid_at` / `known_at`
- Procedural / identity / working: ignored

## Provenance in results

Each `Hit` carries:

```rust
struct Hit {
    layer: Layer,
    id: String,
    content: String,
    score: f32,
    confidence: f32,
    valid_range: Option<TimeRange>,
    known_range: Option<TimeRange>,
    source: Provenance,
    audit_id: AuditId,
}
```

Callers can decide to surface provenance to the user (e.g., "you said this on Tuesday").

## Capability filtering

Layers a caller can't read are silently omitted. The result includes a flag if any layer was filtered, so the agent can ask the user for a grant if it suspects key info was dropped.

## Caching

A per-session query cache (memoized by query hash) skips repeated identical retrievals within a short window. Invalidated on writes to any consulted layer.

## Streaming

`search()` returns a stream; the agent loop can begin reasoning before the last hit lands. Useful for interactive UIs.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Layer unavailable                | omit; flag in result           |
| Vector index rebuilding          | scalar fallback                |
| Query timeout                    | return partial results with    |
|                                  | a `partial=true` flag          |
| All layers denied                | empty result; surface as       |
|                                  | "no readable memory" error     |

## Performance

- Aggregate retrieval p99: <200ms
- Vector index hit (per layer): <50ms
- Datalog graph traversal: <20ms
- Working / identity: <5ms

## Acceptance criteria

- [ ] Hybrid search returns merged ranked results
- [ ] Capability filtering omits forbidden layers
- [ ] Time filters apply correctly per layer
- [ ] Streaming yields hits as they arrive
- [ ] Provenance is included in each hit
- [ ] Cache invalidation on writes works

## References

- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/MEMORY-FACADE.md`
- `04-memory/EPISODIC-MEMORY.md`
- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/PROCEDURAL-MEMORY.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
