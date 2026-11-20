"""Real footage via yt-dlp: search YouTube's Creative Commons filter, confirm the licence, cut a section, log the credit."""

from __future__ import annotations

import json
import subprocess
import urllib.parse
from pathlib import Path

from vg import config

# YouTube's own "Creative Commons" search filter.
CC_FILTER = "EgIwAQ%3D%3D"
# YouTube bot-checks datacenter IPs. A Netscape cookies.txt from a
# logged-in browser (ideally a throwaway Google account) gets past it.
COOKIES = config.home() / ".youtube-cookies.txt"


def _ytdlp(*args: str) -> str:
    cookies = ["--cookies", str(COOKIES)] if COOKIES.exists() else []
    proc = subprocess.run(["yt-dlp", "--no-warnings", *cookies, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {proc.stderr.strip()[-800:]}")
    return proc.stdout


def info(url: str) -> dict:
    return json.loads(_ytdlp("-J", "--no-playlist", url))


def search(query: str, *, limit: int, cc_only: bool) -> list[dict]:
    q = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={q}" + (f"&sp={CC_FILTER}" if cc_only else "")
    flat = json.loads(_ytdlp("-J", "--flat-playlist", "--playlist-end", str(limit), url))
    results = []
    for e in flat.get("entries", []):
        # The flat listing carries no licence; fetch each video's metadata to confirm it.
        try:
            full = info(e["url"])
        except RuntimeError as err:
            blocked = "not a bot" in str(err)
            results.append(
                {
                    "url": e["url"],
                    "title": e.get("title"),
                    "channel": e.get("channel"),
                    "duration": e.get("duration"),
                    "license": f"UNCONFIRMED ({'YouTube bot check; see footage.md' if blocked else 'metadata failed'})",
                    "height": None,
                    "chapters": [],
                }
            )
            continue
        results.append(
            {
                "url": full["webpage_url"],
                "title": full.get("title"),
                "channel": full.get("channel") or full.get("uploader"),
                "duration": full.get("duration"),
                "license": full.get("license"),
                "height": full.get("height"),
                "chapters": [c.get("title") for c in full.get("chapters") or []],
            }
        )
    return results


def download(url: str, out: Path, *, start: float | None, end: float | None, max_height: int, credits: Path) -> Path:
    meta = info(url)
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ["-f", f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b", "--merge-output-format", "mp4"]
    if start is not None or end is not None:
        args += ["--download-sections", f"*{start or 0}-{end if end is not None else 'inf'}", "--force-keyframes-at-cuts"]
    _ytdlp(*args, "-o", str(out.with_suffix(".%(ext)s")), url)
    got = out.with_suffix(".mp4")

    log = json.loads(credits.read_text()) if credits.exists() else []
    log.append(
        {
            "file": str(got),
            "url": meta["webpage_url"],
            "title": meta.get("title"),
            "author": meta.get("channel") or meta.get("uploader"),
            "license": meta.get("license") or "UNKNOWN — check before publishing",
            "section": [start, end],
        }
    )
    credits.write_text(json.dumps(log, indent=2))
    return got
