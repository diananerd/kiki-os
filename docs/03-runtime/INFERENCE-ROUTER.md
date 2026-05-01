---
id: inference-router
title: Inference Router
type: SPEC
status: draft
version: 0.0.0
implements: [inference-router]
depends_on:
  - agentd-daemon
  - model-registry
  - capability-taxonomy
  - audit-log
depended_on_by:
  - agent-loop
  - ai-gateway
  - arbiter-classifier
  - cost-control
  - dreaming
  - inference-engine
  - inference-models
  - privacy-model
  - stt-cloud
  - tts-cloud
  - voice-pipeline
last_updated: 2026-04-30
---
# Inference Router

## Purpose

Specify the component in `inferenced` that decides where each inference request runs (local, remote, or refused), enforces privacy classification, and adapts requests to the chosen model's capabilities.

## Behavior

### Request shape

```rust
struct InferenceRequest {
    prompt: Prompt,
    privacy_level: PrivacyLevel,         // Sensitive | Standard | Public
    latency_budget: LatencyBudget,       // Realtime | Conversational | Background | Whenever
    capabilities_required: ModelCapabilities,
    model_hint: Option<ModelName>,
    cost_limit: Option<CostCap>,
    network_required: bool,
    initiated_by: RequestSource,
    user: Option<UserId>,
    audit_tags: Vec<Tag>,
}
```

### Privacy levels

- **Sensitive** — must run locally.
- **Standard** — prefer local; may go remote if local insufficient and policy allows.
- **Public** — may go remote for quality.

The router never demotes privacy. Sensitive cannot quietly route to remote.

### Latency budgets

- **Realtime** — first token <700ms (voice barge-in).
- **Conversational** — first token <2000ms.
- **Background** — total <30s. Quality prioritized.
- **Whenever** — no deadline. Batch.

### Required capabilities

Bitfield:

```
tool_calling, thinking, vision, audio_input, multi_turn,
context_64k, context_200k, structured_output, streaming
```

### User policy

```toml
[router_policy]
allow_remote = true
allow_third_party_remote = true
default_privacy_level = "standard"
realtime_budget_local_only = false
disable_remote_below_battery_pct = 15
preferred_model = "auto"
disable_third_party_for_voice = true
trace_decisions = false
```

### Decision algorithm (deterministic)

```
decide(request, registry, state, policy) -> Decision:
  candidates = registry.healthy_models()

  // Step 1: privacy
  if privacy == Sensitive:
    candidates = filter(privacy_class == Local)

  // Step 2: capabilities
  candidates = filter(supports_all(capabilities_required))

  // Step 3: user policy
  if not policy.allow_remote: candidates = filter(local)
  if not policy.allow_third_party_remote: candidates = filter(not third_party)
  if state.battery < policy.disable_remote_below_battery_pct: candidates = filter(local)
  if policy.disable_third_party_for_voice and is_voice: candidates = filter(not third_party)

  // Step 4: network
  if request.network_required and not has_network: return Refuse(NoNetwork)
  if not has_network: candidates = filter(local)

  // Step 5: cost cap
  if request.cost_limit: candidates = filter(estimated_cost <= cap)
  if cost_budget_exhausted(user): candidates = filter(local)

  // Step 6: model hint
  if hint and hint in candidates: return Route(hint, adaptations)

  // Step 7: empty?
  if candidates.is_empty(): return Refuse(diagnose())

  // Step 8: rank
  ranked = rank(candidates, request, state)

  // Step 9: pick + adapt
  chosen = ranked[0]
  return Route(chosen, adaptations(chosen, request))
```

### Ranking

When multiple candidates remain, rank by: latency fit, quality, cost, recency (warm models load faster), health. Local always tie-breaks above cloud.

### Adaptations

If chosen model differs in capability from request:

| Request asked | Model has | Adaptation |
|---|---|---|
| `thinking=extended` | `thinking=streaming` | use streaming syntax |
| `tool_calling=native` | `tool_calling=basic` | parse JSON from output |
| `vision` | text-only | use auxiliary vision model first |
| `context_200k` | 64k | prune context aggressively |

Adaptations recorded in audit log.

### Cost accounting

Per-user budget counter:

```rust
struct UserCostBudget {
    period_start: DateTime,
    plan_tokens_in: u64,
    plan_tokens_out: u64,
    consumed_in: u64,
    consumed_out: u64,
}
```

Before routing to paid model, check budget. If exhausted: fall back to local for Standard/Public; refuse for network-required.

Local inference does not consume budget.

### Circuit breaker

When model fails (5xx, timeout, parse error):

- First failure: log, retry once.
- Subsequent within window: mark Degraded.
- Continued failures: mark Unavailable for cool-down.
- Health rechecked after cool-down.

### Refusal reasons

- `NoNetwork`
- `NoCompatibleModel`
- `BudgetExhausted`
- `PolicyForbidden`
- `AllUnavailable`

## Interfaces

### Programmatic

```rust
struct InferenceRouter {
    fn decide(&self, req: &InferenceRequest) -> Decision;
    fn record_outcome(&self, decision: &Decision, outcome: InferenceOutcome);
    fn budget_for(&self, user: UserId) -> CostBudget;
    fn registry(&self) -> &ModelRegistry;
}
```

### Configuration

```
/etc/kiki/inferenced.toml         [router] static
/var/lib/kiki/inferenced-runtime.toml  [router_policy] hot-reloadable
```

### CLI

```
agentctl router status
agentctl router policy
agentctl router budget
agentctl router test <prompt> --priv=sensitive --latency=conv
```

## State

- Model registry (in memory; rebuilt at startup).
- Per-user cost budgets (persisted to SQLite).
- Circuit breaker state (in memory).
- Recent-failures window (in memory).

## Failure modes

| Failure | Response |
|---|---|
| Model load fails | mark Unavailable |
| Network down | local only; refuse if network_required |
| Backend gateway 5xx | retry once; then Degraded |
| Repeated provider errors | circuit-break |
| Cost budget exhausted mid-stream | let stream finish; inform user |
| Policy contradiction | most restrictive wins |

## Performance contracts

- Decision latency: <1ms typical, <5ms p99.
- Negligible overhead vs inference itself.
- Per-request memory: ~2KB.

## Acceptance criteria

- [ ] Sensitive requests cannot reach remote.
- [ ] Voice barge-in routes within Realtime budget.
- [ ] Cost budget exhaustion falls back correctly.
- [ ] User policy honored.
- [ ] Circuit breaker prevents repeated requests to bad provider.
- [ ] All decisions in audit log.
- [ ] CLI test command consistent with live router.
- [ ] Hot-reload of policy applies to next request.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/MODEL-REGISTRY.md`
- `03-runtime/INFERENCE-ENGINE.md`
- `09-backend/AI-GATEWAY.md`
- `10-security/PRIVACY-MODEL.md`
- `10-security/AUDIT-LOG.md`
