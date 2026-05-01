---
id: consent-flow
title: Consent Flow
type: SPEC
status: draft
version: 0.0.0
implements: [consent-flow]
depends_on:
  - memory-architecture
  - identity-files
  - capability-gate
  - mailbox
  - audit-log
depended_on_by:
  - contradiction-resolution
  - device-provisioning
  - identity-files
  - soul-format
last_updated: 2026-04-30
---
# Consent Flow

## Purpose

Specify the non-bypassable user-confirmation flow that gates identity-class memory writes and other high-stakes changes. Whatever the capability table says, identity changes do not happen without the user reviewing and approving the proposed change in front of them.

## Inputs

- A proposed change (write, supersession, retraction)
- The actor proposing it (agent, hook, app, remote)
- The relevant context (why the change is being proposed)
- The user's current presence (in-front-of-device, via remote, asleep)

## Outputs

- An approved write applied
- A declined attempt logged
- A timeout decision (default Deny) when unanswered
- Audit log entries on every step

## Behavior

### Trigger conditions

The consent flow runs when *any* of:

- Writing to identity files (SOUL.md, IDENTITY.md, USER.md)
- Resolving a high-stakes contradiction in semantic memory
- Granting an `ElevatedConsent` capability
- Approving an app's request for identity-class read
- Reset / erasure operations on memory

These are non-bypassable: the gate alone is insufficient.

### Flow

```
1. The proposer constructs a ChangeProposal:
     - kind ("identity_write", "supersede", "elevate_grant", ...)
     - target (which file / fact / capability)
     - diff (a human-readable representation of what will change)
     - rationale (why; from the agent or app)
     - actor (who is proposing)

2. memoryd hands the proposal to the consent service.

3. The consent service:
     a. Verifies the proposal is well-formed
     b. Checks if a recent confirmation covers this proposal
        (small window for batch operations)
     c. If not covered, queues a mailbox prompt

4. The mailbox renders the prompt:
     +---------------------------------------+
     | Update your preferred name?           |
     |   from: Diana N.                       |
     |   to:   Diana                          |
     | Reason given: friends use just "Diana"|
     |                                       |
     | [Approve]   [Decline]   [Tell me more]|
     +---------------------------------------+

5. The user responds.

6. On Approve: the write is committed; audit logs the approval.
   On Decline: write is not made; audit logs the decline; a
              cool-down prevents nagging.
   On Timeout: default Deny; audit logs the timeout.
```

### Where the prompt lives

The prompt is rendered in the channel most likely to reach the user *in front of the device*:

- Primary on-device UI (launcher, voice)
- If no in-front-of-device user, a paired remote (with reduced trust)
- For very high-stakes (identity reset), in-person required: a paired remote alone is not sufficient

The mailbox knows the user's presence and routes accordingly.

### Out-of-band confirmation

Some changes additionally require an out-of-band step:

- Identity reset: requires a passphrase the user set at provisioning, or a confirmation from an existing high-trust pairing
- Granting a new ElevatedConsent capability: confirmation must come from the device itself, not just from a remote

The pairing scope (see `DEVICE-PAIRING.md` in remotes) declares per-action whether on-device confirmation is required.

### Diff representation

For every proposal, memoryd produces a human-readable diff. Examples:

- File diff (Markdown patch) for IDENTITY.md edits
- Before/after JSON for typed fields
- Worded summary for relations and properties

The user sees the diff plus the rationale; ambiguous proposals are rejected at construction (the agent must produce a clear diff).

### Batching

Some agent operations propose multiple identity changes at once (a "set up your profile" wizard, a major identity reset). The flow supports a single prompt covering N items with per-item approve/decline.

### Cool-down

Declined proposals enter a cool-down per (kind, target):

- Same exact change: 24 hours minimum before re-proposal
- Similar shape: rate-limited to a few per week

The cool-down prevents the agent (or an injection) from nagging the user into approval.

### Audit

Every step is audited:

- Proposal received
- Prompt rendered
- User response (or timeout)
- Final commit (if any)

Audit entries link to the diff and the actor; reviewers can reconstruct exactly what was proposed and decided.

### Programmatic API

```rust
struct Consent {
    fn propose(&self, p: ChangeProposal) -> Result<ProposalId>;
    fn status(&self, id: ProposalId) -> ProposalStatus;
    fn cancel(&self, id: ProposalId) -> Result<()>;
}

enum ProposalStatus {
    Pending,
    Approved(CommitId),
    Declined(Reason),
    TimedOut,
    Cancelled,
}
```

### CLI

```
kiki-consent pending            # list awaiting prompts
kiki-consent show <id>          # see a proposal's diff
kiki-consent approve <id>       # only via UI; CLI is read-only
kiki-consent history --since=7d
```

The CLI is read-only; approval must go through the user-facing channel to ensure the right human is responding.

## Anti-patterns

- **Auto-approving low-risk changes silently.** Even small identity edits warrant a glance.
- **Stacking many proposals on the user without context.** Use batching with clear summary.
- **Allowing remote-only approval for identity reset.** A stolen remote should not be enough.
- **Hidden prompts.** All prompts visible in `kiki-consent pending`.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Mailbox unavailable              | refuse the proposal; alert     |
|                                  | user when reachable            |
| User absent (no presence)        | proposal queued; expires       |
|                                  | per policy                     |
| Diff construction fails          | refuse the proposal; log bug   |
| Concurrent identity edits        | second proposal blocks until   |
|                                  | first resolves                 |
| Audit write fails                | refuse the commit              |

## Performance

- Proposal -> prompt render: <500ms typical
- User response handling: bounded by user
- Commit (post-approval): <100ms

## Acceptance criteria

- [ ] Identity writes go through this flow regardless of capability grants
- [ ] Diffs are rendered for every proposal
- [ ] Out-of-band confirmation is enforced where configured
- [ ] Cool-down prevents nagging
- [ ] Audit log captures the full chain

## References

- `04-memory/IDENTITY-FILES.md`
- `04-memory/MEMORY-FACADE.md`
- `04-memory/CONTRADICTION-RESOLUTION.md`
- `03-runtime/MAILBOX.md`
- `03-runtime/CAPABILITY-GATE.md`
- `10-security/AUDIT-LOG.md`
- `13-remotes/DEVICE-PAIRING.md`
