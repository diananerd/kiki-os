---
id: workspaces
title: Workspaces
type: SPEC
status: draft
version: 0.0.0
implements: [workspaces]
depends_on:
  - shell-overview
  - canvas-model
  - workspace-lifecycle
  - gesture-vocabulary
depended_on_by:
  - task-manager
last_updated: 2026-04-30
---
# Workspaces

## Purpose

Specify the user-facing model for parallel agentic sessions. Each workspace is its own agent session with its own canvas, memory context, and lifecycle (see `WORKSPACE-LIFECYCLE.md` for the runtime side).

## Why workspaces (UX framing)

Without workspaces, a user with three concurrent tasks merges them into one conversation: confusion follows. Workspaces give a clean mental model: each context is its own "thread", switchable, pausable, cancellable.

## States visible to the user

- **Active**: in front of you on the screen
- **Background**: running, not visible
- **Paused**: frozen, low resource use, resumable
- **Hibernated**: persisted, must wake to use
- **Archived**: read-only transcript

Active and Background run; Paused and Hibernated hold; Archived is finished.

## Switcher UX

```
┌──────────────────────────────────┐
│ Workspaces                       │
│                                  │
│ ◉ Trip planner                   │
│ ○ News briefing                   │
│ ○ Email triage   (background)     │
│ ○ Annual report  (hibernated)    │
│                                   │
│ + New workspace                   │
└──────────────────────────────────┘
```

Tap to switch; long-press for properties; "+ New" creates one with an optional template.

Switch latency:

- Active ↔ Background: <100ms (already in memory)
- Hibernated → Active: <2s typical (load context, warm cache)

## Naming

Workspaces auto-name from the first task ("Trip planner"); the user can rename.

## Templates

A "new workspace" can be empty or from a template:

- General agent
- Code workspace (worktree-attached)
- Research (sets defaults for memory, search)
- Voice-only
- Focus (no canvas, voice-only, low chrome)

Templates set initial latches and default policies.

## Capabilities per workspace

A workspace can have a *narrower* capability scope than the user (e.g., a "guest" workspace for a visitor with no email access). Settings exposes this; the agent honors it on every action.

## Resource limits

- Active workspace: full resources
- Background: throttled CPU and tokens
- Paused: zero CPU
- Hibernated: zero RAM
- Archived: read-only

Each workspace has its own loop and cost budgets (see `COST-CONTROL.md`).

## Persistence

A workspace's transcript persists in episodic memory under a dedicated session id. Hibernated workspaces also persist their working memory snapshot (see `WORKSPACE-LIFECYCLE.md`).

## Cross-workspace observability

The user can see all workspaces in the task manager (G3). The agent of one workspace cannot read another's working memory; cross-workspace summaries go through episodic memory and explicit user actions.

## Privacy

A workspace can be marked "private" (locked; passphrase to access). Private workspaces don't appear in the switcher unless unlocked; their transcripts are encrypted at rest with a per-workspace key.

## Voice integration

Voice commands target the active workspace by default. "Switch to news briefing" changes active. "In email triage, ..." targets that workspace without switching.

## Accessibility

- Switcher fully keyboard navigable
- Each workspace name announced with state
- Switching announces a polite live update

## Anti-patterns

- A "shared workspace" across users — confusing privacy model
- Auto-creating workspaces without user action — user loses track
- Pinning many workspaces to Active — defeats the model

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Resume from hibernation fails    | surface error; keep transcript;|
|                                  | offer to start fresh           |
| Workspace limit reached          | suggest archiving oldest       |
|                                  | inactive                       |
| Private workspace passphrase     | timeout; lock; do not reveal   |
| forgotten                        | content                        |

## Acceptance criteria

- [ ] Five user-visible states map to runtime lifecycle
- [ ] Switch latency targets met
- [ ] Templates initialize correctly
- [ ] Per-workspace capability scopes enforced
- [ ] Private workspaces encrypted at rest

## References

- `03-runtime/WORKSPACE-LIFECYCLE.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/TASK-MANAGER.md`
- `07-ui/GESTURE-VOCABULARY.md`
- `11-agentic-engineering/COST-CONTROL.md`
