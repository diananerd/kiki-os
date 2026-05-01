---
id: meta-packages
title: Meta-Packages
type: SPEC
status: draft
version: 0.0.0
implements: [meta-packages]
depends_on:
  - artifact-catalog
  - oci-native-model
depended_on_by:
  - release-cadence
last_updated: 2026-04-30
---
# Meta-Packages

## Purpose

Specify the meta-package compositions: named bundles of artifacts that compose Kiki for a particular use case. A device's profile picks one meta-package as its baseline; from that, individual apps and components are added on top.

## Why meta-packages

Listing 30 artifacts every time is fragile. Meta-packages name a coherent bundle ("desktop", "headless", "developer") and refer to a versioned set of artifacts. Devices update the meta-package; the manager resolves to the underlying artifacts.

## Meta-packages

### desktop

Standard interactive Kiki experience. Includes:

- Base + interactive sysexts (cage, agentui, voice daemon)
- Standard apps (launcher, settings, audit, memory, files, terminal)
- Default profile + kid-friendly profile
- Default model set (LLM 8B, Whisper Medium, Kokoro)
- Standard components

### headless

Server-class Kiki without GUI. Includes:

- Base headless + system sysexts (no cage, no agentui, no voice)
- Headless apps (settings via TUI, audit, memory)
- Default profile
- LLM only (no ASR/TTS unless added)

### developer

Adds developer tooling on top of desktop:

- All of desktop
- Developer console app
- Terminal app with elevated capabilities
- Developer profile
- Developer prompts pack

### minimal

Small kiosk-style baseline:

- Base minimal
- Compositor + agentui only
- One profile (the user picks at provisioning)
- Smallest model set (Whisper Small, Piper TTS, LLM 8B)
- No standard apps

### accessibility-first

Same as desktop but with accessibility profile applied:

- All of desktop
- accessibility-first profile applied at install
- Switch-access defaults
- Larger text + high contrast

### secops

Security-research-focused profile:

- Base + interactive sysexts
- Tools relevant for security work (curated; gated)
- secops-engagement profile (for engagement-scoped capabilities)
- No general-purpose desktop apps unless added

## Composition

A meta-package is itself an OCI artifact whose config lists the included artifacts:

```toml
id = "kiki:meta/desktop"
version = "1.0.0"
description = "Standard interactive Kiki experience."

[base]
image = "kiki:system/base@1.5.0"

[sysexts]
include = [
    "kiki:system/agentd@1.4.2",
    "kiki:system/policyd@1.4.0",
    "kiki:system/inferenced@1.4.0",
    "kiki:system/memoryd@1.4.0",
    "kiki:system/toolregistry@1.4.0",
    "kiki:system/cage@1.2.0",
    "kiki:system/agentui@1.4.1",
    "kiki:system/voice-daemon@1.3.0",
]

[apps]
include = [
    "kiki:apps/launcher@1.4.0",
    "kiki:apps/settings@1.3.0",
    ...
]

[models]
include = [
    "kiki:models/llama-3.3-8b-q4@1.0.0",
    "kiki:models/whisper-medium@1.0.0",
    "kiki:models/kokoro-82m@1.0.0",
    ...
]

[profiles]
default = "kiki:profiles/default@2.0.0"
also_install = ["kiki:profiles/kid-friendly@2.1.0"]
```

## Updates

When a meta-package version bumps, it lists new pinned versions of its constituents. Devices on the meta-package channel update accordingly.

A user may pin a constituent to an older version (e.g., "stay on this app version"); the meta-package update warns about deviations.

## Custom meta-packages

Maintainers can publish their own meta-packages under their namespaces (`kiki:<vendor>/meta/<name>`). A device's profile chooses one to track.

## Reproducibility

Meta-packages reference exact digests, not floating tags. A reference manifest captures the entire constituent set.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Missing constituent              | meta-package install fails;    |
|                                  | retry; alert maintainer        |
| Cross-artifact incompatibility   | release blocked at CI          |
| User pin conflicts with bump     | warning; user resolves         |

## Acceptance criteria

- [ ] All meta-packages listed install end-to-end
- [ ] Update bumps coordinate constituent versions
- [ ] User pins respected with warnings
- [ ] Custom meta-packages from third-party namespaces work

## References

- `12-distribution/ARTIFACT-CATALOG.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/RELEASE-CADENCE.md`
- `03-runtime/UPDATE-ORCHESTRATOR.md`
