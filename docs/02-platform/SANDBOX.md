---
id: sandbox
title: Sandbox
type: SPEC
status: draft
version: 0.0.0
implements: [kernel-sandbox-primitives]
depends_on:
  - kernel-config
  - process-model
  - container-runtime
depended_on_by:
  - agentd-daemon
  - browser-engine
  - capability-gate
  - compositor
  - container-runtime
  - kernel-config
  - network-stack
  - tool-dispatch
  - transport-unix-socket
last_updated: 2026-04-30
---
# Sandbox

## Purpose

Specify the kernel-level sandbox applied to every Kiki app and to system services with reduced privilege: how Landlock, seccomp, namespaces, and cgroups compose to provide defense in depth, and how policies are derived from app Profiles.

## Inputs

- An app Profile declaring permissions and resource limits.
- The hardware manifest (for hardware capability gating).
- A per-app uid range allocated at install.
- Sandbox preset templates per tier (tool/light/full).

## Outputs

- A sandboxed process that cannot exceed declared capabilities.
- An audit log entry for sandbox application.
- A failure event if sandbox setup fails (the app does not start).

## Behavior

### Sandbox composition

The sandbox is built from four orthogonal kernel-enforced layers:

```
1. Landlock          filesystem access control
2. seccomp-bpf       syscall filtering
3. Namespaces        isolation of network, mount, IPC, UTS, PID, user
4. cgroups v2        CPU, memory, I/O, PID limits
```

Each layer is independent; bypassing one does not bypass others. For apps, a fifth layer applies at the host: AppArmor system-wide profiles cover the host services that supervise the apps (defense in depth at the OS level, not per-app).

### Why this stack

- **Landlock** is the modern Linux unprivileged sandbox. Mainline since 5.13, with TCP/UDP scoping in kernel 6.x. No root required to sandbox a process. Composable.
- **seccomp-bpf** restricts syscalls. Composes cleanly with Landlock.
- **Namespaces** provide isolation primitives that the container runtime uses naturally.
- **cgroups v2** enforce resource limits. Required for hibernation (cgroup freezer).
- **AppArmor (host-level)** provides Mandatory Access Control on system services. Kiki uses AppArmor as a backstop, not as the per-app primary sandbox.

We chose Landlock over SELinux because:

- Landlock is unprivileged (apps can sandbox themselves further if they want).
- SELinux's policy model is heavyweight; Landlock's is concise.
- Debian/Ubuntu/CentOS Stream all ship Landlock. SELinux requires Fedora-class distros.

### Per-tier sandbox preset

Three tier presets, applied via quadlet directives or systemd unit directives:

#### Tier tool (CLI tool, headless service)

```
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateNetwork=yes        # unless Profile declares network
PrivateDevices=yes
PrivateTmp=yes
RestrictNamespaces=~CLONE_NEWUSER
RestrictRealtime=yes
RestrictSUIDSGID=yes
LockPersonality=yes
SystemCallFilter=@system-service ~@privileged ~@resources
LandlockPaths=ro:/usr ro:/etc rw:/var/lib/kiki/apps/<id>/data
DropCapability=ALL

# cgroup
MemoryMax=256M
CPUQuota=20%
TasksMax=64
```

#### Tier light (system widgets)

Tier tool plus:

```
# DBus access for org.kiki.Components1
BindReadOnlyPaths=/run/dbus/system_bus_socket
```

#### Tier full (own surface)

Tier light plus:

```
# Wayland socket
BindReadOnlyPaths=/run/kiki/wayland-0

# GPU device
DeviceAllow=/dev/dri/renderD128 rw

# Larger resources
MemoryMax=2G
CPUQuota=80%

# Bind shared memory paths for libagentos-render
BindPaths=/run/kiki/render-<id>:/run/kiki/render
```

### Process spawn flow

When `agentd` (via systemd quadlet) launches an app:

```
1. systemd resolves the unit file (quadlet-generated).
2. podman+crun:
   a. Pull image if needed (cosign-verified).
   b. Allocate per-app uid in subordinate range.
   c. unshare namespaces: NEWUSER, NEWNET, NEWNS, NEWPID, NEWIPC, NEWUTS.
   d. Apply Landlock ruleset from Profile.
   e. Apply seccomp BPF filter for tier.
   f. Apply cgroup v2 limits.
   g. exec the app's entrypoint.
3. Container is running; app announces readiness via sd_notify.
4. agentd registers the app's tools in toolregistry.
```

If any step fails, the container does not start. The audit log records the failure.

### Filesystem allowlist

Each app's Profile declares filesystem access:

```yaml
filesystem:
  read_only:
    - /usr/share/<app-id>            # static assets in the container image
  read_write:
    - /data                          # the bind-mounted data dir
  no_access:
    - /                              # everything else (default deny)
```

Landlock translates these to its filesystem ruleset. The container's base image is read-only by virtue of `ReadOnly=true` in the quadlet.

Apps cannot access:

- Other apps' data directories.
- Identity files (`/var/lib/kiki/identity/`).
- Other users' data (per-user containers don't see other users' bind mounts).
- `/dev/*` directly (device access is mediated by HAL).

### Network allowlist

Profile declares:

```yaml
network:
  outbound_hosts:
    - https://api.example.com
  outbound_local: false
  inbound_local: false
  inbound_wan: false
```

The quadlet generator creates a podman network with iptables rules. Outbound is blocked except to declared hosts. Inbound is blocked entirely except for explicit local sockets.

### Syscall filter

Each tier has a seccomp BPF filter compiled from a JSON spec. Common syscalls allowed:

```
read, write, openat, close, fstat, fstatat, lseek, mmap, mprotect, munmap,
rt_sigaction, rt_sigprocmask, futex, epoll_*, poll, recv*, send*, accept4,
connect (subject to netns), nanosleep, clock_*, exit, exit_group
```

Always blocked:

```
ptrace, process_vm_readv, process_vm_writev,
kexec_load, kexec_file_load, init_module, finit_module, delete_module,
swapon, swapoff, mount, umount2 (except in mount namespace),
pivot_root, syslog, acct, add_key, request_key, keyctl
```

Per-tier additions per `/etc/kiki/seccomp/<tier>.json`.

### Detection of denials

Sandbox denials are observable:

- Landlock denials: log via auditd.
- seccomp denials: SIGSYS or EPERM (configurable per syscall).
- Network denials: connect/sendto returns EHOSTUNREACH or EPERM.
- cgroup limits: OOM kill (memory) or throttling (CPU).

Auditd captures these. agentd's audit log records summarized denials. Repeated denials from one app suggest:

- A bug in the app.
- A bug in the app's Profile (insufficient capability declared).
- An attempted escape.

The audit log captures syscall, path (if applicable), timing. Patterns are flagged.

### Sandbox profile generation

When an app is installed, agentctl:

```
1. Parse Profile YAML.
2. Validate capabilities and resource limits.
3. Compile seccomp BPF for the declared tier.
4. Compose Landlock rules from filesystem capabilities.
5. Generate quadlet file with all directives.
6. Place at /etc/containers/systemd/<name>.container.
7. systemctl daemon-reload.
```

Profile updates regenerate the sandbox profile. Apps in flight continue with old profile until restarted.

### Per-user scoping

For multi-user devices, app instances are per-user:

```
app uid = base_app_uid + user_offset
```

Each user's app has their own data dir bind-mounted. The Landlock rules restrict access to that data dir, not to other users' dirs.

## Interfaces

### Profile (declarative)

App Profiles in `06-sdk/PROFILE-OCI-FORMAT.md` declare:

- `tier` (tool / light / full)
- `filesystem.read_only`, `read_write`
- `network.outbound_hosts`
- `resources.memory_max_mb`, `cpu_quota_pct`, etc.

The sandbox is generated from this declaration.

### Diagnostics

```
agentctl app sandbox <name>          # show resolved Landlock + seccomp + netns rules
agentctl app sandbox-denials <name>  # recent denials (from auditd)
```

## State

### Persistent

- Sandbox profile in /etc/containers/systemd/ (quadlet) and /etc/kiki/seccomp/.
- Audit log entries for denials.

### In-memory

- Active sandbox state per running container (kernel-side).

## Failure modes

| Failure | Response |
|---|---|
| Profile generation fails | install rejected |
| Profile load at spawn fails | container does not start; logged |
| Landlock kernel feature missing | refuse to install OS image |
| seccomp BPF rejected by kernel | container start fails; surfaced |
| netns creation fails | container start fails |
| cgroup creation fails | container start fails |
| App attempts denied operation | denied at kernel; logged |
| Profile out of sync with capabilities | regenerate at next install/start |

## Performance contracts

- Sandbox profile generation (at install): <100ms.
- Sandbox application at process spawn: <20ms (in addition to container start ~60–100ms).
- Per-syscall overhead from seccomp: <500ns.
- Per-fs-call overhead from Landlock: <1µs.

## Acceptance criteria

- [ ] App cannot read files outside declared filesystem capabilities (verified by Landlock).
- [ ] App cannot make denied syscalls (verified by seccomp).
- [ ] App cannot connect to undeclared hosts (verified by netns iptables).
- [ ] App cannot exceed cgroup memory limit (OOM kill).
- [ ] All denials are recorded in the audit log.
- [ ] Profile regeneration on capability change works without restarting unaffected apps.
- [ ] Per-user scoping: User A's app instance cannot read User B's data.

## Open questions

- Whether to add bpf-lsm for additional telemetry on system services (currently no; complexity vs benefit not worth it).

## References

- `02-platform/CONTAINER-RUNTIME.md`
- `02-platform/KERNEL-CONFIG.md`
- `02-platform/NETWORK-STACK.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `14-rfcs/0037-landlock-primary-apparmor-backstop.md`
