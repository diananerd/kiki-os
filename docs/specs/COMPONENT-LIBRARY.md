---
id: component-library
title: Component Library
type: SPEC
status: draft
version: 0.0.0
implements: [component-library]
depends_on:
  - block-types
  - design-tokens
depended_on_by:
  - block-types
  - component-registry
last_updated: 2026-04-30
---
# Component Library

## Purpose

Specify the standard catalog of native components that ship with agentui. The library is the toolbox for native blocks; consistent styling, accessibility, and behavior across the system come from a small, well-curated set.

## Contents

The library is organized by category:

```
components/
├── text/
│   ├── Heading
│   ├── Body
│   ├── Caption
│   └── Link
├── containers/
│   ├── Card
│   ├── List
│   ├── Section
│   └── Group
├── inputs/
│   ├── TextField
│   ├── Checkbox
│   ├── Radio
│   ├── Toggle
│   ├── Slider
│   ├── Stepper
│   ├── DatePicker
│   ├── TimePicker
│   ├── Combobox
│   └── Form
├── actions/
│   ├── Button
│   ├── ActionGroup
│   └── Menu
├── feedback/
│   ├── Spinner
│   ├── Progress
│   ├── Toast
│   └── Banner
├── media/
│   ├── Image
│   ├── Avatar
│   └── Video
├── data/
│   ├── Table
│   ├── DataGrid
│   ├── Chart  (delegates to chart engine)
│   └── Code
├── navigation/
│   ├── Tabs
│   ├── Breadcrumbs
│   ├── Stepper
│   └── BackLink
└── system/
    ├── StatusPill
    ├── BatteryIndicator
    ├── NetworkIndicator
    └── VoiceIndicator
```

About 40 components total. The list is bounded; new components require an RFC.

## Style discipline

- Each component has a typed prop schema
- Props are minimal; styling comes from design tokens
- Variants are enumerated, not free-form (`variant: "primary" | "secondary" | "destructive"`)
- No inline color or spacing — only token references

## Slint implementation

Components are Slint `.slint` files under `agentui/components/`:

```slint
import { tokens } from "../tokens.slint";
import { focus_ring } from "../mixins.slint";

component Button inherits Rectangle {
    in property <string> label;
    in property <string> variant: "primary";
    in property <bool> disabled: false;
    callback clicked();

    background: variant == "primary"
        ? tokens.color.button.primary.background
        : tokens.color.button.secondary.background;
    // ...
}
```

The build emits a single binary; components are not dynamically loaded.

## Accessibility built in

Every component has:

- A correct ARIA role / AccessKit role
- Keyboard navigation
- Reduced-motion variants
- High-contrast variants

These are not opt-in; they are part of the component contract.

## Theming

Components only reference tokens (see `DESIGN-TOKENS.md`). Theme changes don't require code changes; they replace token values.

## Localization

Component labels are not hardcoded. The library expects the caller to provide localized strings; built-in strings (e.g., "Cancel" in a dialog) are pulled from the per-locale string table.

## Versioning

The library has a semver; the OS image's agentui binary embeds a single version. Apps that contribute surfaces use whatever version their host runs (the surface protocol is the contract, not the component class hierarchy).

## Anti-patterns

- **Custom components per app injected as native.** Apps render their own subtrees in app_surface blocks.
- **Inline styling on a component.** Use variants or define a new component.
- **Components without keyboard navigation.** Build is rejected by lint.
- **Components without a11y role.** Build is rejected.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Component prop type mismatch     | render placeholder; log; agent |
|                                  | sees a typed error             |
| Localization missing             | fall back to default locale    |
| Token value missing              | fall back to spec default      |

## Performance

- Mount: <500µs per simple component
- Update: <200µs
- 1000 components on screen: feasible at 60FPS

## Acceptance criteria

- [ ] All ~40 components ship and pass a11y audit
- [ ] Tokens drive all styling
- [ ] Variants are enumerated; no free-form
- [ ] Reduced-motion and high-contrast variants exist
- [ ] Lint enforces a11y and keyboard nav

## References

- `07-ui/BLOCK-TYPES.md`
- `07-ui/DESIGN-TOKENS.md`
- `07-ui/COMPONENT-REGISTRY.md`
- `07-ui/ACCESSIBILITY.md`
