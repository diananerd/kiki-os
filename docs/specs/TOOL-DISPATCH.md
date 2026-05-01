---
id: tool-dispatch
title: Tool Dispatch
type: SPEC
status: draft
version: 0.0.0
implements: [tool-dispatcher]
depends_on:
  - agentd-daemon
  - capnp-rpc
  - capability-gate
  - app-runtime-modes
  - sandbox
depended_on_by:
  - agent-loop
  - toolregistry
last_updated: 2026-04-30
---
# Tool Dispatch

## Purpose

Specify how the agent invokes tools provided by apps: tool discovery, registration, dispatch via Cap'n Proto, error handling, timeouts, and the per-call lifecycle.

## Behavior

### Tool catalog

`toolregistry` maintains the catalog at runtime:

```rust
struct ToolDescriptor {
    uri: ToolURI,                    // kiki:<ns>/<name>/<tool>
    app_id: AppId,
    runtime_mode: RuntimeMode,       // CLI tool / headless / interactive ephemeral / interactive service
    required_caps: Vec<Capability>,
    parameters_schema: Schema,
    result_schema: Schema,
    description: String,
    summary: String,                  // for agent context
    risk_class: RiskClass,            // Trivial | Standard | Risky | Critical | Trifecta
    cost_class: CostClass,            // Free | Cheap | Expensive
    expected_latency: LatencyClass,
    side_effects: SideEffectFlags,    // ReadOnly, Destructive, Reversible, External
    timeout_ms: u32,
}
```

### Lazy schema injection

The agent sees only ~8–10 core tools by default + a `tools.search(query)` meta-tool. Full schemas loaded on demand. This prevents context bloat (above ~10 tools, agents lose 2–6× efficiency).

### Discovery and registration

App install:

```
1. Read app's Profile.
2. Extract tool definitions.
3. For each:
   a. Validate schema.
   b. Check required capabilities sensible.
   c. Register in catalog.
4. For service apps:
   a. Reserve a Cap'n Proto connection slot.
   b. Optionally start the service per Profile.
```

Tool URIs are unique. Two apps cannot register tools with the same URI; the second registration is rejected.

### Dispatch lifecycle

```
1. Agent loop emits ToolCall.
2. Resolve tool: catalog lookup.
3. Validate arguments against parameters_schema.
4. Pre-tool-call hooks fire.
5. Capability gate check (each required cap).
6. Risk class handling:
   - Trivial / Standard: dispatch immediately.
   - Risky: post mailbox approval; await user response.
   - Critical: post mailbox approval with elevated UX.
   - Trifecta: route via CaMeL pattern (privileged planner / quarantined parser).
7. Dispatch:
   - CLI tool: spawn transient quadlet container per call.
   - Headless service: send Cap'n Proto via existing socket.
   - Interactive ephemeral: spawn with agentui socket bind.
   - Interactive service: send via persistent socket.
8. Wait for response or timeout.
9. Validate response against result_schema.
10. Post-tool-call hooks fire.
11. Return result to agent loop.
12. Audit log entry.
```

### Risk classes and timeouts

| Risk class | Default timeout | Approval flow |
|---|---|---|
| Trivial | 500ms | none |
| Standard | 5s | none |
| Risky | 10s + approval window | mailbox |
| Critical | 20s + approval window | mailbox elevated |
| Trifecta | per-step | CaMeL planner+parser |
| Long-running | 60s+ (special flag) | progress streaming |

### Long-running tools

Some tools genuinely take time:

```rust
struct LongRunningResult {
    progress: Stream<Progress>,
    final: Future<ToolResult>,
}
```

Agent can show progress via blocks during the wait.

### Parallel dispatch

Model can emit multiple tool calls in one inference:

```
agent emits [call_a, call_b, call_c]
dispatcher dispatches all three concurrently
results return in any order
agent loop waits for all to complete
re-enters inference with all results in context
```

Parallelism cap: 8 per call; per-app rate limit.

### Tool errors

Errors are first-class results:

```rust
enum ToolError {
    CapabilityDenied { capability: Capability },
    SchemaValidationFailed { detail: String },
    Timeout { elapsed_ms: u32 },
    AppCrash { exit_code: i32 },
    AppLogicError { string: String },
    ConnectionLost,
    HookDenied { hook_id: String, reason: String },
    RateLimited,
}
```

The agent receives the error and decides next action.

### Auditing

Every dispatch records:

```json
{"event": "tool_dispatched", "request_id": "...", "user_id": "...",
 "tool": "kiki:acme/notes/list", "app_id": "kiki:acme/notes",
 "caps_checked": ["data.notes.read"], "caps_granted": ["data.notes.read"],
 "risk_class": "Standard", "result": "Success", "duration_ms": 42}
```

Sensitive arguments NOT in audit log; only metadata.

## Interfaces

### Programmatic

```rust
struct ToolDispatcher {
    fn register_tool(&self, app_id: AppId, descriptor: ToolDescriptor) -> Result<()>;
    fn unregister_tool(&self, uri: &ToolURI) -> Result<()>;
    fn list_tools(&self, user: UserId) -> Vec<ToolDescriptor>;
    async fn dispatch(&self, call: ToolCall) -> ToolResult;
}
```

### CLI

```
agentctl tools list
agentctl tools show <uri>
agentctl tools test <uri> <json>
agentctl tools recent
```

## State

### In-memory

- Tool catalog.
- Service connection pool.
- Worker pool for ephemeral dispatches.
- Recent dispatch metrics.

### Persistent

- Per-tool metrics (success/fail rates, latency) in DuckDB.

## Failure modes

| Failure | Response |
|---|---|
| Tool not found | error to agent |
| Schema validation failed | error to agent |
| Capability denied | error; user may be prompted |
| Pre-hook denied | error to agent |
| App ephemeral crash | error to agent; log |
| Service connection drop | retry once; then error |
| Service repeatedly crashes | mark unavailable |
| Tool timeout | error to agent; kill process |
| Result schema invalid | error to agent (app bug); log |
| Mailbox approval denied | error to agent |
| Backend tool unreachable | network error |

## Performance contracts

- Service tool dispatch + result (warm): <50ms.
- Ephemeral tool dispatch + result: 50–500ms (process spawn cost).
- Tool catalog lookup: <10µs.
- Capability check: <2µs (redb).

## Acceptance criteria

- [ ] Tool catalog reflects installed apps; install/uninstall updates atomically.
- [ ] Capability denial returns structured error visible to agent.
- [ ] Mailbox approval blocks dispatch until user response.
- [ ] Parallel dispatch works.
- [ ] Timeouts kill ephemeral processes; service calls canceled.
- [ ] Audit log records every dispatch.
- [ ] Long-running progress events propagate.
- [ ] Trifecta tools route via CaMeL.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/TOOLREGISTRY.md`
- `03-runtime/MAILBOX.md`
- `03-runtime/HOOKS.md`
- `05-protocol/CAPNP-RPC.md`
- `06-sdk/APP-RUNTIME-MODES.md`
- `10-security/CAMEL-PATTERN.md`
## Graph links

[[AGENTD-DAEMON]]  [[CAPNP-RPC]]  [[CAPABILITY-GATE]]  [[APP-RUNTIME-MODES]]  [[SANDBOX]]
