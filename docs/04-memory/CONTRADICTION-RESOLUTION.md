---
id: contradiction-resolution
title: Contradiction Resolution
type: SPEC
status: draft
version: 0.0.0
implements: [contradiction-resolution]
depends_on:
  - memory-architecture
  - semantic-graph
  - bitemporal-facts
  - consent-flow
depended_on_by:
  - drift-mitigation
last_updated: 2026-04-30
---
# Contradiction Resolution

## Purpose

Specify how the system detects, classifies, and resolves contradictions between facts in semantic memory: when two beliefs clash, what the agent does, when it asks the user, and how the resolution is recorded.

## Inputs

- Two or more facts whose valid ranges overlap and whose values are incompatible
- Optionally, evidence (the source events that produced each fact)
- The user's policy on auto-resolution

## Outputs

- A resolution: supersession, retraction, or held-as-uncertain
- An audit entry
- Often a user prompt

## Detecting contradictions

Triggers fire on:

- Insert: an `assert` whose value conflicts with an active fact for the same (entity, attribute) and overlapping valid range
- Dreaming sweep (REM phase) over recent windows
- Cross-layer reconciliation (an episodic statement contradicts a semantic fact)

Detection uses:

- Exact value mismatch on the same attribute
- Type-aware comparison (e.g., "Berlin" vs "berlin" vs "BER" — same after normalization; not a contradiction)
- Numeric tolerance (e.g., age 33 vs 32 in adjacent windows requires bitemporal disambiguation, not contradiction)

False positives are expected; the classifier filters them.

## Classifier

A small classifier (Granite Guardian or similar safety/judgment model) decides the resolution path:

```
classify(fact_A, fact_B, evidence) ->
  {
    type: "succession" | "correction" | "ambiguous" | "spurious",
    confidence: f32,
    rationale: text,
  }
```

- **succession**: A was true, then B; auto-supersede A by B if confidence high enough
- **correction**: B is the corrected belief about the same time period; supersede A in transaction time only
- **ambiguous**: cannot tell; surface to user
- **spurious**: false positive (e.g., normalization issue); merge or drop

The classifier emits a structured rationale that goes into the audit log.

## Auto-resolution policy

Auto-resolve only when *all* are true:

- Classifier confidence above threshold (default 0.9)
- Type is `succession` or `spurious`
- The change is not identity-class
- Sources don't conflict (both from the same trusted channel)

Otherwise, surface to user via the consent flow.

## User-facing prompt

When the system can't resolve automatically, the mailbox renders:

```
+--------------------------------------------+
| You said:                                  |
|   "I live in Berlin" — last week           |
| But we have on file:                        |
|   "Lives in Lisbon" — since 2024-06        |
|                                            |
| What's true?                                |
|                                            |
|  [Berlin replaces Lisbon as of 2025-01]    |
|  [Lisbon was wrong — fix it]                |
|  [Berlin was wrong — keep Lisbon]           |
|  [I'll tell you later]                      |
+--------------------------------------------+
```

The user picks; the resolution updates facts via the consent-flow path. "I'll tell you later" lowers confidence on both facts and re-surfaces in a few days.

## Resolution actions

```
succession(old, new) ->
  close(old.known_to)
  insert(new)
  audit("succession", old.id, new.id)

correction(old, new) ->
  close(old.known_to)
  insert(new with valid_from = old.valid_from)
  audit("correction", old.id, new.id)

retract(fact, reason) ->
  close(fact.known_to)
  audit("retract", fact.id, reason)

merge(a, b) ->
  pick canonical
  close the other
  audit("merge", a.id, b.id)
```

All four use the same low-level write primitives in `BITEMPORAL-FACTS.md`.

## Cross-layer reconciliation

Sometimes episodic memory contains a turn ("I just got home in Berlin") that contradicts a semantic fact (`lives_in: Lisbon`). Resolution:

1. The dreaming consolidator detects the cross-layer mismatch
2. Constructs a candidate `correction` (with episodic as evidence)
3. Surfaces to user

The episodic memory is the authoritative *record* (what was said); the semantic graph is the authoritative *summary* (what is). Reconciling the two is a design feature, not a flaw.

## Confidence dynamics

Each contradiction reduces confidence on both facts (for the duration of resolution). Successful resolution restores confidence on the surviving fact. Repeatedly contradicted facts drift down regardless; eventually users will be re-asked.

## Identity-class contradictions

Contradictions in identity files always go through the full consent flow with on-device confirmation. The classifier may pre-assemble the prompt, but the user must approve.

## Capability

The contradiction-resolution machinery runs inside memoryd as part of dreaming and ingest paths. No per-call capability beyond the underlying writes (which already require consent for identity-class).

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Classifier unavailable           | hold contradictions; surface   |
|                                  | next time the classifier is up |
| User declines to resolve         | hold; lower both facts'        |
|                                  | confidence; re-surface later   |
| Repeated identical contradiction | dedupe at proposal time        |
| Resolution writes fail           | abort; preserve both facts;    |
|                                  | audit error                    |

## Performance

- Detection per assert: <5ms
- Classifier call: <500ms (small model)
- Resolution commit: <50ms

## Acceptance criteria

- [ ] Contradictions detected on assert and during dreaming
- [ ] Classifier proposes a resolution path with rationale
- [ ] Auto-resolution honors the policy thresholds
- [ ] User prompts via mailbox + consent flow for ambiguous
- [ ] All resolutions audited
- [ ] Identity-class always asks the user

## References

- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/BITEMPORAL-FACTS.md`
- `04-memory/CONSENT-FLOW.md`
- `04-memory/DREAMING.md`
- `04-memory/DRIFT-MITIGATION.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
