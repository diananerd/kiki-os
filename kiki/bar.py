#!/usr/bin/env python3
"""Kiki Bar — Floating command palette.

A lightweight HUD for sending goals to the Kiki agent daemon.
Supports text input and push-to-talk voice (Space to record).

Features:
  - Undecorated floating window, top-center of screen
  - Text entry with Enter to send
  - Space (hold) = push-to-talk voice input → STT → auto-send
  - Mic button click = toggle recording
  - Escape = hide window
  - Real-time agent log via SSE from daemon
  - Toggle via: python3 bar.py --toggle  (Unix socket IPC)

Usage:
  python3 kiki/bar.py           # start visible
  python3 kiki/bar.py --hidden  # start hidden (for autostart)
  python3 kiki/bar.py --toggle  # toggle if running, else start

Configure a GNOME keyboard shortcut to run:
  python3 /path/to/kiki/bar.py --toggle
"""

import json
import os
import socket
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango

# ── Config ─────────────────────────────────────────────────────────

DAEMON_URL = "http://127.0.0.1:8888"
BAR_API_PORT = int(os.getenv("KIKI_BAR_PORT", "7071"))
SOCK_PATH  = "/tmp/kiki-bar.sock"
BAR_WIDTH  = 640
LOG_LINES  = 5   # visible log lines in the output area
_HERE      = Path(__file__).parent

# ── CSS ─────────────────────────────────────────────────────────────

CSS = b"""
window {
    background: rgba(16, 16, 20, 0.96);
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.bar-box {
    padding: 14px 16px 12px 16px;
}
.input-row {
}
entry {
    background: rgba(255, 255, 255, 0.06);
    color: #e8e8f0;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.10);
    padding: 8px 12px;
    font-size: 15px;
    caret-color: #7c9ef8;
}
entry:focus {
    border-color: rgba(124, 158, 248, 0.5);
    background: rgba(255, 255, 255, 0.09);
}
.mic-btn {
    background: rgba(255,255,255,0.07);
    color: #a0a0b8;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.08);
    min-width: 36px;
    min-height: 36px;
    padding: 0;
    font-size: 16px;
}
.mic-btn:hover {
    background: rgba(124, 158, 248, 0.15);
    color: #c0ccf8;
}
.mic-btn.recording {
    background: rgba(220, 80, 80, 0.25);
    color: #f07070;
    border-color: rgba(220, 80, 80, 0.4);
}
.log-area {
    padding: 6px 4px 2px 4px;
}
.log-line {
    font-family: monospace;
    font-size: 12px;
    color: #606080;
    padding: 1px 0;
}
.log-line.tool   { color: #8aacf8; }
.log-line.reply  { color: #70d090; }
.log-line.error  { color: #e07070; }
.log-line.goal   { color: #a0b8f0; }
.log-line.system { color: #484860; }
.log-line.result { color: #484860; }
.status-dot {
    font-size: 11px;
    color: #484860;
    padding: 2px 0 4px 4px;
}
.status-dot.running { color: #8aacf8; }
.status-dot.error   { color: #e07070; }
"""

_ICON = {"tool": "⚡", "reply": "✓", "error": "✗", "goal": "▶",
         "system": "·", "result": "·"}

# ── IPC: socket toggle ────────────────────────────────────────────────

def _send_toggle():
    """Connect to running bar and send 'toggle'. Returns True if contacted."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(SOCK_PATH)
            s.sendall(b"toggle\n")
        return True
    except Exception:
        return False


def _start_socket_server(on_toggle):
    """Listen on Unix socket for toggle commands."""
    try:
        os.unlink(SOCK_PATH)
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK_PATH)
    srv.listen(1)

    def _loop():
        while True:
            try:
                conn, _ = srv.accept()
                data = conn.recv(64).decode().strip()
                conn.close()
                if data == "toggle":
                    GLib.idle_add(on_toggle)
            except Exception:
                pass

    threading.Thread(target=_loop, daemon=True).start()


# ── Voice ─────────────────────────────────────────────────────────────

class _Voice:
    def __init__(self):
        self._rec = None
        self.available = False
        self._load()

    def _load(self):
        try:
            sys.path.insert(0, str(_HERE))
            from voice import Recorder
            self._rec = Recorder()
            self.available = True
        except Exception:
            self.available = False

    def start(self):
        if self._rec:
            self._rec.start()

    def stop(self) -> str:
        if self._rec:
            return self._rec.stop()
        return ""


# ── Daemon poller ─────────────────────────────────────────────────────

class _DaemonPoller:
    def __init__(self, on_update):
        self._cb = on_update
        self._last_len = 0
        self._status   = "?"

    def start(self):
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while True:
            try:
                with urllib.request.urlopen(f"{DAEMON_URL}/state", timeout=1) as r:
                    state = json.loads(r.read())
                status = state.get("status", "?")
            except Exception:
                status = "offline"

            try:
                with urllib.request.urlopen(f"{DAEMON_URL}/log", timeout=1) as r:
                    log = json.loads(r.read())
            except Exception:
                log = []

            if status != self._status or len(log) != self._last_len:
                self._status   = status
                self._last_len = len(log)
                entries = log[-LOG_LINES:]
                GLib.idle_add(self._cb, status, entries)

            time.sleep(0.5)


# ── HTTP API (makes the bar controllable as an app tool) ─────────────

def _start_api_server(bar: "KikiBar"):
    """Expose bar state and controls via HTTP, same pattern as demo app."""

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _json(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                return json.loads(self.rfile.read(n)) if n else {}
            except Exception:
                return {}

        def do_GET(self):
            if self.path in ("/", "/api/state"):
                GLib.idle_add(_capture_state, bar)
                # state captured asynchronously; return last known
                self._json(200, {
                    "visible":   bar.is_visible(),
                    "recording": bar._recording,
                    "entry":     bar._entry.get_text() if hasattr(bar, "_entry") else "",
                    "voice_available": bar._voice.available,
                    "api_port":  BAR_API_PORT,
                    "actions": ["show", "hide", "toggle", "set_text", "submit",
                                "send_goal", "start_recording", "stop_recording"],
                })
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self.path.startswith("/api/"):
                self._json(404, {"error": "not found"})
                return
            action = self.path[5:]  # strip /api/
            body   = self._body()

            def _dispatch():
                if action == "show":
                    bar.present()
                elif action == "hide":
                    bar.set_visible(False)
                elif action == "toggle":
                    bar._toggle_visibility()
                elif action == "set_text":
                    bar._entry.set_text(body.get("text", ""))
                    bar._entry.set_position(-1)
                elif action == "submit":
                    bar._on_send(bar._entry)
                elif action == "send_goal":
                    goal = body.get("goal", body.get("text", "")).strip()
                    if goal:
                        bar._send_goal(goal)
                elif action == "start_recording":
                    bar._start_recording()
                elif action == "stop_recording":
                    bar._stop_recording(send=body.get("send", True))
                else:
                    return
            GLib.idle_add(_dispatch)
            self._json(200, {"ok": True, "action": action})

    def _capture_state(b):
        pass  # state is read directly in do_GET

    def _serve():
        try:
            HTTPServer(("127.0.0.1", BAR_API_PORT), _Handler).serve_forever()
        except OSError as e:
            print(f"[bar api] port {BAR_API_PORT} unavailable: {e}", file=sys.stderr)

    threading.Thread(target=_serve, daemon=True).start()


# ── Main window ───────────────────────────────────────────────────────

class KikiBar(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(BAR_WIDTH, -1)
        self.set_title("Kiki")

        self._voice     = _Voice()
        self._recording = False
        self._hidden    = "--hidden" in sys.argv

        self._build_ui()
        self._apply_css()
        self._position_window()

        self._poller = _DaemonPoller(self._on_daemon_update)
        self._poller.start()

        _start_socket_server(self._toggle_visibility)
        _start_api_server(self)

        if self._hidden:
            self.set_visible(False)
        else:
            self.present()

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.add_css_class("bar-box")

        # ── input row ──
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_row.add_css_class("input-row")

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Ask Kiki… (Enter to send, Space = voice)")
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_send)
        input_row.append(self._entry)

        self._mic_btn = Gtk.Button(label="🎤")
        self._mic_btn.add_css_class("mic-btn")
        self._mic_btn.set_tooltip_text("Hold to talk (or hold Space)")

        gesture = Gtk.GestureClick()
        gesture.connect("pressed",  self._on_mic_pressed)
        gesture.connect("released", self._on_mic_released)
        self._mic_btn.add_controller(gesture)
        input_row.append(self._mic_btn)

        outer.append(input_row)

        # ── status dot ──
        self._status_label = Gtk.Label(label="● idle")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.add_css_class("status-dot")
        outer.append(self._status_label)

        # ── log area ──
        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        log_box.add_css_class("log-area")
        self._log_labels: list[Gtk.Label] = []
        for _ in range(LOG_LINES):
            lbl = Gtk.Label(label="")
            lbl.set_halign(Gtk.Align.START)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.set_max_width_chars(72)
            lbl.add_css_class("log-line")
            log_box.append(lbl)
            self._log_labels.append(lbl)
        outer.append(log_box)

        self.set_child(outer)

        # ── keyboard handling ──
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed",  self._on_key_pressed)
        key_ctrl.connect("key-released", self._on_key_released)
        self.add_controller(key_ctrl)

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _position_window(self):
        display = Gdk.Display.get_default()
        monitor = display.get_monitors().get_item(0)
        if monitor:
            geo = monitor.get_geometry()
            x = geo.x + (geo.width - BAR_WIDTH) // 2
            y = geo.y + 48
            # GTK4/Wayland: set_position not available; use startup notification workaround
            # Best we can do: set default size and let compositor place it
            # On X11 this works via move(); on Wayland we rely on centering
            pass

    # ── Keyboard events ─────────────────────────────────────────────

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        # Escape → hide
        if keyval == Gdk.KEY_Escape:
            if self._recording:
                self._stop_recording(send=False)
            else:
                self.set_visible(False)
            return True

        # Space → PTT (only when text entry is empty and not focused)
        if keyval == Gdk.KEY_space:
            focused = self.get_focus()
            entry_text = self._entry.get_text()
            if focused != self._entry or entry_text == "":
                if not self._recording:
                    self._start_recording()
                return True

        return False

    def _on_key_released(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_space and self._recording:
            self._stop_recording(send=True)
            return True
        return False

    # ── Mic button ──────────────────────────────────────────────────

    def _on_mic_pressed(self, gesture, n, x, y):
        if not self._recording:
            self._start_recording()

    def _on_mic_released(self, gesture, n, x, y):
        if self._recording:
            self._stop_recording(send=True)

    # ── Recording ───────────────────────────────────────────────────

    def _start_recording(self):
        if not self._voice.available:
            self._entry.set_placeholder_text("voice not available — type instead")
            return
        self._recording = True
        self._mic_btn.add_css_class("recording")
        self._mic_btn.set_label("🔴")
        self._entry.set_placeholder_text("Listening…")
        threading.Thread(target=self._voice.start, daemon=True).start()

    def _stop_recording(self, send: bool = True):
        if not self._recording:
            return
        self._recording = False
        self._mic_btn.remove_css_class("recording")
        self._mic_btn.set_label("🎤")
        self._entry.set_placeholder_text("Transcribing…")

        def _finish():
            text = self._voice.stop()
            def _update():
                self._entry.set_placeholder_text("Ask Kiki… (Enter to send, Space = voice)")
                if text:
                    self._entry.set_text(text)
                    if send:
                        self._send_goal(text)
                        self._entry.set_text("")
            GLib.idle_add(_update)

        threading.Thread(target=_finish, daemon=True).start()

    # ── Send goal ───────────────────────────────────────────────────

    def _on_send(self, entry):
        text = entry.get_text().strip()
        if text:
            self._send_goal(text)
            entry.set_text("")

    def _send_goal(self, goal: str):
        def _post():
            try:
                body = json.dumps({"goal": goal}).encode()
                req  = urllib.request.Request(
                    f"{DAEMON_URL}/goal", data=body,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception as e:
                GLib.idle_add(
                    self._append_log_line, "error",
                    f"daemon unreachable: {e}"
                )
        threading.Thread(target=_post, daemon=True).start()

    # ── Log update ──────────────────────────────────────────────────

    def _on_daemon_update(self, status: str, entries: list):
        # Status dot
        self._status_label.set_label(f"● {status}")
        for cls in ("running", "error"):
            self._status_label.remove_css_class(cls)
        if status in ("running", "error"):
            self._status_label.add_css_class(status)

        # Log lines
        padded = ([""] * LOG_LINES + entries)[-LOG_LINES:]
        for lbl, entry in zip(self._log_labels, padded):
            if not entry:
                lbl.set_text("")
                for c in ("tool","reply","error","goal","system","result"):
                    lbl.remove_css_class(c)
                continue
            icon = _ICON.get(entry["type"], "·")
            lbl.set_text(f"{entry['ts']} {icon} {entry['text']}")
            for c in ("tool","reply","error","goal","system","result"):
                lbl.remove_css_class(c)
            lbl.add_css_class(entry["type"])

    def _append_log_line(self, entry_type: str, text: str):
        self._on_daemon_update(
            self._status_label.get_label().lstrip("● ").strip(),
            [{"ts": time.strftime("%H:%M:%S"), "type": entry_type, "text": text}],
        )

    # ── Visibility ──────────────────────────────────────────────────

    def _toggle_visibility(self):
        if self.is_visible():
            self.set_visible(False)
        else:
            self.present()
            self._entry.grab_focus()


# ── Application ──────────────────────────────────────────────────────

class KikiApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.kiki.bar")

    def do_activate(self):
        win = KikiBar(self)
        win.connect("close-request", lambda _: True)  # hide instead of quit


def main():
    # --toggle: contact running instance or start new
    if "--toggle" in sys.argv:
        if _send_toggle():
            return
        # not running — start visible
        sys.argv.remove("--toggle")

    app = KikiApp()
    app.run(None)


if __name__ == "__main__":
    main()
