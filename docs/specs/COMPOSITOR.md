---
id: compositor
title: Compositor
type: SPEC
status: draft
version: 0.0.0
implements: [compositor]
depends_on:
  - shell-overview
  - drm-display
  - 0013-cage-kiosk-compositor
  - sandbox
depended_on_by:
  - agentui
  - input-pipeline
last_updated: 2026-04-30
---
# Compositor

## Purpose

Specify the role, configuration, and constraints of cage as Kiki's compositor. Cage exposes a single Wayland client (agentui), forwards input, manages outputs, and otherwise stays out of the way.

## Why cage

- Kiosk-style: one client, no chrome
- wlroots-based: modern, well-maintained
- Tiny attack surface
- DRM/KMS direct (no X compatibility)

## Inputs

- `cage` invoked by `kiki-cage.service` (systemd)
- DRM nodes (`/dev/dri/cardN`) with the right permissions
- libinput device events (touch, keyboard, pointer)
- The agentui binary path

## Outputs

- A Wayland socket exposed to agentui only
- Frames composited to KMS planes
- Input events forwarded to the client
- Output reconfiguration on hotplug

## Behavior

### Startup

```
1. systemd starts kiki-cage.service after multi-user.target
2. cage opens DRM and finds outputs
3. cage execs agentui as its single client
4. agentui connects via WAYLAND_SOCKET inherited from cage
5. cage waits for agentui's first surface; presents to KMS
```

If agentui fails to start, cage exits; systemd restarts the unit.

### One-client invariant

cage rejects connections from any process other than the one it spawned. The Wayland socket has 0700 permissions, owned by the user; the only path that opens it is via the inherited fd.

A misbehaving app trying to launch its own GUI gets `connect() refused`.

### Outputs

cage detects outputs at startup and on hotplug. For each:

- Resolution and refresh rate from EDID
- Scale derived from physical size and resolution (Kiki's HiDPI policy)
- Color profile (sRGB by default; HDR off in v0)

Multi-output is supported: agentui sees them as separate Wayland outputs and lays out per surface.

### Input forwarding

Input events are forwarded to agentui via Wayland's input protocols:

- `wl_pointer` for cursor (touchpads, mice)
- `wl_touch` for direct touch
- `wl_keyboard` for keyboards
- `wlr_input_inhibit` for kiosk-mode lock

libinput-rs runs *in agentui*, not in cage. Cage forwards raw events; agentui interprets gestures.

### No virtual keyboard

Cage does not provide one. agentui draws its own on-screen keyboard when needed (touch device with no physical keyboard).

### Cursor

Hardware cursor when the GPU supports it; otherwise software. Agentui picks the cursor image; cage applies via `wlr_layer_shell` or default protocol.

### Sandbox

cage runs as the user (`<user>`), not root. DRM access via the user's `seat` membership through logind. AppArmor profile `kiki-cage` constrains:

- Read: /dev/dri/* (via logind), /etc/kiki/cage.toml
- Write: nothing under /etc; agentui's stdio
- Network: none

### Configuration

```toml
# /etc/kiki/cage.toml
[output."*"]
scale = "auto"
allow_hdr = false
vrr = "auto"

[input]
tap_to_click = true
natural_scroll = true

[startup]
client = "/usr/bin/agentui"
on_client_exit = "restart"
```

cage hot-reloads on SIGHUP.

### Lock screen

The lock screen is rendered by agentui (it's just another UI state). cage does not implement its own.

### Headless

If `[output]` reports zero outputs and `KIKI_HEADLESS=1`, cage exits cleanly; the GUI stack stays down. Voice and remote clients still operate.

### Capabilities

cage runs without elevated capabilities. DRM is via session/seat, not raw root.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| agentui crashes                  | cage exits; systemd restarts   |
| Output disconnect                | reconfigure; agentui re-lays   |
| DRM permission denied            | log; cage exits; user surfaced |
|                                  | via journalctl                 |
| GPU hang                         | DRM reset path; cage continues |

## Performance contracts

- Compose frame: <2ms cage overhead (excluding render)
- Input event forward: <500µs
- Hotplug reconfigure: <300ms

## Acceptance criteria

- [ ] Only one Wayland client connects (agentui)
- [ ] Multi-output works (resolution + scale per output)
- [ ] Input devices via libinput route correctly
- [ ] Headless mode exits cleanly
- [ ] AppArmor profile in effect

## References

- `02-platform/DRM-DISPLAY.md`
- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/AGENTUI.md`
- `02-platform/SANDBOX.md`
- `14-rfcs/0013-cage-kiosk-compositor.md`
## Graph links

[[SHELL-OVERVIEW]]  [[DRM-DISPLAY]]  [[0013-cage-kiosk-compositor]]  [[SANDBOX]]
