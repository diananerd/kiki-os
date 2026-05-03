#!/usr/bin/env python3
"""Kiki OS — Full Demo Runner.

Starts everything and runs the scripted "oh shit" sequence:
  1. System autopilot  — agent controls GNOME: opens apps, toggles WiFi
  2. App autopilot     — agent controls live GTK4 UI in real time

Usage:
  python3 demo/run.py          # full sequence
  python3 demo/run.py shell    # system demo only
  python3 demo/run.py app      # GTK4 app demo only
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE  = Path(__file__).parent
AGENT = HERE / "agent" / "daemon.py"
APP   = HERE / "app"   / "app.py"
APP_AGENT = HERE / "app" / "agent.py"

DAEMON_URL = "http://127.0.0.1:8888"
APP_URL    = "http://127.0.0.1:7070"

CYAN  = "\033[36m"
GREEN = "\033[32m"
GREY  = "\033[90m"
BOLD  = "\033[1m"
RESET = "\033[0m"
DIM   = "\033[2m"

BANNER = f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════╗
║          K I K I   O S   —   F U L L   D E M O          ║
║     offline · agentic · no cloud · no magic              ║
╚══════════════════════════════════════════════════════════╝
{RESET}"""

# ── demo scripts ──────────────────────────────────────────────────

SHELL_DEMO_GOAL = """\
Execute each step in order:
1. open_app gnome-calculator
2. shell: gsettings set org.gnome.desktop.interface color-scheme default
3. shell: sleep 2
4. shell: gsettings set org.gnome.desktop.interface color-scheme prefer-dark
5. shell: sleep 2
6. close_app gnome-calculator\
"""

APP_DEMO_GOAL = """\
Do these steps in order:
1. Toggle autopilot on.
2. Add task "Review open PRs", add task "Team sync".
3. Mark task 0 as done.
4. Show a dialog title "Kiki OS" message "Offline. No cloud. Fully agentic."\
"""

# ── helpers ───────────────────────────────────────────────────────

def _wait_for(url: str, timeout: int = 10, label: str = "") -> bool:
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    print(f"  timeout waiting for {label or url}", file=sys.stderr)
    return False


def _inject_goal(goal: str) -> bool:
    body = json.dumps({"goal": goal}).encode()
    req = urllib.request.Request(
        f"{DAEMON_URL}/goal", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read()).get("ok", False)


def _wait_for_idle(timeout: int = 120) -> bool:
    for _ in range(timeout * 2):
        try:
            with urllib.request.urlopen(f"{DAEMON_URL}/state", timeout=2) as r:
                if json.loads(r.read()).get("status") == "idle":
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _print_log():
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/log", timeout=2) as r:
            entries = json.loads(r.read())
        print()
        for e in entries:
            if e["type"] in ("tool", "reply", "error"):
                icon = {"tool": "⚡", "reply": "✓", "error": "✗"}.get(e["type"], "·")
                color = {"tool": CYAN, "reply": GREEN, "error": "\033[31m"}.get(e["type"], GREY)
                print(f"  {color}{icon} {e['text']}{RESET}")
    except Exception:
        pass


def _step(n: int, label: str):
    print(f"\n{CYAN}{BOLD}[{n}] {label}{RESET}")


# ── demos ─────────────────────────────────────────────────────────

def demo_shell(daemon_proc):
    _step(1, "SYSTEM AUTOPILOT — agent controls GNOME desktop")
    print(f"{GREY}  goal: {SHELL_DEMO_GOAL.splitlines()[0]}…{RESET}")
    print(f"{DIM}  (watch the desktop — calculator will open, WiFi will go off and on){RESET}\n")
    _inject_goal(SHELL_DEMO_GOAL)
    print(f"{GREY}  running… (this takes ~30–60s on first inference){RESET}", flush=True)
    _wait_for_idle(timeout=600)
    _print_log()


def demo_app():
    _step(2, "APP AUTOPILOT — agent controls live GTK4 UI")
    print(f"{GREY}  goal: {APP_DEMO_GOAL.splitlines()[0]}…{RESET}")
    print(f"{DIM}  (watch the Kiki OS app window — UI updates in real time){RESET}\n")
    result = subprocess.run(
        [sys.executable, str(APP_AGENT), APP_DEMO_GOAL],
        capture_output=False,
    )


# ── main ──────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(BANNER)

    # ── Start daemon ──
    procs = []
    if mode in ("all", "shell"):
        print(f"{GREY}  starting agent daemon…{RESET}", flush=True)
        daemon_proc = subprocess.Popen(
            [sys.executable, str(AGENT), "--quiet"],
            stdin=subprocess.DEVNULL,
        )
        procs.append(daemon_proc)
        if not _wait_for(f"{DAEMON_URL}/state", timeout=6, label="daemon"):
            print("  daemon failed to start", file=sys.stderr)
            sys.exit(1)
        print(f"  {GREEN}✓ daemon ready{RESET}  {GREY}debug: curl {DAEMON_URL}/{RESET}")

    # ── Start GTK4 app ──
    if mode in ("all", "app"):
        print(f"{GREY}  starting Kiki OS app…{RESET}", flush=True)
        app_proc = subprocess.Popen(
            [sys.executable, str(APP)],
            stdin=subprocess.DEVNULL,
        )
        procs.append(app_proc)
        if not _wait_for(f"{APP_URL}/api/state", timeout=8, label="app"):
            print("  app failed to start", file=sys.stderr)
            [p.terminate() for p in procs]
            sys.exit(1)
        print(f"  {GREEN}✓ app ready{RESET}  {GREY}api: curl {APP_URL}/api/state{RESET}")

    print()
    if "--auto" not in sys.argv:
        input(f"{CYAN}  Press Enter to start the demo…{RESET} ")

    try:
        if mode in ("all", "shell"):
            demo_shell(daemon_proc)
            if mode == "all":
                print(f"\n{GREY}  ─────────────────────────────────────────{RESET}")
                if "--auto" not in sys.argv:
                    input(f"{CYAN}  Press Enter for the app demo…{RESET} ")
                else:
                    time.sleep(3)

        if mode in ("all", "app"):
            demo_app()

    except KeyboardInterrupt:
        print(f"\n{GREY}  interrupted{RESET}")
    finally:
        for p in procs:
            p.terminate()
        print(f"\n{GREY}  demo ended{RESET}")


if __name__ == "__main__":
    main()
