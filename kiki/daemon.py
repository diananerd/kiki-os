#!/usr/bin/env python3
"""Kiki — Agent Daemon.

Long-running agent service with universal OS tools.
Accepts goals via HTTP API and processes them through Ollama + tool loop.

HTTP API (port 8888):
  GET  /state     — status, goal, step count
  GET  /log       — full log as JSON [{ts, type, text}]
  GET  /stream    — SSE real-time log stream
  POST /goal      — {"goal": "..."}
  POST /pause     — pause after current step
  POST /resume    — resume
  DELETE /log     — clear log + session memory

Env:
  OLLAMA_URL      default http://localhost:11434
  KIKI_MODEL      default granite4.1:3b
  KIKI_PORT       HTTP port (default 8888)
  KIKI_APPS       path to apps.json (default kiki/apps.json)
"""

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import URLError

# ── Config ──────────────────────────────────────────────────────────

OLLAMA    = os.getenv("OLLAMA_URL",  "http://localhost:11434")
MODEL     = os.getenv("KIKI_MODEL",  "granite4.1:3b")
PORT      = int(os.getenv("KIKI_PORT", "8888"))
OUT       = 2000

_HERE     = Path(__file__).parent
APPS_FILE = Path(os.getenv("KIKI_APPS", str(_HERE / "apps.json")))

# ── GNOME puppeteer import ───────────────────────────────────────────

sys.path.insert(0, str(_HERE))
try:
    import gnome as _gnome
    _GNOME_OK  = True
    _GNOME_ERR = ""
except Exception as _e:
    _GNOME_OK  = False
    _GNOME_ERR = str(_e)
    _gnome     = None  # type: ignore

# ── App registry ─────────────────────────────────────────────────────

def _load_apps() -> dict:
    try:
        return json.loads(APPS_FILE.read_text())
    except Exception:
        return {}

_apps: dict = _load_apps()

# ── Shared state ─────────────────────────────────────────────────────

_lock = threading.Lock()
_sse_clients: list = []

_state = {
    "status":       "idle",
    "current_goal": None,
    "step":         0,
    "log":          [],
    "paused":       False,
}
_goal_queue: list[str] = []
_goal_event = threading.Event()

# Persistent conversation across goals; cleared on DELETE /log.
_session: list[dict] = []

# ── Colors ───────────────────────────────────────────────────────────

CYAN   = "\033[36m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
GREY   = "\033[90m"
RED    = "\033[31m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_TYPE_COLOR = {"goal": CYAN, "tool": YELLOW, "result": GREY,
               "reply": GREEN, "error": RED, "system": GREY}
_TYPE_ICON  = {"goal": "▶", "tool": "⚡", "result": "·",
               "reply": "✓", "error": "✗", "system": "·"}


def _log(entry_type: str, text: str):
    entry = {"ts": time.strftime("%H:%M:%S"), "type": entry_type, "text": text}
    color = _TYPE_COLOR.get(entry_type, RESET)
    icon  = _TYPE_ICON.get(entry_type, "·")
    print(f"{color}{icon} {text}{RESET}", flush=True)
    with _lock:
        _state["log"].append(entry)
        for q in list(_sse_clients):
            try:
                q.put_nowait(entry)
            except Exception:
                pass


def _set_status(s: str):
    with _lock:
        _state["status"] = s


# ── Tool implementations ─────────────────────────────────────────────

_DANGER = ["rm -rf /", "mkfs", ":(){:|:&};:", "dd if=/dev/zero of=/dev/sd"]


def _tool_shell(cmd: str) -> str:
    if any(d in cmd for d in _DANGER):
        return "blocked: dangerous command"
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return (r.stdout + r.stderr).strip()[:OUT]
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return str(e)


def _tool_read(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace")[:OUT]
    except Exception as e:
        return f"error: {e}"


def _tool_write(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"wrote {p}"
    except Exception as e:
        return f"error: {e}"


def _tool_app(app_id: str, action: str, args: dict | None = None) -> str:
    global _apps
    _apps = _load_apps()
    entry = _apps.get(app_id)
    if not entry:
        available = list(_apps.keys()) or ["none registered"]
        return f"unknown app '{app_id}'. available: {available}"
    base      = entry if isinstance(entry, str) else entry.get("url", "")
    api_style = entry.get("api_style", "rest") if isinstance(entry, dict) else "rest"
    args      = args or {}

    if api_style == "tool":
        url  = f"{base}/api"
        body = json.dumps({"tool": action, **args}).encode()
    else:
        url  = f"{base}/api/{action}"
        body = json.dumps(args).encode()

    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.read().decode()[:OUT]
    except Exception as e:
        return f"error calling {url}: {e}"


def _tool_gnome(action: str, args: dict) -> str:
    if not _GNOME_OK:
        return f"gnome module unavailable: {_GNOME_ERR}"
    g = _gnome
    a = action.lower().replace("-", "_")
    try:
        if a == "overview_show":     return g.overview_show()
        if a == "overview_hide":     return g.overview_hide()
        if a == "overview_toggle":   return g.overview_toggle()
        if a == "show_applications": return g.show_applications()
        if a == "focus_search":      return g.focus_search(args.get("query", ""))
        if a == "screen_transition":  return g.screen_transition()
        if a == "extension_status":   return json.dumps(g.extension_status())
        if a == "extension_install":  return g.extension_install()
        if a == "focus_app":
            return g.focus_app(args.get("app_id", ""))
        if a == "show_osd":
            return g.show_osd(args.get("text", ""),
                              args.get("icon", "dialog-information"),
                              int(args.get("level", -1)))
        if a == "launch":
            return g.launch(args.get("app_id", ""))
        if a == "list_apps":
            return json.dumps(g.list_apps()[:40])
        if a == "notify":
            return g.notify(args.get("title", ""), args.get("body", ""),
                            args.get("icon", "dialog-information"),
                            args.get("urgency", "normal"))
        if a == "set_theme":
            return g.set_theme(args.get("mode", "light"))
        if a == "get_theme":
            return g.get_theme()
        if a == "volume_get":
            return g.volume_get()
        if a == "volume_set":
            return g.volume_set(int(args.get("percent", 50)))
        if a == "volume_mute":
            return g.volume_mute(bool(args.get("muted", True)))
        if a == "gsettings_get":
            return g.gsettings_get(args.get("schema", ""), args.get("key", ""))
        if a == "gsettings_set":
            return g.gsettings_set(args.get("schema", ""),
                                   args.get("key", ""), args.get("value", ""))
        if a == "gsettings_list":
            return g.gsettings_list(args.get("schema", ""))
        if a == "shell_eval":
            return g.shell_eval(args.get("script", ""))
        if a == "topbar_get":        return json.dumps(g.topbar_get())
        if a == "topbar_click":      return g.topbar_click(args.get("item", ""))
        if a == "dock_list":         return json.dumps(g.dock_list())
        if a == "dock_click":        return g.dock_click(args.get("app_name", ""))
        if a == "workspace_list":      return json.dumps(g.workspace_list())
        if a == "workspace_switch":    return g.workspace_switch(int(args.get("n", 1)))
        if a == "workspace_add":       return g.workspace_add()
        if a == "workspace_remove":    return g.workspace_remove(int(args.get("n", -1)))
        if a == "workspace_dynamic":   return g.workspace_set_dynamic(bool(args.get("enabled", True)))
        if a == "workspace_get_name":  return g.workspace_get_name(int(args.get("n", 1)))
        if a == "workspace_set_name":  return g.workspace_set_name(int(args.get("n", 1)), args.get("name", ""))
        if a == "brightness_get":      return g.brightness_get()
        if a == "brightness_set":      return g.brightness_set(int(args.get("percent", 50)))
        if a == "system_status":       return json.dumps(g.system_status())
        if a == "running_apps":        return json.dumps(g.running_apps())
        if a == "monitors":            return json.dumps(g.monitors())
        if a == "overview_state":      return json.dumps(g.overview_state())
        if a == "idle_time":           return str(g.idle_time())
        if a == "shell_mode":          return g.shell_mode()
        if a == "clipboard_get":       return g.clipboard_get()
        if a == "clipboard_set":       return g.clipboard_set(args.get("text", ""))
        if a == "screenshot":          return g.screenshot(args.get("path", ""))
        if a == "screenshot_area":
            return g.screenshot_area(int(args.get("x", 0)), int(args.get("y", 0)),
                                     int(args.get("w", 1920)), int(args.get("h", 1080)),
                                     args.get("path", ""))
        return (f"unknown gnome action: {action}. "
                f"valid: overview_show/hide/toggle/state, show_applications, focus_search, focus_app, "
                f"show_osd, screen_transition, launch, list_apps, running_apps, notify, "
                f"set_theme, get_theme, volume_get/set/mute, brightness_get/set, "
                f"gsettings_get/set/list, topbar_get, topbar_click, dock_list, dock_click, "
                f"workspace_list/switch/add/remove/dynamic/get_name/set_name, "
                f"system_status, monitors, idle_time, shell_mode, "
                f"clipboard_get, clipboard_set, screenshot, screenshot_area, "
                f"extension_status, extension_install")
    except Exception as e:
        return f"gnome error ({action}): {e}"


def _tool_window(action: str, args: dict) -> str:
    if not _GNOME_OK:
        return f"gnome module unavailable: {_GNOME_ERR}"
    g = _gnome
    a = action.lower().replace("-", "_")
    p = args.get("pattern", "")
    try:
        if a == "list":           return json.dumps(g.window_list())
        if a == "find":           return json.dumps(g.window_find(p))
        if a == "focus":          return g.window_focus(p)
        if a == "close":          return g.window_close(p)
        if a == "minimize":       return g.window_minimize(p)
        if a == "unminimize":     return g.window_unminimize(p)
        if a == "maximize":       return g.window_maximize(p)
        if a == "unmaximize":     return g.window_unmaximize(p)
        if a == "fullscreen":     return g.window_fullscreen(p, bool(args.get("on", True)))
        if a == "move":           return g.window_move(p, int(args.get("x", 0)), int(args.get("y", 0)))
        if a == "resize":         return g.window_resize(p, int(args.get("w", 800)), int(args.get("h", 600)))
        if a == "move_workspace": return g.window_move_to_workspace(p, int(args.get("n", 1)))
        if a == "set_above":      return g.window_set_above(p, bool(args.get("above", True)))
        if a == "shake":          return g.window_shake(p)
        return (f"unknown window action: {action}. "
                f"valid: list, find, focus, close, minimize, unminimize, maximize, "
                f"unmaximize, fullscreen, move, resize, move_workspace, set_above, shake")
    except Exception as e:
        return f"window error ({action}): {e}"


def _tool_input(action: str, args: dict) -> str:
    if not _GNOME_OK:
        return f"gnome module unavailable: {_GNOME_ERR}"
    g = _gnome
    a = action.lower().replace("-", "_")
    try:
        if a == "move":
            return g.pointer_move(float(args.get("x", 0)), float(args.get("y", 0)))
        if a == "click":
            return g.pointer_click(float(args.get("x", 0)), float(args.get("y", 0)),
                                   int(args.get("button", 1)))
        if a == "double_click":
            return g.pointer_double_click(float(args.get("x", 0)), float(args.get("y", 0)))
        if a == "scroll":
            return g.pointer_scroll(float(args.get("dx", 0)), float(args.get("dy", 0)))
        if a == "key":
            return g.keyboard_key(args.get("key", ""))
        if a == "type":
            return g.keyboard_type(args.get("text", ""))
        return f"unknown input action: {action}. valid: move, click, double_click, scroll, key, type"
    except Exception as e:
        return f"input error ({action}): {e}"


def _tool_ui(app: str, action: str, args: dict) -> str:
    if not _GNOME_OK:
        return f"gnome module unavailable: {_GNOME_ERR}"
    g = _gnome
    a    = action.lower()
    role = args.get("role") or None
    name = args.get("name") or None
    try:
        if a == "find":
            return json.dumps(g.ui_find(app, role, name))
        if a == "click":
            return g.ui_click(app, role, name)
        if a == "read":
            return g.ui_read(app, role, name)
        if a == "type":
            return g.ui_type(app, args.get("text", ""), role or "text", name)
        return f"unknown ui action: {action}. valid: find, click, read, type"
    except Exception as e:
        return f"ui error ({action}): {e}"


def dispatch(name: str, args: dict) -> str:
    if name == "shell":   return _tool_shell(args.get("cmd", ""))
    if name == "read":    return _tool_read(args.get("path", ""))
    if name == "write":   return _tool_write(args.get("path", ""), args.get("content", ""))
    if name == "app":     return _tool_app(args.get("id", ""), args.get("action", ""),
                                           args.get("args") or {})
    if name == "gnome":   return _tool_gnome(args.get("action", ""), args)
    if name == "window":  return _tool_window(args.get("action", ""), args)
    if name == "input":   return _tool_input(args.get("action", ""), args)
    if name == "ui":      return _tool_ui(args.get("app", ""), args.get("action", ""), args)
    return f"unknown tool: {name}"


# ── Tool definitions for LLM ─────────────────────────────────────────

def _app_registry_description() -> str:
    apps = _load_apps()
    if not apps:
        return "none registered"
    lines = []
    for app_id, entry in apps.items():
        desc = entry.get("description", "") if isinstance(entry, dict) else ""
        lines.append(f'  "{app_id}": {desc}')
    return "\n" + "\n".join(lines)


def _build_tools() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": "shell",
                "description": (
                    "Run any shell command on the OS (Debian 13, GNOME/Wayland, aarch64). "
                    "Use for file ops, processes, network (nmcli), package queries, "
                    "and anything not covered by more specific tools."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"cmd": {"type": "string"}},
                    "required": ["cmd"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read a file and return its contents.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write",
                "description": "Write content to a file (creates parent dirs if needed).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path":    {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "app",
                "description": (
                    "Control a registered GUI application via its HTTP API. "
                    f"Registered apps:{_app_registry_description()}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id":     {"type": "string", "description": "App ID from registry"},
                        "action": {"type": "string", "description": "API action name"},
                        "args":   {"type": "object", "description": "Action arguments"},
                    },
                    "required": ["id", "action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "gnome",
                "description": (
                    "Control GNOME Shell natively — kiki@kiki-os extension, DBus, AT-SPI, gtk4-launch. "
                    "Actions: overview_show, overview_hide, overview_toggle, "
                    "show_applications (app grid), focus_search (query: optional text to type), "
                    "focus_app (app_id), show_osd (text, icon, level: -1=no bar 0-100=bar), "
                    "screen_transition (brief fade — requires extension), "
                    "launch (app_id — uses gtk4-launch zoom animation), "
                    "list_apps (installed .desktop apps), "
                    "notify (title, body, icon, urgency: low|normal|critical), "
                    "set_theme (mode: dark|light), get_theme, "
                    "system_status (battery+wifi+datetime+volume+theme in one call), "
                    "topbar_get (read Activities/Clock/System menu positions), "
                    "topbar_click (item: activities|system|clock), "
                    "dock_list (apps in dash/dock), dock_click (app_name), "
                    "workspace_list, workspace_switch (n: 1-based), "
                    "workspace_add, workspace_remove (n), workspace_dynamic (enabled: bool), "
                    "volume_get, volume_set (percent 0-100), volume_mute (muted: bool), "
                    "brightness_get, brightness_set (percent 0-100), "
                    "gsettings_get (schema, key), gsettings_set (schema, key, value), "
                    "gsettings_list (schema), "
                    "screenshot (path: optional — returns saved path), "
                    "screenshot_area (x, y, w, h, path: optional — area screenshot), "
                    "running_apps (list apps currently running with window count), "
                    "monitors (list displays with geometry and scale), "
                    "idle_time (ms since last user input), "
                    "shell_mode (current session mode), "
                    "clipboard_get, clipboard_set (text), "
                    "extension_status (check if kiki@kiki-os is running), "
                    "extension_install (enable kiki@kiki-os — then log out/in)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action":   {"type": "string"},
                        "app_id":   {"type": "string"},
                        "app_name": {"type": "string"},
                        "item":     {"type": "string",
                                     "description": "topbar item: activities|system|clock"},
                        "n":        {"type": "integer",
                                     "description": "workspace number (1-based)"},
                        "query":    {"type": "string"},
                        "text":     {"type": "string"},
                        "script":   {"type": "string"},
                        "icon":     {"type": "string"},
                        "level":    {"type": "integer"},
                        "title":    {"type": "string"},
                        "body":     {"type": "string"},
                        "urgency":  {"type": "string"},
                        "mode":     {"type": "string", "enum": ["dark", "light"]},
                        "percent":  {"type": "integer"},
                        "muted":    {"type": "boolean"},
                        "enabled":  {"type": "boolean"},
                        "schema":   {"type": "string"},
                        "key":      {"type": "string"},
                        "value":    {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "window",
                "description": (
                    "Manage open windows via Meta API (extension) + AT-SPI fallback. "
                    "Actions: list (all windows with position/size/state), "
                    "find (pattern → first match), "
                    "focus (pattern → foreground), "
                    "close (pattern → close gracefully), "
                    "minimize / unminimize (pattern), "
                    "maximize / unmaximize (pattern), "
                    "fullscreen (pattern, on: bool), "
                    "move (pattern, x, y), "
                    "resize (pattern, w, h), "
                    "move_workspace (pattern, n: 1-based), "
                    "set_above (pattern, above: bool), "
                    "shake (pattern — Clutter animation)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action":  {"type": "string",
                                    "enum": ["list", "find", "focus", "close",
                                             "minimize", "unminimize",
                                             "maximize", "unmaximize",
                                             "fullscreen", "move", "resize",
                                             "move_workspace", "set_above", "shake"]},
                        "pattern": {"type": "string",
                                    "description": "Case-insensitive match against app or title"},
                        "x":       {"type": "integer"},
                        "y":       {"type": "integer"},
                        "w":       {"type": "integer"},
                        "h":       {"type": "integer"},
                        "n":       {"type": "integer",
                                    "description": "workspace number (1-based)"},
                        "on":      {"type": "boolean"},
                        "above":   {"type": "boolean"},
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "input",
                "description": (
                    "Inject pointer and keyboard events via Mutter RemoteDesktop. "
                    "Actions: move (x, y), click (x, y, button=1), "
                    "double_click (x, y), scroll (dx, dy), "
                    "key (key: 'ctrl+c', 'Return', 'Escape', 'ctrl+alt+t', etc.), "
                    "type (text: string to type character by character)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string",
                                   "enum": ["move", "click", "double_click",
                                            "scroll", "key", "type"]},
                        "x":      {"type": "number"},
                        "y":      {"type": "number"},
                        "button": {"type": "integer", "description": "1=left 2=middle 3=right"},
                        "dx":     {"type": "number"},
                        "dy":     {"type": "number"},
                        "key":    {"type": "string"},
                        "text":   {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ui",
                "description": (
                    "Interact with UI elements via AT-SPI accessibility tree. "
                    "Actions: find (returns list of matching elements with position), "
                    "click (activate element), read (get text/value), "
                    "type (focus element then type text). "
                    "role examples: button, text, label, check box, toggle button, "
                    "menu item, list item, slider, spin button."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string",
                                   "enum": ["find", "click", "read", "type"]},
                        "app":    {"type": "string",
                                   "description": "App name pattern (case-insensitive)"},
                        "role":   {"type": "string",
                                   "description": "Element role filter (optional)"},
                        "name":   {"type": "string",
                                   "description": "Element name/label filter (optional)"},
                        "text":   {"type": "string",
                                   "description": "Text to type (for type action)"},
                    },
                    "required": ["action", "app"],
                },
            },
        },
    ]


SYSTEM = """\
You are Kiki, an agentic OS assistant running on GNOME 48 / Wayland (Debian 13, aarch64).
You have persistent memory within this session — remember prior exchanges.
Use tools to complete every request. Summarize what you did after each task.

TOOL STRATEGY — pick the right layer:
  • gnome  → native GNOME actions WITH animations (launch, theme, notify, OSD, overview…)
  • window → list/focus/close/minimize/maximize/move/resize/shake windows by name
  • input  → inject pointer + keyboard events (click coords, type text, key combos)
  • ui     → interact with specific UI elements by role/name via accessibility tree
  • app    → control registered HTTP-API apps (bar, demo)
  • shell  → everything else: files, processes, network, package queries
  • read / write → file I/O

GNOME ACTIONS (prefer over shell for everything GNOME-related):
  Launch app (zoom anim)     : gnome(action=launch, app_id="gnome-calculator")
  Show overview              : gnome(action=overview_show|overview_hide|overview_toggle)
  App grid                   : gnome(action=show_applications)
  Search for app             : gnome(action=focus_search, query="firefox")
  Focus running app          : gnome(action=focus_app, app_id="gnome-calculator")
  Desktop notification       : gnome(action=notify, title="Kiki", body="Done")
  Theme                      : gnome(action=set_theme, mode=dark|light) | gnome(action=get_theme)
  Volume                     : gnome(action=volume_get|volume_set, percent=70) | gnome(action=volume_mute, muted=true)
  Brightness                 : gnome(action=brightness_get|brightness_set, percent=80)
  List installed apps        : gnome(action=list_apps)
  Read/write gsetting        : gnome(action=gsettings_get|gsettings_set, schema="...", key="...", value="...")

SYSTEM STATUS (battery, wifi, date/time, volume):
  All status info at once    : gnome(action=system_status)
  → returns: datetime, wifi.ssid, wifi.signal, battery.percent, battery.status, volume, theme

TOP BAR:
  Read bar items/positions   : gnome(action=topbar_get)
  Click Activities           : gnome(action=topbar_click, item=activities)
  Click System status menu   : gnome(action=topbar_click, item=system)
  Click Clock/calendar       : gnome(action=topbar_click, item=clock)

DOCK (needs overview open to see all items):
  List dock apps             : gnome(action=dock_list)
  Click dock app             : gnome(action=dock_click, app_name="Firefox")

WORKSPACES:
  List workspaces            : gnome(action=workspace_list)
  Switch to workspace N      : gnome(action=workspace_switch, n=2)
  Add workspace              : gnome(action=workspace_add)
  Remove workspace           : gnome(action=workspace_remove)

THEME RULE: ONLY color-scheme controls dark/light — NEVER set gtk-theme to 'Adwaita Dark'.
  dark  → gnome(action=set_theme, mode=dark)
  light → gnome(action=set_theme, mode=light)

WINDOW MANAGEMENT:
  See all windows    : window(action=list)
  Focus a window     : window(action=focus, pattern="calculator")
  Close a window     : window(action=close, pattern="calculator")
  Minimize           : window(action=minimize, pattern="calculator")
  Maximize           : window(action=maximize, pattern="calculator")
  Fullscreen on/off  : window(action=fullscreen, pattern="calculator", on=true)
  Move               : window(action=move, pattern="calculator", x=100, y=200)
  Resize             : window(action=resize, pattern="calculator", w=800, h=600)
  Move to workspace  : window(action=move_workspace, pattern="calculator", n=2)
  Pin above all      : window(action=set_above, pattern="calculator", above=true)
  Shake (animation)  : window(action=shake, pattern="calculator")

POINTER + KEYBOARD (use coordinates from window/ui/topbar_get):
  Move cursor        : input(action=move, x=500, y=300)
  Left click         : input(action=click, x=500, y=300)
  Right click        : input(action=click, x=500, y=300, button=3)
  Key combo          : input(action=key, key="ctrl+c")
  Type text          : input(action=type, text="hello world")
  Common keys        : Return, Escape, Tab, BackSpace, Delete, space, Up, Down, Left, Right, F1-F12, super+N

UI AUTOMATION (by role/name, no coords needed):
  Find elements      : ui(action=find, app="calculator", role="button")
  Click element      : ui(action=click, app="calculator", role="button", name="=")
  Read text          : ui(action=read, app="calculator", role="text")
  Type in field      : ui(action=type, app="text editor", text="Hello")

SHELL — for files, network, processes, packages:
  Network    : nmcli radio wifi on|off | nmcli device status | nmcli con show --active
  Processes  : ps aux | pkill -f <name> | kill <pid>
  Files      : ls | find | grep | mkdir | cp | mv
  Clipboard  : wl-copy "text" | wl-paste

SCREENSHOT (requires kiki@kiki-os extension):
  Full screenshot              : gnome(action=screenshot)  — returns path
  Area screenshot              : gnome(action=screenshot_area, x=0, y=0, w=800, h=600)
  Note: gnome.screenshot() saves to /tmp/kiki-screenshot-TIMESTAMP.png by default.

DISPLAY / SESSION:
  List monitors                : gnome(action=monitors)
  Running apps (with windows)  : gnome(action=running_apps)
  Idle time (ms)               : gnome(action=idle_time)
  Session mode                 : gnome(action=shell_mode)
  Clipboard read               : gnome(action=clipboard_get)
  Clipboard write              : gnome(action=clipboard_set, text="hello")

KIKI EXTENSION (kiki@kiki-os) — unlocks GNOME 48 restricted Shell methods:
  Check extension status       : gnome(action=extension_status)
  Enable extension (one-time)  : gnome(action=extension_install)  → then log out/in
  When active, these are real  : focus_search, show_applications, focus_app, show_osd,
                                  screen_transition, workspace_switch, shell_eval

IMPORTANT: Read before writing. Use system_status for status bar queries.\
"""


# ── LLM chat ─────────────────────────────────────────────────────────

def _chat(messages: list) -> dict:
    body = json.dumps({
        "model":    MODEL,
        "messages": messages,
        "tools":    _build_tools(),
        "stream":   False,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["message"]


# ── Agent loop ────────────────────────────────────────────────────────

def _ctx() -> list:
    """Build context: system msg + last 12 session turns."""
    with _lock:
        if not _session:
            return []
        sys_msg = _session[0]
        tail    = _session[max(1, len(_session) - 12):]
    return [sys_msg] + tail


def _run_goal(goal: str):
    global _session
    _set_status("running")
    _log("goal", goal)
    with _lock:
        _state["current_goal"] = goal
        _state["step"] = 0
        if not _session:
            _session = [{"role": "system", "content": SYSTEM}]
        _session.append({"role": "user", "content": goal})

    for _ in range(20):
        while _state["paused"]:
            time.sleep(0.5)

        with _lock:
            _state["step"] += 1

        try:
            msg = _chat(_ctx())
        except URLError as e:
            _log("error", f"Ollama unreachable: {e}")
            _set_status("error")
            return
        except Exception as e:
            _log("error", str(e))
            _set_status("error")
            return

        with _lock:
            _session.append(msg)
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            content = msg.get("content", "").strip()
            if content:
                _log("reply", content)
            break

        for tc in tool_calls:
            fn    = tc["function"]
            name  = fn["name"]
            args  = fn.get("arguments") or {}
            label = (f"{name}({', '.join(f'{k}={v!r}' for k, v in args.items())})"
                     if args else f"{name}()")
            _log("tool", label)
            result  = dispatch(name, args)
            preview = result[:150] + ("…" if len(result) > 150 else "")
            _log("result", preview)
            with _lock:
                _session.append({"role": "tool", "content": result})

    _set_status("idle")
    with _lock:
        _state["current_goal"] = None


# ── HTTP server ───────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _json(self, code: int, obj):
        data = json.dumps(obj, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n)) if n else {}
        except Exception:
            return {}

    def do_GET(self):
        if self.path == "/state":
            with _lock:
                snap = {k: v for k, v in _state.items() if k != "log"}
                snap["session_turns"] = max(0, len(_session) - 1)
                snap["gnome_ok"]      = _GNOME_OK
            self._json(200, snap)

        elif self.path == "/log":
            with _lock:
                self._json(200, _state["log"])

        elif self.path == "/stream":
            import queue
            q: queue.Queue = queue.Queue(maxsize=100)
            with _lock:
                _sse_clients.append(q)
                backlog = list(_state["log"])
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                for entry in backlog:
                    self.wfile.write(f"data: {json.dumps(entry)}\n\n".encode())
                    self.wfile.flush()
                while True:
                    try:
                        entry = q.get(timeout=15)
                        self.wfile.write(f"data: {json.dumps(entry)}\n\n".encode())
                        self.wfile.flush()
                    except Exception:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with _lock:
                    _sse_clients.remove(q)

        elif self.path == "/":
            with _lock:
                snap = {k: v for k, v in _state.items() if k != "log"}
            self._json(200, {
                "service": "kiki-daemon",
                "model":   MODEL,
                **snap,
                "gnome_ok": _GNOME_OK,
                "endpoints": ["GET /state", "GET /log", "GET /stream",
                               "POST /goal", "POST /pause", "POST /resume",
                               "DELETE /log"],
            })
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        body = self._body()
        if self.path == "/goal":
            goal = body.get("goal", "").strip()
            if not goal:
                self._json(400, {"error": "goal required"})
                return
            with _lock:
                _goal_queue.append(goal)
            _goal_event.set()
            self._json(200, {"ok": True, "queued": goal})
        elif self.path == "/pause":
            with _lock:
                _state["paused"] = True
            self._json(200, {"ok": True})
        elif self.path == "/resume":
            with _lock:
                _state["paused"] = False
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    def do_DELETE(self):
        if self.path == "/log":
            with _lock:
                _state["log"].clear()
                _session.clear()
            self._json(200, {"ok": True, "session": "cleared"})
        else:
            self._json(404, {"error": "not found"})


def _start_server():
    HTTPServer(("127.0.0.1", PORT), _Handler).serve_forever()


def _goal_worker():
    while True:
        _goal_event.wait()
        _goal_event.clear()
        while True:
            with _lock:
                if not _goal_queue:
                    break
                goal = _goal_queue.pop(0)
            _run_goal(goal)


# ── Main ──────────────────────────────────────────────────────────────

BANNER = f"""{CYAN}{BOLD}
  ██╗  ██╗██╗██╗  ██╗██╗    ██████╗  █████╗ ███████╗███╗   ███╗ ██████╗ ███╗   ██╗
  ██║ ██╔╝██║██║ ██╔╝██║    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔═══██╗████╗  ██║
  █████╔╝ ██║█████╔╝ ██║    ██║  ██║███████║█████╗  ██╔████╔██║██║   ██║██╔██╗ ██║
  ██╔═██╗ ██║██╔═██╗ ██║    ██║  ██║██╔══██║██╔══╝  ██║╚██╔╝██║██║   ██║██║╚██╗██║
  ██║  ██╗██║██║  ██╗██║    ██████╔╝██║  ██║███████╗██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
{RESET}{GREY}  daemon · {MODEL} · http://127.0.0.1:{PORT} · gnome={'ok' if _GNOME_OK else 'unavailable'}{RESET}
"""


def main():
    quiet = "--quiet" in sys.argv
    if not quiet:
        print(BANNER)
        print(f"{GREY}  debug  → curl http://127.0.0.1:{PORT}/")
        print(f"  stream → curl http://127.0.0.1:{PORT}/stream")
        print(f"  inject → curl -X POST http://127.0.0.1:{PORT}/goal -d '{{\"goal\":\"...\"}}'")
        print(f"{RESET}")
        if not _GNOME_OK:
            print(f"{YELLOW}  ⚠ gnome module not loaded: {_GNOME_ERR}{RESET}\n")

    threading.Thread(target=_start_server, daemon=True).start()
    threading.Thread(target=_goal_worker,  daemon=True).start()
    _log("system", f"daemon started — model: {MODEL} — gnome: {'ok' if _GNOME_OK else 'unavailable'}")

    if sys.stdin.isatty():
        while True:
            try:
                goal = input(f"{CYAN}kiki>{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{GREY}bye{RESET}")
                break
            if not goal or goal in ("exit", "quit", "q"):
                break
            with _lock:
                _goal_queue.append(goal)
            _goal_event.set()
    else:
        _log("system", f"headless — send goals via POST http://127.0.0.1:{PORT}/goal")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
