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

- `APP-CONTAINER-FORMAT.md` — OCI container conventions for Kiki apps.
- `APP-RUNTIME-MODES.md` — four types: CLI tool, headless service, interactive ephemeral, interactive service.
- `APP-LIFECYCLE.md` — install, launch, pause, resume, terminate via quadlet.
- `KERNEL-FRAMEWORK.md` — state + commands + auto-MCP via rmcp.
- `BLOCKS-API.md` — emitting blocks, reactive bindings.
- `RENDER-API.md` — DMA-BUF offscreen surface for tier-full apps.
- `SYSTEM-CLIENTS.md` — memory, inference, focusbus, tools, agents.

## Artifact formats

- `COMPONENT-OCI-FORMAT.md` — Slint markup as OCI artifact.
- `PROFILE-OCI-FORMAT.md` — signed YAML profile as OCI artifact.
- `SOUL-FORMAT.md` — SOUL.md and extensions.
- `SKILL-FORMAT.md` — Markdown skill format.
- `AGENT-BUNDLE.md` — `.kab` packaged subagent configurations.

## Publishing

- `PUBLISHING.md` — build, sign with cosign, push to registry.

## Language bindings

- `SDK-RUST.md` — canonical Rust SDK.
- `SDK-CODEGEN.md` — bindings auto-generation.
- `SDK-BINDINGS-PYTHON.md`
- `SDK-BINDINGS-TYPESCRIPT.md`
- `SDK-BINDINGS-C.md`
- `SDK-BINDINGS-GO.md`
