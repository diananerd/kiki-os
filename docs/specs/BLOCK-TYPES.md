---
id: block-types
title: Block Types
type: SPEC
status: draft
version: 0.0.0
implements: [block-types]
depends_on:
  - canvas-model
  - layout-intents
  - component-library
  - browser-engine
depended_on_by:
  - blocks-api
  - browser-engine
  - canvas-model
  - component-library
  - render-api
last_updated: 2026-04-30
---
# Block Types

## Purpose

Specify the kinds of blocks that can appear on the canvas. Each kind has a typed payload, declared capability requirements, and rendering rules.

## The four kinds

### native

Built-in component from the standard library. Most blocks are native:

- text
- card
- list
- form / input
- button / action
- image
- chart
- code
- table
- progress / status

Native blocks render via Slint with theme tokens applied.

### app_surface

A view contributed by an installed app. The app declares views in its manifest; the agent references them by `(app_id, view_id)`. agentui fetches the rendered subtree from the app via Cap'n Proto.

```
{ kind: "app_surface",
  app: "kiki-music",
  view: "now-playing",
  params: { track: "..." } }
```

The surface is sandboxed to the app's capability scope. The agent composes it with native blocks around it.

### web

A web view rendered by Servo. Used for blocks whose content is naturally HTML (an article, a documentation page, a constrained third-party widget).

```
{ kind: "web",
  url: "https://...",
  network_required: true,
  capabilities_required: ["network.outbound.host:..."] }
```

Web blocks are subject to:

- Network capability gating (the URL host)
- A constrained Servo profile (no cross-origin storage, no popups)
- A size cap and a load timeout

### system

System-rendered blocks for system info that doesn't belong to any app:

- battery
- network
- update status
- audit summary
- mailbox
- workspaces overview
- voice state

These have privileged access to system data via agentd's system surfaces.

## Common metadata

```rust
struct Block {
  id: String,                 // stable across deltas
  kind: BlockKind,
  payload: BlockPayload,
  importance: Importance,     // default | hint | critical
  size_class: SizeClass,      // small | medium | large | flex
  sticky: bool,
  dismissible: bool,
  ttl: Option<Duration>,
  a11y: AccessibilityHints,
  capabilities_required: Vec<Capability>,
}
```

## Native catalog

A curated list of native blocks ships in the component library (see `COMPONENT-LIBRARY.md`). Each native block has:

- A typed payload
- A theme binding
- An accessibility role
- A size policy

Examples:

```
text:
  content: String
  role: "user" | "assistant" | "tool" | "system" | "annotation"
  markdown: bool
  truncate: enum

card:
  title: String
  subtitle: Option<String>
  body: BlockChildren
  footer: BlockChildren

list:
  items: List<Block>
  separators: bool

form:
  fields: List<FormField>
  submit_label: String
  cancel_label: Option<String>

action:
  label: String
  variant: "primary" | "secondary" | "destructive"
  intent: ActionIntent

chart:
  kind: "line" | "bar" | "pie"
  series: List<DataSeries>

code:
  language: String
  content: String
  line_numbers: bool

progress:
  value: f32
  label: String
  variant: "linear" | "circular"
```

## App surface contract

An app contributes views via its tool registry registration:

```toml
[[ui_views]]
id = "now-playing"
title = "Now Playing"
provides = ["focus.media", "media.controls"]
size_class = "flex"
required_capabilities = ["audio.read.metadata"]
```

agentui fetches the view's render content via Cap'n Proto when the agent composes a canvas with that view referenced.

## Web block constraints

- URL must match a granted host capability.
- Default Servo profile: no JS unless the block declares `js_required = true` (an explicit grant).
- No cross-origin storage; per-block storage cleared on canvas dismiss.
- Max load time 8s; on timeout, render error placeholder.

## System block payloads

Each system block has a stable schema; the agent doesn't compose its internals, just declares "show the network status here." agentui pulls the live data from agentd.

## Animations

Each block kind declares default animations (mount, unmount, change). Adaptation can disable animations.

## Capabilities

Block-kind-specific capabilities:

- `web` → `network.outbound.host:<host>`
- `app_surface` → `app.<id>.surface.read`
- `system.audit` → `audit.read`
- `system.mailbox` → `mailbox.read`

The capability gate runs at render time; failed checks render a placeholder.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Unknown block kind               | render placeholder; log        |
| App surface unavailable          | render placeholder until app   |
|                                  | reconnects                     |
| Web block fails to load          | error block with retry         |
| Capability denied                | placeholder with grant CTA     |

## Performance

- Native block render: <1ms p99
- App surface fetch + render: <50ms p99
- Web block first paint: <800ms p99

## Acceptance criteria

- [ ] All four kinds render correctly
- [ ] Capability gating runs at render time
- [ ] App surfaces sandboxed to app scope
- [ ] Web blocks isolated per block
- [ ] System blocks update live

## References

- `07-ui/CANVAS-MODEL.md`
- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/COMPONENT-REGISTRY.md`
- `07-ui/BROWSER-ENGINE.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
## Graph links

[[CANVAS-MODEL]]  [[LAYOUT-INTENTS]]  [[COMPONENT-LIBRARY]]  [[BROWSER-ENGINE]]
