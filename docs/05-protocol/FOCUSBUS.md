---
id: focusbus
title: Focusbus
type: SPEC
status: draft
version: 0.0.0
implements: [focusbus]
depends_on:
  - dbus-integration
  - nats-bus
  - capability-gate
depended_on_by: []
last_updated: 2026-04-30
---
# Focusbus

## Purpose

Specify the cross-app focus coordination surface
`org.kiki.Focus1`. The focusbus tells the agent and other
apps what the user is currently looking at, working on, or
listening to. It replaces ad-hoc "what's playing right now"
hacks per app and gives the agent a coherent view of user
attention.

## Why a focusbus

The agent often needs to know:

- "What track is playing?" — to do "skip" without naming
  the player
- "Which document is the user editing?" — to summarize the
  selection or run a transformation
- "Which conversation is in front?" — to avoid notifying
  about the same thread

Without a shared protocol, every app must integrate with
every other app. With one, apps publish their state and
others subscribe.

This is the same pattern as MPRIS for media players, but
generalized: any app may declare focus context, in any
domain. We do not reuse MPRIS directly because we want a
broader vocabulary; MPRIS is a useful subset and apps that
implement it are bridged into focusbus by an adapter.

## Scope

What the focusbus represents:

- The user's current foreground content, per app
- Selection ranges within content
- Active media playback state
- Active calls / conversations

What it does *not* represent:

- Document contents (that would be a privacy disaster).
  Focus is a pointer, not a payload.
- Per-keystroke cursor activity (too noisy)
- Anything from non-foreground tabs unless the app
  explicitly publishes it

## Inputs

- App-published focus snapshots
- Wayland surface activation events (foreground tracking)
- MPRIS bridge for legacy media apps

## Outputs

- A read-only view of current focus per app
- Notifications on changes
- An aggregated "primary focus" the agent can query

## Behavior

### Focus context shape

Each app publishes a `FocusContext` to the focusbus. The
shape is intentionally generic:

```capnp
# focus.capnp
struct FocusContext {
  appId @0 :Text;
  surfaceId @1 :Text;          # which window/surface
  domain @2 :Text;             # "media", "document", "chat",
                               # "call", "shell", "browser",
                               # "code", "image", ...
  title @3 :Text;              # human-readable
  uri @4 :Text;                # canonical reference if any
  selection @5 :Text;          # short hint, NOT the content
  media @6 :MediaState;        # for "media" domain
  document @7 :DocumentState;  # for "document" domain
  chat @8 :ChatState;          # for "chat" domain
  call @9 :CallState;          # for "call" domain
  custom @10 :List(KeyValue);  # additional fields
  timestamp @11 :UInt64;
}

struct MediaState {
  state @0 :MediaStateKind;    # playing | paused | stopped
  trackTitle @1 :Text;
  artist @2 :Text;
  album @3 :Text;
  position @4 :UInt32;          # seconds
  duration @5 :UInt32;
}

struct DocumentState {
  pages @0 :UInt32;
  currentPage @1 :UInt32;
  hasUnsavedChanges @2 :Bool;
  fileType @3 :Text;
}

struct ChatState {
  channel @0 :Text;
  unreadCount @1 :UInt32;
  participants @2 :List(Text);
}

struct CallState {
  with @0 :Text;
  durationSeconds @1 :UInt32;
  muted @2 :Bool;
}
```

Apps fill the fields they support. The agent treats absent
fields as "unknown".

### Privacy

Focus context is sensitive. Rules:

- Apps publish only what their user explicitly enables in
  app settings (default: title and domain only)
- The `selection` field is a hint, not the content; never
  publish full text
- Document URIs are normalized to remove tokens or query
  parameters that may contain auth
- Per-app a kill switch in settings: "do not publish focus"

The agent does not store focus context durably except as
part of the audit log when an action depends on it.

### Capability scoping

Subscribing to focusbus is gated by `focus.read.<domain>` or
`focus.read.all`. Default capabilities:

- The agent: `focus.read.all`
- The launcher: `focus.read.all`
- A third-party app: per-domain grants only, with user
  consent

Publishing requires the app's manifest to declare the
domain it owns. Apps can only publish their own domain
contexts (an audio player declares `media`; it cannot
publish a `chat` context).

### Wire surface

The focusbus is exposed on:

- **DBus**: `org.kiki.Focus1` (session bus)
- **NATS** mirror: `focus.changed`, `focus.cleared`

DBus is the well-known surface for apps; NATS mirrors for
internal subscribers.

```
org.kiki.Focus1
  Methods:
    Get(s app_id)            -> a{sv}     current context for app
    GetPrimary()              -> a{sv}     "the" focus
    List()                    -> a(sa{sv}) all apps
  Signals:
    Changed(s app_id, a{sv} context)
    Cleared(s app_id)
```

### Primary focus

`GetPrimary()` returns the most likely "what the user is
attending to right now". Heuristics:

1. The Wayland-foregrounded surface, if its app publishes
   focus
2. The most recently active media player (if `media.state =
   playing`)
3. The most recently active call (if any)
4. Falls back to "shell"

The agent uses `GetPrimary()` for "what's playing" and
"summarize this" intents.

### Update cadence

- Apps update focus on user-visible changes (not on every
  keystroke).
- Rate-limited: ≤2 updates per second per app.
- The MediaState `position` field is *not* meant for
  high-frequency seek updates; clients that need real-time
  position derive it from `playing` + `position` +
  wall-clock.

### Wayland surface activation

The compositor (cage) emits `surface_activated` events. The
focusbus daemon (a small task in agentd) tracks the active
surface; if the app owning the surface has a recent
focus context, it becomes the primary.

### MPRIS bridge

Existing MPRIS-only media players appear on the system bus
as `org.mpris.MediaPlayer2.<player>`. A bridge in agentd:

- Subscribes to MPRIS players on appearance
- Translates MPRIS metadata into FocusContext (domain=media)
- Republishes on the focusbus under the app's id

The bridge handles a subset of MPRIS sufficient for the
common cases.

### History and ttl

The focusbus is an in-memory cache. Each context has a TTL
of 30s (refreshed by app updates). When an app crashes or
is closed, its context is cleared either by an explicit
`Clear()` call or by TTL expiry.

The agent does not query historical focus from the bus; for
"what was I doing 5 minutes ago", it uses episodic memory.

### Voice integration

When the user says "play that song again" or "summarize
this":

1. Voice transcript arrives at the agent
2. The agent calls `Focus1.GetPrimary()`
3. It binds the deictic ("that", "this") to the focus
   context
4. It dispatches the appropriate tool (e.g., the music
   player's "play" or a summarizer over the document URI)

The capability gate runs before the tool dispatch; the focus
context is just the disambiguator.

### Anti-patterns

- Apps streaming the document body via `selection`
- Apps publishing focus they don't actually have
- Subscribers polling instead of listening to signals
- Logging focus context to durable storage outside audit

## Interfaces

### Programmatic (Rust SDK)

```rust
struct Focus {
    fn publish(&self, context: FocusContext) -> Result<()>;
    fn clear(&self) -> Result<()>;
    fn subscribe(&self) -> impl Stream<Item = (AppId, Option<FocusContext>)>;
    fn get_primary(&self) -> Option<FocusContext>;
}
```

### CLI

```
kiki-focus list                       # all apps with focus
kiki-focus primary                    # the current primary
kiki-focus subscribe                  # tail signals
kiki-focus clear <app>                # admin: drop a stale ctx
```

### App manifest declaration

```toml
[focus]
domain = "media"             # or "document", "chat", ...
publishes = ["state", "trackTitle", "artist", "position",
             "duration"]
defaults_off = false         # publish by default after install
```

## State

### In-memory only

- The current contexts per app
- Subscriber list
- TTL timers

### Persistent

- Per-app user preferences for focus publishing (in their
  settings store)

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| App publishes for a domain it    | reject; log; alert user        |
| doesn't own                      |                                |
| App publishes more than rate     | drop; log; rate-limit at       |
| limit                            | broker                         |
| MPRIS bridge can't parse player  | log; skip that player          |
| Subscriber crashes               | drop subscription; nothing     |
|                                  | else affected                  |
| Compositor disconnects           | bus continues without          |
|                                  | surface-activation hint;       |
|                                  | primary heuristic falls back   |

## Performance contracts

- Publish to subscribers: <1ms p99
- Get/GetPrimary: <500µs (cached)
- TTL eviction sweep: every 5s

## Acceptance criteria

- [ ] Apps publishing focus appear on the bus and are
      readable via DBus and NATS
- [ ] Capability gate enforces both publish-domain and
      subscribe scope
- [ ] MPRIS bridge translates legacy players correctly
- [ ] Primary focus heuristic is documented and predictable
- [ ] Settings can disable focus publishing per app
- [ ] No focus context persists across reboot

## Open questions

None.

## References

- `05-protocol/DBUS-INTEGRATION.md`
- `05-protocol/NATS-BUS.md`
- `03-runtime/AGENT-LOOP.md`
- `07-ui/CANVAS-MODEL.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/PRIVACY-MODEL.md`
