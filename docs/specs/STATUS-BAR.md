---
id: status-bar
title: Status Bar
type: SPEC
status: draft
version: 0.0.0
implements: [status-bar]
depends_on:
  - shell-overview
  - canvas-model
  - design-tokens
depended_on_by: []
last_updated: 2026-04-30
---
# Status Bar

## Purpose

Specify the always-visible status bar at the top of the canvas. The bar shows critical state at a glance: time, voice, network, battery, mailbox, active workspace.

## Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ 9:42 AM   ⏵ Workspace 1   ◉ listening   Wi-Fi   78% ▮▮▮▯  📬 3  │
└──────────────────────────────────────────────────────────────────┘
```

Left to right (LTR locales):

- Time (locale-aware)
- Active workspace name
- Voice state pill
- Network (icon + name)
- Battery (icon + percent)
- Mailbox (count of unread/important)

Order is reflected in RTL locales; spacing is tokenized.

## Visibility

- Default: always visible
- Focus mode (G8): hidden by default; reappears on edge swipe top
- Lock screen: shown but in reduced detail (no mailbox count)

## Behavior

### Time

Real-time, updated every minute (and every second if seconds are configured to show). Locale-aware format.

### Workspace

Tap opens the workspace switcher; long-press opens the workspace properties.

### Voice state

A pill that shows current voice state:

- Idle (no pill)
- Listening (animated mic icon)
- Transcribing (subtle spinner)
- Speaking (animated waveform)
- Muted (mic crossed out)

Tap toggles mute.

### Network

Icon and current connection name. Tap opens network settings. Captive portal indicator if relevant.

### Battery

Percent and remaining estimate (when on battery). Tap opens power settings. Low-battery threshold pulses the icon.

### Mailbox

Count of unread + important items. Tap opens the mailbox.

## Adaptation

- Battery low: minimal updates (time updates per minute, not per second; animations damped)
- DND: mailbox counter hidden or muted
- Reduced motion: no animations
- Large text: bar grows; non-essential pieces drop

## Accessibility

- Each section is a keyboard-focusable element with a label
- Screen reader announces in a sensible order
- Status changes announce as a polite live-region update

## Capabilities

Status bar reads from privileged system surfaces:

- `system.read.power` for battery
- `system.read.network` for network
- `mailbox.read` for counts
- `audio.read.state` for voice state

Apps cannot impersonate status bar items.

## Customization

Limited. The user can:

- Hide seconds in the time
- Hide battery percent (icon only)
- Set mailbox to "important only"

We do not allow apps to inject items here. (Notifications go to the mailbox; permanent items would compete for attention.)

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| System surface unavailable       | item shows "—"; logs           |
| Time source jumps (NTP correct)  | smooth-update; no flash        |
| Voice state stale                | refresh on next event          |

## Acceptance criteria

- [ ] All six items visible by default
- [ ] Tap targets meet 44pt min
- [ ] Adaptation behaviors fire on triggers
- [ ] Screen reader order is stable
- [ ] No app injection paths

## References

- `07-ui/SHELL-OVERVIEW.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/DESIGN-TOKENS.md`
- `07-ui/ADAPTATION-RULES.md`
- `03-runtime/MAILBOX.md`
