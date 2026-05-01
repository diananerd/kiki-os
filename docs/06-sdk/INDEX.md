---
id: sdk-index
title: SDK — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# SDK

How to build apps, components, tools, profiles, skills, and bundles for Kiki OS.

## Overview

- `SDK-OVERVIEW.md` — four contracts (Kernel, Blocks, Render, System).

## App authoring

- `../../specs/APP-CONTAINER-FORMAT.md` — OCI container conventions for Kiki apps.
- `../../specs/APP-RUNTIME-MODES.md` — four types: CLI tool, headless service, interactive ephemeral, interactive service.
- `../../specs/APP-LIFECYCLE.md` — install, launch, pause, resume, terminate via quadlet.
- `../../specs/KERNEL-FRAMEWORK.md` — state + commands + auto-MCP via rmcp.
- `../../specs/BLOCKS-API.md` — emitting blocks, reactive bindings.
- `../../specs/RENDER-API.md` — DMA-BUF offscreen surface for tier-full apps.
- `../../specs/SYSTEM-CLIENTS.md` — memory, inference, focusbus, tools, agents.

## Artifact formats

- `../../specs/COMPONENT-OCI-FORMAT.md` — Slint markup as OCI artifact.
- `../../specs/PROFILE-OCI-FORMAT.md` — signed YAML profile as OCI artifact.
- `../../specs/SOUL-FORMAT.md` — SOUL.md and extensions.
- `../../specs/SKILL-FORMAT.md` — Markdown skill format.
- `../../specs/AGENT-BUNDLE.md` — `.kab` packaged subagent configurations.

## Publishing

- `PUBLISHING.md` — build, sign with cosign, push to registry.

## Language bindings

- `../../specs/SDK-RUST.md` — canonical Rust SDK.
- `../../specs/SDK-CODEGEN.md` — bindings auto-generation.
- `../../specs/SDK-BINDINGS-PYTHON.md`
- `../../specs/SDK-BINDINGS-TYPESCRIPT.md`
- `../../specs/SDK-BINDINGS-C.md`
- `../../specs/SDK-BINDINGS-GO.md`
