#!/usr/bin/env python3
"""Kiki OS — Agent Daemon.

Long-running agent service. Accepts goals from stdin (interactive shell)
and processes them through the LLM + tool loop.

Exposes an MCP-style debug HTTP server on port 8888:
  GET  /state       — agent state (status, goal, step count)
  GET  /log         — full agent log as JSON
  POST /goal        — inject a goal: {"goal": "..."}
  POST /pause       — pause after current step
  POST /resume      — resume
  DELETE /log       — clear log

Usage:
  python3 demo/agent/daemon.py          # interactive shell
  python3 demo/agent/daemon.py --quiet  # no banner, just prompts

Env:
  OLLAMA_URL        default http://localhost:11434
  KIKI_MODEL        default qwen3:4b
  KIKI_SHELL        path to demo/shell/demo.py (auto-detected)
  KIKI_MCP_PORT     debug server port (default 8888)
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

# ── Config ────────────────────────────────────────────────────────

OLLAMA   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
MODEL    = os.getenv("KIKI_MODEL",   "granite4.1:3b")
MCP_PORT = int(os.getenv("KIKI_MCP_PORT", "8888"))
OUT      = 1500

# Locate demo/shell/demo.py relative to this file
_HERE = Path(__file__).parent
SHELL = os.getenv("KIKI_SHELL", str(_HERE.parent / "shell" / "demo.py"))

# ── Shared agent state ────────────────────────────────────────────

_lock = threading.Lock()

_state = {
    "status":       "idle",      # idle | running | paused | error
    "current_goal": None,
    "step":         0,
    "log":          [],          # list of {ts, type, text}
    "paused":       False,
}
_goal_queue: list[str] = []
_goal_event = threading.Event()


def _log(entry_type: str, text: str):
    with _lock:
        _state["log"].append({
            "ts":   time.strftime("%H:%M:%S"),
            "type": entry_type,   # goal | tool | result | reply | error | system
            "text": text,
        })
        _COLORS = {"goal": CYAN, "tool": YELLOW, "result": GREY,
                   "reply": GREEN, "error": RED, "system": GREY}
        color = _COLORS.get(entry_type, RESET)
        prefix = {"goal": "▶", "tool": "⚡", "result": "·",
                  "reply": "✓", "error": "✗", "system": "·"}.get(entry_type, "·")
        print(f"{color}{prefix} {text}{RESET}", flush=True)


def _set_status(s: str):
    with _lock:
        _state["status"] = s


# ── System controller (calls demo/shell/demo.py) ──────────────────

def _shell_tool(command: str, *args) -> str:
    cmd = [sys.executable, SHELL, command] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (r.stdout + r.stderr).strip()[:OUT]
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return str(e)


# ── LLM tool definitions ──────────────────────────────────────────

SYSTEM = """\
You are Kiki, an agentic OS running on GNOME/Wayland (Debian 13).
Use tools to complete tasks. Each tool maps to a real system action.
Be concise. After the task is done, summarize what you did.\
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_apps",
            "description": "List running GUI applications.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch an application (e.g. gnome-calculator, nautilus, xterm).",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close a running application by process name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wifi_status",
            "description": "Get WiFi radio status and connected network.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wifi_on",
            "description": "Enable WiFi.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wifi_off",
            "description": "Disable WiFi.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Run a shell command for anything not covered by other tools.",
            "parameters": {
                "type": "object",
                "properties": {"cmd": {"type": "string"}},
                "required": ["cmd"],
            },
        },
    },
]


def dispatch(name: str, args: dict) -> str:
    if name == "list_apps":
        return _shell_tool("list_apps")
    if name == "open_app":
        return _shell_tool("open_app", args.get("app", ""))
    if name == "close_app":
        return _shell_tool("close_app", args.get("name") or args.get("app", ""))
    if name == "wifi_status":
        return _shell_tool("wifi_status")
    if name == "wifi_on":
        return _shell_tool("wifi_on")
    if name == "wifi_off":
        return _shell_tool("wifi_off")
    if name == "shell":
        return _shell_tool("shell", args.get("cmd", ""))
    return f"unknown tool: {name}"


# ── LLM chat ──────────────────────────────────────────────────────

def _inject_no_think(messages):
    if not MODEL.startswith("qwen3"):
        return messages
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        if out[i]["role"] == "user":
            out[i] = {**out[i], "content": "/no_think " + out[i]["content"]}
            break
    return out


def _chat(messages: list) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": _inject_no_think(messages),
        "tools": TOOLS,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["message"]


# ── Agent loop ────────────────────────────────────────────────────

def _run_goal(goal: str):
    _set_status("running")
    _log("goal", goal)
    with _lock:
        _state["current_goal"] = goal
        _state["step"] = 0

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": goal},
    ]

    for _ in range(20):
        # Pause check
        while _state["paused"]:
            _log("system", "paused — waiting…")
            time.sleep(1)

        with _lock:
            _state["step"] += 1

        try:
            msg = _chat(messages[-12:])
        except URLError as e:
            _log("error", f"Ollama unreachable: {e}")
            _set_status("error")
            return
        except Exception as e:
            _log("error", str(e))
            _set_status("error")
            return

        messages.append(msg)
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            content = msg.get("content", "").strip()
            if content:
                _log("reply", content)
            break

        for tc in tool_calls:
            fn   = tc["function"]
            name = fn["name"]
            args = fn.get("arguments") or {}
            label = f"{name}({', '.join(f'{k}={v!r}' for k,v in args.items())})" if args else f"{name}()"
            _log("tool", label)
            result = dispatch(name, args)
            preview = result[:120] + ("…" if len(result) > 120 else "")
            _log("result", preview)
            messages.append({"role": "tool", "content": result})

    _set_status("idle")
    with _lock:
        _state["current_goal"] = None


# ── MCP-style debug HTTP server ───────────────────────────────────

class _DebugHandler(BaseHTTPRequestHandler):
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
        with _lock:
            snapshot = {k: v for k, v in _state.items() if k != "log"}
        if self.path == "/state":
            self._json(200, snapshot)
        elif self.path == "/log":
            with _lock:
                self._json(200, _state["log"])
        elif self.path == "/":
            self._json(200, {
                "service": "kiki-agent-daemon",
                "model": MODEL,
                **snapshot,
                "mcp_endpoints": [
                    "GET /state", "GET /log",
                    "POST /goal", "POST /pause", "POST /resume",
                    "DELETE /log",
                ],
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
            self._json(200, {"ok": True, "paused": True})
        elif self.path == "/resume":
            with _lock:
                _state["paused"] = False
            self._json(200, {"ok": True, "paused": False})
        else:
            self._json(404, {"error": "not found"})

    def do_DELETE(self):
        if self.path == "/log":
            with _lock:
                _state["log"].clear()
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})


def _start_debug_server():
    server = HTTPServer(("127.0.0.1", MCP_PORT), _DebugHandler)
    server.serve_forever()


# ── Terminal colors ───────────────────────────────────────────────

CYAN   = "\033[36m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
GREY   = "\033[90m"
RED    = "\033[31m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
  ██╗  ██╗██╗██╗  ██╗██╗    ██████╗  █████╗ ███████╗███╗   ███╗ ██████╗ ███╗   ██╗
  ██║ ██╔╝██║██║ ██╔╝██║    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔═══██╗████╗  ██║
  █████╔╝ ██║█████╔╝ ██║    ██║  ██║███████║█████╗  ██╔████╔██║██║   ██║██╔██╗ ██║
  ██╔═██╗ ██║██╔═██╗ ██║    ██║  ██║██╔══██║██╔══╝  ██║╚██╔╝██║██║   ██║██║╚██╗██║
  ██║  ██╗██║██║  ██╗██║    ██████╔╝██║  ██║███████╗██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
{RESET}{GREY}  agentic OS · offline · {MODEL} · debug api: http://127.0.0.1:{MCP_PORT}{RESET}
"""


# ── Main ──────────────────────────────────────────────────────────

def _goal_worker():
    """Drain the goal queue, running one goal at a time."""
    while True:
        _goal_event.wait()
        _goal_event.clear()
        while True:
            with _lock:
                if not _goal_queue:
                    break
                goal = _goal_queue.pop(0)
            _run_goal(goal)


def main():
    quiet = "--quiet" in sys.argv

    if not quiet:
        print(BANNER)
        print(f"{GREY}  debug  →  curl http://127.0.0.1:{MCP_PORT}/{RESET}")
        print(f"{GREY}  inject →  curl -X POST http://127.0.0.1:{MCP_PORT}/goal -d '{{\"goal\":\"...\"}}'")
        print(f"{RESET}")

    # Start MCP debug server
    t = threading.Thread(target=_start_debug_server, daemon=True)
    t.start()

    # Start goal worker
    w = threading.Thread(target=_goal_worker, daemon=True)
    w.start()

    _log("system", f"daemon started — model: {MODEL}")

    # Interactive shell (only when stdin is a real terminal)
    if sys.stdin.isatty():
        while True:
            try:
                goal = input(f"{CYAN}kiki>{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{GREY}bye{RESET}")
                break
            if not goal:
                continue
            if goal in ("exit", "quit", "q"):
                break
            with _lock:
                _goal_queue.append(goal)
            _goal_event.set()
    else:
        # Headless mode: run until killed (goals come via HTTP)
        _log("system", f"headless mode — send goals to http://127.0.0.1:{MCP_PORT}/goal")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
