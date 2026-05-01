---
id: agent-bundle
title: Agent Bundle (.kab)
type: SPEC
status: draft
version: 0.0.0
implements: [agent-bundle]
depends_on:
  - subagents
  - procedural-memory
  - capability-taxonomy
depended_on_by:
  - publishing
last_updated: 2026-04-30
---
# Agent Bundle (.kab)

## Purpose

Specify the `.kab` (Kiki Agent Bundle) format: a packaged subagent configuration the user installs to extend or specialize their agent. A bundle is a SOUL extension + skills + a default scope + sometimes a custom inference target — wrapped in a single signed artifact.

## What's in a bundle

```
example.kab/                         OCI artifact (or tarball variant)
├── manifest.toml
├── soul-extension.md                 contributes to SOUL
├── recipes/                          skills the bundle ships
│   └── ...
├── tools/                            optional tool references
│   └── ...
├── prompts/                          curated prompts (if any)
│   └── ...
└── README.md
```

A bundle is *not* an app; it's a configuration profile applied to the agent loop. It can refer to apps and tools that must be installed separately.

## Manifest

```toml
id = "kiki:agents/coding-buddy"
version = "1.0.0"
title = "Coding Buddy"
description = "Specialized for software work; reasons aloud, prefers concise diffs."
authors = ["Acme"]
license = "MIT"

[applies_to]
mode = "subagent"                    # subagent | persona | profile-extension
trigger = "explicit"                  # explicit | intent | always

[scope]
capabilities_required = [
    "tool:filesystem.read",
    "tool:git",
    "tool:run.shell",
]
capabilities_locked = [
    "agent.memory.write.identity = denied",
]
loop_budget = 50                      # higher than default

[components]
soul_extension = "soul-extension.md"
recipes_dir = "recipes/"
prompts_dir = "prompts/"

[default_models]
prefer_thinking = true
fallback_local = true
```

## Use cases

- **Subagent**: a specialized teammate the user can call with a phrase ("ask coding buddy ...").
- **Persona**: a temporary persona the user adopts for a session.
- **Profile extension**: a profile that contributes recipes + SOUL fragments without locking the system.

The mode determines integration:

- subagent: registered with the subagent dispatcher; invoked via Subagents API
- persona: applied to the active workspace as a session overlay
- profile-extension: like a profile but lighter

## Installation

```
kiki agents install kiki:agents/coding-buddy
```

The user reviews the bundle's capabilities and the SOUL extension; on consent:

- SOUL extension placed under `SOUL.d/`
- Recipes copied to procedural/
- Prompts loaded into the agent's prompt registry (scoped)
- Subagent registration if applicable

## Signing

cosign + Sigstore. Same as everything else.

## Sandboxing

A bundle does not run code itself — it is configuration. The configuration applies to the agent loop, which runs with the system's existing capability gate. A malicious bundle cannot do anything the user has not already granted.

That said, a malicious SOUL extension could try to manipulate behavior; the user reviews the SOUL diff at install. The arbiter classifier observes runtime behavior either way.

## Versioning

Semver. Updates are diffed against the installed version; capability changes prompt.

## Sharing

Users can author and share .kab bundles:

```
kiki agents init my-bundle
# edit files
kiki agents pack my-bundle ./my-bundle.kab
kiki agents push registry.example/my-bundle:1.0
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Manifest invalid                 | reject install                 |
| Required tool unavailable        | install with warning;          |
|                                  | bundle disabled until tool     |
|                                  | installed                       |
| SOUL extension conflicts          | most-restrictive wins; show    |
|                                  | diff                            |

## Acceptance criteria

- [ ] Bundle artifact pulls + verifies
- [ ] SOUL extension applied with consent
- [ ] Recipes installed in procedural memory
- [ ] Subagent registration works for mode=subagent
- [ ] Audit log captures install / remove

## References

- `03-runtime/SUBAGENTS.md`
- `04-memory/IDENTITY-FILES.md`
- `04-memory/PROCEDURAL-MEMORY.md`
- `06-sdk/SOUL-FORMAT.md`
- `06-sdk/SKILL-FORMAT.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
- `10-security/COSIGN-TRUST.md`
