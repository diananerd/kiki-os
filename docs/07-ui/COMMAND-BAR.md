---
id: command-bar
title: Command Bar
type: SPEC
status: draft
version: 0.0.0
implements: [command-bar]
depends_on:
  - shell-overview
  - canvas-model
  - gesture-vocabulary
  - input-pipeline
depended_on_by: []
last_updated: 2026-04-30
---
# Command Bar

## Purpose

Specify the contextually-visible command bar — Kiki's universal entry point for typed commands, voice prompts, slash commands, and quick actions. The command bar is the primary fast path for users who don't want to navigate the canvas.

## When it appears

The command bar pops as a transient overlay on:

- Summon gesture (G1)
- The agent inviting input ("what would you like to do?")
- App or system requesting input

It auto-dismisses on:

- Esc / Back gesture
- Selecting an action
- Tapping outside (configurable; default on)

## Layout

A horizontally-centered overlay near the top of the content region:

```
┌────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────┐ │
│  │  ▶  ___                                  │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  Suggestions                                   │
│  • Plan a trip to Lisbon                       │
│  • Set reminder for 3pm                        │
│  • What's the news?                            │
└────────────────────────────────────────────────┘
```

The input field grows as the user types; suggestions update live.

## Inputs

- Free text (interpreted by the agent)
- Slash commands (typed identifiers; `/skill`, `/workspace`, `/find`)
- Voice (transcript pipes into the field)
- Paste

## Slash commands

A small built-in set:

```
/skill <name>            invoke a skill
/workspace <name>        switch / create
/find <query>            full-text find across canvas + memory
/settings                open settings
/help                    open help
/audit                   open audit viewer
/restart                 restart the active workspace
```

Apps may register slash commands with their manifest (subject to capability).

## Suggestions

The command bar surfaces:

- Recent commands
- Slash command completions
- Skill triggers matching the input
- Search results from procedural memory
- Voice transcript suggestions

Suggestions are ranked; top 5 shown by default.

## Voice integration

When voice mode is active, the command bar shows the live transcript instead of waiting for finalization. The user can tap "send" or speak "execute" to dispatch.

## Capability scoping

The command bar runs in agentui's process; it can dispatch only what the agent loop permits. Capability checks happen at dispatch time, not display time, so the user sees suggestions but a denied action surfaces a clear error.

## Adaptation

- Reduced motion: no slide-in
- Large text: input field height scales
- Switch access: a labeled menu of commands replaces free-form input

## Accessibility

- Default focus on the input field on appear
- Suggestions navigable via Up/Down arrows
- Each suggestion has a label and (where relevant) a hint announced by screen readers

## Persistence

The command bar's recent-commands list is per-user, persisted at:

```
/var/lib/kiki/users/<uid>/ui/command-history.json
```

Bounded (default 200 entries); older drop.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Suggestion source slow           | show partial; no blocking      |
| Slash command unknown            | render error inline; do not    |
|                                  | dispatch                       |
| Capability denied                | show error in result area      |
| Voice transcript stale           | re-fetch on Send               |

## Acceptance criteria

- [ ] Summon gesture pops the bar within 100ms
- [ ] Slash commands dispatch correctly
- [ ] Voice transcript appears live
- [ ] Recent commands persist across sessions
- [ ] Switch access alternative works

## References

- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/GESTURE-VOCABULARY.md`
- `07-ui/INPUT-PIPELINE.md`
- `07-ui/STATUS-BAR.md`
