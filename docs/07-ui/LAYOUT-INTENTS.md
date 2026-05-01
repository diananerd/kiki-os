---
id: layout-intents
title: Layout Intents
type: SPEC
status: draft
version: 0.0.0
implements: [layout-intents]
depends_on:
  - canvas-model
  - design-tokens
depended_on_by:
  - block-types
  - canvas-model
last_updated: 2026-04-30
---
# Layout Intents

## Purpose

Specify the small set of layout patterns the agent can declare for the content region. Intents are typed, named, and bounded. The agent picks one; agentui resolves it into geometry per output, theme, and adaptation rules.

## Why intents (not free-form layout)

Free-form layout invites inconsistency. A small typed catalog gives:

- Predictable behavior across surfaces
- Designable theming (intents have known anchors)
- Reasonable fallbacks when constraints change (small screen, accessibility)
- A short list of patterns the user learns once

## The intents

### single-card

One block, centered, sized to content with theme-defined min/max.

Use: a single answer card, a single confirmation prompt.

### list

Vertical list of blocks, scrollable. Each block sized to content with consistent spacing.

Use: messages, notifications, search results.

### split

Two blocks side by side, primary larger. On narrow outputs, falls back to `list`.

Use: an article + actions, a map + details.

### dashboard

Grid of small cards. Min cell size enforced; cells reflow to available width.

Use: status, fleet view, multi-source summaries.

### focus

A single block fills the available area, no chrome around it. Status bar may be hidden per adaptation.

Use: a video, a cooking timer, a focus mode for reading.

### conversation

Chat-like layout: turn-aligned messages, auto-scroll, sticky composer.

Use: live agent conversation.

### timeline

Horizontal scrollable timeline with anchored blocks.

Use: schedule view, history.

### inspector

Two-pane: list on the left, detail on the right. Falls back to drill-down on narrow.

Use: settings, audit log review, memory exploration.

That's eight intents. Keep it bounded.

## Common parameters

Each intent accepts:

- `density` (compact | comfortable | spacious; defaults derived from theme)
- `accent` (string token referencing a design palette role)
- `responsive` (allow fallbacks; default true)
- `scroll` (bool; default true for long content)
- `safe_area` (bool; respect system bars)

## Resolution

```
resolve(intent, blocks, output, theme, adaptation):
  geometry = layout_for(intent, output.size_class)
  if adaptation.minimal: simplify(geometry)
  if adaptation.large_text: scale(geometry)
  arrange(blocks, geometry)
  return scene_graph_subtree
```

The output's size class (compact / regular / large) drives breakpoints; theme provides spacing and typography; adaptation can simplify or scale.

## Fallbacks

Some intents have no sensible rendering on small outputs:

| Intent      | Fallback when narrow      |
|-------------|----------------------------|
| split       | list                       |
| dashboard   | list (1-col)               |
| inspector   | list with drill-down        |
| timeline    | list (date-grouped)         |

Single-card, list, focus, conversation work everywhere.

## Sticky zones interaction

The content region sits between the status bar (top) and the workspace switcher (bottom or side per orientation). Layout intents respect these zones; they do not draw under fixed zones.

The command bar and prompts overlay the content region without changing its layout (transparent backdrop or shifted on attention).

## Accessibility considerations

- Each intent has a defined reading order for screen readers
- Focus traversal follows the reading order
- Density modes never produce target sizes below 44×44pt
- High-contrast theme works for all intents

## Examples

### Conversation

```
{ kind: "conversation", blocks: [
    { kind: "text", role: "user", content: "..." },
    { kind: "text", role: "assistant", content: "..." },
    { kind: "tool_call", role: "tool", payload: {...} },
    ...
] }
```

### Dashboard

```
{ kind: "dashboard", density: "comfortable", blocks: [
    { kind: "card", title: "Battery", value: "78%" },
    { kind: "card", title: "Network", value: "Wi-Fi (Casa)" },
    { kind: "card", title: "Memory", value: "OK" },
    ...
] }
```

### Inspector

```
{ kind: "inspector", left: [...], right: { ... } }
```

## Anti-patterns

- **Custom one-off intents per app.** Use the catalog or extend it via RFC.
- **Embedding intent inside a block.** Blocks belong to intents, not the other way.
- **Hidden chrome that ignores adaptation.** Adaptation must always succeed; if it can't, fall back to `list`.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Intent unknown                   | fall back to `list`            |
| Block kind incompatible with     | render block as placeholder    |
| intent                           |                                |
| Insufficient space               | scroll; if scroll disabled,    |
|                                  | drop low-priority blocks       |

## Acceptance criteria

- [ ] Eight intents render correctly across size classes
- [ ] Fallbacks engage on narrow outputs
- [ ] Density and theme tokens applied
- [ ] Reading order matches accessibility tree

## References

- `07-ui/CANVAS-MODEL.md`
- `07-ui/BLOCK-TYPES.md`
- `07-ui/DESIGN-TOKENS.md`
- `07-ui/ADAPTATION-RULES.md`
- `07-ui/ACCESSIBILITY.md`
