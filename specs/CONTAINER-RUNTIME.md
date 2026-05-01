---
id: container-runtime
title: Container Runtime
type: SPEC
status: draft
version: 0.0.0
implements: [podman-quadlet-runtime]
depends_on:
  - init-system
  - sandbox
  - storage-layout
depended_on_by:
  - app-container-format
  - app-lifecycle
  - app-runtime-modes
  - sandbox
  - workspace-lifecycle
last_updated: 2026-04-30
---
# Container Runtime

## Purpose

Specify the container runtime that hosts Kiki apps: podman with crun, integrated via systemd quadlet, with sandbox primitives applied at container start.

## Inputs

- App OCI images pulled from OCI registries.
- App Profiles declaring permissions, mounts, network.
- Quadlet definitions in `/etc/containers/systemd/`.
- systemd unit dependencies from quadlet-generated units.

## Outputs

- Running app containers with appropriate sandbox applied.
- systemd units generated from quadlet definitions.
- Audit log entries for container start/stop.

## Behavior

### Why podman + crun + quadlet

- **podman** is rootless, daemonless, OCI-compliant. No central daemon to compromise.
- **crun** is a fast OCI runtime in C with lower startup latency than runc (~60ms vs 95ms cold start).
- **quadlet** integrates podman containers as systemd units, giving us systemd's supervision and dependency management for free.

`youki` is the runner-up if we want a pure-Rust OCI runtime (~45ms cold start). v0 uses crun for ecosystem maturity; revisit youki when bugs in podman's youki integration settle.

### How apps run

Each app is an OCI container image. When an app is installed:

```
agentctl install kiki:acme/notes
   ↓
1. resolve namespace via namespace registry
2. pull OCI image registry.acme.dev/notes:1.2.0
3. cosign verify against acme's key
4. extract Profile
5. generate quadlet file at /etc/containers/systemd/<name>.container
6. systemctl daemon-reload
7. ready to start (per Profile lifecycle policy)
```

When an app is launched:

```
agentd → systemctl start <unit>.service (the quadlet-generated unit)
   ↓
1. systemd starts the container via podman
2. podman pulls (cached) image, prepares container
3. crun applies sandbox: namespaces, cgroups, Landlock, seccomp
4. container starts; app process runs
5. app SDK contacts agentd via Cap'n Proto
```

### Quadlet file structure

A typical quadlet file generated for a tier-light interactive service:

```ini
# /etc/containers/systemd/kiki-acme-notes--ws01.container
[Unit]
Description=Kiki app: kiki:acme/notes (workspace ws01)
After=kiki-runtime.target
PartOf=kiki-shell.target

[Container]
Image=registry.acme.dev/notes:1.2.0
ContainerName=kiki-acme-notes-ws01
Volume=/var/lib/kiki/apps/acme/notes/data-ws01:/data:rw
Volume=/run/kiki/agentd.sock:/run/kiki/agentd.sock:ro
Network=app-acme-notes
NoNewPrivileges=true
ReadOnly=true
Tmpfs=/tmp:size=64M
Environment=KIKI_WORKSPACE=ws01

# Sandbox extras
SecurityLabelType=container_t
DropCapability=ALL
SeccompProfile=/etc/kiki/seccomp/app-light.json

[Service]
Restart=on-failure
RestartSec=2
Type=notify

[Install]
WantedBy=kiki-shell.target
```

quadlet generates `kiki-acme-notes--ws01.service` from this. systemd treats it as any other unit.

### Sandbox application

The container's default sandbox already provides:

- User namespace (per-app uid mapped to subordinate range on host).
- Network namespace (per-app netns).
- Mount namespace (read-only base, bind-mounted data dir).
- PID namespace.
- IPC namespace.
- UTS namespace.
- cgroups v2 for resource control.
- seccomp filter applied by crun.

Kiki layers on top of this:

- **Landlock** rules for filesystem access (declared in Profile, enforced via quadlet directives).
- **Capability drops** (`DropCapability=ALL` plus selective `AddCapability=` per Profile).
- **Specific seccomp profiles** per app tier (in `/etc/kiki/seccomp/`).
- **Network namespace configuration** with allowed outbound hosts.

### Per-tier sandbox preset

Three tiers, each with a default sandbox preset:

- **Tier tool (CLI tool / headless service):** strict. No display, no audio. Network only if Profile declares.
- **Tier light (interactive ephemeral / interactive service with system widgets):** tool + DBus access to `org.kiki.Components1`. No own Wayland surface.
- **Tier full (interactive service with own surface):** light + GPU device + Wayland socket bind-mount + access to libagentos-render shared memory.

The preset is applied via the quadlet generator from the Profile.

### Networking

Each app's container has its own network namespace. The Profile declares:

```yaml
network:
  outbound_hosts:
    - https://api.example.com
  outbound_local: false
  inbound_local: false
  inbound_wan: false
```

The quadlet generator creates a podman network configuration with iptables rules permitting only the declared hosts. Per-app networks do not bridge to other apps.

### Resource limits

Profile declares:

```yaml
resources:
  memory_max_mb: 512
  cpu_quota_pct: 20
  storage_max_mb: 100
  pids_max: 64
```

Quadlet translates to cgroup v2 directives:

```
MemoryMax=512M
CPUQuota=20%
TasksMax=64
```

cgroup v2 enforces. OOM kill happens within the cgroup, not affecting other apps.

### Image storage

Images are pulled and cached in `/var/lib/containers/storage/`. podman's overlay filesystem layer sharing means apps with similar bases share layers on disk.

A typical Kiki desktop with 5–10 apps active uses 1–3 GB of container storage. Images are garbage-collected by `agentctl storage gc`.

### Multi-user

For tier-full apps with `workspace_scope: per_workspace`, a separate container instance runs per workspace (and effectively per user, since workspaces are per-user). Each instance has its own data directory bind-mounted.

For apps with `workspace_scope: shared_singleton`, one instance serves all users; the app receives the calling user's identity in its context.

### Hibernation

When a workspace is hibernated, its tier-full app containers are paused via cgroup freezer:

```
echo 1 > /sys/fs/cgroup/.../<container>/cgroup.freeze
```

The container's memory and threads remain but are inert. On workspace resume:

```
echo 0 > /sys/fs/cgroup/.../<container>/cgroup.freeze
```

The app resumes from where it was paused. Background agents (the agent itself) are paused/resumed similarly per workspace lifecycle policy.

### Logging

Containers' stdout/stderr go to journald via the systemd unit. `journalctl -u <unit>` shows app logs. Apps using `tracing`-style structured logging emit to stdout JSON; journald parses.

### Updates

Container updates flow through `agentctl install <package>@<new-version>` or `podman auto-update` for apps configured with that policy. Updates are atomic (new image pulled, container restarted).

## Interfaces

### Programmatic

```rust
pub fn launch_app(app_id: &AppId, workspace: Option<&WorkspaceId>) -> Result<ContainerHandle>;
pub fn pause_app(handle: &ContainerHandle) -> Result<()>;
pub fn resume_app(handle: &ContainerHandle) -> Result<()>;
pub fn terminate_app(handle: &ContainerHandle) -> Result<()>;
```

The agentd lifecycle manager uses these via systemd's DBus API.

### CLI

```
agentctl app list
agentctl app start <name>
agentctl app stop <name>
agentctl app logs <name>
agentctl storage gc                # cleanup unused images
```

`podman ps`, `podman logs`, `podman inspect` are available for diagnostics in developer mode.

## State

### Persistent

- Container images in `/var/lib/containers/storage/`.
- Quadlet definitions in `/etc/containers/systemd/`.
- App data dirs in `/var/lib/kiki/apps/`.

### In-memory

- Running container state managed by podman + crun.

## Failure modes

| Failure | Response |
|---|---|
| Container fails to start | systemd records; restart per Restart= policy; alert after StartLimitBurst |
| OOM in container | cgroup kills; restart; agent treats tool as unavailable temporarily |
| Image pull fails | abort install; agent informs user |
| cosign verification fails | abort install; alert |
| Network namespace setup fails | container does not start; log; alert |
| Hibernation freeze fails | log; agent treats workspace as Active |

## Performance contracts

- Cold container start: ~100–200ms (crun + podman).
- Warm container start (image cached): ~50–100ms.
- Per-call overhead for tier tool ephemeral: 60–150ms (spawn + tool execution).
- Container hibernation freeze/thaw: <50ms.

## Acceptance criteria

- [ ] podman + crun + quadlet wired to systemd.
- [ ] Apps run as containers with per-tier sandbox.
- [ ] Bind mounts isolate data per app/user/workspace.
- [ ] cosign verification before launch.
- [ ] Resource limits enforced per Profile.
- [ ] Hibernation via cgroup freezer works.
- [ ] Image storage GC removes unused images.

## Open questions

- When to evaluate youki as primary OCI runtime.
- Whether to expose podman CLI to developer mode users.

## References

- `02-platform/SANDBOX.md`
- `02-platform/INIT-SYSTEM.md`
- `02-platform/STORAGE-LAYOUT.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `06-sdk/APP-RUNTIME-MODES.md`
- `06-sdk/APP-LIFECYCLE.md`
- `14-rfcs/0012-podman-quadlet-app-runtime.md`
