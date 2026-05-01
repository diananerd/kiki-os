---
id: canvas-model
title: Canvas Model
type: SPEC
status: draft
version: 0.0.0
implements: [canvas-model]
depends_on:
  - shell-overview
  - agentui
  - layout-intents
  - block-types
depended_on_by:
  - accessibility
  - adaptation-rules
  - agentui
  - block-types
  - blocks-api
  - command-bar
  - layout-intents
  - status-bar
  - task-manager
  - workspaces
last_updated: 2026-04-30
---
# Canvas Model

## Purpose

Specify the canvas: the typed scene graph the agent builds and agentui renders. The canvas is *the* surface the user sees; it is composed by the agent, not by individual apps.

## Why a canvas, not windows

Windows fragment attention and complicate accessibility. A canvas is a single composition the agent reasons about as a whole. The user sees one coherent view at a time per workspace; the agent decides what blocks to show, in what arrangement.

## Inputs

- The agent's intent (the response, the prompt, the data to display)
- The user's current task and active workspace
- Adaptation rules (battery, idle, DND, locale, accessibility)
- Block contributions from apps

## Outputs

- A scene graph rendered by agentui
- An accessibility tree (mirrored)
- An ops log for diffing across frames

## Structure

A canvas is a tree:

```
Canvas
├── statusBar (fixed-zone)
├── workspaceSwitcher (fixed-zone)
├── content (variable; layout intent applies here)
│   ├── Block(...)
│   ├── Block(...)
│   └── ...
├── commandBar (transient overlay)
├── taskManager (overlay)
└── prompts (overlay; consent prompts, voice transcript, etc.)
```

The fixed zones (status bar, workspace switcher) are always rendered the same way. The content region uses one of a small set of layout intents (see `LAYOUT-INTENTS.md`).

## Block

Every renderable thing is a Block. Blocks have:

- `kind` (one of the block types in `BLOCK-TYPES.md`)
- A typed payload (varies per kind)
- Layout hints (size class, importance, sticky/dismissible)
- Accessibility metadata (label, role, description)

Examples:

- `Block(kind=text, content="...", role=assistant_message)`
- `Block(kind=app_surface, app="kiki-music", view_id=now_playing)`
- `Block(kind=image, src=...)`
- `Block(kind=web, url=..., capabilities_required=[...])`

## Reconciler

The agent doesn't push pixels; it pushes a *target canvas* (or a delta from the previous one). The reconciler diffs and applies:

```
prev = current scene graph
next = target canvas
diff = compute_diff(prev, next)
for op in diff:
  apply(op)         # add, remove, update, move
emit_animations(op)
schedule_repaint()
```

The diff is computed by stable ids (the agent assigns block ids that persist across re-emits). Without ids, blocks would re-mount on every change; with ids, animations behave naturally.

## Ops log

Each frame's diff is appended to a per-session ops log. Useful for:

- Replay (debugging, testing)
- Audit (what did the user see at time T?)
- Crash recovery (rebuild scene graph from log)

The log is bounded; old entries are dropped.

## Layout intents

The content region declares an intent (one of ~6-8). agentui resolves the intent into concrete positions per output and theme. Examples:

- `single-card` — one centered block
- `list` — vertical list
- `split` — two side-by-side
- `dashboard` — grid of small cards
- `focus` — one block, full screen

See `LAYOUT-INTENTS.md`.

## Sticky and transient

Blocks can be:

- `sticky` — survive most layout changes (the current task block)
- `transient` — auto-dismiss after a TTL or interaction
- `pinned` — user-pinned; persists across workspace switches if scoped global

## Focus model

Exactly one block holds focus at a time per workspace. Focus determines:

- Where keyboard input goes
- Which block reads voice context for "this"
- Which block's accessibility tree is announced first

Focus follows touch/keyboard navigation; the agent can request focus shift programmatically.

## Multi-output

A canvas can target multiple outputs (e.g., a docked Kiki with an external display). Layout intents declare per-output behavior; the simplest is "mirror" or "extend with status bar duplicated."

## Capabilities

Rendering a block of `kind=app_surface` requires the app to have its surface registered with agentd. Web blocks check `network.outbound` capability for the destination. Sensitive data blocks honor the user's privacy mode.

## Animations

Declarative: the reconciler emits hint events ("block X moved from A to B"); agentui plays the animation. Adaptation rules can disable animations (battery, accessibility profile).

## Streaming content

A streaming block (e.g., assistant tokens) updates in place. The reconciler handles this efficiently by treating the block content as a stream rather than a sequence of full updates.

## Testing

A canvas can be serialized to JSON for snapshot tests. The reconciler is deterministic given inputs.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Block kind unknown               | render placeholder; log        |
| Cyclic id assignment             | refuse; agent must fix         |
| Layout intent invalid            | fall back to `list`            |
| Adaptation rule contradicts      | most-restrictive wins          |
|                                  |                                |

## Performance

- Diff compute: <2ms p99 for typical canvases
- Reconciler apply: <5ms p99
- Full redraw: <16ms (frame budget)

## Acceptance criteria

- [ ] Stable ids preserve block identity across deltas
- [ ] Layout intents render predictably
- [ ] Ops log reproduces a frame on replay
- [ ] Accessibility tree matches scene graph

## References

- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/AGENTUI.md`
- `07-ui/LAYOUT-INTENTS.md`
- `07-ui/BLOCK-TYPES.md`
- `07-ui/WORKSPACES.md`
- `07-ui/ADAPTATION-RULES.md`
- `07-ui/ACCESSIBILITY.md`
## Graph links

[[SHELL-OVERVIEW]]  [[AGENTUI]]  [[LAYOUT-INTENTS]]  [[BLOCK-TYPES]]
