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
- `COMPOSITOR.md` — cage kiosk Wayland.
- `AGENTUI.md` — the only GUI app.

## Canvas

- `CANVAS-MODEL.md` — scene graph + reconciliation + ops log.
- `LAYOUT-INTENTS.md` — six to eight layout patterns.
- `BLOCK-TYPES.md` — native, web, app_surface, system widget.

## Components

- `COMPONENT-LIBRARY.md` — standard Slint catalog.
- `COMPONENT-REGISTRY.md` — third-party components, OCI-distributed.
- `DESIGN-TOKENS.md` — eight token categories with layered resolution.

## Input

- `GESTURE-VOCABULARY.md` — nine system gestures and alternates.
- `INPUT-PIPELINE.md` — libinput-rs gestures and multi-touch.
- `COMMAND-BAR.md` — contextual visibility, voice, slash commands.

## Layout fixed zones

- `STATUS-BAR.md` — always-visible info.
- `TASK-MANAGER.md` — agentic task overlay.

## Workspaces and adaptation

- `WORKSPACES.md` — parallel sessions UX.
- `ADAPTATION-RULES.md` — battery, idle, DND, accessibility, locale.
- `ACCESSIBILITY.md` — AccessKit and AT-SPI export.

## Web rendering

- `BROWSER-ENGINE.md` — Servo embedded for web blocks.
