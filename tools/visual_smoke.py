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

    audio_dir = ROOT / "echo_assets" / "audio"
    required_audio = ["ambience.wav", "step.wav", "pulse.wav", "sting.wav",
                      "pickup.wav", "knock.wav", "whisper.wav", "jumpscare.wav"]
    missing_audio = [name for name in required_audio if not (audio_dir / name).is_file()]
    if missing_audio:
        fail("Generated audio files are missing: " + ", ".join(missing_audio), process)

    log_text = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
    if "no audio found with name:" in log_text:
        fail("Ursina could not resolve a generated audio file path.", process)

    image = Image.open(SHOT).convert("RGB")
    stats = ImageStat.Stat(image)
    if max(stats.stddev) < 8:
        fail("Captured image looks almost uniform/blank.", process)

    # Measure the actual game viewport, excluding Xvfb's black outer margins.
    viewport = image.crop((160, 90, min(1440, image.width), min(810, image.height)))
    pixels = list(viewport.resize((160, 90)).getdata())
    near_white = sum(1 for r, g, b in pixels if min(r, g, b) > 242) / max(1, len(pixels))
    if near_white > 0.72:
        fail(f"Game viewport is still mostly blank/white ({near_white:.0%} near-white pixels).", process)

    sample = viewport.resize((160, 90))
    if len(sample.getcolors(maxcolors=160 * 90) or []) < 35:
        fail("Game viewport has too little visual detail.", process)

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
