---
id: hooks
title: Hooks
type: SPEC
status: draft
version: 0.0.0
implements: [hook-system]
depends_on:
  - agentd-daemon
  - agent-loop
  - capability-taxonomy
depended_on_by: []
last_updated: 2026-04-30
---
# Hooks

## Purpose

Specify the hook system: registered handlers that fire at defined points in the agent's lifecycle. Hooks are the principal extension mechanism for cross-cutting behavior — content filters, privacy classifiers, audit observers, drift defenses — without modifying core daemons.

## Behavior

### Hook points (18+)

```
BeforeInference            before context goes to model
AfterInference             after model returns, before parsing

BeforeCapabilityCheck      before gate evaluates
AfterCapabilityCheck       after gate decides

BeforeToolCall             before tool dispatch
AfterToolCall              after tool result returns

BeforeMemoryWrite          before memory layer write
AfterMemoryWrite

BeforePushEvent            before push event causes cycle
BeforeUserOutput           before voice/canvas/message emit

OnConnectivityChange       network state transitions
OnIdle                     agent transitions to idle
OnUserSwitch               active user changes
OnPerception               new sensory promotion (filtered)

BeforeIdentityProposal     consent flow pre-check
AfterIdentityChange        consent flow committed
BeforeRetrieval            before memory retrieval query
AfterRetrieval             after retrieval results returned
```

Each point has a defined payload schema.

### Hook modes

```rust
enum HookMode {
    Observe,       // read-only; cannot affect outcome
    Intercept,     // can return Continue or Deny
    Transform,     // can modify the payload
}
```

- **Observe**: telemetry, audit, training data. Cannot block. Failures ignored.
- **Intercept**: policy enforcement. Returns Continue or Deny.
- **Transform**: redaction, normalization, augmentation. Returns modified payload.

### Registration

Apps declare hooks in their Profile:

```yaml
hooks:
  - point: BeforeInference
    mode: Transform
    priority: 50
    timeout_ms: 200
    endpoint: tool://kiki:acme/redactor/redact
    required_capabilities:
      - agent.hook.register
```

Platform hooks register programmatically by `agentd` subsystems (drift checker, audit observer, etc.).

Registration requires `agent.hook.register`. Some points (`BeforeCapabilityCheck`, `OnPerception`) require `agent.hook.intercept` (KikiSigned only).

### Priority bands

```
0-9     platform-critical (cannot be skipped)
10-29   security and privacy
30-69   features
70-89   audit and observe
90-99   training and telemetry
```

Apps cannot register hooks below priority 30 unless KikiSigned. This prevents user-installed apps from positioning themselves before security hooks.

### Execution

```
hooks = registry.hooks_for(point) sorted by priority
payload = original_payload

for hook in hooks:
    result = invoke(hook, payload, timeout = hook.timeout_ms)
    match (hook.mode, result):
        (Observe, _):
            // ignore result
        (Intercept, Ok(Continue)):
            continue
        (Intercept, Ok(Deny(reason))):
            audit_log: hook_denied
            return Denied(hook.id, reason)
        (Intercept, Err(timeout)):
            audit_log: hook_timeout
            // policy: per-hook fail-open or fail-closed
        (Transform, Ok(Modified(new_payload))):
            payload = new_payload
        (Transform, Ok(Unchanged)):
            continue
        (Transform, Err(_)):
            audit_log: hook_failure
            // continue with unchanged payload

return Continue(payload)
```

### Timeouts

| Mode | Default |
|---|---|
| Observe | 100ms |
| Intercept | 200ms |
| Transform | 200ms |

Behavior on timeout:

- Observe: ignored.
- Intercept: fail-open (Continue) by default; critical hooks declare fail-closed.
- Transform: payload unchanged.

A hook that times out repeatedly is auto-disabled with audit entry.

### Hook implementation forms

1. **In-process platform hook**: compiled into agentd or peer daemon. Used for built-in policies (drift checker, audit writer).
2. **Tool hook**: registered by an app; fires by invoking a tool over Cap'n Proto.
3. **Inline expression hook**: small expression evaluated in-process. Used for built-in filters in config.

Tool hooks have higher latency (Cap'n Proto round trip). Critical hooks should be in-process or inline.

### Built-in hooks (cannot be disabled)

- `drift_check` (Intercept on BeforeMemoryWrite for identity layer).
- `audit_observer` (Observe on AfterCapabilityCheck).
- `pii_classifier` (Transform on BeforeUserOutput; flags PII).
- `rate_limit_checker` (Intercept on BeforeToolCall).
- `identity_lock` (Intercept on BeforeMemoryWrite for SOUL/IDENTITY/USER).

Apps can add hooks but cannot disable these.

### Hook composition

- Observe hooks all fire (their results ignored relative to control flow).
- Intercept hooks chain: any Deny stops the chain.
- Transform hooks chain: each sees the previous one's modified output.

Hooks must not assume payload is unchanged since registration; always inspect what's there now.

### Failure isolation

A hook failure (panic, timeout, malformed return) does not crash agentd. Each hook execution is sandboxed within the task runtime; failures are caught, logged, and the loop continues.

A hook with too many failures is auto-disabled and the user is notified.

## Interfaces

### Profile registration

```yaml
hooks:
  - point: BeforeInference
    mode: Transform
    priority: 45
    timeout_ms: 200
    endpoint: tool://kiki:acme/redactor/redact_pii
    description: Redacts SSN-like patterns
```

### Programmatic (in-process)

```rust
agentd.hooks.register(
    point: HookPoint::BeforeInference,
    mode: HookMode::Transform,
    priority: 25,
    handler: Box::new(my_handler),
);
```

### Hook payload schemas

Defined in Cap'n Proto schema files at `/usr/share/kiki/schema/hooks/`.

### CLI

```
agentctl hooks list
agentctl hooks show <hook-id>
agentctl hooks disable <hook-id>     # admin
agentctl hooks recent                 # recent invocations
```

## State

### In-memory

- Registered hook list, sorted by point and priority.
- Per-hook recent invocation metrics.
- Disabled-hook list.

### Persistent

- Hook configurations (in app Profiles + platform defaults).
- Hook telemetry rolling window in DuckDB.

## Failure modes

| Failure | Response |
|---|---|
| Hook panics | catch; log; treat as failure-per-mode |
| Hook timeout | per-mode default |
| Hook returns invalid schema | log; Continue (fail-open) for safety |
| Too many failures | auto-disable; notify user |
| Critical hook missing | refuse to start affected feature |
| Tool hook target unavailable | per-mode default |
| Recursive hook (depth limit hit) | error |

## Performance contracts

- Hook chain at one point: total <500ms typical.
- Per-hook overhead: depends on mode and form (in-process <1ms; tool hook 10–50ms).

## Acceptance criteria

- [ ] All documented hook points fire.
- [ ] Hook priorities honored.
- [ ] Intercept hooks can deny operations.
- [ ] Transform hooks can modify payloads (verified by chain).
- [ ] Observe hooks cannot affect control flow.
- [ ] Hook timeouts behave per mode.
- [ ] Apps cannot register below priority 30 without KikiSigned.
- [ ] Built-in hooks cannot be disabled.
- [ ] Hook failures isolated; agentd does not crash.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/CAPABILITY-GATE.md`
- `04-memory/DRIFT-MITIGATION.md`
- `10-security/CAPABILITY-TAXONOMY.md`
## Graph links

[[AGENTD-DAEMON]]  [[AGENT-LOOP]]  [[CAPABILITY-TAXONOMY]]
