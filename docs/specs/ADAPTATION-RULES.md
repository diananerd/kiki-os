---
id: adaptation-rules
title: Adaptation Rules
type: SPEC
status: draft
version: 0.0.0
implements: [adaptation-rules]
depends_on:
  - canvas-model
  - design-tokens
  - accessibility
depended_on_by: []
last_updated: 2026-04-30
---
# Adaptation Rules

## Purpose

Specify the rules that adapt UI behavior and appearance to current conditions: battery, idle, DND, accessibility profile, locale, presence. Adaptation is declarative; rules trigger on conditions and apply token overrides + behavioral flags.

## Inputs

- System signals (battery percent, AC state, idle time, network)
- User mode (DND, focus mode, child mode, accessibility profile)
- Locale (language, region, time zone, RTL)
- Presence (in front of device, paired remote, away)

## Outputs

- Active token overrides
- Behavioral flags (disable animations, simplify chrome)
- Layout intent fallbacks
- Block visibility changes (e.g., hide cost graphs on low battery)

## Rule shape

```toml
[rule.battery_low]
when = "battery_pct < 15 && !on_ac"
overrides = [
    { token = "motion.duration.*", value = "0ms" },
    { token = "shadow.*", value = "none" },
    { flag = "disable_idle_animations" },
    { flag = "minimal_status_bar" },
]
```

Each rule has a name, a condition, and a list of overrides/flags. Rules are evaluated continuously; matches activate; no-match deactivates.

## Built-in rules

### battery_low

`battery_pct < 15 && !on_ac`. Disables motion, hides cost graphs, dims accents.

### battery_critical

`battery_pct < 5 && !on_ac`. Adds a banner; reduces refresh rate; disables wake-word listening unless on-AC override.

### idle

`idle_time > 60s`. Dims chrome; pauses ambient animations; the canvas dims.

### dnd

User-set. Hides mailbox count; suppresses prompts (queued not shown until exit DND); voice barge-in still works.

### child_mode

User-set per-user. Restricts capabilities; simplifies vocabulary; bigger touch targets; locked settings.

### high_contrast

Accessibility profile. Swaps token palette; doubles focus-ring width; outlines on all interactive elements.

### large_text

Accessibility profile. Scales typography; relaxes density; falls back layout intents to single-column.

### reduced_motion

Accessibility profile. Sets all motion durations to 0; disables transitions.

### switch_access

Accessibility profile. Activates the switch-access input remapper; menus replace gestures.

### rtl

`locale.direction == "rtl"`. Mirrors layouts; right-aligns text; the status bar order reverses.

### narrow_output

`output.width < threshold`. Layout intents fall back per their rules.

### focus_mode

User-invoked. Hides status bar; activates `focus` intent; mutes notifications.

## Composition

Multiple rules can be active simultaneously. Conflicts resolve by *most-restrictive wins*:

- Smaller motion duration wins
- More-contrast token wins
- More-restrictive capability wins

Order:

```
1. base theme
2. user theme + preferences
3. accessibility overrides (always allowed to make things more accessible)
4. user mode overrides (DND, child mode)
5. system condition overrides (battery, idle)
```

Higher tiers can never override accessibility in the *less* accessible direction.

## Hot evaluation

Rules are evaluated on every relevant signal change. Token resolution invalidates affected components; agentui re-renders only the affected subtrees.

## Per-user

Each user has their own active rule set; switching users activates their preferences.

## Discoverability

```
kiki-ui adaptation status              # current active rules
kiki-ui adaptation simulate <rule>     # apply one rule for testing
```

## Authoring

System rules ship in the OS image. Users can author custom rules via Settings (limited surface; mostly toggling and parameterizing).

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Condition unparseable            | reject; log                    |
| Token reference unresolved       | fall back; log                 |
| Conflict in non-accessibility    | most-restrictive wins; log     |
| Adaptation oscillates            | hysteresis on threshold        |
|                                  | conditions                     |

## Performance

- Evaluate all rules: <500µs
- Apply overrides + repaint: <16ms

## Acceptance criteria

- [ ] All built-in rules present and functional
- [ ] Composition rule (most-restrictive wins) holds
- [ ] Accessibility overrides cannot be reduced
- [ ] Hot evaluation; no restart needed
- [ ] Per-user rule isolation

## References

- `07-ui/CANVAS-MODEL.md`
- `07-ui/DESIGN-TOKENS.md`
- `07-ui/ACCESSIBILITY.md`
- `07-ui/STATUS-BAR.md`
- `01-architecture/HARDWARE-ABSTRACTION.md`
## Graph links

[[CANVAS-MODEL]]  [[DESIGN-TOKENS]]  [[ACCESSIBILITY]]
