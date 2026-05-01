---
id: app-lifecycle
title: App Lifecycle
type: SPEC
status: draft
version: 0.0.0
implements: [app-lifecycle]
depends_on:
  - app-container-format
  - app-runtime-modes
  - container-runtime
  - capability-gate
depended_on_by: []
last_updated: 2026-04-30
---
# App Lifecycle

## Purpose

Specify the lifecycle states of a Kiki app — install, launch, pause, resume, terminate, uninstall — and the events that drive transitions. The lifecycle is implemented via quadlet/systemd for services and ad-hoc podman invocations for ephemeral modes.

## States

```
absent ──install──▶ installed ──launch──▶ running
   ▲                    │              │
   │                    │              ├──pause──▶ paused
   │                    │              │           │
   │                    │              │           resume
   │                    │              ▼           │
   │                    │           stopped ◀──────┘
   │                    │              │
   │                  uninstall      terminate
   └────────────────────┴──────────────┘
```

## Install

```
1. User chooses to install (`kiki install <id>`)
2. Pull OCI image; verify signature; verify Sigstore log
3. Parse manifest; show capabilities; user reviews and consents
4. Generate quadlet unit (or none for cli_tool / interactive_ephemeral)
5. Run on_install hook (optional)
6. Register tools, views, recipes with the registry
7. App is `installed`
8. Audit entry
```

If any step fails, the partial state is rolled back.

## Launch

For interactive_service / headless_service: started by systemd at the configured trigger (login, boot, on-demand socket activation).

For cli_tool: invoked per tool dispatch.

For interactive_ephemeral: invoked when an entry point intent fires (a user surface or a tool dispatch declares it).

The runtime applies sandbox + quadlet config; agentd registers the app's surfaces and tools.

## Pause

For service modes only. The runtime can pause an app via cgroup freezer. The pause is fast (<10ms); resume is similarly fast. Reasons:

- Idle (no recent use)
- Resource pressure (need RAM for foreground tasks)
- User intent (pause an app)
- DND or focus mode

Paused apps persist their last memory state in cgroup-frozen pages; no disk writes.

## Resume

Unfreeze the cgroup. The app continues from where it left off. If significant time has passed, the app may need to refresh state (timers expired, connections dropped); the SDK provides hooks for this.

## Terminate

A graceful stop: SIGTERM, wait, SIGKILL after grace period. The app's `on_terminate` hook (if declared) runs first.

Triggered by:

- Normal mode (cli_tool exits naturally)
- User stop
- Resource pressure (after pause / hibernate fails to free enough)
- Crash recovery

## Uninstall

```
1. Stop the app
2. Run on_uninstall hook
3. Remove quadlet unit
4. Unregister tools, views, recipes
5. Revoke capability grants
6. Optionally delete app data
7. Remove image from local OCI cache
8. Audit entry
```

User decides whether to keep the app's data or wipe it.

## Update

A new version installed:

```
1. Pull new image; verify
2. Parse new manifest
3. If new manifest requires *more* capabilities than old, prompt
4. If new manifest requires *fewer* capabilities, auto-revoke
   the dropped ones
5. Stop old app
6. Replace image
7. Restart
```

The user is informed of capability changes in the prompt.

## Hooks

```
on_install        runs once at install; bootstrap
on_uninstall      runs once at uninstall; cleanup
on_pause          notifies the app it's about to be paused
on_resume         notifies the app it's resuming
on_terminate      graceful shutdown
on_update         called between stop and start during update
```

Hooks are optional; if missing, the runtime proceeds with defaults.

## Capability lifecycle

- Persistent grants (interactive_service / headless_service): survive reboot
- Session grants (interactive_ephemeral): scoped to the session
- Per-call grants (cli_tool): scoped to the call

Revocation is immediate via the gate; the app sees the revocation either via SIGUSR1 (configurable) or by failing on the next gated call.

## Multi-version coexistence

Multiple versions of the same app can be installed but only one is "active" at a time. Older versions are archived for rollback.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Install hook fails               | rollback; install rejected     |
| Service repeatedly crashes       | back-off restart; eventually   |
|                                  | mark as failed; user prompted  |
| Pause fails                      | log; treat as continuing to    |
|                                  | run                             |
| Update introduces new caps the   | pre-prompt at install; if user |
| user denies                      | declines, leave old version    |

## Acceptance criteria

- [ ] All five state transitions work for service modes
- [ ] cli_tool launch + exit works on dispatch
- [ ] Pause/resume via cgroup freezer
- [ ] Capability grants follow the mode
- [ ] Update flow handles capability changes
- [ ] Audit log captures lifecycle transitions

## References

- `06-sdk/APP-CONTAINER-FORMAT.md`
- `06-sdk/APP-RUNTIME-MODES.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `02-platform/SANDBOX.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/UPDATE-ORCHESTRATOR.md`
- `10-security/AUDIT-LOG.md`
