---
id: workspace-lifecycle
title: Workspace Lifecycle
type: SPEC
status: draft
version: 0.0.0
implements: [workspace-lifecycle]
depends_on:
  - agentd-daemon
  - filesystem-btrfs
  - container-runtime
depended_on_by:
  - task-manager
  - workspaces
last_updated: 2026-04-30
---
# Workspace Lifecycle

## Purpose

Specify the lifecycle of workspaces (parallel agentic sessions): creation, switching, hibernation, archival, restoration. Memory partition, app instance scoping, concurrency rules.

The user-facing UX of workspaces is in `07-ui/WORKSPACES.md`. This document covers the runtime concurrency, persistence, and resource management.

## Behavior

### Workspace state

```rust
struct WorkspaceState {
    id: WorkspaceId,                 // ULID
    user_id: UserId,
    name: String,
    mode: WorkspaceMode,             // Default | Scoped | Ephemeral | Restricted | BackgroundOnly
    canvas_state: CanvasState,
    ops_log: OpsLog,
    agent_task: Option<AgentTask>,
    memory_namespace: MemoryNamespace,
    policy_overlay: Option<PolicyOverlay>,
    soul_extension: Option<PathBuf>,
    app_instances: Vec<AppInstance>,
    lifecycle: Lifecycle,            // Active | Background | Hibernated | Archived
    created_at: DateTime,
    last_active_at: DateTime,
}
```

### Modes

```
Default          standard; persists; shares memory with user; can run in background
Scoped           memory episodic/procedural scoped to workspace; soul ext propio; policy override propio
Ephemeral        no persist post-close; episodic in RAM only; for sensitive tasks
Restricted       stricter policy class; inherited to spawned apps/agents (kids mode, parental controls)
BackgroundOnly   no canvas; agent reports to mailbox when done
```

Mode declared at creation. Only the user can change mode (consent flow if loosening from Restricted).

### Lifecycle states

```
NEW   user creates ws (gesture, /workspace new, app)
   │
   ▼
ACTIVE                     ← exactly one foreground per display
   ↑↓
BACKGROUND                 ← user switched to another ws
   ↑↓                      ← agent may continue running if pending work
HIBERNATED                 ← inactive > N min (default 5)
   ↑                       ← cgroup freeze; canvas unrendered
ARCHIVED                   ← user closed explicitly; persisted; require restoration
```

### Transitions

```
NEW → ACTIVE: spawn coordinator, allocate WorkingMemory, render canvas.
ACTIVE → BACKGROUND: pause render; agent continues if pending work; status bar badge if active.
BACKGROUND → ACTIVE: resume render; canvas redraws from scene graph; re-acquire input focus.
BACKGROUND → HIBERNATED: after grace period:
   - cgroup freeze tier-4 apps
   - drop GPU textures (Slint/Servo cache)
   - if agent idle: suspend; else continue background
   - scene graph stays in RAM
HIBERNATED → ACTIVE: thaw cgroups; request fresh frames from apps; animate transition;
                     <500ms warm; <2s cold.
ANY → ARCHIVED: flush ops log + state to disk; release RAM;
                tier-4 apps stopped (state persisted via their kernel).
ARCHIVED → ACTIVE: restoration like opening saved file; replay ops log; respawn apps.
```

### State partition

```
                                PER-WORKSPACE      SHARED (per-user)    SHARED (global)
canvas state                          ✓
ops log + branches                    ✓
working memory                        ✓
agent task / LoopBudget               ✓
soul-extension (optional)             ✓
policy class override                 ✓                                base policy
app instances (tier 4)                ✓
                                                  ↓
identity (SOUL/USER.md)                           ✓
episodic memory (default)                         ✓ (queryable by ws tag)
semantic graph                                    ✓ (bitemporal)
procedural memory                                 ✓ (some scope-tagged)
capability grants                                 ✓ (overlay per ws)
audit log                                         ✓ (entries tagged with ws_id)
mailbox                                           ✓ (per-user; items tagged ws)
voice prints                                      ✓
                                                                       ↓
hardware (display, audio)                                              ✓
inferenced gateway                                                     ✓
toolregistry catalog                                                   ✓
```

### Scoped workspace memory

When mode is Scoped, the workspace gets its own memory namespace:

```
/var/lib/kiki/users/<u>/workspaces/<ws-id>/
   memory/
      episodic.lance/
      episodic.vec/
      procedural/
```

Queries from agent in this ws default to scoped + identity + (optionally) read-only of user-wide.

### Concurrency rules

1. Exactly one workspace is Foreground per display.
2. One agent main task per workspace. Subagents within (Coordinator/Worker) are not workspaces.
3. Concurrent inference across workspaces: `inferenced` multiplexes per resource budget.
4. Concurrent tool calls: each workspace has its own pool; total cap per-user.
5. Memory reads parallel; writes serialized per user_id.
6. Audit log entries serialized; tagged with workspace_id.
7. Capability grants: overlay per workspace.
8. Policy: Restricted ws inherits stricter policy; never looser.

### App instance model

| Tipo | Instance scope |
|---|---|
| CLI tool | per-call; contextual to invoking workspace |
| Headless service (Tipo 2) | per-user singleton; or per-workspace if Profile declares |
| Interactive ephemeral (Tipo 3) | per-call; lives during block |
| Interactive service (Tipo 4) | per (app, workspace); distinct cgroup, distinct app data dir |

App data layout:

```
/var/lib/kiki/apps/<ns>/<name>/data-<workspace-id>/
```

For tier-4 apps with `workspace_scope: per_workspace`. With `shared_singleton`, one instance serves all workspaces; the app receives ws_id in context.

### Hibernation

```
hibernate(workspace_id):
   for each Type4 instance in workspace:
      if profile.signal_busy: skip
      if has_active_block_in_other_workspace: skip
      request_flush(instance)         # sd_notify FLUSHING=1
      wait for FLUSHED or timeout 5s
      cgroup_freeze(instance.systemd_unit)
      mark instance Hibernated
      audit_log
   // Type 2 services global; never hibernate per workspace
   // Type 1/3 ephemeral; not applicable
```

Background tasks (the agent) may continue running unless explicitly paused.

### Resume

```
resume(workspace_id):
   for each Hibernated instance:
      cgroup_thaw(instance.systemd_unit)
      mark Running
      notify app via DBus signal: WorkspaceResumed
      if Tier 4 GUI: request fresh frames
      audit_log
```

### Persistence

```
/var/lib/kiki/users/<u>/workspaces/<ws-id>/
├── manifest.toml         (id, name, mode, created, last_active)
├── canvas.db             (ops log + branches via SQLite)
├── working-snapshot.toml (periodic snapshot of working memory)
├── grants.db             (workspace-overlay capability grants)
├── policy.toml           (workspace policy class)
├── soul-extension.md     (optional, if Scoped mode)
├── memory/               (only if Scoped mode)
└── audit.log             (subset; tagged entries)
```

btrfs subvolume per workspace enables snapshots and export.

### Reboot recovery

```
1. systemd starts kiki-runtime.target.
2. agentd loads workspace registry from index.toml.
3. Restore last_active workspace as Foreground:
   - replay ops log → reconstruct canvas
   - respawn tier-4 apps with state files
   - reload working memory snapshot if recent
4. Other workspaces lazy: registered, not running; appear in status bar as Hibernated.
5. User switches → activate as needed.
6. Background tasks pending pre-reboot: agentd inspects per-ws journal;
   if unfinished agent task, prompt user "retomar?" via mailbox.
   No silent resume of agentic work post-reboot.
```

### Policy overlay

```
Base user policy:
   inference: { allow_remote: true, daily_budget: $5 }
   sensitive: medical = local-only

Workspace "work" override:
   inference: { allow_remote: true, daily_budget: $1 }   # stricter
   data.calendar: read = require_explicit_per_call         # stricter

Workspace "kids" override (Restricted mode):
   inference: { allow_remote: false }                       # stricter
   sensitive: all = blocked
   capabilities: very limited set
```

policyd evaluates with overlay: ws-policy → user-policy → device-policy. Stricter wins.

### Cross-workspace operations

By default isolated. Agent in one workspace cannot read another workspace's working memory without explicit handoff.

Cross-ws agent invocations require capability `agent.workspace.send`, granted at workspace creation per policy.

## Interfaces

### Programmatic

```rust
struct WorkspaceManager {
    fn create(&mut self, mode: WorkspaceMode, name: String) -> Result<WorkspaceId>;
    fn switch(&mut self, target: WorkspaceId) -> Result<()>;
    fn archive(&mut self, ws: WorkspaceId) -> Result<()>;
    fn restore(&mut self, ws: WorkspaceId) -> Result<()>;
    fn hibernate(&mut self, ws: WorkspaceId) -> Result<()>;
    fn list(&self) -> Vec<WorkspaceInfo>;
}
```

### CLI

```
agentctl workspace list
agentctl workspace create --mode=<m> --name=<n>
agentctl workspace switch <name>
agentctl workspace archive <name>
agentctl workspace export <ws-id>
```

## State

### Persistent

- Per-workspace data in btrfs subvolume.
- Workspace registry in user's state.sqlite.

### In-memory

- Active workspace's CanvasState.
- Running app containers.

## Failure modes

| Failure | Response |
|---|---|
| Memory with many workspaces | hibernation aggressive; soft cap N=8 active |
| Ws hibernation thaw fails | mark broken; user can repair via reset |
| App tier-4 declares per_workspace, ws explosion | warn at 12 active; refuse spawn at 20 |
| Cross-ws operation missing target | mailbox holds payload until target restored |
| Ephemeral ws closed during inference | inference canceled; results discarded |

## Performance contracts

- Workspace switch (Active → Background → Active warm): <100ms perceived.
- Workspace switch (Active → Hibernated → Active): <500ms–2s.
- Workspace creation: <300ms.
- Workspace archival: <2s (disk I/O).
- Restoration from Archived: <5s typical.
- Per-workspace canvas memory footprint: ~10–50 MB (no apps active); 100–500 MB with tier-4 app.
- Per-user max active workspaces (recommended): 8.

## Acceptance criteria

- [ ] Multiple workspaces coexist per user; one is Foreground.
- [ ] Switching is animated and <500ms warm.
- [ ] Hibernation reduces RAM via cgroup freeze; thaw works.
- [ ] Per-ws scene graph + ops log persists; reboot restores last active.
- [ ] Tier-4 apps have per (app, workspace) instances by default.
- [ ] Memory queries respect ws scope per mode.
- [ ] Audit log tags every entry with workspace_id.
- [ ] Cross-ws operations require explicit user intent or capability.
- [ ] Restricted workspaces enforce stricter policy.
- [ ] Ephemeral workspaces leave no trace post-close.

## References

- `07-ui/WORKSPACES.md`
- `02-platform/FILESYSTEM-BTRFS.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `03-runtime/AGENTD-DAEMON.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `14-rfcs/0043-workspaces-model.md`
