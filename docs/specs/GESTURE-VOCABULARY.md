---
id: gesture-vocabulary
title: Gesture Vocabulary
type: SPEC
status: draft
version: 0.0.0
implements: [gesture-vocabulary]
depends_on:
  - input-pipeline
  - shell-overview
depended_on_by:
  - command-bar
  - input-pipeline
  - workspaces
last_updated: 2026-04-30
---
# Gesture Vocabulary

## Purpose

Specify the small, named set of system gestures the user can rely on across surfaces. Apps don't define system gestures; they receive only the residual gestures within their bounds. The vocabulary is bounded; surprise gestures are forbidden.

## The nine system gestures

### G1. Summon command bar

- **Touch**: 3-finger swipe down from any edge
- **Keyboard**: Cmd/Super+K
- **Voice**: "Kiki, command"
- **Switch access**: dedicated key

Pops the command bar overlay.

### G2. Switch workspace

- **Touch**: 3-finger swipe left/right
- **Keyboard**: Cmd/Super+Shift+Left/Right
- **Voice**: "switch to <name>"
- **Switch**: cycle key

### G3. Open task manager

- **Touch**: 4-finger pinch in
- **Keyboard**: Cmd/Super+T
- **Voice**: "show tasks"

Shows the agentic task overlay.

### G4. Dismiss / Back

- **Touch**: edge swipe from left
- **Keyboard**: Esc / Cmd/Super+Left
- **Voice**: "back" / "cancel"
- **Switch**: dedicated back key

### G5. Confirm / Forward

- **Touch**: tap the primary action
- **Keyboard**: Enter
- **Voice**: "confirm" / "yes"
- **Switch**: dedicated confirm

### G6. Mute / Wake mute

- **Touch**: 2-finger long-press
- **Hardware**: physical mic kill switch (definitive)
- **Keyboard**: Cmd/Super+M
- **Voice**: "mute" / "stop listening"

### G7. Show prompts / Mailbox

- **Touch**: edge swipe from top
- **Keyboard**: Cmd/Super+P
- **Voice**: "show messages"

### G8. Focus mode

- **Touch**: 4-finger swipe up
- **Keyboard**: Cmd/Super+F
- **Voice**: "focus mode"

Switches the canvas to `focus` layout intent.

### G9. Help / Discover

- **Touch**: 2-finger tap and hold
- **Keyboard**: F1 / Cmd/Super+?
- **Voice**: "help"

Surfaces a help overlay including the gesture cheat sheet.

## Why nine

A user can plausibly remember nine. More invites contention with apps. We add new system gestures only via RFC.

## Conflict resolution

A gesture starting in a block but matching a system gesture (e.g., 3-finger swipe inside a list) is intercepted by the system *before* reaching the block. Apps cannot register conflicting gestures.

A gesture that does *not* match a system pattern is forwarded to the focused block. Apps may interpret single-touch and basic multi-touch within their bounds.

## Alternatives mandatory

Every gesture has a non-touch alternative (keyboard, voice, switch). Touch-only is forbidden — accessibility requires every action be reachable some other way.

## Reduced-motion / one-handed mode

Some gestures (4-finger pinch) are hard for users with motor differences. Settings allows mapping any gesture to:

- A keyboard shortcut
- A button on a long-press menu
- A voice command alone

## Discovery

The help overlay (G9) shows the cheat sheet. First-run includes a brief tutorial that demonstrates the nine gestures.

## Switch access

Switch access (a single button cycling through actions) maps to a virtual keyboard equivalent of each gesture. The system mode "switch" enables a dwell-based selection over a labeled menu.

## Anti-patterns

- App declaring a 3-finger swipe handler — system intercepts.
- A single-touch gesture (slide) that means different things in different apps without context.
- Gestures with no visible affordance (a swipe corner with no hint).

## Acceptance criteria

- [ ] All nine gestures work via touch, keyboard, voice, and switch
- [ ] Conflicts always resolve to system gesture
- [ ] First-run tutorial covers the vocabulary
- [ ] Help overlay shows the cheat sheet
- [ ] Settings allows alternative mappings

## References

- `07-ui/INPUT-PIPELINE.md`
- `07-ui/COMMAND-BAR.md`
- `07-ui/TASK-MANAGER.md`
- `07-ui/WORKSPACES.md`
- `07-ui/ACCESSIBILITY.md`
