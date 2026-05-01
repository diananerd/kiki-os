---
id: sdk-bindings-c
title: C SDK Bindings
type: SPEC
status: draft
version: 0.0.0
implements: [sdk-bindings-c]
depends_on:
  - sdk-codegen
  - sdk-rust
last_updated: 2026-04-30
---
# C SDK Bindings

## Purpose

Specify the C SDK: a stable C ABI for embedded contexts and existing C/C++ code that wants to talk to Kiki. The C SDK is the *base* for many other-language bindings (Lua, Ruby, Swift) that prefer to FFI into a stable C library rather than build native bindings.

## Package

A static + shared library plus headers:

```
/usr/include/kiki/kiki.h
/usr/lib/libkiki.a
/usr/lib/libkiki.so
```

`pkg-config --cflags --libs kiki` works.

## ABI

The library's ABI is stable across minor versions; major bumps may change. The header guards versions:

```c
#define KIKI_API_VERSION 1
```

## Hello world

```c
#include <kiki/kiki.h>

int main(void) {
    kiki_app_t* app = kiki_app_create();

    kiki_app_with_command(app, "increment", increment_cb, NULL);
    kiki_app_with_view(app, "home", home_render_cb, NULL);

    return kiki_app_run(app);
}

void increment_cb(kiki_state_t* state, kiki_call_ctx_t* ctx) {
    int* counter = (int*)kiki_state_data(state);
    (*counter)++;
}
```

The C API is callback-based; the runtime calls into the C code at the right times.

## System clients

```c
kiki_memory_t* mem = kiki_app_memory(app);
kiki_hits_t* hits = kiki_memory_search(mem, "trip Lisbon");
size_t n = kiki_hits_len(hits);
for (size_t i = 0; i < n; i++) {
    kiki_hit_t* h = kiki_hits_at(hits, i);
    printf("%s\n", kiki_hit_content(h));
}
kiki_hits_free(hits);
```

## Memory management

C requires explicit memory management. Every `kiki_*_create` / `kiki_*_get` returns a handle that must be freed with the matching `kiki_*_free`. The header documents ownership clearly.

## Async

C lacks async/await. We provide a callback-based model and an event-loop integration for libuv / libev:

```c
kiki_app_run_libuv(app, loop);
```

For simpler cases, `kiki_call_blocking` blocks the current thread.

## Errors

```c
kiki_error_t* err = NULL;
int rc = kiki_memory_search_2(mem, query, &out, &err);
if (rc != 0) {
    fprintf(stderr, "error: %s (%s)\n",
            kiki_error_message(err),
            kiki_error_code(err));
    kiki_error_free(err);
}
```

## Threading

The library is thread-safe at the public-API level; internal state uses tokio under the hood (we link a Rust runtime).

## Use cases

- Embedded C/C++ applications
- Other-language FFI base
- Systems that already have an event loop

## Anti-patterns

- Long-running compute on the runtime thread (use a worker thread)
- Forgetting to free handles
- Concurrent mutation of a single handle from multiple threads

## Acceptance criteria

- [ ] Stable ABI per major version
- [ ] Memory management documented per handle
- [ ] Hello-world compiles + runs
- [ ] libuv integration works
- [ ] Errors expose category + code + message

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/SDK-RUST.md`
- `06-sdk/SDK-CODEGEN.md`
## Graph links

[[SDK-CODEGEN]]  [[SDK-RUST]]
