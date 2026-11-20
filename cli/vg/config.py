"""Where vg keeps its settings, and how it reads keys.

VG_HOME (default ~/ove; an older ~/media-gen or ~/video-gen install with a .env is used while ~/ove is absent) holds `.env` (API keys), `costs.jsonl` (the spend ledger) and the optional
`.youtube-cookies.txt`. Keys are read from the environment first, then from VG_HOME/.env. Nothing here
ever prints a key.
"""

from __future__ import annotations

import os
from pathlib import Path


def home() -> Path:
    if env := os.environ.get("VG_HOME"):
        return Path(env).expanduser()
    new = Path.home() / "ove"
    if not new.exists():
        for old in (Path.home() / "media-gen", Path.home() / "video-gen"):   # earlier names of this tool
            if (old / ".env").exists():
                return old
    return new


def env_file() -> Path:
    return home() / ".env"


def secret(name: str) -> str | None:
    """A key from the environment, else from VG_HOME/.env (KEY=value lines; quotes stripped)."""
    if value := os.environ.get(name):
        return value
    f = env_file()
    found = None
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            if line.startswith(f"{name}="):
                found = line.split("=", 1)[1].strip().strip("'\"") or found   # the last non-empty one wins
    return found


def require(name: str) -> str:
    if value := secret(name):
        return value
    raise RuntimeError(f"{name} is not set: put {name}=... in {env_file()} (or export it)")
