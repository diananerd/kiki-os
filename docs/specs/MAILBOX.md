---
id: mailbox
title: Mailbox
type: SPEC
status: draft
version: 0.0.0
implements: [mailbox-system]
depends_on:
  - agentd-daemon
  - capability-gate
depended_on_by:
  - consent-flow
  - coordinator
  - subagents
last_updated: 2026-04-30
---
# Mailbox

## Purpose

Specify the durable async messaging system used between agentd components and between the system and the user: capability prompts, approval requests, notifications, identity-change consent flow, subagent results.

The mailbox is the channel for "this needs eventual user attention" — distinct from the event bus (in-process, ephemeral) and the audit log (read-only history).

## Behavior

### Message taxonomy

```rust
enum MailboxMessage {
    CapabilityPrompt(CapabilityPromptMessage),
    ApprovalRequest(ApprovalRequestMessage),
    Notification(NotificationMessage),
    SubagentToParent(SubagentMessage),
    SubagentToSubagent(SubagentMessage),
    SystemAlert(SystemAlertMessage),
    IdentityProposal(IdentityProposalMessage),  // for consent flow
}

struct MailboxEnvelope {
    id: MessageId,                  // ULID
    sender: Sender,
    recipient: Recipient,
    payload: MailboxMessage,
    priority: Priority,             // Critical | High | Normal | Low
    created_at: DateTime,
    expires_at: Option<DateTime>,
    requires_response: bool,
    correlation_id: Option<RequestId>,
}
```

### Delivery semantics

At-least-once durable queue:

- Messages survive agentd restart.
- Each has a unique ID.
- Delivered in priority then FIFO order.
- Acknowledged when:
  - User responds (for prompts).
  - User dismisses (for notifications).
  - Recipient processes (for inter-subagent).
  - Timeout expires.

### Storage

SQLite-as-queue (per-user) at `/var/lib/kiki/users/<user-id>/state.sqlite`:

```sql
CREATE TABLE mailbox (
    id TEXT PRIMARY KEY,
    sender JSON,
    recipient JSON,
    priority INTEGER,
    payload BLOB,                   -- MessagePack
    created_at INTEGER,
    deliver_after INTEGER,
    expires_at INTEGER,
    requires_response INTEGER,
    delivered_channels TEXT,
    acked_at INTEGER,
    correlation_id TEXT
);
CREATE INDEX idx_mailbox_priority_ts ON mailbox(priority DESC, created_at ASC);
```

WAL mode with `synchronous=FULL` for durability.

### Capability prompt flow

```
1. Gate decides Prompt; constructs CapabilityPromptMessage; posts to user mailbox; returns Defer to caller.
2. agentui shows prompt: app, capability, optional reason. Buttons: Allow once / Allow always / Deny once / Deny always.
3. User responds; response posted back.
4. Gate receives:
   - Allow always: records grant.
   - Allow once: grants this single check.
   - Deny always: records denial.
   - Deny once: denies this check, no grant change.
5. Mailbox routes resolution to original caller; tool dispatch resumes.
```

### Approval request flow

For risky tool calls:

```
1. Tool dispatch builds ApprovalRequestMessage (what tool, args, impact).
2. Posts to user mailbox; blocks dispatch.
3. agentui shows request with detail.
4. User responds: Approve / Cancel / Modify.
5. Dispatch resumes per response.
```

### Notifications

Non-blocking informational messages:

```
1. Agent emits NotificationMessage.
2. Mailbox enqueues per attention model:
   - User interactive: show now (urgent) or queue.
   - User in DND: queue silently; show summary later.
3. User can dismiss, expand, or act on.
```

### Subagent messaging

Teammates and worktrees use mailbox to communicate with parent:

```
teammate sends MailboxMessage to parent
parent's coordinator picks up
processes (may inject into next inference cycle)
optionally sends back response
```

The mailbox is the persistence backbone: agentd crash mid-conversation between subagents → messages survive, resume on restart.

### Priority and timeouts

| Priority | UI behavior | Default timeout |
|---|---|---|
| Critical | takeover surface; immediate | 24h |
| High | banner; chime if voice on | 12h |
| Normal | quiet badge; visible in mailbox view | 24h |
| Low | mailbox view only | 7d |

On timeout:
- Prompts requiring response: default to safe denial.
- Notifications: silently expire.
- Subagent messages: per subagent policy.

### DND and quiet hours

```toml
[user_attention]
dnd_active = false
quiet_hours = "22:00-07:00"
quiet_hours_breakthrough = "Critical"
notification_throttle = "max 5 / hour"
```

Mailbox respects:
- DND: only Critical messages surface.
- Quiet hours: only configured priority breaks through.
- Throttle: limits per window.

### Multi-channel delivery

User can receive via:

- Native UI (display, voice).
- Messaging bridge (e.g., user's preferred messenger app, when paired).
- Email summary (digest mode for low-priority backlog).

Mailbox routes per channel preference. User configures: "send Critical to messenger; show others on device only."

### Inter-subagent messages

Routing:
- Scope check: sender has relationship with recipient (parent-child or teammates in same task).
- Capability check: sender has `agent.subagent.message_send`.
- Privacy check: cross-user messages denied unless explicitly authorized.

## Interfaces

### Programmatic

```rust
struct Mailbox {
    fn post(&self, env: MailboxEnvelope) -> Result<MessageId>;
    async fn await_response(&self, id: MessageId, timeout: Duration) -> Result<MailboxMessage>;
    fn cancel(&self, id: MessageId) -> Result<()>;
    fn list_pending(&self, recipient: Recipient) -> Vec<MailboxEnvelope>;
    fn resolve(&self, id: MessageId, response: MailboxMessage) -> Result<()>;
    fn purge_history(&self, before: DateTime) -> Result<usize>;
}
```

### CLI

```
agentctl mailbox list <user>
agentctl mailbox show <id>
agentctl mailbox respond <id> "<resp>"
agentctl mailbox history <user>
agentctl mailbox purge <user>
```

### UI integration

The agentui task manager surface lists pending messages. Voice exposes via "Kiki, what do you need from me?"

## State

### Persistent

- Per-user queue and history (SQLite, WAL+FTS5).
- System mailbox (low volume).

### In-memory

- Recent message cache for fast UI rendering.
- Routing tables (channel preferences per user).
- Throttling counters.

## Failure modes

| Failure | Response |
|---|---|
| Queue DB corrupt | rebuild from history; alert; degrade |
| Recipient unreachable | queue; deliver when reachable; per timeout |
| Recipient subagent terminated | deliver to parent as dead-letter |
| Channel down | retry; fall back to next preferred |
| Timeout reached | per message-type policy |
| Disk full | refuse new posts; alert |

## Performance contracts

- Post latency: <10ms typical (SQLite write).
- List pending: <50ms typical.
- Response delivery: <100ms from response to caller resume.
- Storage per message: ~2KB typical, capped 100KB.

## Acceptance criteria

- [ ] Messages survive agentd restart.
- [ ] Capability prompts work end-to-end.
- [ ] Approval requests block dispatch until resolved.
- [ ] DND and quiet hours honored.
- [ ] Multi-channel routing where channels configured.
- [ ] Timeouts default safely (denial for security messages).
- [ ] Subagent messages route correctly.
- [ ] History purge keeps storage bounded.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/TOOL-DISPATCH.md`
- `03-runtime/SUBAGENTS.md`
- `03-runtime/COORDINATOR.md`
- `04-memory/CONSENT-FLOW.md`
- `07-ui/TASK-MANAGER.md`
## Graph links

[[AGENTD-DAEMON]]  [[CAPABILITY-GATE]]
