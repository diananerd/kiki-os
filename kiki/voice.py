#!/usr/bin/env python3
"""Kiki — Voice module.

Push-to-talk: record audio with arecord, transcribe with vosk.

Usage as library:
    from voice import Recorder
    r = Recorder()
    r.start()          # begin capturing mic
    ...user speaks...
    text = r.stop()    # stop and return transcribed text (or "" on failure)

Usage as CLI (returns transcription on stdout):
    python3 voice.py record <seconds>   # record N seconds, print text
"""

import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

_HERE  = Path(__file__).parent
MODEL_DIR = _HERE / "vosk-model-small-en-us-0.15"

# venv python for vosk
_VENV_PYTHON = Path.home() / ".kiki-env" / "bin" / "python3"
_PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

RATE   = 16000
CHANS  = 1
FORMAT = "S16_LE"


def _transcribe_file(wav_path: str) -> str:
    """Run vosk on a WAV file. Returns text or empty string."""
    script = f"""
import sys, json, wave
sys.path.insert(0, '')
try:
    import vosk
    model = vosk.Model("{MODEL_DIR}")
    wf    = wave.open("{wav_path}")
    rec   = vosk.KaldiRecognizer(model, {RATE})
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    print(result.get("text", ""))
except Exception as e:
    print("", file=sys.stdout)
    print(f"vosk error: {{e}}", file=sys.stderr)
"""
    try:
        r = subprocess.run([_PYTHON, "-c", script],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


class Recorder:
    """Push-to-talk recorder. start() → stop() → transcribed text."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._wav:  str = ""
        self.recording = False

    def start(self):
        if self.recording:
            return
        fd, self._wav = tempfile.mkstemp(suffix=".wav", prefix="kiki_")
        os.close(fd)
        self._proc = subprocess.Popen(
            ["arecord", "-r", str(RATE), "-f", FORMAT,
             "-c", str(CHANS), "-q", self._wav],
            stderr=subprocess.DEVNULL,
        )
        self.recording = True

    def stop(self) -> str:
        if not self.recording or not self._proc:
            return ""
        self.recording = False
        self._proc.terminate()
        try:
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None

        text = _transcribe_file(self._wav)
        try:
            os.unlink(self._wav)
        except Exception:
            pass
        return text


# ── CLI helper ────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "record":
        import time
        secs = float(sys.argv[2])
        r = Recorder()
        r.start()
        print(f"[recording {secs}s…]", file=sys.stderr, flush=True)
        time.sleep(secs)
        text = r.stop()
        print(text)
    else:
        print(__doc__)
