"""Hands-free key setup: open the right account pages, then take a key from the clipboard into VG_HOME/.env.

The person copies a key in their browser; `vg keys paste openrouter` reads the clipboard, checks the key looks
right, writes it to .env (mode 600), clears the clipboard, and tests it against the provider. The key never
appears in a chat or a terminal: only its last four characters are shown.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import webbrowser

import httpx

from vg import config

PROVIDERS = {
    "openrouter": {
        "env": "OPENROUTER_API_KEY",
        "pages": [
            ("Sign up or sign in, then add credit", "https://openrouter.ai/settings/credits"),
            ("Turn OFF Zero Data Retention (video and music need it off)", "https://openrouter.ai/settings/privacy"),
            ("Create a key with a weekly limit, then copy it", "https://openrouter.ai/settings/keys"),
        ],
    },
    "fal": {
        "env": "FAL_KEY",
        "pages": [
            ("Sign up or sign in, then add credit", "https://fal.ai/dashboard/billing"),
            ("Create a key, then copy it", "https://fal.ai/dashboard/keys"),
        ],
    },
}


def pages(provider: str) -> list[tuple[str, str]]:
    return PROVIDERS[provider]["pages"]


def open_pages(provider: str) -> list[tuple[str, str]]:
    for _, url in pages(provider):
        webbrowser.open(url)
    return pages(provider)


def _clipboard_cmd() -> list[str] | None:
    if custom := os.environ.get("VG_CLIPBOARD_CMD"):
        return shlex.split(custom)
    for cmd in (["pbpaste"], ["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "-b", "-o"]):
        if shutil.which(cmd[0]):
            return cmd
    return None


def read_clipboard() -> str:
    cmd = _clipboard_cmd()
    if not cmd:
        raise RuntimeError("no clipboard tool found (pbpaste, wl-paste, xclip or xsel)")
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def clear_clipboard() -> None:
    if os.environ.get("VG_CLIPBOARD_CMD"):
        return
    if shutil.which("pbcopy"):
        subprocess.run(["pbcopy"], input="", text=True)


def problem(provider: str, value: str) -> str | None:
    """Why this doesn't look like a key for the provider, or None if it does."""
    if not value:
        return "the clipboard is empty: copy the key first"
    if any(c.isspace() for c in value):
        return "the clipboard holds more than one word: copy just the key"
    if len(value) < 20:
        return "that is too short to be a key"
    if provider == "openrouter" and not value.startswith("sk-or-"):
        return "OpenRouter keys start with sk-or-; copy the key itself"
    return None


def save(name: str, value: str) -> None:
    """Set NAME=value in VG_HOME/.env, replacing an existing line, keeping comments and other keys."""
    f = config.env_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    lines = f.read_text().splitlines() if f.exists() else []
    out, done = [], False
    for line in lines:
        bare = line.strip().removeprefix("export ").strip()
        if bare.startswith(f"{name}=") and not line.lstrip().startswith("#"):
            if not done:
                out.append(f"{name}={value}"); done = True
            continue
        out.append(line)
    if not done:
        out.append(f"{name}={value}")
    f.write_text("\n".join(out) + "\n")
    f.chmod(0o600)


def masked(value: str | None) -> str:
    return f"…{value[-4:]}" if value else "not set"


def check(provider: str) -> tuple[bool | None, str]:
    """(works?, detail) by a free call to the provider. None = couldn't tell (network)."""
    key = config.secret(PROVIDERS[provider]["env"])
    if not key:
        return False, "not set"
    try:
        if provider == "openrouter":
            r = httpx.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"}, timeout=20)
        else:
            r = httpx.get("https://api.fal.ai/v1/models/pricing", params={"endpoint_id": "fal-ai/elevenlabs/sound-effects/v2"},
                          headers={"Authorization": f"Key {key}"}, timeout=20)
    except httpx.HTTPError as e:
        return None, f"could not reach the provider ({type(e).__name__})"
    if r.status_code == 200:
        return True, "works"
    if r.status_code in (401, 403):
        return False, "the provider rejected it: copy the key again (or make a new one)"
    return None, f"provider answered HTTP {r.status_code}"
