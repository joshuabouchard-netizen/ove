"""ffmpeg/ffprobe helpers shared by the other modules."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run(cmd: list[str], *, quiet: bool = True) -> subprocess.CompletedProcess:
    """Run a command, raising with its stderr tail if it fails."""
    if cmd[0] == "ffmpeg" and quiet:
        cmd = [cmd[0], "-hide_banner", "-loglevel", "error", "-y", *cmd[1:]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}):\n{tail}")
    return proc


def probe(path: str | Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(out.stdout)


def duration(path: str | Path) -> float:
    return float(probe(path)["format"]["duration"])


def has_audio(path: str | Path) -> bool:
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])


def is_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


def black_borders(path: str | Path) -> tuple[int, int, int, int] | None:
    """(left, right, top, bottom) bars in px if an image or first frame has black borders baked in, else None.

    Image models sometimes compose a 4:3 picture inside a 16:9 frame and pad it with black; the bars then
    carry into every clip made from that keyframe.
    """
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loop", "1", "-i", str(path), "-t", "0.1",
                           "-vf", "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"],
                          capture_output=True, text=True)
    crops = [ln.split("crop=")[-1].strip() for ln in proc.stderr.splitlines() if "crop=" in ln]
    if not crops:
        return None
    w, h, x, y = (int(v) for v in crops[-1].split(":"))
    s = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
    W, H = int(s["width"]), int(s["height"])
    left, right, top, bottom = x, W - w - x, y, H - h - y
    # a dark background reads as a border on one side; only symmetric bars of real width count
    side = left > W * 0.04 and right > W * 0.04 and abs(left - right) < W * 0.02
    flat = top > H * 0.04 and bottom > H * 0.04 and abs(top - bottom) < H * 0.02
    return (left, right, top, bottom) if side or flat else None


def overlay(base: str | Path, over: str | Path, out: str | Path, *, size: tuple[int, int] = (1920, 1080),
            fps: int = 30, dur: float | None = None) -> Path:
    """Composite a transparent overlay (a .mov/.webm with alpha, or a PNG) over a clip or still.

    The base is scaled and cropped to `size`; when it is shorter than `dur` its last frame is held, so a
    4 s generated clip can carry a 4.5 s title or counter.
    """
    w, h = size
    out = Path(out)
    total = dur or duration(base) if not is_image(base) else (dur or 4.0)
    base_in = ["-loop", "1", "-t", f"{total}", "-i", str(base)] if is_image(base) else ["-i", str(base)]
    over_in = ["-loop", "1", "-i", str(over)] if is_image(over) else ["-i", str(over)]
    vf = (f"[0]scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},fps={fps},"
          f"tpad=stop_mode=clone:stop_duration={total},format=yuv420p[b];[1]format=yuva420p[o];"
          f"[b][o]overlay=0:0:eof_action=pass:shortest=0")
    run(["ffmpeg", *base_in, *over_in, "-filter_complex", vf, "-t", f"{total}", "-an",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", str(out)])
    return out
