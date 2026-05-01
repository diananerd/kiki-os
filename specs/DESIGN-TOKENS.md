---
id: design-tokens
title: Design Tokens
type: SPEC
status: draft
version: 0.0.0
implements: [design-tokens]
depends_on:
  - shell-overview
depended_on_by:
  - accessibility
  - adaptation-rules
  - component-library
  - layout-intents
  - status-bar
last_updated: 2026-04-30
---
# Design Tokens

## Purpose

Specify the typed design-token system that drives all visual styling. Tokens are layered: base palette → semantic roles → component bindings → adaptation overrides → user preferences. A single resolution path produces the values components consume.

## Eight categories

```
1. color           palette + semantic mappings
2. typography      families, weights, sizes, leading
3. spacing         scale (px or rem)
4. radius          corners and curves
5. shadow          elevation
6. motion          durations + easings
7. opacity         translucency scale
8. focus           ring color, width, offset
```

## Layered resolution

```
user_preferences        e.g., "always large text"
adaptation_overrides    battery-low, high-contrast, reduced-motion
theme_pack              system theme (light/dark + accent)
semantic_layer          token roles (button.primary.background)
base_palette            raw values (gray.700 = #2C2C2C)
```

A component reads a *token role* (e.g., `tokens.color.button.primary.background`); the resolver walks the layers in order from top to bottom, returning the first defined value.

## Themes

The default themes ship with the OS:

```
themes/
├── system-light/
├── system-dark/
├── high-contrast-light/
├── high-contrast-dark/
└── default-accent/   (red, blue, green, etc.)
```

A theme is a TOML file that overrides specific token paths. Themes can be combined (a high-contrast variant of dark).

```toml
# themes/system-dark.toml
[color.background.app]
value = "{base.gray.950}"

[color.background.surface]
value = "{base.gray.900}"

[color.border.subtle]
value = "{base.gray.800}"
```

## User preferences

Per-user overrides live at:

```
/var/lib/kiki/users/<uid>/ui/tokens.toml
```

Examples:

- `tokens.typography.body.size = 18` (larger default text)
- `tokens.color.accent = "{base.green.500}"`

These persist across sessions and survive theme changes.

## Adaptation overrides

Adaptation rules (battery, idle, accessibility) can layer on dynamic overrides:

```
battery_low:
  motion.duration.medium = 0
  shadow.* = "none"

reduced_motion:
  motion.duration.* = 0

high_contrast:
  color.* = (palette swap)
```

Adaptation overrides expire when their condition does.

## Semantic roles

Components never read base palette directly; they read semantic roles:

```
color.button.primary.background      → maps to base.accent.500
color.button.primary.text             → base.white
color.text.primary                    → base.gray.100 (dark) / 900 (light)
color.text.secondary                   → base.gray.300 / 700
color.border.subtle                    → base.gray.800 / 100
```

Adding a new component means adding new semantic roles; never a new base palette entry per component.

## Typography

```
typography.body          family + size + weight + line-height
typography.heading.1
typography.heading.2
typography.code
```

Sizes scale by user preference; min size is 14pt; max varies by component.

## Spacing scale

A 4pt-aligned scale: 0, 2, 4, 8, 12, 16, 24, 32, 48, 64. Components reference these by name (`spacing.md = 16`).

## Radius scale

`none, sm (4), md (8), lg (12), xl (16), full (9999)`.

## Motion

```
motion.duration.fast        100ms
motion.duration.medium      250ms
motion.duration.slow        400ms

motion.easing.standard      cubic-bezier(0.2, 0, 0, 1)
motion.easing.decelerate    cubic-bezier(0, 0, 0.2, 1)
```

Components reference durations and easings; never inline.

## Hot-swap

Theme changes resolve at runtime; agentui invalidates resolved tokens and re-renders. No restart needed.

## Validation

Build-time:

- All semantic roles defined in the default theme
- Component references resolve against a default theme
- No raw color values in components (lint)
- All themes parsed and resolved against semantic role list

## Anti-patterns

- **Inlining colors in components.** Always use tokens.
- **Themes that don't define a semantic role.** The default catches it; custom themes must too.
- **User preference that breaks accessibility.** Min size, focus-ring presence are non-overridable.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Token reference unresolved       | fall back to default value;    |
|                                  | log                            |
| Theme parse error                | refuse to load that theme;     |
|                                  | use system default             |
| User preference invalid          | reject; surface in settings    |
| Adaptation override conflict     | most-restrictive wins (smaller |
|                                  | motion, more contrast, etc.)   |

## Performance

- Token resolve (cached): <100ns
- Token resolve (cold): <10µs
- Theme swap: <100ms total

## Acceptance criteria

- [ ] All eight categories present
- [ ] Layered resolution implemented
- [ ] Themes hot-swap without restart
- [ ] User preferences honored across reboots
- [ ] Adaptation overrides apply on the right triggers
- [ ] Lint blocks raw values in components

## References

- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/ADAPTATION-RULES.md`
- `07-ui/ACCESSIBILITY.md`
- `07-ui/AGENTUI.md`
