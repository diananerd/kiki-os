"""Kiki — GNOME Puppeteer.

All GNOME Shell / Mutter / AT-SPI interactions in one place.
Used by daemon.py tools; can also be run as CLI for debugging.

GNOME 48 notes:
  • Shell.Eval and several Shell methods (FocusSearch, ShowApplications,
    FocusApp, ShowOSD) are blocked to external callers.
  • The Kiki Shell Bridge extension (kiki@kiki-os) exposes these as a custom
    DBus service io.kiki.Shell — all restricted functions auto-upgrade when
    the extension is active.
  • Without the extension: OverviewActive property + AT-SPI + keyboard fallbacks.
  • Notifications use gi.repository.Notify (no notify-send binary needed).

Layers (in priority order):
  0. Kiki extension (io.kiki.Shell) — unlocks everything when loaded
  1. Shell DBus     — OverviewActive property, GrabAccelerator
  2. gtk4-launch    — app launch WITH GNOME zoom animation
  3. AT-SPI         — UI tree: top bar, dock, windows, elements, input synthesis
  4. gsettings      — structured read/write of GNOME settings
  5. SettingsDaemon — volume, brightness
  6. Workspaces     — gsettings + keyboard injection fallback
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

# ── Constants ────────────────────────────────────────────────────────

_SHELL_DEST  = "org.gnome.Shell"
_SHELL_OBJ   = "/org/gnome/Shell"
_MUTTER_DEST = "org.gnome.Mutter.RemoteDesktop"
_MUTTER_OBJ  = "/org/gnome/Mutter/RemoteDesktop"

# Kiki Shell Bridge extension DBus coordinates
_KIKI_DEST  = "io.kiki.Shell"
_KIKI_OBJ   = "/io/kiki/Shell"
_KIKI_IFACE = "io.kiki.Shell"

# Extension install path
_EXT_ID  = "kiki@kiki-os"
_EXT_DIR = Path.home() / ".local/share/gnome-shell/extensions" / _EXT_ID

KEYSYM = {
    "Return": 0xFF0D, "Escape": 0xFF1B, "Tab": 0xFF09,
    "BackSpace": 0xFF08, "Delete": 0xFFFF, "space": 0x0020,
    "Up": 0xFF52, "Down": 0xFF54, "Left": 0xFF51, "Right": 0xFF53,
    "Home": 0xFF50, "End": 0xFF57, "Page_Up": 0xFF55, "Page_Down": 0xFF56,
    "F1": 0xFFBE, "F2": 0xFFBF, "F3": 0xFFC0, "F4": 0xFFC1,
    "F5": 0xFFC2, "F6": 0xFFC3, "F7": 0xFFC4, "F8": 0xFFC5,
    "F9": 0xFFC6, "F10": 0xFFC7, "F11": 0xFFC8, "F12": 0xFFC9,
    "ctrl": 0xFFE3, "shift": 0xFFE1, "alt": 0xFFE9, "super": 0xFFEB,
}

# ── DBus helpers ─────────────────────────────────────────────────────

def _gdbus_call(dest: str, obj: str, iface_method: str,
                *args: str, timeout: int = 8) -> tuple[str, int]:
    cmd = ["gdbus", "call", "--session",
           "--dest", dest, "--object-path", obj,
           "--method", iface_method] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return (r.stdout.strip() or r.stderr.strip()), r.returncode


def _gdbus_prop_get(iface: str, prop: str,
                    dest: str = _SHELL_DEST,
                    obj: str = _SHELL_OBJ) -> str:
    out, _ = _gdbus_call(dest, obj,
                         "org.freedesktop.DBus.Properties.Get",
                         iface, prop)
    return out


def _gdbus_prop_set(iface: str, prop: str, value: str,
                    dest: str = _SHELL_DEST,
                    obj: str = _SHELL_OBJ) -> str:
    out, rc = _gdbus_call(dest, obj,
                          "org.freedesktop.DBus.Properties.Set",
                          iface, prop, value)
    return "ok" if rc == 0 else f"error: {out}"


# ── Kiki Shell Bridge extension ──────────────────────────────────────

def extension_available() -> bool:
    """Return True if the Kiki Shell Bridge extension is running."""
    out, rc = _gdbus_call(
        "org.freedesktop.DBus", "/org/freedesktop/DBus",
        "org.freedesktop.DBus.ListNames"
    )
    return _KIKI_DEST in out


def _kiki_call(method: str, *args: str) -> tuple[str, int]:
    return _gdbus_call(_KIKI_DEST, _KIKI_OBJ,
                       f"{_KIKI_IFACE}.{method}", *args)


def _kiki_str(out: str) -> str:
    """Extract the string value from gdbus output.

    Handles all formats gdbus produces:
      ('value',)        — normal string method return
      ("value",)        — string containing single quotes
      (<'value'>,)      — GVariant variant (from Properties.Get)
    """
    # Single-quoted: ('value',)
    m = re.match(r"^\s*\('((?:[^'\\]|\\.)*)'\s*,?\s*\)\s*$", out, re.DOTALL)
    if m:
        return m.group(1).replace("\\'", "'").replace("\\\\", "\\")
    # Double-quoted: ("value",) — string contains single quotes
    m = re.match(r'^\s*\("((?:[^"\\]|\\.)*)"\s*,?\s*\)\s*$', out, re.DOTALL)
    if m:
        return m.group(1).replace('\\"', '"').replace("\\\\", "\\")
    # Variant-wrapped: (<'value'>,) — from Properties.Get
    m = re.match(r"^\s*\(<'((?:[^'\\]|\\.)*)'\s*>\s*,?\s*\)\s*$", out, re.DOTALL)
    if m:
        return m.group(1).replace("\\'", "'").replace("\\\\", "\\")
    return out.strip("() <>'\"@\n,")


def extension_status() -> dict:
    """Return extension availability and version info."""
    if not extension_available():
        return {"active": False, "installed": _EXT_DIR.exists()}
    out, rc = _kiki_call("Ping")
    return {"active": True, "ping": _kiki_str(out) if rc == 0 else "error"}


def extension_install() -> str:
    """Copy extension source from repo and enable kiki@kiki-os."""
    here      = Path(__file__).parent
    repo_root = here.parent
    src_ext   = repo_root / "gnome-extension" / _EXT_ID
    if src_ext.exists():
        import shutil
        _EXT_DIR.mkdir(parents=True, exist_ok=True)
        for f in src_ext.iterdir():
            shutil.copy2(f, _EXT_DIR / f.name)
    elif not _EXT_DIR.exists():
        return (f"extension source not found: neither {src_ext} nor {_EXT_DIR}\n"
                f"Clone the repo or manually place extension files.")
    result = subprocess.run(
        ["gnome-extensions", "enable", _EXT_ID],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return (f"enabled {_EXT_ID}\n"
                f"IMPORTANT: Log out and back in (Wayland requires Shell restart)")
    return (f"files ready at {_EXT_DIR}\n"
            f"Run: gnome-extensions enable {_EXT_ID}\n"
            f"Then log out and log back in to activate.")


# ── Shell DBus ───────────────────────────────────────────────────────

def shell_version() -> str:
    if extension_available():
        out, rc = _kiki_call("ShellVersion")
        if rc == 0:
            v = _kiki_str(out)
            if v and v != '?':
                return v
    return _kiki_str(_gdbus_prop_get(_SHELL_DEST, "ShellVersion"))


def shell_eval(script: str) -> str:
    """Execute JavaScript inside GNOME Shell (requires kiki@kiki-os extension)."""
    if not extension_available():
        return "kiki extension not active — install and enable kiki@kiki-os, then log out/in"
    out, rc = _kiki_call("Eval", script)
    if rc != 0:
        return f"eval error: {out}"
    try:
        data = json.loads(_kiki_str(out))
        return data["result"] if data.get("ok") else f"error: {data.get('error', out)}"
    except Exception:
        return _kiki_str(out)


def overview_show() -> str:
    return _gdbus_prop_set(_SHELL_DEST, "OverviewActive", "<true>")


def overview_hide() -> str:
    return _gdbus_prop_set(_SHELL_DEST, "OverviewActive", "<false>")


def overview_toggle() -> str:
    state = _gdbus_prop_get(_SHELL_DEST, "OverviewActive")
    if "true" in state.lower():
        return overview_hide()
    return overview_show()


def show_applications() -> str:
    """Open app grid — uses extension if available, otherwise AT-SPI click."""
    if extension_available():
        _kiki_call("ShowApplications")
        return "app grid opened"
    overview_show()
    time.sleep(0.4)
    els = ui_find("gnome-shell", None, "Show Apps")
    if els:
        pointer_click(els[0]["x"] + els[0]["w"] // 2,
                      els[0]["y"] + els[0]["h"] // 2)
        return "app grid opened (AT-SPI fallback)"
    return "overview shown (Show Apps button not found)"


def focus_search(query: str = "") -> str:
    """Open overview with search focused. Uses extension when available."""
    if extension_available():
        _kiki_call("FocusSearch", query)
        return f"search opened{': ' + query if query else ''}"
    overview_show()
    time.sleep(0.3)
    if query:
        keyboard_type(query)
    return f"search opened (fallback){': ' + query if query else ''}"


def focus_app(app_id: str) -> str:
    """Activate an app by .desktop id — uses extension when available."""
    if extension_available():
        out, rc = _kiki_call("FocusApp", app_id)
        return _kiki_str(out) if rc == 0 else f"FocusApp error: {out}"
    result = window_focus(app_id.replace(".desktop", ""))
    if "no window" in result:
        return launch(app_id)
    return result


def show_osd(text: str, icon: str = "dialog-information",
             level: int = -1) -> str:
    """Show real OSD overlay (extension) or fallback notification."""
    if extension_available():
        _kiki_call("ShowOSD", text, icon, str(float(level)))
        return f"OSD: {text}"
    return notify(text, "", icon, "low")


# ── App launch ───────────────────────────────────────────────────────

def _resolve_desktop_id(name: str) -> str:
    """Return the .desktop filename that best matches name."""
    desktop_dir = Path("/usr/share/applications")
    # 1. Exact match (with or without .desktop)
    bare = name.removesuffix(".desktop")
    candidates = [
        bare + ".desktop",
        f"org.gnome.{bare.capitalize()}.desktop",
        f"org.gnome.{bare}.desktop",
    ]
    for c in candidates:
        if (desktop_dir / c).exists():
            return c
    # 2. Case-insensitive grep — also try stripping vendor prefixes
    short = re.sub(r'^(?:gnome|kde|org\.gnome|org\.kde)\-?', '', bare, flags=re.IGNORECASE)
    for pattern in [bare, short]:
        if not pattern:
            continue
        r = subprocess.run(
            f"ls /usr/share/applications/*.desktop 2>/dev/null | grep -i '{pattern}'",
            shell=True, capture_output=True, text=True
        )
        if r.stdout.strip():
            hits = [Path(p.strip()).name for p in r.stdout.splitlines() if p.strip()]
            return hits[0]
    return candidates[0]  # best guess


def launch(app_id: str) -> str:
    """Launch an app with GNOME zoom animation via gtk4-launch (non-blocking)."""
    desktop_id = _resolve_desktop_id(app_id)
    # gtk4-launch stays alive until the app closes — use Popen + brief poll
    proc = subprocess.Popen(
        ["gtk4-launch", desktop_id],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    time.sleep(0.4)
    rc = proc.poll()
    if rc is not None and rc != 0:
        err = proc.stderr.read().decode().strip()
        # Fallback: gio launch (also non-blocking)
        proc2 = subprocess.Popen(
            ["gio", "launch", f"/usr/share/applications/{desktop_id}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(0.4)
        rc2 = proc2.poll()
        if rc2 is None or rc2 == 0:
            return f"launched {desktop_id} (gio)"
        return f"launch failed: {err}"
    return f"launched {desktop_id}"


def list_apps() -> list[dict]:
    """List all installed .desktop apps."""
    apps = []
    desktop_dir = Path("/usr/share/applications")
    for f in sorted(desktop_dir.glob("*.desktop")):
        name = icon = comment = ""
        try:
            for line in f.read_text(errors="replace").splitlines():
                if line.startswith("Name=") and not name:
                    name = line[5:]
                elif line.startswith("Icon=") and not icon:
                    icon = line[5:]
                elif line.startswith("Comment=") and not comment:
                    comment = line[8:]
                elif line.startswith("NoDisplay=true"):
                    name = ""
                    break
        except Exception:
            pass
        if name:
            apps.append({"id": f.stem, "name": name,
                         "icon": icon, "comment": comment})
    return apps


# ── Top bar ──────────────────────────────────────────────────────────

def _topbar_elements() -> list[dict]:
    """Return interactive elements in the GNOME top bar (y <= 32)."""
    _init_atspi()
    desktop = Atspi.get_desktop(0)
    elements = []

    def _scan(node, depth=0):
        if depth > 8:
            return
        try:
            ext = node.get_extents(Atspi.CoordType.SCREEN)
            role = node.get_role_name()
            name = node.get_name() or ""
            if ext.y <= 32 and ext.height > 0 and ext.width > 0 and role not in ("panel", "application"):
                elements.append({
                    "role": role, "name": name,
                    "x": ext.x, "y": ext.y, "w": ext.width, "h": ext.height,
                    "cx": ext.x + ext.width // 2, "cy": ext.y + ext.height // 2,
                })
            for i in range(node.get_child_count()):
                child = node.get_child_at_index(i)
                if child:
                    _scan(child, depth + 1)
        except Exception:
            pass

    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app and "gnome-shell" in (app.get_name() or "").lower():
            _scan(app)
            break
    return elements


def topbar_get() -> dict:
    """Read top bar state: Activities button, clock, System menu."""
    els = _topbar_elements()
    result = {"items": []}
    for e in els:
        item = {"role": e["role"], "name": e["name"],
                "position": {"x": e["x"], "y": e["y"],
                             "w": e["w"], "h": e["h"]}}
        result["items"].append(item)
        if e["role"] == "toggle button" and "activit" in e["name"].lower():
            result["activities"] = {"cx": e["cx"], "cy": e["cy"]}
        elif e["role"] == "menu" and "system" in e["name"].lower():
            result["system_menu"] = {"cx": e["cx"], "cy": e["cy"]}
        elif e["role"] == "menu" and not e["name"]:
            result["clock"] = {"cx": e["cx"], "cy": e["cy"]}
    return result


def topbar_click(item: str) -> str:
    """Click a top bar item. item: 'activities' | 'system' | 'clock'."""
    tb = topbar_get()
    target = item.lower()
    if target == "activities":
        pos = tb.get("activities")
    elif target in ("system", "status"):
        pos = tb.get("system_menu")
    elif target in ("clock", "calendar", "date"):
        pos = tb.get("clock")
    else:
        return f"unknown topbar item '{item}'. use: activities, system, clock"
    if not pos:
        return f"topbar item '{item}' not found in AT-SPI tree"
    pointer_click(pos["cx"], pos["cy"])
    return f"clicked topbar: {item} at ({pos['cx']},{pos['cy']})"


# ── Dock ─────────────────────────────────────────────────────────────

def dock_list() -> list[dict]:
    """List apps pinned/shown in the GNOME dock (dash).

    Returns items when overview is open OR when the dock is visible.
    """
    _init_atspi()
    desktop = Atspi.get_desktop(0)
    items = []

    def _scan(node, depth=0):
        if depth > 8:
            return
        try:
            ext = node.get_extents(Atspi.CoordType.SCREEN)
            role = node.get_role_name()
            name = node.get_name() or ""
            # Dock items appear as labels at lower part of screen (y > 500)
            if role == "label" and name and ext.y > 200 and ext.w > 0:
                items.append({
                    "name": name,
                    "x": ext.x, "y": ext.y,
                    "w": ext.w, "h": ext.h,
                    "cx": ext.x + ext.w // 2,
                    "cy": ext.y + ext.h // 2,
                })
            for i in range(node.get_child_count()):
                child = node.get_child_at_index(i)
                if child:
                    _scan(child, depth + 1)
        except Exception:
            pass

    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app and "gnome-shell" in (app.get_name() or "").lower():
            _scan(app)
            break
    return items


def dock_click(app_name: str) -> str:
    """Click an app in the dock by name (case-insensitive)."""
    items = dock_list()
    target = app_name.lower()
    for item in items:
        if target in item["name"].lower():
            pointer_click(item["cx"], item["cy"])
            return f"clicked dock item: {item['name']} at ({item['cx']},{item['cy']})"
    return f"dock item '{app_name}' not found. available: {[i['name'] for i in items]}"


# ── Window management ─────────────────────────────────────────────────
# Extension path (Meta API) preferred; AT-SPI fallback when extension inactive.

def _ext_window_list() -> list[dict]:
    """Return window list from extension (empty list if unavailable)."""
    if not extension_available():
        return []
    try:
        out, rc = _kiki_call("WindowList")
        if rc == 0:
            return json.loads(_kiki_str(out))
    except Exception:
        pass
    return []


def _ext_find_win(pattern: str) -> dict | None:
    """Find first window matching pattern in title or app via extension."""
    p = pattern.lower()
    for w in _ext_window_list():
        if p in w.get("title", "").lower() or p in w.get("app", "").lower():
            return w
    return None


def _init_atspi() -> Atspi.Accessible:
    Atspi.init()
    return Atspi.get_desktop(0)


def window_list() -> list[dict]:
    """List windows — extension (Meta API) preferred, AT-SPI fallback."""
    wins = _ext_window_list()
    if wins:
        return wins
    # AT-SPI fallback
    desktop = _init_atspi()
    result = []
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app:
            continue
        app_name = app.get_name()
        for j in range(app.get_child_count()):
            win = app.get_child_at_index(j)
            if not win:
                continue
            try:
                role = win.get_role_name()
                if role not in ("frame", "dialog", "alert"):
                    continue
                title = win.get_name()
                ext   = win.get_extents(Atspi.CoordType.SCREEN)
                state = win.get_state_set()
                result.append({
                    "app":    app_name,
                    "title":  title,
                    "role":   role,
                    "x": ext.x, "y": ext.y,
                    "w": ext.width, "h": ext.height,
                    "active": state.contains(Atspi.StateType.ACTIVE),
                })
            except Exception:
                pass
    return result


def window_find(pattern: str) -> dict | None:
    p = pattern.lower()
    for w in window_list():
        if p in w.get("title", "").lower() or p in w.get("app", "").lower():
            return w
    return None


def window_focus(pattern: str) -> str:
    """Focus window by pattern — extension (Meta activate) preferred."""
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowFocus", str(w["id"]))
        return f"focused: {w['title']}"
    # AT-SPI fallback: click title bar
    wa = window_find(pattern)
    if not wa:
        return f"no window matching '{pattern}'"
    cx = wa["x"] + wa["w"] // 2
    cy = wa["y"] + 16
    pointer_click(cx, cy)
    time.sleep(0.1)
    return f"focused: {wa['title']} at ({cx},{cy})"


def window_close(pattern: str) -> str:
    """Close window by pattern — extension preferred."""
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowClose", str(w["id"]))
        return f"closed: {w['title']}"
    # AT-SPI fallback
    wa = window_find(pattern)
    if wa:
        desktop = _init_atspi()
        for i in range(desktop.get_child_count()):
            app = desktop.get_child_at_index(i)
            if not app or wa["app"] not in app.get_name():
                continue
            for j in range(app.get_child_count()):
                win = app.get_child_at_index(j)
                if win and wa["title"] in (win.get_name() or ""):
                    try:
                        actions = win.get_action_iface()
                        for k in range(actions.get_n_actions()):
                            if "close" in actions.get_action_name(k).lower():
                                actions.do_action(k)
                                return f"closed: {wa['title']}"
                    except Exception:
                        pass
    r = subprocess.run(f"pkill -f '{pattern}'", shell=True,
                       capture_output=True, text=True)
    return f"pkill {pattern}: {'ok' if r.returncode == 0 else 'not found'}"


def window_minimize(pattern: str) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowMinimize", str(w["id"]))
        return f"minimized: {w['title']}"
    return f"no window matching '{pattern}'"


def window_unminimize(pattern: str) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowUnminimize", str(w["id"]))
        return f"unminimized: {w['title']}"
    return f"no window matching '{pattern}'"


def window_maximize(pattern: str) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowMaximize", str(w["id"]))
        return f"maximized: {w['title']}"
    return f"no window matching '{pattern}'"


def window_unmaximize(pattern: str) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowUnmaximize", str(w["id"]))
        return f"unmaximized: {w['title']}"
    return f"no window matching '{pattern}'"


def window_fullscreen(pattern: str, on: bool = True) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowFullscreen", str(w["id"]), "<true>" if on else "<false>")
        return f"{'fullscreen' if on else 'unfullscreen'}: {w['title']}"
    return f"no window matching '{pattern}'"


def window_move(pattern: str, x: int, y: int) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowMove", str(w["id"]), str(x), str(y))
        return f"moved: {w['title']} → ({x},{y})"
    return f"no window matching '{pattern}'"


def window_resize(pattern: str, width: int, height: int) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowResize", str(w["id"]), str(width), str(height))
        return f"resized: {w['title']} → {width}×{height}"
    return f"no window matching '{pattern}'"


def window_move_to_workspace(pattern: str, n: int) -> str:
    """Move window to workspace n (1-based)."""
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowMoveToWorkspace", str(w["id"]), str(n - 1))
        return f"moved {w['title']} to workspace {n}"
    return f"no window matching '{pattern}'"


def window_set_above(pattern: str, above: bool = True) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowSetAbove", str(w["id"]), "<true>" if above else "<false>")
        return f"{'pinned above' if above else 'unpinned'}: {w['title']}"
    return f"no window matching '{pattern}'"


def window_shake(pattern: str) -> str:
    w = _ext_find_win(pattern)
    if w:
        _kiki_call("WindowShake", str(w["id"]))
        return f"shook: {w['title']}"
    return f"no window matching '{pattern}'"


# ── New capabilities (extension-native) ──────────────────────────────

def running_apps() -> list[dict]:
    """List running apps with window counts via extension."""
    if extension_available():
        out, rc = _kiki_call("RunningApps")
        if rc == 0:
            try:
                return json.loads(_kiki_str(out))
            except Exception:
                pass
    return []


def monitors() -> list[dict]:
    """List display monitors with geometry and scale."""
    if extension_available():
        out, rc = _kiki_call("Monitors")
        if rc == 0:
            try:
                return json.loads(_kiki_str(out))
            except Exception:
                pass
    return []


def overview_state() -> dict:
    """Return overview visibility and current view (overview|apps)."""
    if extension_available():
        out, rc = _kiki_call("OverviewState")
        if rc == 0:
            try:
                return json.loads(_kiki_str(out))
            except Exception:
                pass
    out = _gdbus_prop_get(_SHELL_DEST, "OverviewActive")
    return {"visible": "true" in out.lower(), "view": "unknown"}


def idle_time() -> int:
    """Return milliseconds since last user input (requires extension)."""
    if extension_available():
        out, rc = _kiki_call("IdleTime")
        if rc == 0:
            # gdbus format: "(uint32 12345,)"
            m = re.search(r'uint32\s+(\d+)', out)
            if m:
                return int(m.group(1))
    return -1


def shell_mode() -> str:
    """Return GNOME session mode (user, unlock-dialog, etc.)."""
    if extension_available():
        out, rc = _kiki_call("ShellMode")
        if rc == 0:
            return _kiki_str(out)
    return "unknown"


def workspace_get_name(n: int) -> str:
    """Return the name of workspace n (1-based)."""
    if extension_available():
        out, rc = _kiki_call("WorkspaceGetName", str(n - 1))
        if rc == 0:
            return _kiki_str(out)
    return f"Workspace {n}"


def workspace_set_name(n: int, name: str) -> str:
    """Set the name of workspace n (1-based)."""
    if extension_available():
        _kiki_call("WorkspaceSetName", str(n - 1), name)
        return f"workspace {n} named '{name}'"
    return "extension required for workspace naming"


def clipboard_get() -> str:
    """Get clipboard text — extension cache preferred, wl-paste fallback."""
    if extension_available():
        out, rc = _kiki_call("ClipboardGet")
        if rc == 0:
            return _kiki_str(out)
    try:
        r = subprocess.run(["wl-paste", "--no-newline"],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return r.stdout
    except Exception:
        pass
    return ""


def clipboard_set(text: str) -> str:
    """Set clipboard text — extension preferred, wl-copy fallback."""
    if extension_available():
        _kiki_call("ClipboardSet", text)
        return "ok"
    try:
        r = subprocess.run(["wl-copy"],
                           input=text, capture_output=True, text=True, timeout=3)
        return "ok" if r.returncode == 0 else r.stderr.strip()
    except Exception as e:
        return f"error: {e}"


def _screenshot_via_eval(path: str, area: tuple | None = None) -> str:
    """Take screenshot via shell_eval+polling — fallback when DBus method is unavailable.

    Uses async/await inside Shell JS context (promisified Shell.Screenshot).
    Writes a .done sentinel file and polls for it.
    """
    done = path + ".done"
    Path(done).unlink(missing_ok=True)
    if area:
        x, y, w, h = area
        script = (
            f"(async()=>{{try{{const f=Gio.File.new_for_path('{path}');"
            f"const s=f.replace(null,false,Gio.FileCreateFlags.NONE,null);"
            f"const ss=new Shell.Screenshot();"
            f"await ss.screenshot_area({x},{y},{w},{h},s);"
            f"try{{s.close(null);}}catch(_){{}}"
            f"}}catch(e){{logError(e);}}"
            f"finally{{GLib.file_set_contents('{done}','1');}}"
            f"}})();"
        )
    else:
        script = (
            f"(async()=>{{try{{const f=Gio.File.new_for_path('{path}');"
            f"const s=f.replace(null,false,Gio.FileCreateFlags.NONE,null);"
            f"const ss=new Shell.Screenshot();"
            f"await ss.screenshot(true,s);"
            f"try{{s.close(null);}}catch(_){{}}"
            f"}}catch(e){{logError(e);}}"
            f"finally{{GLib.file_set_contents('{done}','1');}}"
            f"}})();"
        )
    shell_eval(script)
    for _ in range(40):
        time.sleep(0.25)
        if Path(done).exists():
            Path(done).unlink(missing_ok=True)
            return path
    return f"screenshot timeout: {path}"


def screenshot(path: str = "") -> str:
    """Take a full-screen screenshot. Returns path to saved file."""
    if not path:
        path = f"/tmp/kiki-screenshot-{int(time.time())}.png"
    if extension_available():
        # Try DBus method first (works after extension reload with async fix)
        try:
            out, rc = _gdbus_call(_KIKI_DEST, _KIKI_OBJ,
                                  f"{_KIKI_IFACE}.Screenshot", path, timeout=5)
            if rc == 0:
                return _kiki_str(out) or path
        except Exception:
            pass
        # Fallback: shell_eval + sentinel file (works while old extension is in memory)
        return _screenshot_via_eval(path)
    return "screenshot requires kiki@kiki-os extension (GNOME 48+ restriction)"


def screenshot_area(x: int, y: int, w: int, h: int, path: str = "") -> str:
    """Take a screenshot of a screen area. Returns path."""
    if not path:
        path = f"/tmp/kiki-screenshot-{int(time.time())}.png"
    if extension_available():
        try:
            out, rc = _gdbus_call(_KIKI_DEST, _KIKI_OBJ,
                                  f"{_KIKI_IFACE}.ScreenshotArea",
                                  str(x), str(y), str(w), str(h), path, timeout=5)
            if rc == 0:
                return _kiki_str(out) or path
        except Exception:
            pass
        return _screenshot_via_eval(path, area=(x, y, w, h))
    return "screenshot_area requires kiki@kiki-os extension (GNOME 48+ restriction)"


# ── AT-SPI UI element automation ─────────────────────────────────────

def _atspi_walk(root: Atspi.Accessible, role: str | None, name: str | None,
                results: list, max_results: int = 10):
    if len(results) >= max_results:
        return
    try:
        node_role = root.get_role_name()
        node_name = root.get_name() or ""
        role_match = (role is None) or (role.lower() in node_role.lower())
        name_match = (name is None) or (name.lower() in node_name.lower())
        if role_match and name_match and node_role not in ("application", "desktop frame"):
            results.append(root)
        for i in range(root.get_child_count()):
            child = root.get_child_at_index(i)
            if child:
                _atspi_walk(child, role, name, results, max_results)
    except Exception:
        pass


def ui_find(app_pattern: str, role: str | None = None,
            name: str | None = None) -> list[dict]:
    desktop = _init_atspi()
    elements = []
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app:
            continue
        if app_pattern.lower() not in app.get_name().lower():
            continue
        nodes: list[Atspi.Accessible] = []
        _atspi_walk(app, role, name, nodes)
        for node in nodes:
            try:
                ext = node.get_extents(Atspi.CoordType.SCREEN)
                elements.append({
                    "role": node.get_role_name(),
                    "name": node.get_name(),
                    "x": ext.x, "y": ext.y,
                    "w": ext.width, "h": ext.height,
                    "app": app.get_name(),
                })
            except Exception:
                pass
    return elements


def ui_click(app_pattern: str, role: str | None = None,
             name: str | None = None) -> str:
    elements = ui_find(app_pattern, role, name)
    if not elements:
        return f"element not found: app={app_pattern} role={role} name={name}"
    desktop = _init_atspi()
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app or app_pattern.lower() not in app.get_name().lower():
            continue
        nodes: list[Atspi.Accessible] = []
        _atspi_walk(app, role, name, nodes)
        for node in nodes:
            try:
                action = node.get_action_iface()
                for k in range(action.get_n_actions()):
                    aname = action.get_action_name(k).lower()
                    if aname in ("click", "press", "activate", "toggle"):
                        action.do_action(k)
                        return f"clicked: {node.get_name()} ({node.get_role_name()})"
            except Exception:
                pass
    el = elements[0]
    cx, cy = el["x"] + el["w"] // 2, el["y"] + el["h"] // 2
    return pointer_click(cx, cy)


def ui_read(app_pattern: str, role: str | None = None,
            name: str | None = None) -> str:
    elements = ui_find(app_pattern, role, name)
    if not elements:
        return f"element not found: app={app_pattern} role={role} name={name}"
    desktop = _init_atspi()
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app or app_pattern.lower() not in app.get_name().lower():
            continue
        nodes: list[Atspi.Accessible] = []
        _atspi_walk(app, role, name, nodes)
        for node in nodes:
            try:
                txt = node.get_text_iface()
                if txt:
                    return txt.get_text(0, -1)
            except Exception:
                pass
            try:
                val = node.get_value_iface()
                if val:
                    return str(val.get_current_value())
            except Exception:
                pass
            return node.get_name() or "(no text)"
    return "(no text found)"


def ui_type(app_pattern: str, text: str,
            role: str = "text", name: str | None = None) -> str:
    ui_click(app_pattern, role, name)
    time.sleep(0.1)
    return keyboard_type(text)


# ── Input: AT-SPI event synthesis (Wayland-native, no session needed) ───

_KEY_MAP = {
    "return": 0xFF0D, "enter": 0xFF0D, "escape": 0xFF1B, "esc": 0xFF1B,
    "tab": 0xFF09, "backspace": 0xFF08, "delete": 0xFFFF, "del": 0xFFFF,
    "space": 0x0020, "up": 0xFF52, "down": 0xFF54,
    "left": 0xFF51, "right": 0xFF53,
    "home": 0xFF50, "end": 0xFF57,
    "page_up": 0xFF55, "pageup": 0xFF55, "prior": 0xFF55,
    "page_down": 0xFF56, "pagedown": 0xFF56, "next": 0xFF56,
    "f1": 0xFFBE, "f2": 0xFFBF, "f3": 0xFFC0, "f4": 0xFFC1,
    "f5": 0xFFC2, "f6": 0xFFC3, "f7": 0xFFC4, "f8": 0xFFC5,
    "f9": 0xFFC6, "f10": 0xFFC7, "f11": 0xFFC8, "f12": 0xFFC9,
    "ctrl": 0xFFE3, "shift": 0xFFE1, "alt": 0xFFE9,
    "super": 0xFFEB, "meta": 0xFFEB, "win": 0xFFEB,
}
_MOD_KEYS = {"ctrl", "shift", "alt", "super", "meta", "win"}


def pointer_move(x: float, y: float) -> str:
    """Move pointer to absolute screen coordinates via AT-SPI."""
    Atspi.generate_mouse_event(int(x), int(y), "abs")
    return f"moved to ({x}, {y})"


def pointer_button(button: int = 1, pressed: bool = True) -> str:
    """This is a no-op: use pointer_click for complete press+release."""
    return "ok"


def pointer_click(x: float, y: float, button: int = 1) -> str:
    """Move to (x,y) and click via AT-SPI mouse synthesis."""
    btn_map = {1: "b1c", 2: "b2c", 3: "b3c"}
    event = btn_map.get(button, "b1c")
    Atspi.generate_mouse_event(int(x), int(y), event)
    return f"clicked ({x}, {y}) button={button}"


def pointer_double_click(x: float, y: float) -> str:
    Atspi.generate_mouse_event(int(x), int(y), "b1d")
    return f"double-clicked ({x}, {y})"


def pointer_scroll(dx: float = 0, dy: float = 0) -> str:
    """Scroll via AT-SPI mouse events."""
    steps = int(abs(dy)) or 1
    event = "b4c" if dy > 0 else "b5c"  # b4=scroll up, b5=scroll down
    for _ in range(steps):
        Atspi.generate_mouse_event(0, 0, event)
    return f"scrolled dx={dx} dy={dy}"


def keyboard_keysym(keysym: int, pressed: bool = True) -> str:
    """Press or release a key by keysym via AT-SPI."""
    synth_type = (Atspi.KeySynthType.PRESS if pressed
                  else Atspi.KeySynthType.RELEASE)
    Atspi.generate_keyboard_event(keysym, None, synth_type)
    return "ok"


def keyboard_key(key: str) -> str:
    """Press and release a named key or combo like 'ctrl+c', 'super+page_down'."""
    parts = [p.strip() for p in key.lower().split("+")]
    mods   = [p for p in parts[:-1] if p in _MOD_KEYS]
    keystr = parts[-1]
    keysym = _KEY_MAP.get(keystr, ord(keystr) if len(keystr) == 1 else 0)
    if keysym == 0:
        return f"unknown key: {keystr}"
    for m in mods:
        keyboard_keysym(_KEY_MAP[m], True)
    # PRESSRELEASE for the main key
    Atspi.generate_keyboard_event(keysym, None, Atspi.KeySynthType.PRESSRELEASE)
    for m in reversed(mods):
        keyboard_keysym(_KEY_MAP[m], False)
    return f"key: {key}"


def keyboard_type(text: str) -> str:
    """Type a string using AT-SPI STRING synthesis (fast, handles Unicode)."""
    Atspi.generate_keyboard_event(0, text, Atspi.KeySynthType.STRING)
    return f"typed {len(text)} chars"


# ── Workspaces ───────────────────────────────────────────────────────

def workspace_list() -> dict:
    """Return workspaces with names, count, active index, dynamic flag."""
    if extension_available():
        out, rc = _kiki_call("Workspaces")
        if rc == 0:
            try:
                data = json.loads(_kiki_str(out))
                data["dynamic"] = gsettings_get("org.gnome.mutter", "dynamic-workspaces")
                return data
            except Exception:
                pass
    # Fallback: gsettings only (no active workspace info)
    return {
        "count":   gsettings_get("org.gnome.desktop.wm.preferences", "num-workspaces"),
        "dynamic": gsettings_get("org.gnome.mutter", "dynamic-workspaces"),
        "active":  "unknown",
    }


def workspace_switch(n: int) -> str:
    """Switch to workspace number n (1-based)."""
    if extension_available():
        _kiki_call("SwitchWorkspace", str(n - 1))  # extension is 0-indexed
        return f"switched to workspace {n}"
    # Fallback: Super+number (works for workspace 1-9)
    if 1 <= n <= 9:
        keyboard_key(f"super+{n}")
        return f"switched to workspace {n}"
    # For higher workspaces: go to 1, then page down
    keyboard_key("super+1")
    time.sleep(0.1)
    for _ in range(n - 1):
        keyboard_key("super+page_down")
        time.sleep(0.1)
    return f"switched to workspace {n}"


def screen_transition() -> str:
    """Play a brief screen fade transition (requires kiki@kiki-os extension)."""
    if not extension_available():
        return "screen_transition requires kiki@kiki-os extension"
    _kiki_call("ScreenTransition")
    return "transition played"


def workspace_add() -> str:
    """Add a new workspace (disables dynamic workspaces + increments count)."""
    r = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.wm.preferences", "num-workspaces"],
        capture_output=True, text=True
    )
    try:
        count = int(r.stdout.strip())
    except ValueError:
        count = 4
    subprocess.run(["gsettings", "set", "org.gnome.mutter", "dynamic-workspaces", "false"],
                   capture_output=True)
    subprocess.run(["gsettings", "set", "org.gnome.desktop.wm.preferences",
                    "num-workspaces", str(count + 1)], capture_output=True)
    return f"workspace added: now {count + 1} workspaces"


def workspace_remove(n: int = -1) -> str:
    """Remove last workspace (or workspace n). Won't go below 1."""
    r = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.wm.preferences", "num-workspaces"],
        capture_output=True, text=True
    )
    try:
        count = int(r.stdout.strip())
    except ValueError:
        count = 4
    if count <= 1:
        return "already at minimum (1 workspace)"
    subprocess.run(["gsettings", "set", "org.gnome.mutter", "dynamic-workspaces", "false"],
                   capture_output=True)
    subprocess.run(["gsettings", "set", "org.gnome.desktop.wm.preferences",
                    "num-workspaces", str(count - 1)], capture_output=True)
    return f"workspace removed: now {count - 1} workspaces"


def workspace_set_dynamic(enabled: bool = True) -> str:
    val = "true" if enabled else "false"
    subprocess.run(["gsettings", "set", "org.gnome.mutter", "dynamic-workspaces", val],
                   capture_output=True)
    return f"dynamic workspaces: {val}"


# ── Notifications ────────────────────────────────────────────────────

def notify(title: str, body: str = "", icon: str = "dialog-information",
           urgency: str = "normal") -> str:
    """Send a desktop notification via gi.repository.Notify (no binary needed)."""
    try:
        gi.require_version("Notify", "0.7")
        from gi.repository import Notify as _Notify
        if not _Notify.is_initted():
            _Notify.init("kiki")
        n = _Notify.Notification.new(title, body, icon)
        urgency_map = {
            "low": _Notify.Urgency.LOW,
            "normal": _Notify.Urgency.NORMAL,
            "critical": _Notify.Urgency.CRITICAL,
        }
        n.set_urgency(urgency_map.get(urgency.lower(), _Notify.Urgency.NORMAL))
        n.show()
        return "sent"
    except Exception as e1:
        # Fallback: dbus-send to org.freedesktop.Notifications
        try:
            cmd = [
                "dbus-send", "--session", "--type=method_call",
                "--dest=org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications.Notify",
                f"string:kiki", "uint32:0", f"string:{icon}",
                f"string:{title}", f"string:{body}",
                "array:string:", "dict:string:variant:", "int32:-1",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return "sent"
        except Exception:
            pass
        return f"notify failed: {e1}"


# ── gsettings helpers ────────────────────────────────────────────────

def gsettings_get(schema: str, key: str) -> str:
    if extension_available():
        out, rc = _kiki_call("GSettingsGet", schema, key)
        if rc == 0:
            return _kiki_str(out)
    r = subprocess.run(["gsettings", "get", schema, key],
                       capture_output=True, text=True, timeout=5)
    return r.stdout.strip() or r.stderr.strip()


def gsettings_set(schema: str, key: str, value: str) -> str:
    if extension_available():
        out, rc = _kiki_call("GSettingsSet", schema, key, value)
        if rc == 0:
            return _kiki_str(out)
    r = subprocess.run(["gsettings", "set", schema, key, value],
                       capture_output=True, text=True, timeout=5)
    return "ok" if r.returncode == 0 else r.stderr.strip()


def gsettings_list(schema: str) -> str:
    r = subprocess.run(["gsettings", "list-recursively", schema],
                       capture_output=True, text=True, timeout=5)
    return r.stdout.strip()[:2000]


def set_theme(mode: str) -> str:
    """mode: 'dark' | 'light'. Sets color-scheme only (gtk-theme stays Adwaita)."""
    scheme = {"dark": "prefer-dark", "light": "default", "auto": "default"}.get(
        mode.lower(), mode
    )
    gsettings_set("org.gnome.desktop.interface", "gtk-theme", "Adwaita")
    gsettings_set("org.gnome.desktop.interface", "color-scheme", scheme)
    return f"theme: {mode} (color-scheme={scheme}, gtk-theme=Adwaita)"


def get_theme() -> str:
    scheme = gsettings_get("org.gnome.desktop.interface", "color-scheme")
    gtk    = gsettings_get("org.gnome.desktop.interface", "gtk-theme")
    return f"color-scheme={scheme}  gtk-theme={gtk}"


# ── System status ────────────────────────────────────────────────────

def system_status() -> dict:
    """Aggregate battery, WiFi, date/time, hostname — mirrors the top bar info."""
    result: dict = {}

    # Date / time
    try:
        result["datetime"] = subprocess.run(
            ["date", "+%Y-%m-%d %H:%M:%S %Z"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except Exception:
        result["datetime"] = "unavailable"

    # WiFi — connection name + SSID + signal
    try:
        r = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid,signal,security,device", "dev", "wifi"],
            capture_output=True, text=True, timeout=5
        )
        wifi_active = None
        for line in r.stdout.splitlines():
            parts = line.split(":")
            if parts and parts[0].lower() == "yes":
                wifi_active = {
                    "ssid":     parts[1] if len(parts) > 1 else "",
                    "signal":   parts[2] if len(parts) > 2 else "",
                    "security": parts[3] if len(parts) > 3 else "",
                    "device":   parts[4] if len(parts) > 4 else "",
                }
                break
        result["wifi"] = wifi_active or "disconnected"
        # Also get IP
        ip_r = subprocess.run(
            "ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \\K[\\d.]+'",
            shell=True, capture_output=True, text=True, timeout=3
        )
        result["ip"] = ip_r.stdout.strip() or "unknown"
    except Exception as e:
        result["wifi"] = f"unavailable: {e}"

    # Battery
    try:
        bat_path = Path("/sys/class/power_supply")
        bat = next((p for p in bat_path.iterdir()
                    if p.name.startswith("BAT")), None)
        if bat:
            capacity = (bat / "capacity").read_text().strip()
            status   = (bat / "status").read_text().strip()
            result["battery"] = {"percent": int(capacity), "status": status}
        else:
            result["battery"] = "no battery"
    except Exception:
        result["battery"] = "unavailable"

    # Hostname
    try:
        result["hostname"] = subprocess.run(
            ["hostname"], capture_output=True, text=True, timeout=2
        ).stdout.strip()
    except Exception:
        pass

    # Volume
    result["volume"] = volume_get()

    # Theme
    result["theme"] = get_theme()

    return result


# ── Volume / Brightness ──────────────────────────────────────────────

def volume_get() -> str:
    r = subprocess.run(
        ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
        capture_output=True, text=True
    )
    return r.stdout.strip() or "unavailable"


def volume_set(percent: int) -> str:
    r = subprocess.run(
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"],
        capture_output=True, text=True
    )
    return "ok" if r.returncode == 0 else r.stderr.strip()


def volume_mute(muted: bool = True) -> str:
    val = "1" if muted else "0"
    subprocess.run(
        ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", val],
        capture_output=True, text=True
    )
    return "muted" if muted else "unmuted"


def brightness_get() -> str:
    try:
        out, rc = _gdbus_call(
            "org.gnome.SettingsDaemon.Power",
            "/org/gnome/SettingsDaemon/Power/Screen",
            "org.freedesktop.DBus.Properties.Get",
            "org.gnome.SettingsDaemon.Power.Screen",
            "Brightness"
        )
        return out
    except Exception as e:
        return f"unavailable: {e}"


def brightness_set(percent: int) -> str:
    try:
        out, rc = _gdbus_call(
            "org.gnome.SettingsDaemon.Power",
            "/org/gnome/SettingsDaemon/Power/Screen",
            "org.freedesktop.DBus.Properties.Set",
            "org.gnome.SettingsDaemon.Power.Screen",
            "Brightness",
            f"<int32 {percent}>"
        )
        return "ok" if rc == 0 else f"error: {out}"
    except Exception as e:
        return f"error: {e}"


# ── CLI debug interface ───────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    arg = sys.argv[2] if len(sys.argv) > 2 else ""

    dispatch = {
        # Overview / search
        "overview":          lambda: overview_show(),
        "overview_hide":     lambda: overview_hide(),
        "overview_toggle":   lambda: overview_toggle(),
        "overview_state":    lambda: json.dumps(overview_state(), indent=2),
        "apps":              lambda: show_applications(),
        "search":            lambda: focus_search(arg),
        # App launch
        "launch":            lambda: launch(arg),
        "list_apps":         lambda: json.dumps(list_apps()[:10], indent=2),
        "running_apps":      lambda: json.dumps(running_apps(), indent=2),
        # Top bar / dock
        "topbar":            lambda: json.dumps(topbar_get(), indent=2),
        "topbar_click":      lambda: topbar_click(arg),
        "dock":              lambda: json.dumps(dock_list(), indent=2),
        "dock_click":        lambda: dock_click(arg),
        # Window management
        "windows":           lambda: json.dumps(window_list(), indent=2),
        "focus_win":         lambda: window_focus(arg),
        "close_win":         lambda: window_close(arg),
        "min_win":           lambda: window_minimize(arg),
        "unmin_win":         lambda: window_unminimize(arg),
        "max_win":           lambda: window_maximize(arg),
        "unmax_win":         lambda: window_unmaximize(arg),
        "fullscreen_win":    lambda: window_fullscreen(arg, True),
        "unfullscreen_win":  lambda: window_fullscreen(arg, False),
        "move_win":          lambda: window_move(arg, *[int(x) for x in (sys.argv[3:5] if len(sys.argv) > 4 else ["0","0"])]),
        "resize_win":        lambda: window_resize(arg, *[int(x) for x in (sys.argv[3:5] if len(sys.argv) > 4 else ["800","600"])]),
        "shake_win":         lambda: window_shake(arg),
        "pin_win":           lambda: window_set_above(arg, True),
        "unpin_win":         lambda: window_set_above(arg, False),
        # AT-SPI UI automation
        "ui_find":           lambda: json.dumps(ui_find(*arg.split(":", 1)), indent=2),
        "ui_click":          lambda: ui_click(*arg.split(":", 1)),
        "ui_read":           lambda: ui_read(*arg.split(":", 1)),
        # Input
        "click":             lambda: pointer_click(*[float(x) for x in arg.split(",")]),
        "move":              lambda: pointer_move(*[float(x) for x in arg.split(",")]),
        "key":               lambda: keyboard_key(arg),
        "type":              lambda: keyboard_type(arg),
        # Notifications / OSD
        "notify":            lambda: notify(arg, arg, "dialog-information"),
        # Theme
        "theme":             lambda: set_theme(arg) if arg else get_theme(),
        # Volume / brightness
        "volume":            lambda: volume_set(int(arg)) if arg.isdigit() else volume_get(),
        "brightness":        lambda: brightness_set(int(arg)) if arg.isdigit() else brightness_get(),
        # Workspaces
        "workspaces":        lambda: json.dumps(workspace_list(), indent=2),
        "ws_switch":         lambda: workspace_switch(int(arg)) if arg else "need workspace number",
        "ws_add":            lambda: workspace_add(),
        "ws_remove":         lambda: workspace_remove(),
        "ws_name_get":       lambda: workspace_get_name(int(arg)) if arg else "need workspace number",
        "ws_name_set":       lambda: workspace_set_name(int(arg.split(" ")[0]), " ".join(arg.split(" ")[1:])),
        # Clipboard
        "clipboard":         lambda: clipboard_get(),
        "clipboard_set":     lambda: clipboard_set(arg),
        # Display
        "monitors":          lambda: json.dumps(monitors(), indent=2),
        # Screenshot
        "screenshot":        lambda: screenshot(arg),
        "screenshot_area":   lambda: screenshot_area(*[int(x) for x in arg.split(",")]) if arg else "need x,y,w,h",
        # GSettings
        "gsget":             lambda: gsettings_get(*arg.split(" ", 1)),
        "gsset":             lambda: gsettings_set(*arg.split(" ", 2)),
        # System
        "system_status":     lambda: json.dumps(system_status(), indent=2),
        # Misc Shell info
        "idle":              lambda: str(idle_time()),
        "shell_mode":        lambda: shell_mode(),
        "version":           lambda: shell_version(),
        "ext_status":        lambda: json.dumps(extension_status(), indent=2),
        "ext_install":       lambda: extension_install(),
        "shell_eval":        lambda: shell_eval(arg),
        "screen_transition": lambda: screen_transition(),
    }

    fn = dispatch.get(cmd)
    if fn:
        print(fn())
    else:
        print("commands:", " | ".join(dispatch.keys()))
