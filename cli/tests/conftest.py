"""Shared fixtures: synthetic media made with ffmpeg, so the tests need no keys and spend nothing."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point VG_HOME at a throwaway folder so tests never read real keys or touch the real ledger."""
    home = tmp_path / "vg-home"
    home.mkdir()
    monkeypatch.setenv("VG_HOME", str(home))
    for key in ("OPENROUTER_API_KEY", "FAL_KEY"):
        monkeypatch.delenv(key, raising=False)
    return home


@pytest.fixture
def media(tmp_path) -> Path:
    """A small project: two stills, a 3 s clip, a 'voice' tone and a 'music' tone."""
    d = tmp_path / "proj"
    d.mkdir()
    ff("-f", "lavfi", "-i", "color=c=0x2e7d32:s=640x360", "-frames:v", "1", str(d / "a.png"))
    ff("-f", "lavfi", "-i", "color=c=0x1565c0:s=640x360", "-frames:v", "1", str(d / "b.png"))
    ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=30:d=3", "-pix_fmt", "yuv420p", str(d / "clip.mp4"))
    # the 'voice' speaks for 2 s; the 'music' runs the whole edit
    ff("-f", "lavfi", "-i", "sine=frequency=220:duration=2", "-ar", "48000", str(d / "voice.wav"))
    ff("-f", "lavfi", "-i", "sine=frequency=660:duration=8", "-ar", "48000", str(d / "music.wav"))
    return d
