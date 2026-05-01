---
id: blocks-api
title: Blocks API
type: SPEC
status: draft
version: 0.0.0
implements: [blocks-api]
depends_on:
  - sdk-overview
  - kernel-framework
  - block-types
  - canvas-model
depended_on_by:
  - sdk-rust
last_updated: 2026-04-30
---
# Blocks API

## Purpose

Specify how an app emits UI blocks. Apps don't draw windows; they describe blocks the agent composes into the canvas. The Blocks API is small, declarative, and reactive — the app says "here's the current view"; the framework diffs and pushes updates.

## Hello world

```rust
#[view("now-playing")]
fn now_playing_view(state: &MyState) -> View {
    let track = state.queue.front();

    match track {
        Some(t) => view! {
            <Card title=t.title.clone() subtitle=t.artist.clone()>
                <Image src=t.cover_url.clone() alt=t.title.clone() />
                <Progress value=state.position label="position" />
                <ActionGroup>
                    <Button label="Pause" intent={cmd!(pause())} />
                    <Button label="Skip" intent={cmd!(skip())} />
                </ActionGroup>
            </Card>
        },
        None => view! { <Text content="Nothing playing." /> },
    }
}
```

The view function is a pure function from state to view. The framework calls it whenever relevant state changes; only differences are sent.

## Block types accessible

The full set of native blocks (see `BLOCK-TYPES.md`) is available as macros. Apps cannot define new block kinds inline; for new component shapes, ship a Component artifact.

## Reactivity

Views re-render automatically when:

- A field they read from state changes
- A subscribed event fires
- The framework's invalidation API is called explicitly

Performance: the framework uses fine-grained subscriptions; touching one field doesn't re-render unrelated views.

## Layout intents

A view can declare a layout intent:

```rust
#[view("dashboard", intent = "dashboard")]
fn dashboard_view(state: &MyState) -> View { ... }
```

The intent applies to the children of the view's root.

## Bindings to commands

Buttons and inputs bind to commands:

```rust
<Button label="Play" intent={cmd!(play_track(t.id))} />
<TextField bind=state.search_query />
```

`cmd!` produces a typed action descriptor; the framework dispatches the command when the user (or agent) activates it. Capability gates run on dispatch.

## Streaming content

For content that arrives incrementally:

```rust
<TextStream stream=token_stream />
```

The framework wires up the stream and pushes deltas as new tokens arrive.

## Reading focus

A view can request the current focus context:

```rust
fn lyrics_view(state: &MyState, focus: &Focus) -> View {
    let track = focus.media().and_then(|m| m.track_title.clone());
    view! { <Text content=lyrics_for(track) /> }
}
```

Focus access requires the right capability (declared in the manifest).

## A11y

Blocks include a11y info by default; views can add hints:

```rust
<Image src=cover alt={track.title.clone()} a11y_role="img" />
```

The component library enforces required hints; missing alt on an image is a build error.

## Localization

Strings come from the app's locale tables; the framework injects per-user locale:

```rust
view! { <Text content=t!("hello_world") /> }
```

`t!` resolves at render time.

## Theming

Blocks reference design tokens, not raw values:

```rust
<Text content="..." color="text.secondary" />
```

The agentui resolver substitutes the user's active theme.

## Adaptation

Views can branch on adaptation flags:

```rust
fn home(state: &MyState, adapt: &Adaptation) -> View {
    if adapt.reduced_motion {
        view! { <StaticHero ... /> }
    } else {
        view! { <AnimatedHero ... /> }
    }
}
```

## Multiple views per app

An app declares all its views in the manifest; agentui composes the right one when the agent references it.

## Errors

If a view function panics, the framework renders a placeholder block with a "view error" message and logs the panic. The rest of the canvas continues to function.

## Acceptance criteria

- [ ] Views are pure functions from state to View
- [ ] Reactivity triggers minimal re-renders
- [ ] Command bindings dispatch through the gate
- [ ] Layout intents respected
- [ ] A11y hints required for relevant blocks
- [ ] Localization integrated
- [ ] Theme tokens applied

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/KERNEL-FRAMEWORK.md`
- `07-ui/CANVAS-MODEL.md`
- `07-ui/BLOCK-TYPES.md`
- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/LAYOUT-INTENTS.md`
- `07-ui/DESIGN-TOKENS.md`
