---
id: identity-files
title: Identity Files
type: SPEC
status: draft
version: 0.0.0
implements: [identity-files]
depends_on:
  - memory-architecture
  - consent-flow
  - audit-log
depended_on_by:
  - consent-flow
  - device-provisioning
  - hardcoded-restrictions
  - retrieval
  - soul-format
last_updated: 2026-04-30
---
# Identity Files

## Purpose

Specify the layer that holds the user's identity model — who Kiki is to this user, who the user is, what defines the relationship — as a small set of human-editable Markdown files in a per-user git repository, gated by the consent flow.

## Why a separate, special layer

Identity facts are different from semantic facts in stakes. A wrong "lives in Lisbon" is annoying; a wrong "the user prefers to be called X" is corrosive over months. Identity is small enough to put in front of the model on every turn; it deserves a more deliberate write process; and it is exactly the kind of state users want to be able to read, audit, and edit by hand.

We choose a flat-file, version-controlled model so identity is *visible*: the user can `cat` their own SOUL.md, see the history with git log, and edit it.

## Files

```
/var/lib/kiki/users/<uid>/memory/identity/
├── SOUL.md           who Kiki is, in this household, with this user
├── IDENTITY.md       who the user is (name, pronouns, relations, ...)
├── USER.md           preferences, defaults, modes
├── CONSENTS.md       record of what the user has explicitly opted into
├── BOUNDARIES.md     things the user has asked the agent not to do
└── .git/             version control
```

Each file is plain Markdown with optional structured sections (TOML fenced code blocks) for fields the agent reads programmatically.

## Format

A typical IDENTITY.md fragment:

````markdown
# Diana

## Names
- Preferred: Diana
- Full: Diana ...
- Pronouns: she/her

## Birthday
- 1990-04-12

## Languages
- Spanish (native)
- English (fluent)

## Roles
- Software engineer
- Mother of two

```toml
[fields]
preferred_name = "Diana"
pronouns = "she/her"
language_default = "es-ES"
```
````

The TOML block is parsed by the agent for typed fields; the prose is shown to the model as context.

## Editability

Identity files are *intended to be edited by the user*. Three editing paths:

- **In-app editor**: a guided UX in the launcher
- **Text editor**: directly in the file (the daemon watches for changes)
- **Voice**: "Kiki, change my preferred name to ..." → triggers consent flow

Direct edits are reconciled at next read. The consent flow runs in the in-app and voice paths; the text-editor path is treated as the user being explicit (they're literally editing their own files).

## Loading

Identity files are loaded into working memory at session start (the `[identity]` section). They are reloaded on file change (notify watcher). The total budget is small (~1k tokens); files are kept terse.

A larger context model can load more, but the principle stays: identity is what fits comfortably; the rest is semantic.

## Writes via consent flow

All system-initiated writes to identity go through the consent flow:

```
1. Agent proposes a change ("update preferred name to X").
2. memoryd renders the proposed diff.
3. The mailbox prompts the user.
4. On approval: write the file, commit with the user as author.
5. On decline: do nothing; record the decline in audit.
```

See `CONSENT-FLOW.md`.

The capability `agent.memory.write.identity` is *granted but never sufficient* — even with the grant, the consent flow runs. The grant only enables proposing changes.

## Provenance via git

Each commit's author is the user; the committer is the agent (with a clear `Co-Authored-By: Kiki Agent`). The commit message describes the change in plain English. `git log` is a readable diary.

```
commit 8a12...
Author: Diana <diana@example.com>
Date:   2026-03-15

    Updated preferred name from "Diana N." to "Diana"

    Reason given: friends use just "Diana"

    Co-Authored-By: Kiki Agent
```

## Sync

Per-user; identity does not auto-sync across devices. The user can choose to push the repo to a known remote (their own backup or a paired device). Cross-device sync is described separately (see remotes).

## Backup and recovery

The directory is part of btrfs snapshots. Restoring is `git restore` or rolling back the directory.

## Reset

The user can reset identity:

```
kiki-memory identity reset --confirm
```

This archives the current files (rename to `archived/`) and creates fresh ones. Audit log records the reset.

## Capabilities

```
agent.memory.read.identity            ElevatedConsent
agent.memory.write.identity           consent flow always
agent.memory.read.identity.sensitive  RequiresActiveContext
                                      (e.g., for surfaces that need
                                      birthday, address)
```

Most apps cannot read identity directly; they read derived per-app preferences instead.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Identity file parse error        | refuse to start session;       |
|                                  | surface for user fix            |
| git repo corrupt                 | restore from snapshot          |
| Concurrent edit (race)           | git merge with conflict markers|
|                                  | surfaced to user                |
| Consent flow unanswered          | timeout per UX policy; refuse  |
|                                  | the write                      |

## Performance

- Load on session start: <50ms
- File watch latency: <100ms
- Commit + audit: <50ms

## Acceptance criteria

- [ ] Files load into working memory's identity section
- [ ] Consent flow gates all system-initiated writes
- [ ] git history captures every change with the user as author
- [ ] Direct edits propagate via watcher
- [ ] Reset archives prior identity
- [ ] Cross-device sync respects per-user partition

## References

- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/CONSENT-FLOW.md`
- `04-memory/WORKING-MEMORY.md`
- `10-security/AUDIT-LOG.md`
- `10-security/CAPABILITY-TAXONOMY.md`
