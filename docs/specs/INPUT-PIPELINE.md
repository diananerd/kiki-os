---
id: input-pipeline
title: Input Pipeline
type: SPEC
status: draft
version: 0.0.0
implements: [input-pipeline]
depends_on:
  - shell-overview
  - compositor
  - gesture-vocabulary
  - accessibility
depended_on_by:
  - accessibility
  - command-bar
  - gesture-vocabulary
last_updated: 2026-04-30
---
# Input Pipeline

## Purpose

Specify how input events flow from kernel through cage and into agentui, where they become typed gestures or block-targeted events. The pipeline is responsible for low-latency dispatch, multi-touch, gesture detection, and accessibility-input remapping.

## Path

```
kernel evdev
   │
   ▼
libinput (in cage)
   │  raw events
   ▼
Wayland protocols (wl_pointer, wl_touch, wl_keyboard)
   │
   ▼
agentui input pipeline
   ├── libinput-rs gesture detection
   ├── system gesture matcher
   ├── focus router
   ├── accessibility remapper
   └── command bus
```

## Stages

### libinput in cage

cage uses libinput's defaults for tap-to-click, natural scroll, and palm rejection. Configuration via `cage.toml` controls these without per-device tweaking.

### libinput-rs in agentui

agentui re-runs libinput-rs over the Wayland-forwarded events to detect higher-level gestures (3-finger swipe, 4-finger pinch). cage forwards raw multi-touch; agentui composes the gesture state machine.

This duplication is intentional: cage stays small (no gesture logic); agentui owns the user-facing semantics.

### System gesture matcher

The matcher checks each detected gesture against the system vocabulary (`GESTURE-VOCABULARY.md`). If matched, the system action runs and the event is consumed (not forwarded to a block).

### Focus router

For non-system events, the router delivers to the focused block. Focus is tracked per workspace and updated by:

- Touch (tap selects)
- Keyboard navigation (Tab cycles)
- Voice ("focus the song list")
- Programmatic (agent's request)

### Accessibility remapper

If the user has a switch-access profile, raw input is remapped:

- Single-button cycling through "actions"
- Dwell-based selection
- Sip-and-puff (when the device supports)

The remapper sits between the system matcher and the focus router; it can synthesize events.

### Command bus

The final layer; events arrive as typed messages:

```rust
enum InputEvent {
    SystemGesture(GestureKind),
    BlockEvent(BlockId, BlockInputEvent),
    Keyboard(KeyEvent),
    Voice(VoiceEvent),
    Custom(CustomEvent),
}
```

Subscribers are the agent client (forwards to agentd), the canvas reconciler (focus changes), and the gesture cheat sheet.

## Latency

- Touch-to-paint p99: <30ms
- Key-to-action p99: <20ms
- Voice command-to-handler: <100ms (on top of ASR latency)

## Multi-touch

Up to 10 fingers tracked. Gesture state machine handles partial sequences gracefully (3 fingers down → 4 fingers down: cancel previous, start new).

## Pen / stylus

Optional. When a pen is detected via libinput, additional gestures (pen-tap, pen-side-button) become available. The block must declare `accepts_pen` to receive pen-specific events; otherwise pen acts like touch.

## Keyboard

Standard wl_keyboard with xkbcommon for layouts. agentui includes Compose key support and dead-key handling. Kiki's command shortcuts use Cmd/Super to avoid clashing with text input shortcuts.

## On-screen keyboard

When a touch device has no physical keyboard or the user invokes "kiki, type", agentui presents an on-screen keyboard. It's a normal block (kind=system) with input routing.

## Capture and replay

The command bus can record to a JSON file for testing:

```
kiki-input record --to=session.json
kiki-input replay session.json
```

Useful for reproducible UI tests.

## Sandbox

Input devices are accessed via cage; agentui only sees Wayland-protocol events. No raw evdev for agentui.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Gesture state stuck              | timeout (1s); reset            |
| Switch access misconfigured      | revert to default; surface     |
| Accessibility tree out of sync   | refresh on next focus change   |
| Voice event without permission   | drop; log                      |

## Acceptance criteria

- [ ] System gestures are detected reliably
- [ ] Latency budgets met
- [ ] Switch access path works end-to-end
- [ ] Pen events delivered when block declares accepts_pen
- [ ] Capture/replay tooling works

## References

- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/COMPOSITOR.md`
- `07-ui/AGENTUI.md`
- `07-ui/GESTURE-VOCABULARY.md`
- `07-ui/ACCESSIBILITY.md`
