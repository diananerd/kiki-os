---
id: capability-gate
title: Capability Gate
type: SPEC
status: draft
version: 0.0.0
implements: [capability-gate]
depends_on:
  - agentd-daemon
  - capability-taxonomy
  - audit-log
  - sandbox
depended_on_by:
  - agent-loop
  - ai-gateway
  - app-lifecycle
  - arbiter-classifier
  - browser-engine
  - camel-pattern
  - capability-taxonomy
  - capnp-rpc
  - consent-flow
  - cost-control
  - dbus-integration
  - focusbus
  - hardcoded-restrictions
  - mailbox
  - memory-facade
  - nats-bus
  - procedural-memory
  - prompt-injection-defense
  - speaker-id
  - stt-cloud
  - subagents
  - tool-dispatch
  - tts-cloud
  - voice-pipeline
last_updated: 2026-04-30
---
# Capability Gate

## Purpose

Specify the runtime component inside `policyd` that enforces capability checks on every sensitive operation. The gate is the last defensive layer before action; together with the kernel sandbox, it forms defense in depth.

## Behavior

### Position in the system

```
agent loop / hook / service push
            │
            ▼
   [capability gate]   ← grant table (redb), manifest, policy
            │
        check passes
            │
            ▼
   tool dispatch / inference router / hardware op
```

### Grant table

Maintained in redb (per-user, hot-path KV):

```rust
struct Grant {
    actor: Actor,                  // app id or "system"
    user: Option<UserId>,
    capability: Capability,
    grant_level: GrantLevel,
    granted_at: DateTime,
    granted_by: Granter,
    expires_at: Option<DateTime>,
    constraints: Vec<Constraint>,
}

enum GrantLevel {
    Auto, InstallConsent, RuntimeConsent, ElevatedConsent, Denied,
}
```

Persisted at `/var/lib/kiki/users/<user-id>/caps.redb`.

### Check algorithm

```
check(actor, capability, context) -> Decision:
   // Step 1: hardcoded restrictions
   if capability in HARDCODED_DENIED: return Deny(HardcodedRestriction)

   // Step 2: hardware realizability
   if not hardware_supports(capability): return Deny(HardwareUnavailable)

   // Step 3: user policy
   if user_policy_denies(actor, capability): return Deny(UserPolicy)

   // Step 4: pre-decision hooks
   hooks_decision = run_hooks_for(BeforeCapabilityCheck, actor, capability, context)
   if hooks_decision.is_deny(): return Deny(HookDenied)

   // Step 5: grant lookup
   grant = grant_table.lookup(actor, capability, current_user)

   match grant:
     None: return prompt_or_deny_for_required_level(capability)
     Some(g) if g.is_denied(): return Deny(ExplicitDeny)
     Some(g) if g.is_auto(): decision = Allow
     Some(g) if g.is_install_consent(): decision = Allow
     Some(g) if g.is_runtime_consent():
        if g.scope_covers(context): decision = Allow
        else: decision = Prompt(mailbox_message)
     Some(g) if g.is_elevated_consent():
        if recently_confirmed(g): decision = Allow
        else: decision = Prompt(elevated_mailbox_message)

   // Step 6: arbiter classifier (for borderline cases)
   if needs_arbiter(actor, capability, context):
      decision = arbiter.classify(user_request, tool_call_descriptor)

   // Step 7: constraints
   for constraint in grant.constraints:
      if constraint.violated(context):
         decision = Deny(ConstraintViolated(constraint))

   // Step 8: rate limiting
   if rate_limit_exceeded(actor, capability):
      decision = Deny(RateLimit)

   // Step 9: audit log
   audit.log(actor, capability, context, decision)

   // Step 10: post-decision hooks
   run_hooks_for(AfterCapabilityCheck, decision)

   return decision
```

### Decision values

```rust
enum Decision {
    Allow,
    Deny(Reason),
    Prompt(MailboxMessage),
    Defer(WaitOn),
}
```

- **Allow** — action proceeds.
- **Deny** — blocked; reason returned. **Terminal**: agent receives `{ blocked: true, terminal: true }`. The agent cannot route around (semantic similarity detection blocks similar attempts).
- **Prompt** — mailbox prompt enqueued; caller waits for resolution.
- **Defer** — wait for condition (battery, network return); caller decides to wait or abandon.

### Diminishing returns

```
3 consecutive denials → fall back to human prompt mode for this task.
20 total denials in task → abort task; alert.
```

This prevents agents from being persuaded to retry through different channels.

### Constraints

```toml
[grants."kiki:acme/notes"."network.outbound.host:https://api.example.com"]
grant_level = "InstallConsent"
constraints = [
    { type = "rate_limit", per_hour = 1000 },
    { type = "no_user_data" },
    { type = "time_window", window = "08:00-22:00 local" },
]
```

Violation returns Deny.

### Per-user scoping

Grants:
- **System-wide**: rare; apply to all users.
- **Per-user**: one user's grant doesn't extend to another.
- **Per-context**: for specific tasks/workspaces.

### Revocation

User revokes via Settings or voice. Revocation effective immediately on next call. Sandbox profile may be regenerated. Apps may need to re-prompt; handle gracefully.

### Identity-class capabilities

`agent.memory.write.identity` requires:
- The gate alone is not sufficient.
- Explicit consent flow via mailbox.
- User reviews proposed change.

### CaMeL pattern integration

When the tool's risk_class is `trifecta`, the gate triggers the CaMeL pattern (split planner / quarantined parser). See `10-security/CAMEL-PATTERN.md`.

## Interfaces

### Programmatic

```rust
struct CapabilityGate {
    fn check(&self, actor: Actor, capability: Capability, context: CheckContext) -> Decision;
    fn record_grant(&self, grant: Grant) -> Result<()>;
    fn revoke(&self, actor: Actor, capability: Capability, user: Option<UserId>) -> Result<()>;
    fn list_grants(&self, actor: Option<Actor>, user: Option<UserId>) -> Vec<Grant>;
}
```

### CLI

```
agentctl gate check <actor> <capability>
agentctl gate grants
agentctl gate grants <actor>
agentctl gate revoke <actor> <capability>
agentctl gate audit <since>
```

### User UX

```
+-----------------------------------------+
| kiki:acme/notes wants to:               |
| - Use the microphone (for voice search) |
|                                         |
| [Allow always] [Allow once] [Deny]      |
+-----------------------------------------+
```

## State

### Persistent

- Grant table at /var/lib/kiki/users/<id>/caps.redb.
- User policy at /var/lib/kiki/users/<id>/cap-policy.toml.

### In-memory

- Grant table cache.
- Recent decision cache.
- Rate-limit counters.
- Diminishing-returns counters.

## Failure modes

| Failure | Response |
|---|---|
| Grant table corrupt | refuse all sensitive ops; alert; maintenance mode if persistent |
| Hardware claims capability not realizable | gate denies; coordinator reports as fault |
| Hook timeout | per-mode default policy |
| Mailbox prompt timeout | default to Deny |
| Race during check | snapshot at check start; last write wins |

## Performance contracts

- Check latency: <1ms typical, <5ms p99 (cache hit).
- Check with grant lookup miss: <2ms (redb cold).
- Memory footprint: ~1 MB cache typical.

## Acceptance criteria

- [ ] Every sensitive operation in agentd goes through the gate.
- [ ] Hardcoded restrictions cannot be bypassed.
- [ ] User can revoke any grant; effective immediately.
- [ ] Per-user scoping works.
- [ ] Mailbox prompts block dispatch until resolved.
- [ ] Audit log records every decision.
- [ ] Rate limits enforced.
- [ ] Constraints (host, time, rate) enforced.
- [ ] Diminishing returns falls back to human.
- [ ] Permission denials are terminal.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/TOOL-DISPATCH.md`
- `03-runtime/MAILBOX.md`
- `03-runtime/HOOKS.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/HARDCODED-RESTRICTIONS.md`
- `10-security/AUDIT-LOG.md`
- `10-security/CAMEL-PATTERN.md`
- `04-memory/CONSENT-FLOW.md`
## Graph links

[[AGENTD-DAEMON]]  [[CAPABILITY-TAXONOMY]]  [[AUDIT-LOG]]  [[SANDBOX]]
