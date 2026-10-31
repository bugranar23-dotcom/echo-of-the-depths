from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from mss import mss
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "visual-smoke.log"
SHOT = ROOT / "visual-smoke.png"


def fail(message: str, process: subprocess.Popen | None = None) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    print(f"VISUAL SMOKE TEST FAILED: {message}", flush=True)
    if LOG.exists():
        print(LOG.read_text(encoding="utf-8", errors="replace")[-12000:], flush=True)
    raise SystemExit(1)


def main() -> None:
    env = os.environ.copy()
    env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    with LOG.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "Echo_of_the_Depths.py")],
            cwd=ROOT,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )

    deadline = time.monotonic() + 100
    ready = False
    while time.monotonic() < deadline:
        if process.poll() is not None:
            fail(f"Game process exited with code {process.returncode}.", process)
        if LOG.exists():
            log_text = LOG.read_text(encoding="utf-8", errors="replace")
            if "[ECHO] Ilk bolum hazir." in log_text:
                ready = True
                break
            if "OYUN BASLATILAMADI" in log_text or "Traceback (most recent call last)" in log_text:
                fail("Startup traceback was found.", process)
        time.sleep(1)

    if not ready:
        fail("Game did not reach the first-chapter-ready message within 100 seconds.", process)

    # Let the chapter card and room scene settle before the visual capture.
    time.sleep(4)
    if process.poll() is not None:
        fail(f"Game closed before the screenshot (exit {process.returncode}).", process)

    try:
        with mss() as capture:
            monitor = capture.monitors[1]
            frame = capture.grab(monitor)
            from mss.tools import to_png
            to_png(frame.rgb, frame.size, output=str(SHOT))
    except Exception as exc:
        fail(f"Could not capture the game window: {type(exc).__name__}: {exc}", process)

    image = Image.open(SHOT).convert("RGB")
    stats = ImageStat.Stat(image)
    if max(stats.stddev) < 8:
        fail("Captured image looks almost uniform/blank.", process)

    # Confirm the frame contains more than a single flat colour.
    sample = image.resize((160, 90))
    if len(sample.getcolors(maxcolors=160 * 90) or []) < 20:
        fail("Captured frame has too little visual variation.", process)

    print(f"VISUAL SMOKE TEST PASSED: first chapter rendered to {SHOT.name}", flush=True)
    print(f"Screenshot size: {image.width}x{image.height}; colour stddev: {stats.stddev}", flush=True)

    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=4)


if __name__ == "__main__":
    main()
