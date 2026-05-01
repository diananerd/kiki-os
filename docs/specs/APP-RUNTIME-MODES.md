---
id: app-runtime-modes
title: App Runtime Modes
type: SPEC
status: draft
version: 0.0.0
implements: [app-runtime-modes]
depends_on:
  - app-container-format
  - container-runtime
depended_on_by:
  - app-lifecycle
  - tool-dispatch
last_updated: 2026-04-30
---
# App Runtime Modes

## Purpose

Specify the four runtime modes a Kiki app declares in its manifest. The mode determines how the app is started, how long it lives, what tools it can register, and what UI it can contribute.

## The four modes

### cli_tool

A short-lived process invoked on demand:

- Started by the agent or user via tool dispatch
- Exits when the task completes
- May not register persistent UI views
- May contribute tools (the typical use)
- No `app_surface` blocks (lifetime too short)

Example: a `kiki:tools/markdown-render` that converts a Markdown document on demand.

### headless_service

A long-running daemon with no UI:

- Started at boot or on-demand, runs until stopped
- Registers tools the agent can call
- May publish events on NATS in its own namespace
- No UI views

Example: a sync daemon that polls a remote service and emits events when state changes.

### interactive_ephemeral

A short-lived interactive app:

- Started when needed (user invokes a flow)
- Renders one or more UI surfaces while running
- Exits when the user dismisses or after a timeout
- Tools registered for the duration

Example: a guided setup flow ("connect a printer").

### interactive_service

A long-running app with UI surfaces:

- Started at user login or on first use
- Stays running; surfaces visible when the agent composes them
- Tools and surfaces both registered for the daemon's lifetime
- Can hibernate when idle

Example: the music player; the email client; a game.

## Mode-by-mode behavior

| Behavior              | cli_tool | headless_service | interactive_ephemeral | interactive_service |
|-----------------------|----------|-----------------|------------------------|---------------------|
| Started by            | dispatch | systemd / dispatch | dispatch              | systemd / dispatch  |
| Lifetime              | per call | persistent       | per session            | persistent          |
| Can register UI       | no       | no               | yes                    | yes                 |
| Can register tools    | yes      | yes              | yes                    | yes                 |
| Hibernate-eligible    | n/a      | yes              | n/a                    | yes                 |
| Capability scope      | per call | persistent       | per session            | persistent          |

## Quadlet wrapping

systemd-quadlet generates per-app unit files from the manifest:

```
# /etc/containers/systemd/<id>.container
[Unit]
Description=<title>

[Container]
Image=<oci-id>
ContainerName=<id>
Network=none

[Service]
Restart=on-failure                # interactive_service / headless_service
# ExecStart implicit via podman   for cli_tool
RestartSec=5

[Install]
WantedBy=default.target
```

cli_tool and interactive_ephemeral do not have systemd units; they're started ad-hoc by tool dispatch.

## Capabilities and modes

A capability's persistence matches the mode:

- cli_tool: capabilities granted for the call only
- interactive_ephemeral: granted for the session
- interactive_service / headless_service: granted persistently (subject to user revocation)

The user sees mode at install: "this app will run continuously" vs "only when used".

## Resource budgets

Different modes have different defaults:

```
cli_tool                CPU 1×1; memory 256MB; runtime 30s
headless_service        CPU 1×0.5; memory 512MB; runtime persistent
interactive_ephemeral   CPU 1×1; memory 1GB; runtime 5min
interactive_service     CPU 1×1; memory 1GB; runtime persistent
```

These are caps; specific apps can be overridden via manifest with user consent.

## Hibernation

interactive_service and headless_service apps can be hibernated when idle (cgroup freezer). The runtime's idle policy applies.

## Anti-patterns

- A "service" that's really a tool (no persistence needed)
- A cli_tool that runs forever (use headless_service)
- An interactive_service with no UI (use headless_service)
- Picking interactive_ephemeral for something that needs to outlive the user dismissing the surface

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| App misses its mode contract     | install warning; user-visible  |
|                                  | at runtime if capability       |
|                                  | mismatch                        |
| Service crashes repeatedly       | systemd restart loop; user     |
|                                  | informed; capability revoked   |
|                                  | until reinstall                 |
| cli_tool exceeds runtime cap     | killed; tool returns error     |

## Acceptance criteria

- [ ] All four modes implementable via quadlet
- [ ] Capabilities scoped to mode lifetime
- [ ] Resource budgets enforced
- [ ] Mode visible to user at install

## References

- `06-sdk/APP-CONTAINER-FORMAT.md`
- `06-sdk/APP-LIFECYCLE.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `03-runtime/WORKSPACE-LIFECYCLE.md`
