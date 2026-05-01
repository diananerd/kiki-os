---
id: accessibility
title: Accessibility
type: SPEC
status: draft
version: 0.0.0
implements: [accessibility]
depends_on:
  - shell-overview
  - agentui
  - canvas-model
  - input-pipeline
  - design-tokens
depended_on_by:
  - adaptation-rules
  - input-pipeline
last_updated: 2026-04-30
---
# Accessibility

## Purpose

Specify the accessibility model: the AccessKit tree, AT-SPI bridge, keyboard and switch access, screen reader compatibility, and the non-negotiables every component must meet. Accessibility is not a feature; it is a baseline.

## Architecture

```
agentui scene graph
        │
        ▼
 AccessKit tree
        │
        ▼
 AT-SPI bridge (atspi-rs)
        │
        ▼
 Linux assistive tech
   (Orca, espeak, switch software, ...)
```

AccessKit is a cross-platform accessibility tree library. AT-SPI is the Linux assistive-tech bus. The bridge translates between them.

## Roles

Every block has an accessibility role:

```
heading, button, link, list, listitem, form, textbox, checkbox,
radio, slider, image, toolbar, dialog, status, progress,
menu, menuitem, tab, tabpanel, region, banner, navigation
```

Roles are required. The build lints any component without one.

## Labels and descriptions

- Every interactive element has a label
- Every image has alt text or `decorative=true`
- Every form field has a label and (where applicable) a hint
- Status updates use polite live regions; alerts use assertive

## Keyboard navigation

Every action reachable via touch or pointer is reachable via keyboard. Tab cycles through interactive blocks; arrow keys navigate within composite blocks (lists, grids, menus). Esc dismisses overlays. Enter activates.

The reading order matches the visual order in LTR; mirrored in RTL.

## Switch access

For users with motor differences, switch access lets a single button cycle through actions:

- Auto-scan: highlights the next item every N seconds; user presses to select
- Step-scan: user presses to advance, holds to select
- Dwell-select: pointer dwell time triggers select

Settings configure timing and which mode. The input pipeline implements switch access without the agentui developer having to think about it per-block.

## Screen reader compatibility

Tested against:

- Orca (the default Linux screen reader)
- BRLTTY for braille displays
- Custom espeak-based readers

Standard AT-SPI properties (name, description, role, value, state) are populated; live regions announce updates politely or assertively.

## Reduced motion

When the user enables reduced motion, all animations resolve to 0 duration via the design-tokens layer. Components that have an animated variant have a non-animated equivalent.

## High contrast

The high-contrast theme increases contrast ratios beyond WCAG AAA where reasonable. Focus rings are doubled in width; outlines appear on all interactive elements regardless of focus.

## Large text

User-set typography scale (1×, 1.25×, 1.5×, 2×). Layout intents fall back to single-column where needed; touch target minimums grow proportionally.

## Color independence

No information is conveyed by color alone. Status uses both color and icon/label. Charts use shapes/patterns + colors.

## Touch target minimums

44×44 pt minimum for any interactive element. Density modes scale up; never down.

## Voice as accessibility

Voice is a first-class input modality, not a substitute. Every action reachable by gesture or keyboard is also voice-addressable when voice is on. Conversely, voice never replaces non-voice paths (silent users matter).

## Self-test

```
kiki-ui a11y check
```

Runs an in-process audit:

- Every block has a role and label
- Tab order is consistent
- No color-only information
- Reduced-motion respected
- High-contrast theme produces sufficient contrast
- Live regions announce correctly

CI runs this against test canvases; releases fail on regressions.

## Localization interaction

Locale changes can affect screen-reader voice; the OS picks a matching TTS voice. RTL mirroring is automatic via the layout system.

## Settings

```
Settings → Accessibility
   • Screen reader: enabled / off
   • Switch access: configuration
   • Reduced motion: on / off
   • High contrast: on / off
   • Large text: scale slider
   • Color filter: none / protanopia / deuteranopia / tritanopia
   • Voice prompts: on / off
```

User preferences hot-apply.

## Anti-patterns

- Custom focus rings that suppress the default
- Animations that can't be disabled
- Color-only state indication
- Tooltips as the only label
- Modal dialogs without focus trap

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| AccessKit tree out of sync       | refresh on next render         |
| AT-SPI bridge crash              | restart; tree republishes      |
| Component missing role/label     | lint blocks build              |
| Switch access timing too slow    | adjustable; default sane       |

## Acceptance criteria

- [ ] AccessKit tree complete
- [ ] AT-SPI bridge functional with Orca
- [ ] Every component passes a11y lint
- [ ] All adaptation rules functional
- [ ] CI gate on a11y check

## References

- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/AGENTUI.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/INPUT-PIPELINE.md`
- `07-ui/DESIGN-TOKENS.md`
- `07-ui/ADAPTATION-RULES.md`
