---
id: sdk-overview
title: SDK Overview
type: DESIGN
status: draft
version: 0.0.0
implements: [sdk]
depends_on:
  - principles
  - paradigm
  - capability-taxonomy
depended_on_by:
  - app-container-format
  - blocks-api
  - kernel-framework
  - render-api
  - sdk-rust
  - system-clients
last_updated: 2026-04-30
---
# SDK Overview

## Problem

Kiki has many surfaces an outside developer might want to extend: apps that talk to the agent, custom UI components, tools the agent can dispatch, profiles the device can adopt, skills the agent learns, subagent bundles. We want one coherent SDK with a small number of contracts so developers don't have to learn N different mental models.

## The four contracts

```
1. Kernel     state + commands + (auto-MCP) tool surface
2. Blocks     declarative UI emitted by an app
3. Render     optional offscreen DMA-BUF for full-tier graphics
4. System     read-only and capability-gated calls into Kiki
              (memory, inference, focusbus, tools, agents)
```

Most apps need **Kernel + Blocks + System**. Apps that draw their own pixels (a video player, a 3D viewer) add **Render**. Apps with no GUI use **Kernel + System**.

## Artifact types developers ship

```
App                  OCI container, podman quadlet, kernel + blocks
Component            OCI artifact, Slint markup; UI building blocks
Tool                 contracted via the agent; Wassette WASM or Rust binary
Profile              signed YAML, OCI artifact; device profiles
Skill                Markdown + frontmatter; procedural recipes
Subagent bundle      .kab; configuration of a custom subagent
Soul extension       Markdown extending SOUL.md
```

Each has a format spec under this directory.

## Distribution

Everything ships as an **OCI artifact** signed with cosign. No package managers, no app stores in the conventional sense. Developers `cosign sign && oras push`; users `kiki install <id>`. See `12-distribution/`.

## Identity

`kiki:<namespace>/<name>@<version>` — the universal identifier. The namespace registry maps to a real OCI registry (the publisher's). Stable across renames; verifiable via Sigstore.

## Capability discipline

Apps and tools declare required capabilities in their manifest. The capability gate is non-bypassable; the SDK *cannot* request privileged access at runtime that wasn't declared. This is fundamental: review at install, enforcement at every call.

## Languages

- **Rust SDK** is canonical (`SDK-RUST.md`)
- Bindings exist for Python, TypeScript, C, Go; they wrap the Rust core via FFI/WASM
- All SDKs use the same Cap'n Proto schemas under the hood

## Tool ergonomics

A tool's surface auto-publishes via the `rmcp`-style "auto-MCP": a tool's Rust functions become callable by the agent without per-tool plumbing. The SDK macro derives a Cap'n Proto schema from the function signatures.

## Lifecycle

Apps have a defined lifecycle (install, launch, pause, resume, terminate) implemented via systemd quadlet wrappers around podman. See `APP-LIFECYCLE.md`.

## Principles

- **Small contracts, narrow surface.** Four contracts; each is small.
- **Manifest-first.** Every capability and intent is declared at build time.
- **No undocumented backdoors.** What's not in the manifest does not get granted.
- **Idiomatic Rust core; ergonomic bindings.** Don't cripple Rust to be cross-language; wrap Rust to be cross-language.
- **Reuse.** Don't write a new wire format; everything goes through Cap'n Proto.

## What this SDK is NOT

- Not a full GUI framework. Apps emit blocks; agentui composes them. Apps that need full pixel control use the Render contract.
- Not a substitute for the OS. The agent owns dispatch; apps respond.
- Not a place for ad-hoc protocols. Use the four contracts.

## Quick map

| You want to...                       | Use                          |
|--------------------------------------|------------------------------|
| Build a UI app                        | Kernel + Blocks + System     |
| Add a custom UI component             | Component artifact            |
| Add a tool the agent can call         | Tool (Rust + auto-MCP)        |
| Author a skill (recipe)               | Skill format                  |
| Ship a device profile                 | Profile artifact              |
| Ship a custom subagent setup          | Subagent bundle (.kab)        |
| Render your own pixels                | Add Render contract           |

## References

- `00-foundations/PRINCIPLES.md`
- `00-foundations/PARADIGM.md`
- `06-sdk/KERNEL-FRAMEWORK.md`
- `06-sdk/BLOCKS-API.md`
- `06-sdk/RENDER-API.md`
- `06-sdk/SYSTEM-CLIENTS.md`
- `06-sdk/PUBLISHING.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `10-security/CAPABILITY-TAXONOMY.md`
## Graph links

[[PRINCIPLES]]  [[PARADIGM]]  [[CAPABILITY-TAXONOMY]]
