---
id: error-model
title: Error Model
type: SPEC
status: draft
version: 0.0.0
implements: [error-model]
depends_on:
  - capnp-rpc
  - audit-log
depended_on_by:
  - ipc-patterns
last_updated: 2026-04-30
---
# Error Model

## Purpose

Specify a single, structured error format used across all
Kiki IPC: Cap'n Proto exceptions, NATS error payloads, DBus
errors, and tool dispatch failures. A consistent error model
lets callers — including the agent's planner — react
correctly to retries, fallbacks, and user-visible messages.

## Why a unified model

Mixed error formats lead to mixed handling: planners that
retry policy denials, UIs that show stack traces, telemetry
that can't tally categories. We want:

- A small, fixed set of categories
- A reason code with a stable, documented meaning
- A human-readable message
- Optional structured detail for the category
- Machine-actionable retry semantics

## Inputs

- Any failure path in any daemon, tool, or subsystem
- Optional cause chain (errors caused by errors)

## Outputs

- An `ErrorPayload` carried over the relevant transport
- An audit log entry where the failure crossed the
  capability gate

## ErrorPayload

```capnp
# errors.capnp
struct ErrorPayload {
  category @0 :ErrorCategory;
  code @1 :Text;                       # stable identifier
                                       # e.g., "policy.denied"
  message @2 :Text;                    # short, user-readable
  detail @3 :AnyPointer;               # category-specific
                                       # struct (optional)
  retry @4 :RetrySemantics;
  causedBy @5 :ErrorPayload;           # nested cause (optional)
  traceId @6 :Text;
  source @7 :Text;                     # daemon or tool id
}

enum ErrorCategory {
  policy @0;            # capability gate denied
  resource @1;          # not enough memory, no model, etc.
  network @2;           # network failure
  protocol @3;          # IPC protocol violation
  validation @4;        # bad input
  notFound @5;          # missing resource
  conflict @6;          # state conflict
  cancelled @7;         # caller or system cancelled
  timeout @8;           # exceeded deadline
  internal @9;          # bug or unexpected
  external @10;         # third-party service error
  budget @11;           # cost or rate limit exceeded
}

struct RetrySemantics {
  retryable @0 :Bool;
  retryAfter @1 :UInt32;        # seconds; 0 = immediate ok
  jitterMs @2 :UInt32;
  maxAttempts @3 :UInt8;        # advisory; 0 = unlimited
}
```

## Reason code naming

Codes are dotted, lowercase, snake-or-dot, and stable across
versions:

```
policy.denied
policy.deferred
policy.elevation_required
resource.no_model
resource.no_memory
resource.no_capacity
network.no_route
network.timeout
protocol.schema_mismatch
protocol.bad_message
protocol.bootstrap_failed
validation.bad_argument
validation.missing_field
not_found.resource
not_found.user
not_found.app
conflict.locked
conflict.version
cancelled.by_user
cancelled.by_system
timeout.deadline
internal.bug
external.upstream_error
budget.cost_exhausted
budget.rate_limited
```

The `code` is what callers branch on. The `message` is what
users see. The `detail` is what tools log.

## Mapping per transport

### Cap'n Proto

Errors are returned via the standard exception channel. The
exception's `description` is JSON-encoded `ErrorPayload`:

```
exception {
  type: failed
  description: '{"category":"policy","code":"policy.denied",...}'
}
```

The Rust SDK wraps this into a typed `KikiError` for callers.
The exception type maps as:

| Category   | Capnp exception type |
|------------|----------------------|
| validation | failed                |
| protocol   | failed                |
| not_found  | failed                |
| timeout    | overloaded            |
| resource   | overloaded            |
| budget     | overloaded            |
| policy     | unimplemented (no perm) |
| internal   | failed                |
| external   | failed                |
| cancelled  | failed                |
| network    | overloaded            |
| conflict   | failed                |

### NATS

Error events are published on a topic-mirroring error
subject pattern:

```
audit.error.<source>          ErrorPayload-as-JSON
app.<id>.error.<event>         per-app errors
```

The publisher includes a `kiki-error: 1` header. Consumers
that don't expect errors filter by header.

### DBus

DBus errors map to error names in our error namespace:

```
org.kiki.Error.PolicyDenied
org.kiki.Error.ResourceUnavailable
org.kiki.Error.Validation
org.kiki.Error.NotFound
org.kiki.Error.Timeout
org.kiki.Error.Conflict
org.kiki.Error.Internal
org.kiki.Error.External
```

The error message body carries a JSON-encoded `ErrorPayload`
for full detail.

### iceoryx2

Errors do not flow over iceoryx2 (it is a data plane). A
data-plane fault propagates back as a Cap'n Proto error on
the control connection that owns the iceoryx2 service.

## Retry semantics

Callers consult `retry`:

- `retryable: false` — never retry; surface error.
- `retryable: true, retryAfter=0` — retry immediately, with
  exponential backoff if you hit it again.
- `retryable: true, retryAfter=N` — wait N seconds (plus
  jitter) before retrying.
- `maxAttempts` — soft hint; clients may exceed for
  important calls.

The agent's planner uses these signals to decide whether to
retry, fall back to a different tool, or surface the error
to the user.

## User-visible vs internal

A subset of errors is marked `userFacing` in their detail:

```capnp
struct PolicyDeniedDetail {
  reason @0 :Text;                  # user-readable
  capability @1 :Text;
  actor @2 :Text;
  hint @3 :Text;                    # what user can do
  userFacing @4 :Bool;              # true for prompts
}
```

The mailbox renders `userFacing` errors directly; others
are logged and the user sees a summary.

## Cause chains

`causedBy` lets a higher-level error wrap a lower-level one
without losing context:

```
top: code=tool.dispatch_failed, category=internal,
     causedBy: code=resource.no_memory, category=resource
```

Loggers walk the chain. The agent's planner can pattern-match
on the chain leaf if it cares about a specific root cause.

## Error in audit

Errors that cross the gate are recorded in the audit log:

```json
{
  "category": "ipc_error",
  "event_kind": "error",
  "actor": {...},
  "target": {"capability": "..."},
  "error": { ...ErrorPayload... }
}
```

Errors during tool dispatch are recorded with the tool's
manifest and the actor, so users can review what failed and
why.

## Translating from Rust

Daemons use `thiserror` for ergonomic error types and a
small `Into<ErrorPayload>` impl per crate:

```rust
#[derive(thiserror::Error, Debug)]
enum DispatchError {
    #[error("policy denied: {reason}")]
    PolicyDenied { reason: String, capability: String },
    #[error("no model for capabilities {0}")]
    NoModel(String),
    #[error("internal: {0}")]
    Internal(#[from] anyhow::Error),
}

impl From<DispatchError> for ErrorPayload {
    fn from(e: DispatchError) -> Self { /* maps to category/code */ }
}
```

The Rust SDK exposes `KikiError` with the same shape so
client code uses one type regardless of which daemon
produced the error.

## Anti-patterns

- **Generic "internal error" everywhere.** If you can name
  the failure, name it.
- **Putting user-readable strings in `code`.** Codes are
  identifiers; messages are strings.
- **Cause chains with secrets in them.** Strip auth tokens,
  PII, and other sensitive material before wrapping.
- **Retry-on-anything.** Unrecoverable errors should set
  `retryable: false` so callers don't burn resources.
- **Cross-tool action via error semantics.** If a "missing
  capability" error is supposed to trigger a grant prompt,
  do that explicitly via a `Prompt` decision, not by
  catching errors.

## Translation tables

Common cases for the agent's planner:

| Code                       | Planner behavior                  |
|----------------------------|-----------------------------------|
| policy.denied              | inform user; do not retry         |
| policy.deferred            | wait for prompt; resume on        |
|                            | answer                            |
| resource.no_model          | route fallback per                |
|                            | inference-router                  |
| network.timeout            | retry once with jitter            |
| validation.bad_argument    | do not retry; surface             |
| timeout.deadline           | depends on call site              |
| budget.cost_exhausted      | switch to local; inform user      |
| external.upstream_error    | retry per RetrySemantics; if      |
|                            | exhausted, surface                |

## Acceptance criteria

- [ ] All daemons return `ErrorPayload` for IPC failures
- [ ] Codes are stable; no production code uses
      free-form strings as identifiers
- [ ] Retry semantics honored by clients
- [ ] DBus errors mapped to `org.kiki.Error.*`
- [ ] Audit log records errors with the full payload

## Open questions

None.

## References

- `05-protocol/CAPNP-RPC.md`
- `05-protocol/NATS-BUS.md`
- `05-protocol/DBUS-INTEGRATION.md`
- `05-protocol/IPC-PATTERNS.md`
- `10-security/AUDIT-LOG.md`
