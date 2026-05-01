---
id: ui-index
title: UI — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# UI

The shell, the canvas, components, gestures, workspaces, accessibility.

## Shell architecture

- `SHELL-OVERVIEW.md` — cage as compositor, agentui as the only client.
- `../specs/COMPOSITOR.md` — cage kiosk Wayland.
- `../specs/AGENTUI.md` — the only GUI app.

## Canvas

- `../specs/CANVAS-MODEL.md` — scene graph + reconciliation + ops log.
- `../specs/LAYOUT-INTENTS.md` — six to eight layout patterns.
- `../specs/BLOCK-TYPES.md` — native, web, app_surface, system widget.

## Components

- `../specs/COMPONENT-LIBRARY.md` — standard Slint catalog.
- `../specs/COMPONENT-REGISTRY.md` — third-party components, OCI-distributed.
- `../specs/DESIGN-TOKENS.md` — eight token categories with layered resolution.

## Input

- `../specs/GESTURE-VOCABULARY.md` — nine system gestures and alternates.
- `../specs/INPUT-PIPELINE.md` — libinput-rs gestures and multi-touch.
- `../specs/COMMAND-BAR.md` — contextual visibility, voice, slash commands.

## Layout fixed zones

- `../specs/STATUS-BAR.md` — always-visible info.
- `../specs/TASK-MANAGER.md` — agentic task overlay.

## Workspaces and adaptation

- `../specs/WORKSPACES.md` — parallel sessions UX.
- `../specs/ADAPTATION-RULES.md` — battery, idle, DND, accessibility, locale.
- `../specs/ACCESSIBILITY.md` — AccessKit and AT-SPI export.

## Web rendering

- `../specs/BROWSER-ENGINE.md` — Servo embedded for web blocks.
