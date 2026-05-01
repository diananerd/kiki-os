---
id: task-manager
title: Task Manager
type: SPEC
status: draft
version: 0.0.0
implements: [task-manager]
depends_on:
  - canvas-model
  - workspaces
  - workspace-lifecycle
  - cost-control
depended_on_by: []
last_updated: 2026-04-30
---
# Task Manager

## Purpose

Specify the agentic task overlay: a system surface that shows what the agent is doing right now across all workspaces, including in-flight tool calls, subagents, queued work, and cost. Lets the user pause, cancel, or hand off.

## When it appears

- Gesture G3 (4-finger pinch in)
- Slash command `/tasks`
- Status bar long-press on the workspace pill

## Layout

A two-pane inspector:

```
┌─────────────────────┬──────────────────────────────┐
│ Workspaces           │ Active task                   │
│ ▶ Trip planner       │ Plan a 5-day trip to Lisbon  │
│   News briefing       │ ─────────────────────────────│
│   Email triage        │ Cycle 7/25                    │
│                       │ Tools used: 4                 │
│ Background            │ Tokens: 3,200 / 8,000          │
│   Email triage        │ Time: 1m 14s                   │
│   (paused)            │                                │
│                       │ Currently:                     │
│                       │   ↳ web.search "lisbon..."    │
│                       │                                │
│ Hibernated            │ [Pause]  [Cancel]  [Hand off]│
│   Annual report       │                                │
└─────────────────────┴──────────────────────────────┘
```

Left pane: workspaces grouped by state (Active, Background, Hibernated). Right pane: detail for the selected workspace.

## Information shown

Per workspace:

- Title and current task description
- Cycle count vs budget
- Tokens consumed vs budget
- Time elapsed
- The current step (tool call, thinking, idle)
- Attached subagents (with their progress)
- Any pending mailbox prompts

## Actions

- **Pause**: freezes the workspace (cgroup freezer). Active becomes Background or Hibernated.
- **Cancel**: stops the current task; the workspace stays open but idle.
- **Hand off**: surfaces "what would you like me to do next?" without losing context.
- **Resume** (for paused): unfreeze.
- **Archive**: persist transcript; release memory.

These map to operations on the workspace lifecycle (see `WORKSPACE-LIFECYCLE.md`).

## Subagent display

Each running subagent is listed:

```
↳ web.research (3 cycles, 800 tokens)
↳ memory.consolidator (paused)
```

Tapping a subagent surfaces its sidechain transcript.

## Cost roll-up

The task manager shows aggregate cost per period:

```
Today    8,400 tokens    1m 22s active
Week    52,300 tokens   18m active
```

If a workspace is approaching its loop budget or token budget, a warning appears.

## Capability scoping

The task manager reads from agentd via privileged paths:

- `system.read.workspaces`
- `system.read.tasks`

It does *not* expose intermediate model output (that's in the conversation block on the canvas). Subagent transcripts are linked but require an explicit click — they can be long.

## Accessibility

- Keyboard navigable; tab through workspaces
- Each row announces title + state + progress
- Status changes announce politely

## Adaptation

- Reduced motion: no animation on resume
- Battery low: hides cost graphs (still shows numbers)
- Switch access: a labeled list of actions per workspace

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Workspace state stale            | refresh on open; no action     |
|                                  | until consistent               |
| Cancel races with completion     | best-effort; if completed,     |
|                                  | show result                    |
| Hibernated workspace fails to    | error inline; preserve archive |
| resume                           |                                |

## Acceptance criteria

- [ ] Shows all workspaces grouped by state
- [ ] Actions (pause, cancel, hand off, resume) work
- [ ] Cost roll-up updates live
- [ ] Subagent transcripts accessible
- [ ] Keyboard navigable end-to-end

## References

- `07-ui/CANVAS-MODEL.md`
- `07-ui/WORKSPACES.md`
- `03-runtime/WORKSPACE-LIFECYCLE.md`
- `03-runtime/SUBAGENTS.md`
- `03-runtime/LOOP-BUDGET.md`
- `11-agentic-engineering/COST-CONTROL.md`
## Graph links

[[CANVAS-MODEL]]  [[WORKSPACES]]  [[WORKSPACE-LIFECYCLE]]  [[COST-CONTROL]]
