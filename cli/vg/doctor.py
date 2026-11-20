"""`vg doctor`: what is installed, what is missing, and what each missing piece costs you.

Facts only. Keys are reported as present or missing, never printed.
"""

from __future__ import annotations

import shutil
import subprocess

from vg import config
from vg.html import chrome_path

# ffmpeg filters the pipeline uses, and what breaks without each
FILTERS = {
    "ass": "burned-in captions (needs ffmpeg built with libass)",
    "xfade": "crossfades between shots",
    "zoompan": "Ken Burns moves on stills",
    "loudnorm": "loudness normalisation",
    "sidechaincompress": "music ducking under the voice",
    "alimiter": "peak limiting after loudnorm",
    "ebur128": "the critic's loudness report",
    "drawtext": "timestamps on contact sheets",
    "silencedetect": "the critic's silence check",
    "blackdetect": "the critic's black-frame check",
    "freezedetect": "the critic's frozen-frame check",
    "cropdetect": "black-border check on generated images",
}


def _version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (out.stdout or out.stderr).strip().splitlines()
    return text[0][:90] if text else ""


def report() -> tuple[list[str], bool]:
    """Lines to print, and whether everything required is there."""
    lines, ok = [], True

    def row(state: str, name: str, detail: str) -> None:
        lines.append(f"{state:<8} {name:<22} {detail}")

    lines.append(f"VG_HOME  {config.home()}")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            row("ok", tool, _version([tool, "-version"]) or "")
        else:
            ok = False
            row("MISSING", tool, "required: every render, probe and check uses it")

    if shutil.which("ffmpeg"):
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        have = {ln.split()[1] for ln in out.splitlines() if len(ln.split()) > 2 and not ln.startswith(" ---")}
        for f, why in FILTERS.items():
            if f in have:
                row("ok", f"filter {f}", "")
            else:
                ok = False if f in ("ass", "xfade", "zoompan", "loudnorm", "sidechaincompress") else ok
                row("MISSING", f"filter {f}", why)

    for key, why in (("OPENROUTER_API_KEY", "images, video, voice, transcription, music, review"),
                     ("FAL_KEY", "optional: Kling and other fal.ai models, sound effects")):
        if config.secret(key):
            row("ok", key, "set (not shown)")
        else:
            ok = ok if key == "FAL_KEY" else False
            row("MISSING" if key != "FAL_KEY" else "optional", key, f"{why}; add {key}=... to {config.env_file()}")

    optional = {
        "yt-dlp": (["yt-dlp", "--version"], "Creative Commons footage (vg footage)"),
        "manim": (["manim", "--version"], "code-drawn motion graphics"),
        "node": (["node", "--version"], "Hyperframes motion graphics (with pnpm)"),
        "pnpm": (["pnpm", "--version"], "Hyperframes motion graphics"),
    }
    for name, (cmd, why) in optional.items():
        v = _version(cmd) if shutil.which(cmd[0]) else None
        row("ok" if v is not None else "optional", name, v if v is not None else f"not found: {why}")
    chrome = chrome_path()
    row("ok" if chrome else "optional", "chrome", chrome or "not found: vg html (exact text, layouts) needs Chrome or Chromium")
    return lines, ok
