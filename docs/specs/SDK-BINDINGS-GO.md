---
id: sdk-bindings-go
title: Go SDK Bindings
type: SPEC
status: draft
version: 0.0.0
implements: [sdk-bindings-go]
depends_on:
  - sdk-codegen
  - sdk-rust
last_updated: 2026-04-30
---
# Go SDK Bindings

## Purpose

Specify the Go SDK: idiomatic Go API over the generated Cap'n Proto stubs. Go is a common choice for tools, services, and integrations.

## Module

```
go get github.com/kiki/kiki-sdk-go
```

```go
import "github.com/kiki/kiki-sdk-go/kiki"

type State struct {
    Counter int `json:"counter"`
}

func main() {
    app := kiki.NewApp[State]()
    app.WithCommand("increment", func(ctx *kiki.Ctx, state *State) error {
        state.Counter++
        return nil
    })
    app.WithView("home", func(state *State) kiki.View {
        return kiki.Card("Counter",
            kiki.Text(fmt.Sprintf("Count: %d", state.Counter)),
            kiki.Button("Increment", "increment"),
        )
    })
    if err := app.Run(); err != nil {
        log.Fatal(err)
    }
}
```

## Idioms

- Generics for typed state (Go 1.21+)
- Error returns; no exceptions
- Standard `context.Context` for cancellation
- Goroutines for concurrency, with the SDK avoiding the typical pitfalls

## System clients

```go
mem := app.Memory()
hits, err := mem.Search(ctx, &kiki.Query{Text: "trip Lisbon"})
if err != nil { return err }
for _, h := range hits {
    fmt.Println(h.Content)
}
```

## Errors

`*kiki.Error` is the structured error type:

```go
if err := mem.Write(ctx, op); err != nil {
    var ke *kiki.Error
    if errors.As(err, &ke) && ke.Code == "policy.denied" {
        // ...
    }
}
```

## Streaming

Channels for streams:

```go
hits, errs := mem.SearchStream(ctx, query)
for hit := range hits {
    fmt.Println(hit)
}
if err := <-errs; err != nil { /* ... */ }
```

## Build

Go binaries ship inside Kiki container images via standard `kiki-pkg build`:

```yaml
[package.metadata.kiki]
id = "kiki:apps/my-go-app"
```

(or the Go-equivalent build descriptor; the toolchain is detected.)

## Anti-patterns

- Not respecting context cancellation
- Goroutine leaks from unread channels
- Using interface{} where typed data is available

## Acceptance criteria

- [ ] Module installs and builds
- [ ] Hello-world example runs
- [ ] Errors wrap kiki.Error
- [ ] Streaming via channels
- [ ] Context cancellation respected

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/SDK-RUST.md`
- `06-sdk/SDK-CODEGEN.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
## Graph links

[[SDK-CODEGEN]]  [[SDK-RUST]]
