---
id: agentui
title: AgentUI
type: SPEC
status: draft
version: 0.0.0
implements: [agentui]
depends_on:
  - shell-overview
  - compositor
  - canvas-model
  - capnp-rpc
depended_on_by:
  - accessibility
  - browser-engine
  - canvas-model
last_updated: 2026-04-30
---
# AgentUI

## Purpose

Specify the single GUI client that owns Kiki's display. agentui receives Cap'n Proto instructions from agentd, renders surfaces, handles input, exposes accessibility, and drives the canvas. It is the *only* GUI process on the device.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ agentui process                                       │
│                                                       │
│ ┌──────────────────────────────────────────────────┐ │
│ │ render layer                                     │ │
│ │   Slint  ←→  wgpu (Vulkan / GL / Metal backend)  │ │
│ │   Servo (web blocks) shares wgpu surface          │ │
│ └──────────────────────────────────────────────────┘ │
│                          ▲                            │
│ ┌────────────────────────┴───────────────────────┐   │
│ │ canvas reconciler                              │   │
│ │   ops log → scene graph                         │   │
│ └────────────────────────────────────────────────┘   │
│                          ▲                            │
│ ┌────────────────────────┴───────────────────────┐   │
│ │ agent client                                    │   │
│ │   Cap'n Proto over /run/kiki/agentd.sock        │   │
│ │   subscribes to surface streams                 │   │
│ └────────────────────────────────────────────────┘   │
│                          ▼                            │
│ ┌────────────────────────────────────────────────┐   │
│ │ input pipeline                                  │   │
│ │   libinput-rs gestures → CommandBus            │   │
│ └────────────────────────────────────────────────┘   │
│ ┌────────────────────────────────────────────────┐   │
│ │ accessibility                                   │   │
│ │   AccessKit tree → AT-SPI bridge                │   │
│ └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

## Lifecycle

```
1. cage execs agentui with the Wayland socket inherited.
2. agentui connects to /run/kiki/users/<uid>/agentd.sock.
3. Subscribes to surface and event streams.
4. Renders a splash + connects to compositor outputs.
5. Loop:
     a. Receive surface deltas
     b. Reconcile against scene graph
     c. Render frame
     d. Forward input to agent (with capability binding)
6. On agentd reconnect (after restart): replays state.
```

agentui is restartable; transient state (animations) is lost on restart, but persistent state (current canvas) is fetched fresh from agentd.

## Render layer

- **Slint** for declarative native blocks
- **wgpu** as the backend (Vulkan on Linux variants; switches per platform)
- **Servo** embedded for web blocks; renders into a wgpu texture; Slint composites it
- One swapchain per output

Frame budget 16ms p99; we measure and shed quality (animations) under pressure.

## Canvas reconciler

The agent describes the desired surface as a tree of typed blocks. The reconciler:

- Diffs against the current scene graph
- Applies minimal updates (Slint and Servo retained-mode benefit)
- Plays animations declaratively (transitions, list inserts)

See `CANVAS-MODEL.md`.

## Agent client

The Cap'n Proto session is bidirectional:

- agentd → agentui: surface deltas, prompts, focus changes
- agentui → agentd: input events, gesture invocations, voice events

The session is per-user; switching workspaces sends a `SetActiveWorkspace` message and the surface stream rebinds.

## Input pipeline

libinput-rs gives us gesture detection (3-finger swipes, pinch, etc.). The pipeline:

- Maps raw gestures to system actions (`gesture.summon_command_bar`, `gesture.next_workspace`)
- Forwards the rest to the focused block (per the canvas focus model)
- Applies the command bar's own bindings

See `INPUT-PIPELINE.md` and `GESTURE-VOCABULARY.md`.

## Accessibility

AccessKit tree mirrors the scene graph; bridged to AT-SPI for Linux assistive tech (Orca, espeak). Keyboard navigation is first-class; switch access supported via input remapping.

See `ACCESSIBILITY.md`.

## Web rendering (Servo)

Servo is embedded for blocks that declare `kind = "web"`. The Servo embedding is:

- Pinned page configuration; no JS unless the block declares it
- Network access through agentd (apps don't get arbitrary network)
- Local storage scoped per surface
- Renders into a wgpu texture

See `BROWSER-ENGINE.md`.

## Theming

Theme is computed from design tokens (see `DESIGN-TOKENS.md`). agentui resolves tokens into Slint/Servo styles; theme changes hot-swap without reload.

## Voice integration

Voice state (listening, transcribing, speaking) appears in the status bar. Voice transcript pops a transient surface during dictation. Voice events come through the agent client; agentui doesn't talk to the voice stack directly.

## Configuration

```toml
# /etc/kiki/agentui.toml
[render]
target_fps = 60
prefer_vulkan = true

[features]
servo_web_blocks = true
animations = "auto"           # auto | minimal | off

[startup]
splash_min_ms = 0
```

User-level overrides at `/var/lib/kiki/users/<uid>/ui-policy.toml`.

## Sandbox

- AppArmor profile `kiki-agentui`
- Read: theme, fonts, the user's GUI policy
- Write: per-user GUI cache
- Network: only through agentd
- DRM: via Wayland (cage forwards)
- Talk: only `/run/kiki/users/<uid>/agentd.sock`

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| agentd disconnects               | reconnect with backoff;        |
|                                  | overlay "agent unavailable"    |
| Render context lost              | recreate; reload textures      |
| Servo crashes                    | replace web block with         |
|                                  | placeholder; reopen on next    |
|                                  | surface delta                  |
| Out of GPU memory                | shed animations; warn user     |

## Performance contracts

- First paint after startup: <1.5s
- Frame: <16ms p99
- Surface delta apply: <8ms p99

## Acceptance criteria

- [ ] Only one agentui process per user session
- [ ] Surface deltas reconcile correctly
- [ ] Web blocks render via Servo
- [ ] AccessKit tree matches scene graph
- [ ] Theme hot-swaps without reload

## References

- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/COMPOSITOR.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/DESIGN-TOKENS.md`
- `07-ui/INPUT-PIPELINE.md`
- `07-ui/BROWSER-ENGINE.md`
- `07-ui/ACCESSIBILITY.md`
- `05-protocol/CAPNP-RPC.md`
## Graph links

[[SHELL-OVERVIEW]]  [[COMPOSITOR]]  [[CANVAS-MODEL]]  [[CAPNP-RPC]]
