---
id: audit-log
title: Audit Log
type: SPEC
status: draft
version: 0.0.0
implements: [audit-log]
depends_on:
  - principles
  - storage-encryption
  - audit-merkle-chain
depended_on_by:
  - audit-merkle-chain
  - capability-gate
  - consent-flow
  - device-pairing
  - episodic-memory
  - error-model
  - identity-files
  - inference-router
  - prompt-injection-defense
  - pruning
last_updated: 2026-04-30
---
# Audit Log

## Purpose

Specify the audit log: what is recorded, where, with what guarantees, and how the user accesses it. The audit log is the device's accountability record: every significant action is logged so the user can review what happened.

## Behavior

### Why an audit log

Without a record, "what did my agent do?" is unanswerable. The audit log:

- Provides the user with full visibility.
- Supports debugging and trust.
- Enables retroactive review.
- Is required for some compliance contexts.

### Storage

Per-user audit log:

```
/var/lib/kiki/users/<user-id>/state.sqlite
   table: audit_log
```

System-level audit log (for cross-user events like updates, provisioning):

```
/var/lib/kiki/system.sqlite
   table: audit_log
```

Both encrypted at rest via LUKS2. Append-only by API contract; deletion requires the audit-maintenance API which itself logs.

### Schema

```sql
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,            -- ULID
    timestamp_ns INTEGER NOT NULL,
    user_id TEXT,                   -- nullable for system events
    workspace_id TEXT,              -- nullable
    category TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    actor JSON,                     -- {kind: app/user/system, id: ...}
    target JSON,                    -- what was affected
    payload JSON,                   -- structured details (NO sensitive content embedded)
    privacy TEXT,                   -- standard|sensitive|public|highly_sensitive
    diagnostic_id TEXT,
    severity TEXT,                  -- debug|info|warn|error|critical
    correlate_with TEXT,
    prev_hash TEXT,                 -- for hash chain
    entry_hash TEXT NOT NULL        -- SHA-256 of canonical entry incl. prev_hash
);

CREATE INDEX idx_audit_ts ON audit_log(timestamp_ns);
CREATE INDEX idx_audit_user ON audit_log(user_id, timestamp_ns);
CREATE INDEX idx_audit_category ON audit_log(user_id, category);
CREATE INDEX idx_audit_correlate ON audit_log(correlate_with);
```

### 18 categories

```
capability_check
capability_grant
capability_revoke
identity_change
consent_proposal
consent_resolution
tool_invocation
hook_decision
inference_request
network_call
memory_write
memory_read
memory_export
ota_event
provisioning_event
app_lifecycle
sandbox_violation
drift_signal
hardware_event
voice_session
```

Each category has documented `event_kind` values.

### Sample entries

```json
{
  "category": "capability_check",
  "event_kind": "grant_existing",
  "actor": {"kind": "app", "id": "kiki:acme/notes"},
  "target": {"kind": "data", "domain": "calendar", "verb": "read"},
  "payload": {"reason": "user-grant"},
  "privacy": "standard",
  "severity": "info"
}
```

```json
{
  "category": "tool_invocation",
  "event_kind": "completed",
  "actor": {"kind": "agent", "user": "user-1"},
  "target": {"tool": "kiki:acme/notes/list", "request_id": "..."},
  "payload": {"latency_ms": 42, "result": "success"},
  "privacy": "standard"
}
```

```json
{
  "category": "identity_change",
  "event_kind": "applied",
  "actor": {"kind": "user", "id": "user-1"},
  "target": {"file": "USER.md", "version_after": 7, "version_before": 6},
  "payload": {"diff_summary_ref": "/var/lib/kiki/.../proposal-id"},
  "privacy": "sensitive"
}
```

### Privacy in audit

Sensitive content is referenced, not embedded:

- `payload` includes references (file path, memory ID), not the content itself.
- The user can follow references; the audit log itself is shareable for diagnostics without leaking.
- For HighlySensitive: even references are redacted (replaced with opaque IDs).

### Append-only enforcement

The writing API:

```rust
pub trait AuditWriter {
    fn append(&self, event: AuditEvent) -> Result<EventId>;
}
```

No `update`, `delete`, or `redact` in the writer. Mutation requires a separate operator-gated API:

```rust
pub trait AuditMaintenance {
    fn rotate(&self);
    fn purge_archive(&self, before: Time);
    fn redact(&self, event_id: &EventId);  // replaces with redacted marker
}
```

User-initiated purges go through this API with audit-log entries recording the deletion itself. The audit log of audit-log changes is preserved.

### Hash chain

Each event includes a chained hash:

```
entry_hash = SHA-256(prev_hash || canonical(entry))
```

Tampering with one event invalidates all subsequent. The device verifies the chain on read.

The full ct-merkle Merkle tree of entries is also maintained; periodic Merkle roots can be submitted to a Sigstore witness for opt-in transparency. See `10-security/AUDIT-MERKLE-CHAIN.md`.

### Writers

Many components write:

- Capability gate (every check, every grant change).
- Consent flow (proposals, resolutions).
- Tool dispatcher (each tool call).
- Memory subsystem (writes, exports, deletions).
- Inference router (each routing decision).
- Network layer (each app's outbound by category).
- Hooks (Intercept-mode decisions).
- Identity files (changes via consent).

Components write asynchronously: events are queued; a writer task batches and persists.

### Real-time subscribers

Subscribers consume events:

- The agent itself (for self-observation).
- The drift monitor (for anomaly detection).
- Diagnostic tools the user runs.

Subscriptions are capability-gated:

```
agent.audit.read         basic read for the user's audit
agent.audit.subscribe    stream subscription
```

### Querying

```
agentctl audit show
agentctl audit show --since=1h
agentctl audit show --category=capability_check
agentctl audit show --app=kiki:acme/notes
agentctl audit search "calendar"
agentctl audit follow                  # tail in real time
```

Output is human-readable by default; `--json` for machine-readable.

### Export

```
agentctl audit export --user=<id> --since=...
                      --format=json|jsonl|csv
                      --output=audit-export.jsonl
```

Exports respect privacy: Sensitive payloads are redacted unless `--include-sensitive` is passed (with a warning).

### Retention

Default retention:

- Current DB: rolling 90 days.
- Archive: 1 year (compressed).
- Older: discarded unless explicitly preserved.

Retention is policy-configurable. Users in regulated contexts may want longer; users wanting minimal retention can shorten.

### Rotation

The active DB is rotated periodically:

- Daily or when size exceeds threshold.
- Old DB moved to archive.
- New DB created with hash chain continuing from previous.
- Cross-DB queries supported.

### Tamper resistance

ct-merkle hash chain detects in-place tampering. For stronger guarantees, periodic Merkle roots are submitted to a Sigstore witness (sigsum) when opt-in.

### What is NOT in the audit

- Full content of Sensitive events (referenced, not embedded).
- Full audio/video.
- Full text of inferences (summary; full content in episodic memory if needed).
- App-internal logging (apps' own logs are separate).

## Interfaces

### Internal

```rust
pub trait AuditLogger {
    fn append(&self, evt: AuditEvent) -> Result<EventId>;
}

pub trait AuditQuery {
    fn search(&self, q: Query) -> Vec<AuditEvent>;
    fn follow(&self) -> impl Stream<Item = AuditEvent>;
    fn verify_chain(&self) -> Result<VerifyReport>;
}
```

### CLI

See "Querying" and "Export" above.

## State

### Persistent

- Current and archive DBs.
- Hash chain heads.
- Submitted Sigstore witness entries (when opted in).

### In-memory

- Async writer queue.
- Recent-events cache for UI.

## Failure modes

| Failure | Response |
|---|---|
| Audit DB corrupt | start in safe mode; alert (CRITICAL) |
| Disk full | refuse new audit writes; refuse capability-gated ops (audit is mandatory) |
| Async writer queue full | back-pressure to caller |
| Hash chain broken | alert (possible tamper); allow reads of unaffected portion |
| Permission denied to write | abort the operation the writer was logging |

The audit log is structurally critical: actions that cannot be logged are refused.

## Performance contracts

- Async append: <100µs into queue.
- Persisted append: <10ms typical.
- Query on indexed field: <50ms.
- Hash chain verification (full): bounded by total events.

## Acceptance criteria

- [ ] Append-only enforced by API surface.
- [ ] All listed categories have writers.
- [ ] Hash chain verifies.
- [ ] User can query, search, export.
- [ ] Sensitive content not embedded.
- [ ] Critical failures (audit DB unavailable) refuse audited operations.
- [ ] Encryption at rest verified.
- [ ] Retention policy honored.

## References

- `10-security/PRIVACY-MODEL.md`
- `10-security/AUDIT-MERKLE-CHAIN.md`
- `10-security/STORAGE-ENCRYPTION.md`
- `10-security/CRYPTOGRAPHY.md`
- `03-runtime/CAPABILITY-GATE.md`
- `04-memory/CONSENT-FLOW.md`
