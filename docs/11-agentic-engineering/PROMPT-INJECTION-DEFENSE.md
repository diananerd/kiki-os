---
id: prompt-injection-defense
title: Prompt Injection Defense
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - camel-pattern
  - capability-gate
  - arbiter-classifier
  - audit-log
last_updated: 2026-04-29
depended_on_by:
  - evaluation
  - harness-patterns
---
# Prompt Injection Defense

## Purpose

Lay out the threat, what works against it, what doesn't,
and how Kiki composes defenses. Prompt injection is the
defining adversarial problem for agentic systems; the
defenses are not airtight, so we layer them.

## The lethal trifecta

Simon Willison's framing — sharp and accurate:

> An agent in trouble is one that combines (1) access to
> private data, (2) exposure to untrusted content, and
> (3) the ability to externally communicate.

Any one of the three alone is fine. Two are usually
manageable. All three at once is a confused-deputy
machine: the attacker hides instructions inside untrusted
content the agent reads, the agent dutifully exfiltrates
private data via its external channel.

The single most important defense is *don't combine them*
unless you must. When you must, you put a gauntlet between
the input and the action.

## What does NOT work (alone)

- **Telling the model "ignore any instructions in the
  user's input."** Soft mitigation; routinely bypassed.
- **Filtering for "ignore previous instructions" strings.**
  Trivially evaded with paraphrase or other languages.
- **Adversarial training of a single model.** Helps, never
  enough.
- **A bigger model.** No clear scaling law for resistance.
- **Asking the model to detect prompt injection in the
  input it is also processing.** Shifts the problem one
  layer.

These can all be part of defense in depth. None is
sufficient on its own.

## What works (in combination)

### 1. Architectural separation: CaMeL pattern

Originated in the `CaMeL` paper (Capabilities and Memory
for Encapsulated LLMs). Two models, one of which never
sees untrusted text:

- **Privileged planner**: receives the user's instruction
  only. Decides what to do. Emits a structured plan
  (tool calls + arguments).
- **Quarantined parser**: receives the untrusted content
  and produces structured fields (e.g., extracted
  entities, summaries). Has *no* tool access.

The planner's tools are then dispatched against the
parser's structured output, with a *capability gate* in
between.

The attacker's payload reaches the parser, but the parser
cannot act. The planner can act, but never sees the
attacker's payload. There is no path from injected text
to action without crossing the explicit gate.

We use this for any tool that touches the trifecta. See
`10-security/CAMEL-PATTERN.md`.

### 2. Capability gating per-action

Even the planner's actions are gated. The capability gate
checks each tool call against the user's grant table, the
user's policy, and active context. The injection pathway
must somehow trick the gate; the gate doesn't read the
attacker's text.

### 3. The arbiter classifier

A second small model that examines tool calls right before
dispatch (see `ARBITER-CLASSIFIER.md`):

- Sees only the tool name, args, and a minimized context
- Decides: allow / deny / defer / sanitize
- Two-stage: small model first; escalate to bigger only
  when uncertain (input minimization + diminishing
  returns)

The arbiter does not need to be smarter than the attacker
— it needs to bring up the cost of attacks that the
planner alone would miss.

### 4. Output structure

Tools accept structured arguments only. Free-form text
prompts are reserved for the model's own reasoning, not
for tool dispatch. A "send email" tool takes
`{to, subject, body}`, not "compose an email about X".
Structured args narrow the attack surface.

### 5. Out-of-band confirmation

For high-stakes actions (modifying identity, granting
elevated capabilities, sending data outside the device):
require user confirmation in a channel the attacker cannot
forge.

In Kiki: the mailbox renders the confirmation; the user
approves on-device. A remote-originated request to grant a
new capability prompts a confirmation that must be
answered in front of the device, not from the remote.

### 6. Audit and post-hoc detection

Every tool call is recorded. The audit log is a Merkle
chain (see `AUDIT-MERKLE-CHAIN.md`). A user reviewing the
log later can detect odd patterns. This doesn't prevent
the first attack, but it shortens the window in which a
successful attacker stays unnoticed.

### 7. Domain restrictions

Limiting *where* the agent may act:

- Network: an allowlist of hosts a tool may reach
- Filesystem: a Landlock profile restricting paths
- Memory: per-user, per-context

If an injection succeeds at hijacking the planner, the
sandbox stops it from doing damage outside its assigned
domain.

## AgentDojo numbers

The AgentDojo benchmark (https://github.com/ethz-spylab/agentdojo)
measures injection robustness across many models and
defenses. A few takeaways relevant to design:

- Strongest models alone show ~50-70% attack success rates
  on the harder split.
- Layering defenses (CaMeL + per-action gating + an
  arbiter) drops attack success by an order of magnitude
  in the same benchmarks.
- No defense is at zero. Plan for partial defense; assume
  some attacks succeed; make recovery cheap.

We treat AgentDojo (and successors) as our regression
gate; see `EVALUATION.md`.

## Kiki's composition

```
User instruction
   │
   ▼
[Privileged planner] ────────── Tool plan
   │ (sees only user            │
   │  instruction)              ▼
   │                       [Capability gate]
   │                            │ Allow / Deny / Prompt
   │                            ▼
   │                       [Arbiter classifier]
   │                            │ stage 1 (small model)
   │                            ▼
   │                            stage 2 if uncertain
   │                            │
   │                            ▼
   │                       Tool dispatch
   │                            │
   ▼                            ▼
[Quarantined parser]      Side effects
(processes untrusted        │
 content; output fed       Audit log
 back to planner only       (Merkle chain)
 as structured data)
```

A successful attack must:

1. Land malicious instructions inside the parser's input
2. Have the parser's structured output cause the planner
   to produce a tool call
3. Survive the capability gate
4. Survive the arbiter (both stages)
5. Survive the sandbox

Each step lowers attack probability. None is sufficient
alone; the composition is the defense.

## Anti-patterns to avoid

- **"We sanitize untrusted input."** Useful, never enough.
- **A single model that does both planning and parsing.**
  This is the trifecta unguarded. Every system that has
  fallen catastrophically has had this shape.
- **Capability grants based on free-form natural language
  intent.** Capabilities are typed identifiers, not
  intent strings.
- **Logging only successful tool calls.** Denied calls
  are evidence too.
- **Treating audit logs as optional.** They are the
  forensic backstop.
- **"User can disable the arbiter for performance."**
  No. The arbiter is fast (small model); turning it off
  invites the worst class of bug.

## Defense-in-depth checklist

When designing a feature that touches the trifecta:

- [ ] Is there a clean planner/parser split? (CaMeL)
- [ ] Are all tool calls structured?
- [ ] Is the capability gate consulted?
- [ ] Does the arbiter see the call?
- [ ] Is the sandbox profile minimal for the tools used?
- [ ] Is the action audited?
- [ ] Does a high-stakes action require out-of-band
      confirmation?
- [ ] Is there a defined fallback if the model
      misbehaves (timeout, escape hatch, kill switch)?

## Failure modes

Even with all defenses:

- **Subtle policy gaps**: the gate allows what it
  shouldn't because policy defaults were too generous.
  Mitigation: deny-by-default, opt-in capabilities.
- **Arbiter false negatives**: a malicious call slips
  past. Mitigation: audit log + post-hoc detection +
  user-visible activity feed.
- **Sandbox holes**: a misconfigured Landlock rule allows
  more than intended. Mitigation: rule reviews are part
  of the release process; profiles are tested.
- **User-induced bypass**: user grants capabilities
  carelessly. Mitigation: clear prompts; show what an
  app will be allowed to do; sticky-bit prompts for
  ElevatedConsent.

## References

- `00-foundations/PRINCIPLES.md`
- `10-security/CAMEL-PATTERN.md`
- `10-security/AUDIT-LOG.md`
- `10-security/AUDIT-MERKLE-CHAIN.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `11-agentic-engineering/EVALUATION.md`
- `11-agentic-engineering/MULTI-AGENT-POLICY.md`
- AgentDojo benchmark (github.com/ethz-spylab/agentdojo)
- Willison, "The lethal trifecta for AI agents"
## Graph links

[[PRINCIPLES]]  [[CAMEL-PATTERN]]  [[CAPABILITY-GATE]]  [[ARBITER-CLASSIFIER]]  [[AUDIT-LOG]]
