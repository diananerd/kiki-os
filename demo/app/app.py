#!/usr/bin/env python3
"""Kiki OS — Controllable Demo App.

A GTK4 app that exposes an HTTP control API on port 7070.
The Kiki agent (demo/app/agent.py) sends commands to it and the UI updates live.

Controls available to the agent:
  POST /api  {"tool": "toggle",      "id": "autopilot"}
  POST /api  {"tool": "navigate",    "direction": "next"|"prev"}
  POST /api  {"tool": "add_item",    "text": "..."}
  POST /api  {"tool": "remove_item", "index": 0}
  POST /api  {"tool": "clear_items"}
  POST /api  {"tool": "show_dialog", "title": "...", "message": "..."}
  POST /api  {"tool": "set_status",  "text": "..."}
  GET  /api/state  → current state as JSON
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

PORT = 7070

# ── shared state (guarded by GLib.idle_add for GTK thread safety) ──

class AppState:
    def __init__(self):
        self.items: list[str] = []
        self.autopilot: bool = False
        self.dark_mode: bool = False
        self.page: int = 0
        self.status: str = "Waiting for agent…"
        self.log: list[str] = []


state = AppState()
app_ref: "KikiApp | None" = None


# ── GTK4 Application ──────────────────────────────────────────────

CSS = b"""
window { background-color: #0d1117; }
.header { background-color: #161b22; padding: 12px 20px; }
.title  { color: #e6edf3; font-size: 18px; font-weight: bold; }
.subtitle { color: #8b949e; font-size: 12px; }
.panel  { background-color: #161b22; border-radius: 8px; margin: 8px; padding: 12px; }
.log-view { background-color: #0d1117; color: #3fb950; font-family: monospace; font-size: 12px; }
.item-row { color: #e6edf3; font-size: 14px; padding: 6px 4px; }
.item-done { color: #3fb950; }
.item-done label { text-decoration-line: line-through; }
.status-bar { background-color: #21262d; padding: 6px 16px; }
.status-text { color: #8b949e; font-size: 12px; }
.toggle-row { padding: 6px 0; }
.nav-btn { background-color: #21262d; color: #e6edf3; border: none; padding: 8px 16px; border-radius: 6px; }
.nav-btn:hover { background-color: #30363d; }
.section-label { color: #8b949e; font-size: 11px; font-weight: bold; margin-bottom: 4px; }
.agent-badge { background-color: #388bfd20; color: #388bfd; border-radius: 4px;
               font-size: 11px; padding: 2px 8px; }
"""


class KikiApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.kiki.demo")

    def do_activate(self):
        global app_ref
        win = Gtk.ApplicationWindow(application=self)
        win.set_title("Kiki OS")
        win.set_default_size(720, 560)
        win.set_resizable(True)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            win.get_display(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.win = win
        self._build_ui()
        app_ref = self
        win.present()

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # ── Header ──
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("header")
        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lbl = Gtk.Label(label="Kiki OS")
        lbl.add_css_class("title")
        lbl.set_halign(Gtk.Align.START)
        sub = Gtk.Label(label="Agentic OS · offline demo")
        sub.add_css_class("subtitle")
        sub.set_halign(Gtk.Align.START)
        title_col.append(lbl)
        title_col.append(sub)
        header.append(title_col)
        badge = Gtk.Label(label="● AGENT CONNECTED")
        badge.add_css_class("agent-badge")
        badge.set_halign(Gtk.Align.END)
        badge.set_hexpand(True)
        self.agent_badge = badge
        header.append(badge)
        root.append(header)

        # ── Body (two columns) ──
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_vexpand(True)
        root.append(body)

        # Left: controls
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(340, -1)
        body.append(left)

        # Items list panel
        items_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        items_panel.add_css_class("panel")
        items_panel.set_vexpand(True)
        sec1 = Gtk.Label(label="TASK LIST")
        sec1.add_css_class("section-label")
        sec1.set_halign(Gtk.Align.START)
        items_panel.append(sec1)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.items_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroll.set_child(self.items_box)
        items_panel.append(scroll)
        left.append(items_panel)

        # Controls panel
        ctrl_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ctrl_panel.add_css_class("panel")
        left.append(ctrl_panel)

        # Navigation row
        nav_label = Gtk.Label(label="NAVIGATION")
        nav_label.add_css_class("section-label")
        nav_label.set_halign(Gtk.Align.START)
        ctrl_panel.append(nav_label)

        nav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.page_label = Gtk.Label(label="Page 1")
        self.page_label.set_hexpand(True)
        self.page_label.add_css_class("item-row")
        btn_prev = Gtk.Button(label="◄ Prev")
        btn_prev.add_css_class("nav-btn")
        btn_prev.connect("clicked", lambda _: self._navigate("prev"))
        btn_next = Gtk.Button(label="Next ►")
        btn_next.add_css_class("nav-btn")
        btn_next.connect("clicked", lambda _: self._navigate("next"))
        nav_row.append(btn_prev)
        nav_row.append(self.page_label)
        nav_row.append(btn_next)
        ctrl_panel.append(nav_row)

        sep = Gtk.Separator()
        ctrl_panel.append(sep)

        # Toggles
        toggle_label = Gtk.Label(label="CONTROLS")
        toggle_label.add_css_class("section-label")
        toggle_label.set_halign(Gtk.Align.START)
        ctrl_panel.append(toggle_label)

        self.toggles = {}
        for tid, tlabel in [("autopilot", "Autopilot Mode"), ("dark_mode", "Dark Mode")]:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            row.add_css_class("toggle-row")
            lbl = Gtk.Label(label=tlabel)
            lbl.add_css_class("item-row")
            lbl.set_hexpand(True)
            lbl.set_halign(Gtk.Align.START)
            sw = Gtk.Switch()
            sw.set_active(False)
            sw.connect("state-set", lambda sw, s, t=tid: self._on_toggle(t, s))
            self.toggles[tid] = sw
            row.append(lbl)
            row.append(sw)
            ctrl_panel.append(row)

        # Dialog button
        dlg_btn = Gtk.Button(label="Show Agent Dialog")
        dlg_btn.add_css_class("nav-btn")
        dlg_btn.connect("clicked", lambda _: self._show_dialog("Agent", "Triggered manually."))
        ctrl_panel.append(dlg_btn)

        # Right: agent log
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.set_hexpand(True)
        body.append(right)

        log_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        log_panel.add_css_class("panel")
        log_panel.set_vexpand(True)
        log_panel.set_hexpand(True)
        sec2 = Gtk.Label(label="AGENT LOG")
        sec2.add_css_class("section-label")
        sec2.set_halign(Gtk.Align.START)
        log_panel.append(sec2)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        log_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("log-view")
        log_scroll.set_child(self.log_view)
        log_panel.append(log_scroll)
        right.append(log_panel)

        # Status bar
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_bar.add_css_class("status-bar")
        self.status_label = Gtk.Label(label=state.status)
        self.status_label.add_css_class("status-text")
        self.status_label.set_halign(Gtk.Align.START)
        status_bar.append(self.status_label)
        root.append(status_bar)

    # ── Internal actions (called from GLib.idle_add) ──

    def _navigate(self, direction: str):
        if direction == "next":
            state.page += 1
        elif direction == "prev" and state.page > 0:
            state.page -= 1
        self.page_label.set_label(f"Page {state.page + 1}")

    def _on_toggle(self, tid: str, active: bool):
        setattr(state, tid, active)

    def _show_dialog(self, title: str, message: str):
        dlg = Gtk.Window(transient_for=self.win, modal=True, title=title)
        dlg.set_default_size(320, 160)
        dlg.set_resizable(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(24); box.set_margin_end(24)
        box.set_margin_top(24);   box.set_margin_bottom(16)
        lbl = Gtk.Label(label=message)
        lbl.set_wrap(True)
        lbl.add_css_class("item-row")
        btn = Gtk.Button(label="OK")
        btn.add_css_class("nav-btn")
        btn.connect("clicked", lambda _: dlg.close())
        box.append(lbl)
        box.append(btn)
        dlg.set_child(box)
        dlg.present()

    def _append_log(self, text: str):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text + "\n")
        # auto-scroll
        adj = self.log_view.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _refresh_items(self):
        child = self.items_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.items_box.remove(child)
            child = nxt
        for i, item in enumerate(state.items):
            done = item.startswith("[done] ")
            text = item[7:] if done else item
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = Gtk.Label(label="✓" if done else "○")
            icon.add_css_class("item-done" if done else "item-row")
            lbl = Gtk.Label(label=text)
            lbl.add_css_class("item-done" if done else "item-row")
            lbl.set_halign(Gtk.Align.START)
            lbl.set_hexpand(True)
            row.append(icon)
            row.append(lbl)
            if done:
                row.add_css_class("item-done")
            self.items_box.append(row)

    # ── Public API (thread-safe via GLib.idle_add) ──

    def api_add_item(self, text: str):
        def _do():
            state.items.append(text)
            self._refresh_items()
            self._append_log(f"+ item: {text}")
            return False
        GLib.idle_add(_do)

    def api_remove_item(self, index: int):
        def _do():
            if 0 <= index < len(state.items):
                removed = state.items.pop(index)
                self._refresh_items()
                self._append_log(f"- item [{index}]: {removed}")
            return False
        GLib.idle_add(_do)

    def api_clear_items(self):
        def _do():
            state.items.clear()
            self._refresh_items()
            self._append_log("cleared all items")
            return False
        GLib.idle_add(_do)

    def api_complete_item(self, index: int):
        def _do():
            if 0 <= index < len(state.items):
                t = state.items[index]
                if not t.startswith("[done] "):
                    state.items[index] = "[done] " + t
                self._refresh_items()
                self._append_log(f"✓ done [{index}]: {t}")
            return False
        GLib.idle_add(_do)

    def api_navigate(self, direction: str):
        def _do():
            self._navigate(direction)
            self._append_log(f"navigate → {direction} (page {state.page + 1})")
            return False
        GLib.idle_add(_do)

    def api_toggle(self, tid: str):
        def _do():
            current = getattr(state, tid, False)
            new_val = not current
            setattr(state, tid, new_val)
            if tid in self.toggles:
                self.toggles[tid].set_active(new_val)
            self._append_log(f"toggle {tid} → {'on' if new_val else 'off'}")
            return False
        GLib.idle_add(_do)

    def api_show_dialog(self, title: str, message: str):
        def _do():
            self._show_dialog(title, message)
            self._append_log(f"dialog: {title} — {message}")
            return False
        GLib.idle_add(_do)

    def api_set_status(self, text: str):
        def _do():
            state.status = text
            self.status_label.set_label(text)
            self._append_log(f"status: {text}")
            return False
        GLib.idle_add(_do)

    def api_log(self, text: str):
        def _do():
            self._append_log(text)
            return False
        GLib.idle_add(_do)


# ── HTTP Control API ──────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # silence access log

    def _respond(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/state":
            self._respond(200, {
                "items": state.items,
                "autopilot": state.autopilot,
                "dark_mode": state.dark_mode,
                "page": state.page,
                "status": state.status,
            })
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api":
            self._respond(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
        except Exception:
            self._respond(400, {"error": "invalid JSON"})
            return

        tool = payload.get("tool", "")
        result = self._dispatch(tool, payload)
        self._respond(200, {"ok": True, "result": result})

    def _dispatch(self, tool: str, p: dict) -> str:
        if app_ref is None:
            return "app not ready"
        if tool == "add_item":
            app_ref.api_add_item(p.get("text", ""))
            return f"added: {p.get('text')}"
        if tool == "remove_item":
            app_ref.api_remove_item(int(p.get("index", 0)))
            return "removed"
        if tool == "complete_item":
            app_ref.api_complete_item(int(p.get("index", 0)))
            return "completed"
        if tool == "clear_items":
            app_ref.api_clear_items()
            return "cleared"
        if tool == "navigate":
            app_ref.api_navigate(p.get("direction", "next"))
            return f"navigated {p.get('direction')}"
        if tool == "toggle":
            app_ref.api_toggle(p.get("id", "autopilot"))
            return f"toggled {p.get('id')}"
        if tool == "show_dialog":
            app_ref.api_show_dialog(p.get("title", "Kiki"), p.get("message", ""))
            return "dialog shown"
        if tool == "set_status":
            app_ref.api_set_status(p.get("text", ""))
            return "status updated"
        if tool == "log":
            app_ref.api_log(p.get("text", ""))
            return "logged"
        return f"unknown tool: {tool}"


def _start_server():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"  API: http://127.0.0.1:{PORT}/api")
    server.serve_forever()


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    print(f"\n  Kiki OS Demo App")
    print(f"  Agent control API: http://127.0.0.1:{PORT}/api")
    print(f"  Run the agent: python3 demo/app/agent.py\n")

    app = KikiApp()
    app.run([])
