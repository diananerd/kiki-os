---
id: drift-mitigation
title: Drift Mitigation
type: SPEC
status: draft
version: 0.0.0
implements: [drift-mitigation]
depends_on:
  - memory-architecture
  - bitemporal-facts
  - contradiction-resolution
  - dreaming
depended_on_by:
  - hardcoded-restrictions
last_updated: 2026-04-30
---
# Drift Mitigation

## Purpose

Specify how the system detects and mitigates *drift* — the slow degradation of memory's correspondence to reality. Drift is the silent failure mode of long-lived agents; explicit handling keeps it from becoming gaslighting.

## Four categories of drift

### 1. Stale facts

Facts that were true once but have not been re-confirmed for a long time. The user moved; we never noticed. The user changed jobs; we still call them by the old role.

Signal: time since last confirmation, time since last evidence.

### 2. Mis-extracted facts

Facts the system inferred from a session and got wrong. The user said "I'm thinking about moving to Berlin"; we recorded `lives_in: Berlin`.

Signal: low confidence, lack of corroborating evidence, user corrections nearby in time.

### 3. Identity drift

The agent's view of who the user is starts diverging from who the user is now. Preferences shift, life roles change, language preferences shift.

Signal: friction in interactions, increased corrections, user expressing dissatisfaction.

### 4. Recipe rot

Procedural recipes whose external dependencies have changed. The news-source URL is now 404; the user's preferred coffee maker app has new APIs.

Signal: tool failures during execution, user correcting the recipe inline.

## Signals

The drift detector watches:

- **Recency**: time since fact was last confirmed (referenced or re-stated)
- **Confidence trend**: dropping confidence on a fact across recent sessions
- **Correction frequency**: how often the user is correcting the agent in this domain
- **Tool failure rate**: per-recipe and per-source
- **Cross-layer mismatch**: episodic statements contradicting semantic facts (handled by `CONTRADICTION-RESOLUTION.md`)

Each signal has a per-fact (or per-recipe) score; the cumulative score crosses thresholds.

## Mitigation actions

By severity:

### Mild (drift score low)

- Log; do nothing user-facing
- Slight confidence decrement

### Moderate

- Increment a re-confirmation queue
- On the next plausible interaction, ask: "still living in Berlin?"
- Update confidence based on the answer

### Severe

- Surface a contradiction-style prompt asking the user to confirm
- Mark the fact as "needs re-confirmation"; retrieval still returns but flags the score down

### Identity-class drift

- Always surface to the user via the consent flow
- Propose a "review your profile" action

### Recipe rot

- Flag the recipe in the procedural index
- Suggest the user review or unpublish
- Optionally propose updates if the agent has a credible repair

## Re-confirmation flow

Every few sessions (configurable), the agent gently asks one re-confirmation question:

```
"Quick check — you're still working at Acme, right?"
```

The user answers (or says "ask later"); the system updates accordingly.

This is rate-limited: at most one such question per N sessions to avoid annoyance.

## Confidence decay

Without evidence, confidence decays slowly. Decay is not linear; it's gentler at high confidence, steeper at low:

```
new_confidence = old * exp(-lambda * time_since_evidence)
```

Lambda is tuned per fact-type:

- Identity-class: very slow (years for major decay)
- Lifestyle facts: medium (months)
- Project state: faster (weeks)

Decay never goes below a small floor (we don't forget entirely without explicit action).

## Recovery

When the user corrects a stale fact, we:

- Supersede the old fact (close known_to; insert new)
- Note the correction in audit
- Drop the fact's "needs re-confirmation" flag
- Slightly raise confidence in the source category (the user is engaged here)

## Identity drift specific

A subtle category. We watch for:

- The agent calling the user by a name they no longer prefer
- Preferences ("usually orders the espresso") that the user keeps overriding
- The user explicitly saying "I'm not really like that anymore"

When detected, dreaming surfaces a "review your profile" suggestion. The user can update, archive, or reset.

## Recipe rot specific

When a recipe fails repeatedly:

- Mark with `needs_review: true` in its frontmatter
- On next user invocation of the recipe, surface "this recipe failed N times; review?"
- The agent can also propose a patch (with diff) for the user to accept

## Anti-patterns

- **Auto-supersession without evidence.** Decay is fine; outright replacement requires either user correction or a contradiction resolution.
- **Aggressive re-confirmation.** Asking too often turns the agent annoying.
- **Silent forgetting.** The user should never feel the agent "lost" something without warning.

## Capability

Runs inside memoryd as part of dreaming. No per-call capability; uses the consent flow for identity-class actions.

## Configuration

```toml
[drift]
re_confirmation_min_sessions = 5   # min between re-confirmation questions
identity_decay_half_life_days = 720
lifestyle_decay_half_life_days = 90
project_decay_half_life_days = 30
recipe_rot_threshold_failures = 3
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Decay parameters too aggressive  | user feedback path; tunable    |
| Re-confirmation backlog grows    | rate-limit; pick most-stale    |
|                                  | first                          |
| User dismisses prompts forever   | reduce frequency; surface in   |
|                                  | settings instead               |

## Performance

- Drift sweep over ~10k facts: <30s
- Confidence decay: O(n) over recent facts; cheap

## Acceptance criteria

- [ ] Stale facts get confidence decay
- [ ] Re-confirmation questions are rate-limited
- [ ] Recipe rot is detected and surfaced
- [ ] Identity drift surfaces a profile review
- [ ] Recovery on user correction works
- [ ] All updates audited

## References

- `04-memory/SEMANTIC-GRAPH.md`
- `04-memory/BITEMPORAL-FACTS.md`
- `04-memory/CONTRADICTION-RESOLUTION.md`
- `04-memory/DREAMING.md`
- `04-memory/PROCEDURAL-MEMORY.md`
- `04-memory/CONSENT-FLOW.md`
## Graph links

[[MEMORY-ARCHITECTURE]]  [[BITEMPORAL-FACTS]]  [[CONTRADICTION-RESOLUTION]]  [[DREAMING]]
