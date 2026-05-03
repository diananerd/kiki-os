#!/usr/bin/env python3
"""Kiki OS — System Controller CLI.

A thin tool for controlling the GNOME/Wayland desktop and system.
Used directly by humans or called by the agent daemon.

Usage:
  python3 demo/shell/demo.py list_apps
  python3 demo/shell/demo.py open_app gnome-calculator
  python3 demo/shell/demo.py close_app gnome-calculator
  python3 demo/shell/demo.py wifi_status
  python3 demo/shell/demo.py wifi_on
  python3 demo/shell/demo.py wifi_off
  python3 demo/shell/demo.py shell "ls -la ~"

Output is always plain text on stdout. Exit 0 on success.
"""

import os
import subprocess
import sys
import time

OUT = 2000

_KNOWN_APPS = {
    "gnome-calculator", "gnome-text-editor", "nautilus", "gnome-terminal",
    "xterm", "firefox", "firefox-esr", "code", "gedit", "evince",
    "gnome-system-monitor", "gnome-software", "gnome-clocks", "gnome-maps",
    "gnome-control-center",
}

_DANGER = ["rm -rf /", "mkfs", ":(){:|:&};:", "dd if=/dev/zero of=/dev/sd"]


def _run(cmd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()[:OUT]
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return str(e)


def list_apps() -> str:
    apps = []
    for name in sorted(_KNOWN_APPS):
        r = subprocess.run(["pidof", name], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            apps.append(name)
    return "running: " + (", ".join(apps) if apps else "none detected")


def open_app(name: str) -> str:
    # support "gnome-control-center wifi" as a single arg string
    parts = name.split()
    subprocess.Popen(parts, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.4)
    return f"launched: {name}"


def close_app(name: str) -> str:
    _run(f"pkill -f {name}")
    return f"closed: {name}"


def wifi_status() -> str:
    radio = _run("nmcli radio wifi")
    conn  = _run("nmcli -t -f NAME,TYPE,STATE con show --active 2>/dev/null | grep wifi | head -2")
    return f"radio: {radio}" + (f"\nnetwork: {conn}" if conn else "\nnot connected")


def wifi_on() -> str:
    _run("nmcli radio wifi on")
    time.sleep(1)
    return f"wifi on — {_run('nmcli radio wifi')}"


def wifi_off() -> str:
    _run("nmcli radio wifi off")
    time.sleep(1)
    return f"wifi off — {_run('nmcli radio wifi')}"


def shell_cmd(cmd: str) -> str:
    if any(d in cmd for d in _DANGER):
        return "blocked: dangerous command"
    return _run(cmd, timeout=30)


COMMANDS = {
    "list_apps":  (list_apps,  0),
    "open_app":   (open_app,   1),
    "close_app":  (close_app,  1),
    "wifi_status": (wifi_status, 0),
    "wifi_on":    (wifi_on,    0),
    "wifi_off":   (wifi_off,   0),
    "shell":      (shell_cmd,  1),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"unknown command: {cmd}", file=sys.stderr)
        print(f"available: {', '.join(COMMANDS)}", file=sys.stderr)
        sys.exit(1)

    fn, nargs = COMMANDS[cmd]
    args = sys.argv[2:]
    if len(args) < nargs:
        print(f"{cmd} requires {nargs} argument(s)", file=sys.stderr)
        sys.exit(1)

    result = fn(*args[:nargs]) if nargs else fn()
    print(result)


if __name__ == "__main__":
    main()
