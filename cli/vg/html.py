"""Render an HTML page to a PNG with headless Chrome.

This is how text stays exact: image models garble lettering, so titles, captions, speech bubbles, labels,
logotypes and whole layouts are set in HTML/CSS (any Google Font) over generated art, then rendered here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def chrome_path() -> str | None:
    if env := os.environ.get("VG_CHROME"):
        return env if Path(env).exists() else None
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        if found := shutil.which(name):
            return found
    return None


def render(page: Path | str, out: Path, *, width: int = 1920, height: int = 1080, scale: float = 1.0,
           wait_ms: int = 4000) -> Path:
    """Screenshot `page` (a local file, with an optional ?query/#hash, or a URL) at width x height CSS pixels, times `scale` device pixels.

    wait_ms is Chrome's virtual time budget: long enough for web fonts and scripts to settle.
    """
    chrome = chrome_path()
    if not chrome:
        raise RuntimeError("Chrome/Chromium not found; install it or set VG_CHROME=/path/to/chrome")
    url = str(page)
    if not url.startswith(("http://", "https://", "file://")):
        # a local file, optionally with ?query or #hash, so one page can render many assets (mockups.html?d=2&a=poster)
        cut = min((i for i in (url.find("?"), url.find("#")) if i >= 0), default=len(url))
        url = Path(url[:cut]).resolve().as_uri() + url[cut:]
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:  # a throwaway profile, so the user's Chrome is untouched
        cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
               f"--user-data-dir={profile}",
               f"--window-size={width},{height}", f"--force-device-scale-factor={scale}",
               f"--virtual-time-budget={wait_ms}", f"--screenshot={out}", url]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists():
        raise RuntimeError(f"Chrome made no screenshot (exit {proc.returncode}): {proc.stderr.strip()[-600:]}")
    return out
