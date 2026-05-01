---
id: update-orchestrator
title: Update Orchestrator
type: SPEC
status: draft
version: 0.0.0
implements: [update-orchestrator]
depends_on:
  - agentd-daemon
  - oci-native-model
depended_on_by:
  - capnp-schemas
  - model-lifecycle
  - ota-distribution
last_updated: 2026-04-29
---
# Update Orchestrator

## Purpose

Specify the update orchestrator inside `agentd`: detection, scheduling, application, healthcheck, rollback. Coordinates the three OCI-native update channels (base via bootc, daemon runtime via sysext, apps via podman auto-update).

## Behavior

### Three OCI-native channels

```
Base + kernel       bootc upgrade                        atomic; reboot required
Runtime daemons     systemd-sysext refresh + restart      atomic; live (no reboot)
Apps                podman auto-update or agentctl pull   atomic; live (next launch)
```

All three operations are OCI pulls under the hood, with cosign verification.

### Polling

The orchestrator polls each channel periodically:

```
every N minutes:
   for each registered channel:
      check upstream (registry) for newer version
      if newer found and signature valid:
         stage update locally
```

Default poll intervals (configurable per user):

- Base: 6 hours.
- Runtime: 1 hour.
- Apps: per-app declared in Profile (default 24 hours).

### Decision

Once an update is staged, the orchestrator decides when to apply:

```
for each staged update:
   if channel == base:
      ask agentd: any active foreground task? user actively typing?
      if yes: defer; surface in mailbox "update ready, reboot when convenient"
      if no or user approved: schedule reboot with countdown
   elif channel == runtime sysext:
      wait for daemon idle (no active inference for that daemon)
      apply systemd-sysext refresh; systemctl restart kiki-runtime.target
      healthcheck; rollback on failure
   elif channel == app:
      mark "restart on next launch"
      audit log
```

### Per-channel application

#### Base (bootc upgrade)

```
1. Pull new bootc OCI image.
2. cosign verify.
3. dm-verity verify.
4. Stage to inactive partition.
5. Update bootloader entries.
6. Schedule reboot per user policy:
   - immediate (with countdown)
   - at next idle
   - at scheduled quiet window
7. On reboot:
   - Bootloader tries new partition.
   - On successful boot: mark active.
   - On failure: bootloader counts; falls back to old.
8. Audit log: base updated.
```

#### Runtime sysext

```
1. Pull new sysext OCI artifact.
2. cosign verify.
3. systemd-sysext refresh (re-mount /usr layered).
4. systemctl restart kiki-runtime.target.
5. healthcheck each daemon (Cap'n Proto ping + sample call).
6. If all healthy: ops complete; notify in agentui.
7. If any fails: rollback sysext (re-mount previous); restart; alert with log.
8. Audit log: runtime updated.
```

#### Apps

```
1. agentctl pull-app or podman auto-update detects update.
2. Pull new container image.
3. cosign verify.
4. quadlet generates updated unit if Profile changed.
5. Mark "next launch uses new version".
6. On next launch: container starts with new image.
7. Audit log: app updated.
```

Already-running app containers continue with old version until restart. The user can force restart via:

```
agentctl app restart <app>
```

### Per-policy application

User declares update policies:

```toml
[update_policy]
auto_apply_base = false             # require user approval for reboots
auto_apply_runtime = true           # apply daemon updates automatically
auto_apply_apps = true              # apply app updates automatically
quiet_window = "23:00-06:00"
require_user_approval_above_severity = "high"
```

`agentd` respects these.

### Rollback

#### Sysext rollback

If healthcheck fails after sysext refresh:

```
1. Detect failure (daemon doesn't respond, or crashes within 5 min).
2. systemd-sysext refresh with previous artifact.
3. systemctl restart kiki-runtime.target.
4. Re-healthcheck.
5. Alert user; log.
```

#### bootc rollback

Bootc handles automatically: if the new boot doesn't reach kiki-runtime.target within boot count attempts, falls back to old.

#### App rollback

```
agentctl app rollback <app>
   → re-pull previous OCI tag/digest
   → quadlet update
   → restart with old version
```

### Update during workspace activity

The orchestrator avoids interrupting active workspaces:

- Foreground workspace with active agent task: defer.
- Background workspaces with pending work: defer if it would affect them.
- All workspaces idle: apply immediately.

User can override: "update now" or "I'll restart later."

### Replay across reboot

For the base/kernel channel that requires reboot:

- Sessions in workspaces are persisted (canvas ops log, working memory snapshot).
- After reboot, user is offered: "Resume the work I was doing in <workspace>?"
- The user decides; nothing silently resumes.

Background agent tasks pre-reboot: agentd's journal records last state. After reboot, mailbox prompt: "Task X was running before reboot; retomar?"

### Audit

Every update step logged:

```json
{"event": "update_staged", "channel": "runtime", "version": "1.0.5", "from": "1.0.4"}
{"event": "update_applied", "channel": "runtime", "outcome": "Success", "duration_ms": 4200}
{"event": "update_rolled_back", "channel": "runtime", "from": "1.0.5", "to": "1.0.4", "reason": "healthcheck_failed"}
```

## Interfaces

### Programmatic

```rust
struct UpdateOrchestrator {
    fn poll_now(&mut self) -> Result<Vec<StagedUpdate>>;
    fn apply(&mut self, update: StagedUpdate) -> Result<UpdateOutcome>;
    fn rollback(&mut self, channel: Channel) -> Result<()>;
    fn list_staged(&self) -> Vec<StagedUpdate>;
}
```

### CLI

```
agentctl update status              # what's staged, what's applied
agentctl update poll                 # force poll now
agentctl update apply <update-id>    # apply staged update
agentctl update rollback <channel>   # explicit rollback
agentctl update policy               # show update policy
```

## State

### Persistent

- Update policy in user config.
- Update history (recent N) in DuckDB.
- Staged updates queued.

### In-memory

- Last poll times per channel.
- Recent healthcheck results.

## Failure modes

| Failure | Response |
|---|---|
| Registry unreachable | retry; backoff; alert if persistent |
| cosign verification fails | reject; alert |
| Healthcheck fails post-update | rollback; alert |
| Disk full during stage | abort; alert; suggest cleanup |
| User declines repeated reboots | continue deferring; warning if security-critical |

## Performance contracts

- Poll: typically <30s per channel (bounded by network).
- Sysext apply (daemon update): ~1–2s including restart.
- Bootc upgrade reboot: ~12s to login on reference hardware.
- App pull + quadlet update: bounded by image size and network.

## Acceptance criteria

- [ ] Three channels handled.
- [ ] Per-channel polling cadence configurable.
- [ ] cosign verification before any apply.
- [ ] Rollback automatic on healthcheck failure.
- [ ] User policy respected.
- [ ] Quiet window honored.
- [ ] Workspace activity considered before reboot.
- [ ] Replay across reboot via mailbox prompts (no silent resume).

## References

- `09-backend/OTA-DISTRIBUTION.md`
- `02-platform/BOOT-CHAIN.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `10-security/COSIGN-TRUST.md`
## Graph links

[[AGENTD-DAEMON]]  [[OCI-NATIVE-MODEL]]
