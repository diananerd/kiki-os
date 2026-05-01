---
id: dreaming
title: Dreaming
type: SPEC
status: draft
version: 0.0.0
implements: [dreaming]
depends_on:
  - memory-architecture
  - episodic-memory
  - semantic-graph
  - procedural-memory
  - inference-router
depended_on_by:
  - drift-mitigation
last_updated: 2026-04-30
---
# Dreaming

## Purpose

Specify the background consolidation phases that turn raw episodic activity into long-term knowledge: pattern extraction, fact updates, recipe proposals, contradiction surfacing. Dreaming runs when the device is idle and on AC power; it is never on the agent's hot path.

## Why dreaming

A live agent on the hot path doesn't have time to:

- Re-read past sessions and notice patterns
- Update beliefs that turned out to be wrong
- Discover that a sequence of actions is becoming a habit (and could be a recipe)
- Compress redundant facts

Doing it overnight (or whenever the device is idle) makes the next day's agent smarter without slowing today's.

The biological analogy is loose; we use it because it captures the rhythm: the agent is awake during the day, doing things, and dreams about them later.

## Phases

### LIGHT

Fast, frequent (every ~30 minutes when idle).

- Promotes recent episodic content into semantic facts where the extraction is high-confidence
- Updates entity embeddings as new evidence arrives
- Refreshes procedural recipe rankings based on use

Cost: small. Runs even on battery if not foreground.

### REM

Medium, less frequent (every few hours; nightly typical).

- Looks for behavioral patterns: "user has asked for the news every morning at 8am for 14 days" → propose a recipe
- Detects contradictions across episodic and semantic layers; surfaces unresolved ones to the user
- Promotes recurring summaries up the tier ladder (T2 → T3 → T4) for older sessions
- Re-embeds rows that lag behind the active embedder version

Cost: moderate. AC power preferred.

### DEEP

Slow, infrequent (weekly or on user-request).

- Whole-corpus consolidation: cluster recurring topics, build summary entities ("Project X" with members, history, decisions)
- Drift mitigation pass: identify stale facts, reduce confidence, mark for re-confirmation
- Procedural memory housekeeping: deduplicate near-identical recipes, suggest merges
- Audit log cross-check: reconcile episodic content with audit Merkle chain

Cost: high. Only on AC power; user notified.

## Triggering

Dreaming runs are scheduled by agentd's coordinator:

- LIGHT: when the agent loop has been idle for >5 minutes and battery > 30%
- REM: between 02:00 and 05:00 local, AC power, system idle
- DEEP: weekly or on `kiki-memory dream deep`, AC power required

A user can pause dreaming entirely (Settings → Memory → Dreaming).

## Capability scoping

Dreaming runs as a privileged in-process task in memoryd; no per-call gate (it doesn't touch external resources directly). Writes it produces still go through normal write paths and are audited. Identity-class proposals always go through the consent flow.

## Inputs

- Episodic memory (full read)
- Semantic graph (read + write)
- Procedural memory (read + propose write)
- Working memory snapshots (read for trends)
- Audit log (read for cross-check)

## Outputs

- New semantic facts (asserted via the writer)
- Supersessions when evidence supports them
- Recipe proposals queued for user approval
- Contradiction events queued for resolution
- Updated embeddings, indexes, and tier summaries
- A "dream report" the user can view

## Recipe proposal

When REM detects a recurring pattern:

```
1. Cluster sessions where the user-input + agent-action sequence
   looks similar.
2. If support >= threshold (e.g., 5 occurrences over 14 days),
   construct a draft recipe (template + parameters).
3. Submit as a proposal to the user via the mailbox.
4. On approval: write to procedural/.
5. On decline: log and avoid re-proposing the same shape for a
   cool-down period.
```

Recipes are not auto-installed.

## Contradiction surfacing

REM scans for facts whose valid ranges overlap with conflicting values:

```
fact_A: lives_in=Lisbon, valid=[2024-06, +inf]
fact_B: lives_in=Berlin, valid=[2025-01, +inf]
both currently believed
```

The contradiction is surfaced via the consent flow with options:

- "Berlin replaces Lisbon as of 2025-01" (supersede)
- "Lisbon was wrong" (retract A)
- "Berlin was wrong" (retract B)
- "Don't know yet" (lower confidence on both, ask later)

See `CONTRADICTION-RESOLUTION.md`.

## Drift handling

DEEP looks at facts that have not been re-confirmed in N sessions:

- Reduce confidence by a small step
- If confidence drops below threshold and the fact is high-stakes (identity-class), surface for re-confirmation

See `DRIFT-MITIGATION.md`.

## Reports

After each REM and DEEP run, memoryd writes a report:

```
/var/lib/kiki/users/<uid>/memory/dreams/<timestamp>.md
```

The report summarizes what was done, what was proposed, and what was surfaced. The user can review.

## Observability

```
kiki-memory dream status                # current phase / next scheduled
kiki-memory dream history               # recent dreams
kiki-memory dream report <id>            # show a report
kiki-memory dream now --phase=light      # ad-hoc trigger (for debugging)
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Out of budget mid-run            | pause; resume on next window   |
| Pattern false positive           | user declines; cool-down       |
| DEEP run interrupted             | partial state preserved;       |
|                                  | resumed next time              |
| Embedding model unavailable      | skip re-embed for this run;    |
|                                  | retry next                     |

## Performance

- LIGHT: <2 minutes typical
- REM: <30 minutes typical (varies with corpus)
- DEEP: bounded; can be split across nights

## Acceptance criteria

- [ ] LIGHT/REM/DEEP run on the configured cadence
- [ ] Recipe proposals reach the mailbox
- [ ] Contradictions surface via consent flow
- [ ] Drift confidence updates apply
- [ ] Reports are generated and readable
- [ ] User can pause dreaming entirely

## References

- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/EPISODIC-MEMORY.md`
- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/PROCEDURAL-MEMORY.md`
- `04-memory/CONTRADICTION-RESOLUTION.md`
- `04-memory/DRIFT-MITIGATION.md`
- `04-memory/CONSENT-FLOW.md`
- `03-runtime/MAILBOX.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[EPISODIC-MEMORY]]  [[SEMANTIC-GRAPH]]  [[PROCEDURAL-MEMORY]]  [[INFERENCE-ROUTER]]
