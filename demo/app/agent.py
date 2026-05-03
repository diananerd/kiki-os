#!/usr/bin/env python3
"""Kiki OS — App Agent Demo.

Controls the running Kiki demo app (app.py) via its HTTP API.
The LLM decides which UI actions to take and they happen live.

Usage:
  python3 demo/app/agent.py
  python3 demo/app/agent.py "add 3 standup tasks, mark the first done, then show a summary dialog"
"""

import json
import os
import sys
import urllib.request
import urllib.error

OLLAMA  = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL   = os.getenv("KIKI_MODEL", "granite4.1:3b")
APP_API = os.getenv("KIKI_APP_API", "http://127.0.0.1:7070/api")

SYSTEM = """\
You are Kiki, an agentic OS. You control a live GTK4 desktop app through its API.
The app shows a task list, navigation, and toggles.
Use the tools to manipulate the UI — actions happen in real time on screen.
Be direct: complete the goal in as few steps as needed.\
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_item",
            "description": "Add a task/item to the list shown in the app.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_item",
            "description": "Mark an item as done by its index (0-based).",
            "parameters": {
                "type": "object",
                "properties": {"index": {"type": "integer"}},
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_item",
            "description": "Remove an item from the list by its index (0-based).",
            "parameters": {
                "type": "object",
                "properties": {"index": {"type": "integer"}},
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_items",
            "description": "Remove all items from the list.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate forward or backward in the app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["next", "prev"]}
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle",
            "description": "Toggle a switch in the app. Available ids: 'autopilot', 'dark_mode'.",
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_dialog",
            "description": "Show a modal dialog with a title and message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":   {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["title", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_state",
            "description": "Get the current state of the app (items, toggles, page).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _api_call(tool: str, args: dict) -> str:
    if tool == "get_state":
        req = urllib.request.Request(f"{APP_API}/state")
    else:
        body = json.dumps({"tool": tool, **args}).encode()
        req = urllib.request.Request(
            APP_API, data=body,
            headers={"Content-Type": "application/json"},
        )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.read().decode()
    except urllib.error.URLError:
        return f"error: app not reachable at {APP_API} — is demo/app/app.py running?"


def _inject_no_think(messages):
    if not MODEL.startswith("qwen3"):
        return messages
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        if out[i]["role"] == "user":
            out[i] = {**out[i], "content": "/no_think " + out[i]["content"]}
            break
    return out


def chat(messages):
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


CYAN   = "\033[36m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
GREY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
  ██╗  ██╗██╗██╗  ██╗██╗      █████╗ ██████╗ ██████╗
  ██║ ██╔╝██║██║ ██╔╝██║     ██╔══██╗██╔══██╗██╔══██╗
  █████╔╝ ██║█████╔╝ ██║     ███████║██████╔╝██████╔╝
  ██╔═██╗ ██║██╔═██╗ ██║     ██╔══██║██╔═══╝ ██╔═══╝
  ██║  ██╗██║██║  ██╗██║     ██║  ██║██║     ██║
  ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝
{RESET}{GREY}  app controller · offline · demo{RESET}
"""

DEFAULT_GOAL = (
    "Demo sequence: "
    "1) enable Autopilot mode, "
    "2) add 3 morning standup tasks: 'Review PRs', 'Team sync', 'Send weekly report', "
    "3) mark 'Review PRs' as done (index 0), "
    "4) navigate to the next page and back, "
    "5) show a dialog: title='Autopilot Complete', message='Morning standup ready. 1 task done, 2 remaining.'"
)


def run(goal: str):
    # Check app is reachable first
    try:
        urllib.request.urlopen(f"{APP_API}/state", timeout=2)
    except Exception:
        print(f"\n{YELLOW}⚠  App not running. Start it first:{RESET}")
        print(f"   python3 demo/app/app.py\n")
        sys.exit(1)

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": goal},
    ]

    print(f"\n{CYAN}▶ {goal}{RESET}\n")

    for _ in range(20):
        try:
            msg = chat(messages)
        except urllib.error.URLError as e:
            print(f"error: cannot reach Ollama — {e}", file=sys.stderr)
            sys.exit(1)

        messages.append(msg)
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            content = msg.get("content", "")
            if content.strip():
                print(f"{GREEN}{content}{RESET}")
            return

        for tc in tool_calls:
            fn   = tc["function"]
            name = fn["name"]
            args = fn.get("arguments") or {}
            label = f"{name}({', '.join(f'{k}={v!r}' for k,v in args.items())})" if args else f"{name}()"
            print(f"{YELLOW}⚡ {label}{RESET}", flush=True)
            result = _api_call(name, args)
            preview = result[:80] + ("…" if len(result) > 80 else "")
            if preview.strip():
                print(f"{GREY}  {preview}{RESET}")
            messages.append({"role": "tool", "content": result})

    print(f"{GREY}[step limit]{RESET}")


def main():
    print(BANNER)
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        goal = sys.stdin.read().strip()
    else:
        print(f"{GREY}Press Enter for the default demo sequence, or type a goal:{RESET}")
        try:
            goal = input(f"{CYAN}goal>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not goal:
            goal = DEFAULT_GOAL

    run(goal)


if __name__ == "__main__":
    main()
