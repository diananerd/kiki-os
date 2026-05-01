---
id: shell-overview
title: Shell Overview
type: DESIGN
status: draft
version: 0.0.0
implements: [shell-architecture]
depends_on:
  - principles
  - process-model
  - drm-display
  - 0013-cage-kiosk-compositor
depended_on_by:
  - accessibility
  - agentui
  - canvas-model
  - command-bar
  - compositor
  - design-tokens
  - gesture-vocabulary
  - input-pipeline
  - status-bar
  - workspaces
last_updated: 2026-04-30
---
# Shell Overview

## Problem

Kiki's UI is the agent — not a desktop with windows. We need a shell that renders agentic surfaces (cards, panels, blocks composed by the agent) without the conceptual baggage of a window manager. We also need it small enough to audit and predictable enough to reason about.

## Constraints

- **Single GUI client.** Apps don't open windows; the agent composes the canvas. One Wayland client (agentui) holds the display.
- **Local-first, single-user-foreground.** The shell shows the active user's session.
- **Predictable layout.** No floating windows, no overlapping. Layout intents are typed and bounded.
- **Accessible by default.** AccessKit + AT-SPI for screen readers and switch access.
- **Adaptive.** Battery, idle, DND, accessibility profile, locale change appearance and behavior.

## Decision

Two-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│ cage  (kiosk Wayland compositor)                        │
│   - One client allowed: agentui                          │
│   - DRM/KMS via wlroots                                 │
│   - Hardware cursor, multi-touch via libinput            │
│   - HiDPI per output                                     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ agentui  (the only GUI client)                           │
│   - Slint UI toolkit + wgpu renderer                     │
│   - Embedded Servo for web blocks                        │
│   - AccessKit for accessibility                          │
│   - libinput-rs for gestures                             │
│   - Talks to agentd over Cap'n Proto                     │
└─────────────────────────────────────────────────────────┘
```

The compositor is a kiosk: it shows exactly one app, no chrome, no app switcher. The single client implements the entire shell. The agent talks to agentui over Cap'n Proto and instructs it to render canvases, surfaces, and prompts.

## Rationale

### Why cage

Cage is a wlroots-based kiosk compositor. It exposes Wayland to one client and nothing else. Perfect fit for "the agent owns the screen."

### Why one GUI client

Multiple windowed apps make sense for general computing. They don't make sense when the agent is the interface. One client simplifies state, layout, accessibility, and security.

### Why Slint + Servo

Slint is a small, declarative UI toolkit with a Rust renderer that runs on wgpu. It is ergonomic for native blocks. Servo (Rust browser engine) handles web blocks when an app surface needs HTML/CSS. They share the same wgpu backend so compositing is unified.

### Why AccessKit + libinput-rs

AccessKit is the cross-platform accessibility tree from the Slint and egui community; AT-SPI bridge exports to Linux assistive tech. libinput-rs gives us robust gestures and multi-touch without writing a kernel-input parser.

## Consequences

### Surface model

agentd describes a surface as a typed structure (canvas + blocks + intents); agentui renders it. The agent never sends pixels; it describes intent. Resolution, theming, and accessibility adaptations happen on the client side.

### No app windows

An app is a process that exposes a typed surface to the agent. The agent decides whether and where to compose that surface into the user's view. Apps are guests on the canvas, not owners of windows.

### Voice integration

Voice events flow into the same render loop. A voice command can pop a confirmation card; a voice answer can dismiss it. The status bar shows voice state. See `08-voice/`.

### Multiple users

A device with multiple users runs one session at a time on the foreground compositor. Switching users restarts the agentui process (with that user's identity). Background users are not visible on the screen.

### Multiple workspaces

Within one user, multiple agentic workspaces (see `WORKSPACES.md`) coexist. The shell shows one foreground at a time; switching is fast.

### Headless mode

A device shipped without a display (a server-class Kiki) runs no compositor and no agentui. Voice and remote clients are the only surfaces.

### Performance

| Surface       | Budget                            |
|---------------|------------------------------------|
| Render frame  | <16ms p99 (60 FPS)                |
| Input latency | <30ms touch-to-paint              |
| Cold start    | <2s from idle to first frame      |
| Theme change  | <100ms                            |

### Failure isolation

If agentui crashes: cage restarts it; the compositor stays up. If cage crashes: systemd restarts; brief blank screen. Voice and audio are unaffected by GUI crashes.

## References

- `00-foundations/PRINCIPLES.md`
- `01-architecture/PROCESS-MODEL.md`
- `02-platform/DRM-DISPLAY.md`
- `07-ui/COMPOSITOR.md`
- `07-ui/AGENTUI.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/WORKSPACES.md`
- `07-ui/ACCESSIBILITY.md`
- `14-rfcs/0013-cage-kiosk-compositor.md`
