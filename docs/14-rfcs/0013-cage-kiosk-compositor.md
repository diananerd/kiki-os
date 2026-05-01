---
id: 0013-cage-kiosk-compositor
title: cage as Kiosk Wayland Compositor
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
last_updated: 2026-04-29
depended_on_by:
  - compositor
  - shell-overview
---
# ADR-0013: cage as Kiosk Wayland Compositor

## Status

`accepted`

## Context

Kiki OS has a single GUI app (`agentui`) that occupies the entire display. We need a Wayland compositor that runs `agentui` fullscreen with no window management, no dock, no taskbar — just a kiosk surface.

Options: cage, gamescope, weston-kiosk-shell, custom on smithay, full Wayland compositors (Sway, Hyprland, etc.) configured for kiosk.

## Decision

Use **cage** as the kiosk Wayland compositor.

cage is built on wlroots, runs a single Wayland client fullscreen, handles DRM/KMS, libinput, hot-plug, multi-monitor, VT switching, hardware cursor, DPMS, high-DPI scaling. ~3000 lines of C, MIT, mature, used in production for kiosks and embedded systems.

## Consequences

### Positive

- Purpose-built for "run one Wayland client fullscreen."
- ~3 KLOC C — small, readable.
- 10+ years of production use in kiosks.
- Handles all hardware quirks (DRM, libinput, hot-plug) so we don't.
- Crash-resilient: if cage dies, systemd restarts it.

### Negative

- C, not Rust. We accept this because cage is upstream and we don't maintain it.
- Limited customization (it's a kiosk; that's the point).
- For multi-display canvases (v2), we may need additional logic on top.

## Alternatives considered

- **gamescope (Valve)**: more complex, gaming-focused, includes upscaling we don't need.
- **weston-kiosk-shell**: weston with kiosk shell; more layers, similar capability.
- **Custom on smithay**: pure Rust; ~10–25 KLOC of compositor work we'd own. Wrong place to spend engineering for v0.
- **Sway/Hyprland configured kiosk**: overkill; configuration fragile.

## References

- `07-ui/COMPOSITOR.md`
- `07-ui/SHELL-OVERVIEW.md`
- `02-platform/DRM-DISPLAY.md`
## Graph links

[[0001-appliance-os-paradigm]]
