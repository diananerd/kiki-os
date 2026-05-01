---
id: arbiter-classifier
title: Arbiter Classifier
type: SPEC
status: draft
version: 0.0.0
implements: [two-stage-arbiter]
depends_on:
  - capability-gate
  - inference-router
  - inference-models
depended_on_by:
  - curated-prompts
  - prompt-injection-defense
last_updated: 2026-04-29
---
# Arbiter Classifier

## Purpose

Specify the two-stage classifier in `policyd` that gates borderline tool calls and other sensitive operations: a fast first-pass model (Prompt Guard 2 86M) plus a deliberative second-pass model (Granite Guardian 3.2 5B), with input minimization and diminishing returns fallback to human prompts.

## Behavior

### Why an arbiter

The static capability gate (grant table) cannot encode every nuance: "is this specific tool call abusive given this specific context?" An ML classifier evaluates that nuance.

But the classifier itself is an LLM. To prevent prompt injection in the agent's reasoning from hijacking the gate, we apply two principles:

1. **Input minimization**: the classifier sees only `(user_prompt, tool_call_descriptor)`. Never the agent's prose.
2. **Two stages**: fast pre-filter rejects obvious cases; only borderline cases hit the deliberative model.

This pattern is informed by Anthropic's `yoloClassifier` from Claude Code (false positive rate 0.4% with two-stage filter).

### Architecture

```
tool_call descriptor (without agent prose)
        │
        ▼
┌──────────────────────────────────────┐
│ Stage 1: Llama Prompt Guard 2 (86M)  │
│ Input: user_prompt + tool_call       │
│ Output: token (allow|deny|escalate)  │
│ Latency: ~10ms                        │
└──────────────────┬───────────────────┘
                   │ if "escalate"
                   ▼
┌──────────────────────────────────────┐
│ Stage 2: Granite Guardian 3.2 5B     │
│ Input: same + structured intent      │
│ Output: CoT reasoning + verdict      │
│ Latency: ~250ms                       │
└──────────────────┬───────────────────┘
                   │
                   ▼
           decision + reason
```

### Input minimization

The classifier receives:

```rust
struct ArbiterInput {
    user_request: String,           // the user's literal request
    tool_call: ToolCallDescriptor,  // tool name + args
    context: BoundedContext,        // workspace_id, sensitivity tier (only)
}
```

It does NOT receive:

- The agent's reasoning prose.
- Other tool call results.
- Memory retrievals.
- Previous turns of the conversation.

This is critical for preventing prompt injection: an attacker who managed to manipulate the agent's reasoning cannot then influence the gate via that reasoning.

### Stage 1: fast pre-filter

Llama Prompt Guard 2 (86M, INT8). Always loaded. Single-token output:

- `allow`: clearly within bounds; gate proceeds with Allow.
- `deny`: clearly out of bounds; gate returns Deny.
- `escalate`: borderline; route to stage 2.

Most tool calls pass through stage 1 with allow/deny. Only ambiguous cases escalate.

### Stage 2: deliberative

Granite Guardian 3.2 5B. Always-loaded. Receives the same input but generates a CoT (chain-of-thought) reasoning followed by a verdict:

- `allow`: the action is acceptable given user intent.
- `deny`: the action is not acceptable; reason given.

The CoT is recorded in the audit log for diagnostics. The verdict is the gate's decision.

### Diminishing returns

The arbiter has a counter per (user, task):

- 3 consecutive deny verdicts in same task: route to human prompt mode for the next call.
- 20 total deny verdicts in same task: abort task; alert user.

This prevents an agent from being persuaded to retry similar denied tool calls through subtle phrasing changes.

### Performance numbers

Anthropic published `yoloClassifier` data for Claude Code:
- 0.4% false positive rate.
- 17% false negative rate.

Kiki's two-stage classifier targets similar performance. Granite Guardian is benchmarked at 0.944 OOD jailbreak recall on standard adversarial datasets (best in class for size).

### When the arbiter is invoked

The capability gate invokes the arbiter when:

- A tool call's descriptor is ambiguous given grants.
- A tool's risk_class is `risky` or higher.
- A pattern matcher flags the call as worth checking.

For Auto-grant capabilities or clearly-static-grant cases, the arbiter is skipped.

### Failure handling

If the arbiter model is unavailable (loading, OOM, error):

- Fall back to human prompt for the call.
- Log; alert.

The arbiter is not allowed to fail-open to Allow.

## Interfaces

### Programmatic

```rust
pub struct Arbiter {
    pub fn classify(&self, input: ArbiterInput) -> ArbiterDecision;
}

pub struct ArbiterDecision {
    pub verdict: Verdict,    // Allow | Deny | EscalateToHuman
    pub reason: String,      // for audit
    pub stage_used: Stage,   // 1 or 2
    pub latency_ms: u32,
}
```

### CLI

```
agentctl arbiter test --request "..." --tool "kiki:acme/notes/create"
agentctl arbiter stats   # FP/FN rates if benchmarked
```

## State

### In-memory

- Loaded models (always-loaded, pinned).
- Per-task denial counters (in coordinator's UserState).

### Persistent

- Audit log entries with classifier decisions.

## Failure modes

| Failure | Response |
|---|---|
| Stage 1 model unavailable | escalate every call to stage 2 |
| Stage 2 model unavailable | route every borderline call to human |
| Classifier returns invalid output | treat as escalate; stage 2 |
| Diminishing returns triggered | human prompt mode |

## Performance contracts

- Stage 1: <10ms.
- Stage 2: <250ms.
- Combined hot path: <20ms (most calls hit stage 1 only).
- Memory: ~3.3 GB (both stages always loaded).

## Acceptance criteria

- [ ] Two-stage filter implemented.
- [ ] Input minimization: classifier sees only `(user_request, tool_call)`.
- [ ] Diminishing returns falls back to human after 3 consecutive denials.
- [ ] CoT reasoning logged to audit.
- [ ] FP rate target <1%; benchmarked.
- [ ] Models always-loaded and pinned.

## References

- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/INFERENCE-MODELS.md`
- `00-foundations/DETERMINISTIC-VS-AGENTIC.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
- `14-rfcs/0040-arbiter-classifier-two-stage.md`
