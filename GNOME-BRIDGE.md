# Kiki GNOME Bridge — Setup & Status

Notes from the live sessions. Not a spec — operational reality.

## What was built

A GNOME Shell extension (`kiki@kiki-os`) running inside the Shell process,
exposing Shell/Meta/Mutter internals as DBus service `io.kiki.Shell`.

GNOME 48 blocks external callers from `Shell.Eval`, `FocusSearch`,
`ShowApplications`, `FocusApp`, `ShowOSD`, `ScreenTransition`, and all
`Meta.Window` operations. Root doesn't help — it's hardcoded in the Shell JS.

## Extension source

```
gnome-extension/kiki@kiki-os/
  extension.js    — ES6 module, GNOME 45+ required format (v2)
  metadata.json   — id, name, shell-version: ["45","46","47","48"]
```

Deploy / reinstall from repo:
```bash
python3 kiki/gnome.py ext_install   # copies from gnome-extension/ + enables
# → log out and back in (Wayland requires full Shell restart)
```

Or manually:
```bash
cp gnome-extension/kiki@kiki-os/* ~/.local/share/gnome-shell/extensions/kiki@kiki-os/
gsettings set org.gnome.shell enabled-extensions "['kiki@kiki-os']"
# log out / log back in
```

## DBus interface: io.kiki.Shell (v2 — 37 methods)

### Core
| Method | In | Out | Notes |
|---|---|---|---|
| `Ping` | — | s | version string |
| `Eval` | script: s | s | JSON `{ok, result\|error}` |
| `ShellVersion` | — | s | e.g. `"48"` |
| `ShellMode` | — | s | session mode (user, unlock-dialog…) |
| `IdleTime` | — | u | ms since last input |

### Overview / Search
| Method | In | Out |
|---|---|---|
| `FocusSearch` | query: s | — |
| `ShowApplications` | — | — |
| `OverviewState` | — | s | JSON `{visible, view}` |

### App management
| Method | In | Out |
|---|---|---|
| `FocusApp` | app_id: s | s |
| `RunningApps` | — | s | JSON `[{id,name,windows,state}]` |

### Window management
| Method | In | Out |
|---|---|---|
| `WindowList` | — | s | JSON `[{id,title,app,pid,workspace,x,y,w,h,state}]` |
| `WindowFocus` | seq: u | — |
| `WindowClose` | seq: u | — |
| `WindowMinimize` | seq: u | — |
| `WindowUnminimize` | seq: u | — |
| `WindowMaximize` | seq: u | — |
| `WindowUnmaximize` | seq: u | — |
| `WindowFullscreen` | seq: u, on: b | — |
| `WindowMove` | seq: u, x: i, y: i | — |
| `WindowResize` | seq: u, w: i, h: i | — |
| `WindowMoveToWorkspace` | seq: u, workspace: i | — |
| `WindowSetAbove` | seq: u, above: b | — |
| `WindowShake` | seq: u | — | Clutter ease animation |

`seq` = `Meta.Window.get_stable_sequence()` — stable uint, works on Wayland.

### Workspaces
| Method | In | Out |
|---|---|---|
| `Workspaces` | — | s | JSON `{count,active,workspaces[{index,active,name}]}` |
| `SwitchWorkspace` | index: i | — | 0-indexed |
| `WorkspaceGetName` | index: i | s | |
| `WorkspaceSetName` | index: i, name: s | — | |

### Display
| Method | In | Out |
|---|---|---|
| `Monitors` | — | s | JSON `[{index,primary,x,y,w,h,scale,refresh}]` |

### Clipboard
| Method | In | Out | Notes |
|---|---|---|---|
| `ClipboardGet` | — | s | returns 500ms-polled cache |
| `ClipboardSet` | text: s | — | synchronous |

### GSettings (Gio.Settings, no subprocess)
| Method | In | Out |
|---|---|---|
| `GSettingsGet` | schema: s, key: s | s | GVariant.print() format |
| `GSettingsSet` | schema: s, key: s, value: s | s | auto-typed from current key type |

### Visual feedback
| Method | In | Out | Notes |
|---|---|---|---|
| `ShowOSD` | text: s, icon: s, level: d | — | level -1 = no bar, 0–100 = bar % |
| `ScreenTransition` | — | — | Clutter fade on global.stage |
| `Notify` | title: s, body: s, icon: s | — | MessageTray + OSD fallback |

### Screenshot (async)
| Method | In | Out |
|---|---|---|
| `Screenshot` | path: s | s | full screen → saved path |
| `ScreenshotArea` | x,y,w,h: i, path: s | s | area → saved path |

## Python layer

`kiki/gnome.py` proxies everything. Extension path preferred; AT-SPI/CLI fallback
when extension is inactive.

```
# New in v2
running_apps()                    → [{id,name,windows,state}]
monitors()                        → [{index,primary,x,y,w,h,scale,refresh}]
overview_state()                  → {visible, view}
idle_time()                       → int (ms)
shell_mode()                      → str
workspace_get_name(n)             → str  (1-based n)
workspace_set_name(n, name)       → str
clipboard_get()                   → str  (extension cache or wl-paste)
clipboard_set(text)               → str  (extension or wl-copy)
screenshot(path)                  → path
screenshot_area(x, y, w, h, path) → path

# Improved window ops (Meta API via extension, AT-SPI fallback)
window_list()                     → [{id,title,app,workspace,x,y,w,h,state}]
window_focus(pattern)
window_close(pattern)
window_minimize(pattern)
window_unminimize(pattern)
window_maximize(pattern)
window_unmaximize(pattern)
window_fullscreen(pattern, on)
window_move(pattern, x, y)
window_resize(pattern, w, h)
window_move_to_workspace(pattern, n)
window_set_above(pattern, above)
window_shake(pattern)

# GSettings now extension-fast (no subprocess) when extension active
gsettings_get(schema, key)
gsettings_set(schema, key, value)
```

## Activation (one-time per machine)

```bash
python3 kiki/gnome.py ext_install
# → log out and back in
python3 kiki/gnome.py ext_status   # should show {active: true, ping: "kiki-shell-bridge v2 gnome-48"}
```

## Key design decisions

- **Window ID**: `get_stable_sequence()` not `get_id()` — XID is 0 on Wayland.
- **ClipboardGet cache**: `St.Clipboard.get_text()` is async; extension polls every 500ms into `_clipText`. First call after focus change may lag one tick.
- **Screenshot async**: uses `invocation` passed by `wrapJSObject` as last arg; returns `undefined` to prevent auto-reply, calls `invocation.return_value()` in callback.
- **GSettingsSet auto-type**: reads current key type, coerces the string value (handles s/b/i/u/x/d/as/ai; falls back to GVariant.parse for complex types).
- **Extension path for gsettings**: no subprocess spawn; ~10× faster than `gsettings` CLI.
