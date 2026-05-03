#!/usr/bin/env python3
"""Kiki — Launcher.

Starts the daemon and optionally the command palette bar.

Usage:
  python3 kiki/run.py          # daemon + bar
  python3 kiki/run.py daemon   # daemon only (headless)
  python3 kiki/run.py bar      # bar only (assumes daemon running)

The bar can be shown/hidden at any time with:
  python3 kiki/bar.py --toggle

To set a GNOME keyboard shortcut (recommended: Super+K):
  Settings → Keyboard → View and Customize Shortcuts
  → Custom Shortcuts → + → Command: python3 /path/to/kiki/bar.py --toggle
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent

DAEMON_URL = "http://127.0.0.1:8888"

CYAN  = "\033[36m"
GREEN = "\033[32m"
GREY  = "\033[90m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def _wait_for(url: str, timeout: int = 8, label: str = "") -> bool:
    for _ in range(timeout * 4):
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.25)
    print(f"  timeout waiting for {label or url}", file=sys.stderr)
    return False


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(f"\n{CYAN}{BOLD}  K I K I{RESET}  {GREY}agentic OS · offline{RESET}\n")

    procs = []

    if mode in ("all", "daemon"):
        print(f"{GREY}  starting daemon…{RESET}", flush=True)
        daemon = subprocess.Popen(
            [sys.executable, str(HERE / "daemon.py"), "--quiet"],
            stdin=subprocess.DEVNULL,
        )
        procs.append(daemon)
        if not _wait_for(f"{DAEMON_URL}/state", label="daemon"):
            print("  daemon failed to start", file=sys.stderr)
            sys.exit(1)
        print(f"  {GREEN}✓ daemon{RESET}  {GREY}http://127.0.0.1:8888/{RESET}")
        print(f"  {GREY}  stream → curl http://127.0.0.1:8888/stream{RESET}")

    if mode in ("all", "bar"):
        print(f"{GREY}  starting bar…{RESET}", flush=True)
        bar = subprocess.Popen(
            [sys.executable, str(HERE / "bar.py")],
            stdin=subprocess.DEVNULL,
        )
        procs.append(bar)
        time.sleep(1)
        print(f"  {GREEN}✓ bar{RESET}  {GREY}toggle: python3 kiki/bar.py --toggle{RESET}")

    if mode == "daemon":
        print(f"\n{GREY}  daemon running — send goals:{RESET}")
        print(f"  curl -X POST http://127.0.0.1:8888/goal -d '{{\"goal\":\"open calculator\"}}'")

    print()

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print(f"\n{GREY}  stopping…{RESET}")
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
