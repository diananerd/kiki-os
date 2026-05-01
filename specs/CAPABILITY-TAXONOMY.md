---
id: capability-taxonomy
title: Capability Taxonomy
type: SPEC
status: draft
version: 0.0.0
implements: [capability-taxonomy]
depends_on:
  - capability-gate
  - principles
depended_on_by:
  - agent-bundle
  - agentd-daemon
  - anti-patterns
  - capability-gate
  - device-pairing
  - fleet-management
  - hooks
  - inference-router
  - privacy-model
  - profile-oci-format
  - sdk-overview
  - skill-format
  - system-clients
last_updated: 2026-04-30
---
# Capability Taxonomy

## Purpose

Specify the canonical set of capabilities apps and tools can require: namespaces, semantics, default policies, and the rules for adding new capabilities. The taxonomy is the vocabulary the capability gate enforces.

## Behavior

### Why a fixed taxonomy

Without a fixed taxonomy:

- Apps invent overlapping capabilities ("network.access" vs "internet.use").
- Users cannot reason about what they're granting.
- The gate cannot make consistent decisions.

A fixed, documented taxonomy ensures that "data.calendar.read" means the same thing across all apps.

Adding new capabilities is via RFC.

### Top-level namespaces

```
data.<domain>.<verb>             access to user data domains
device.<resource>.<verb>          hardware access
network.<scope>.<host-or-class>   network egress / inbound
inference.<scope>.<class>         inference resources
agent.<area>.<verb>               agent-internal access (memory, tools, hooks)
voice.<aspect>                    voice channels and modes
ui.<area>.<verb>                  UI surface rendering
system.<service>.<verb>           system management
sensitive.<category>              sensitive content categorization
```

### data.<domain>.<verb>

User data, organized by domain. Verb is read or write.

```
data.calendar.read
data.calendar.write
data.contacts.read
data.contacts.write
data.email.read
data.email.write
data.email.send
data.tasks.read
data.tasks.write
data.notes.read
data.notes.write
data.location.read
data.location.history
data.health.read
data.health.write
data.financial.read
data.photos.read
data.photos.write
data.files.read
data.files.write
data.weather.read
data.media.read
data.media.play
data.web.read
```

### device.<resource>.<verb>

Hardware resources.

```
device.audio.input
device.audio.output
device.camera.use
device.display.use
device.display.brightness
device.haptic.use
device.power.read
device.power.manage
device.input.observe
device.network.observe
device.bluetooth.use
device.usb.attach
device.gpu.use
```

### network.<scope>.<host-or-class>

```
network.outbound.host:<host>
network.outbound.host:*
network.outbound.local
network.outbound.api:<class>
network.inbound.local
network.inbound.wan
```

Apps usually request specific outbound hosts. Wildcards are reviewed.

### inference.<scope>.<class>

```
inference.local.cpu
inference.local.gpu
inference.local.npu
inference.cloud.standard
inference.cloud.realtime
inference.cloud.direct
inference.budget.basic
inference.budget.standard
inference.budget.premium
```

The router consults these.

### agent.<area>.<verb>

```
agent.memory.read.episodic
agent.memory.read.semantic
agent.memory.read.procedural
agent.memory.read.identity
agent.memory.write.episodic
agent.memory.write.semantic
agent.memory.write.procedural
agent.memory.write.identity            (consent flow gated regardless)

agent.tool.invoke.self
agent.tool.invoke.other
agent.tool.declare.dangerous           (KikiSigned only)

agent.subagent.spawn
agent.subagent.spawn.persistent

agent.hook.register
agent.hook.intercept                    (KikiSigned only)
agent.hook.priority.system              (KikiSigned only)

agent.bus.discover
agent.ui.surface.render
agent.ui.surface.pin
agent.ui.surface.fullscreen

agent.proactive.self_initiate
agent.proactive.notify
agent.audit.read
agent.workspace.send                    (cross-workspace operations)
agent.multi_agent                       (gates spawning subagents)
```

### voice.<aspect>

```
voice.channel.native
voice.channel.webrtc.host
voice.channel.webrtc.join
voice.channel.bridge
voice.realtime.use
voice.speaker_id.use
voice.train_user_voice
```

### ui.<area>.<verb>

```
ui.compositor.observe
ui.compositor.screenshot                (KikiSigned default)
ui.surface.notification.always
```

### system.<service>.<verb>

```
system.app.install
system.app.uninstall
system.app.enable
system.app.disable
system.bundle.install
system.worktree.activate
system.user.add
system.user.remove
system.policy.modify
system.config.read
system.config.write
system.audit.export
```

Rare; typically only the system itself or a Settings app.

### sensitive.<category>

Sensitive-content classifications:

```
sensitive.medical
sensitive.financial
sensitive.legal
sensitive.relationship
sensitive.identity
sensitive.children
sensitive.location
sensitive.health
```

Sensitive capabilities don't grant access to data; they declare that the app deals with content of that category. The gate uses these to:

- Apply stricter routing.
- Tag episodes/facts as sensitive.
- Apply privacy-aware UI rendering.

### Default policy per capability

| Category | Default | Notes |
|---|---|---|
| data.* (read) | prompt | one-time or session |
| data.* (write/send) | prompt | |
| device.audio.input | prompt | mic |
| device.audio.output | grant | playing audio |
| device.camera.use | prompt | always per session |
| device.location.* | prompt | |
| network.outbound.host:* | review | wildcard reviewed |
| network.outbound.host:X | grant if app declared | |
| inference.cloud.* | per privacy + router | |
| agent.memory.read.identity | grant rarely | |
| agent.memory.write.identity | consent-flow | |
| agent.subagent.spawn | prompt | |
| agent.hook.intercept | KikiSigned | |
| voice.realtime.use | prompt | audio leaves device |
| sensitive.* | declarative | tag + routing |
| system.* | system-only | |

### Capability prompts

When prompting:

- Plain language description.
- Examples of what the app can do with it.
- Default scope: until-revoked, this-session, or one-time.
- Option to deny.

### KikiSigned-only capabilities

Some capabilities are gated to apps signed by `kiki:core`:

- agent.hook.intercept
- agent.hook.priority.system
- inference.cloud.direct
- ui.compositor.screenshot
- system.* (most)

A non-KikiSigned app requesting these fails install.

### Granting and revocation

Grants:

- Per-app, per-user.
- Stored in the gate's grant table (redb).
- Persisted across reboots.
- Audit log records each grant.

Revocations:

- User can revoke at any time.
- Revocation effective on next call.
- Apps may need to re-prompt; gracefully degraded.

### Adding new capabilities

The taxonomy is owned by the platform RFC process. To add:

1. Submit RFC describing the capability, default disposition, prompts, examples.
2. Discussion period.
3. If accepted, added to canonical taxonomy.
4. Apps can declare it after a deprecation cycle.

Apps cannot define their own capabilities. App-specific permissions live within the app and are not visible to the gate.

## Interfaces

### Programmatic

```rust
pub enum Capability {
    DataRead { domain: DataDomain },
    DataWrite { domain: DataDomain, action: WriteAction },
    DeviceUse { resource: DeviceResource },
    NetworkOutbound { scope: NetScope },
    InferenceUse { class: InferenceClass },
    Agent { area: AgentArea, verb: AgentVerb },
    Voice { aspect: VoiceAspect },
    UI { area: UiArea, verb: UiVerb },
    System { service: SystemService, verb: SystemVerb },
    Sensitive { category: SensitiveCategory },
}

pub fn parse_capability(s: &str) -> Result<Capability>;
```

### CLI

```
agentctl cap list                       # full taxonomy
agentctl cap show <id>                  # detail
agentctl cap grants <user>              # per-user grants
agentctl cap grants <app>               # per-app grants
agentctl cap revoke <user> <app> <cap>
```

## State

The taxonomy itself is static. Per-user grants persistent in redb.

## Failure modes

| Failure | Response |
|---|---|
| Unknown capability requested | reject; suggest closest |
| Invalid namespace | reject |
| Wildcard in restricted slot | reject |
| Grant table corrupt | revert to deny-all; alert |

## Performance contracts

- Capability parse: <1µs.
- Lookup in grant table (redb): <2µs typical.

## Acceptance criteria

- [ ] All listed namespaces have at least one capability.
- [ ] Each capability has a documented default disposition.
- [ ] Capability identifiers are stable; no renames.
- [ ] Apps cannot define capabilities outside the taxonomy.
- [ ] Grants are per-user, persistent, audited.
- [ ] Revocation effective on next call.

## References

- `03-runtime/CAPABILITY-GATE.md`
- `00-foundations/PRINCIPLES.md`
- `10-security/PRIVACY-MODEL.md`
- `10-security/HARDCODED-RESTRICTIONS.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
