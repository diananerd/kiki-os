---
id: component-registry
title: Component Registry
type: SPEC
status: draft
version: 0.0.0
implements: [component-registry]
depends_on:
  - component-library
  - oci-native-model
  - cosign-trust
depended_on_by:
  - component-oci-format
last_updated: 2026-04-29
---
# Component Registry

## Purpose

Specify the system through which third-party UI components are distributed (as OCI artifacts), discovered, validated, and made available to apps. Apps don't ship arbitrary GUI code; they declare contributions in terms of either the standard component library or registered third-party components.

## Why a registry

A bounded set of components keeps the system coherent. Allowing arbitrary new ones via a signed registry gives apps room to extend without each one reinventing button styles.

## Distribution

- Components are OCI artifacts: `kiki:components/<name>@<version>`
- Signed with cosign + Sigstore (see `COSIGN-TRUST.md`)
- Built from a Slint manifest + .slint files + tokens override map
- Pulled by the toolregistry at install time

## Manifest

A component bundle's manifest:

```toml
id = "kiki:components/voice-waveform"
version = "1.0.0"
authors = ["Acme UI"]
license = "MIT"
component_type = "block"           # block | inline | inspector

[a11y]
role = "image"
description_required = true

[size]
default = "medium"
min_width = 200
min_height = 80

[capabilities_required]
audio_read_observe = false

[exports]
slint_module = "VoiceWaveform"
```

The manifest is parsed at install time; the registry validates it against the contract.

## Validation

At install:

- Manifest schema valid
- Slint module compiles without errors
- A11y role declared
- No restricted APIs used (file IO, network, raw input)
- Token references resolve against the standard token vocabulary
- Render in a sandboxed test harness with synthetic props

Failure rejects the install.

## Capabilities

Third-party components run in agentui's process; they cannot have arbitrary permissions. The lockdown:

- No filesystem, network, or shell access
- No JS or eval
- No raw input handling outside the component bounds
- Can only read props passed by the agent or app
- Can emit events declared in the manifest

This is enforced by the Slint module compiling against a constrained API surface; the registry ensures no other surface is reachable.

## Invocation

An app declares a component contribution:

```toml
[[ui_views]]
id = "voice-waveform-card"
component = "kiki:components/voice-waveform@1.0.0"
binding = { source = "audio.session.<id>" }
```

The agent composes the canvas; agentui resolves the component reference and instantiates it with the provided binding.

## Versioning

Components carry semver. agentui supports loading multiple versions concurrently; older apps use older versions until they update. Pinned versions ensure stability.

## Discovery

```
kiki-components list
kiki-components show <id>
kiki-components install <id>@<ver>
kiki-components remove <id>@<ver>
```

The registry pulls from configured channels (Kiki-signed by default).

## Theming

Components must reference design tokens; they cannot hardcode colors. Theme changes propagate without recompile.

## Localization

Components handle locale via the standard string-table mechanism; no hardcoded strings inside components.

## Anti-patterns

- **Reinventing standard components.** A "fancy button" should be a token theme of the standard Button.
- **Arbitrary side effects.** Components are pure-render; effects go through their app, not the component.
- **Cross-app coupling via component ids.** Components are per-bundle; sharing happens via tokens and conventions.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Validation fails                 | reject install                 |
| Token reference unresolved       | reject install (CI check)      |
| Runtime exception in render      | render placeholder; log;       |
|                                  | mark component as broken       |
| Signature invalid                | refuse install                 |

## Performance

- Component instantiation: <2ms
- Multi-instance memory: bounded by component implementation

## Acceptance criteria

- [ ] OCI bundles install with signature verification
- [ ] Manifest validation runs at install
- [ ] Constrained API surface enforced
- [ ] Versioned coexistence of multiple component versions
- [ ] Theme tokens applied dynamically

## References

- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/DESIGN-TOKENS.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `10-security/COSIGN-TRUST.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
## Graph links

[[COMPONENT-LIBRARY]]  [[OCI-NATIVE-MODEL]]  [[COSIGN-TRUST]]
