"""Word-timed captions: group ASR words into short lines, write ASS (karaoke highlight) and SRT."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Word:
    text: str
    start: float
    end: float


def load_words(path: Path) -> list[Word]:
    """Read the words JSON that `vg transcribe` writes: {"words": [{"text", "start", "end"}]}."""
    data = json.loads(path.read_text())
    return [Word(w["text"], float(w["start"]), float(w["end"])) for w in data["words"]]


def group(words: list[Word], *, max_words: int, max_chars: int, gap: float = 0.45) -> list[list[Word]]:
    """Break lines at sentence ends, at pauses, and at the size limits."""
    lines: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        if cur:
            chars = sum(len(x.text) + 1 for x in cur) + len(w.text)
            if len(cur) >= max_words or chars > max_chars or w.start - cur[-1].end > gap:
                lines.append(cur)
                cur = []
        cur.append(w)
        if w.text.rstrip()[-1:] in ".?!":
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def _ts_ass(t: float) -> str:
    cs = round(t * 100)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ts_srt(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_ass(lines: list[list[Word]], out: Path, *, width: int, height: int, font: str, highlight: str) -> None:
    """ASS with \\k karaoke tags: each word lights up as it is spoken.

    highlight is an RGB hex like "FFD34E"; ASS wants BGR.
    """
    portrait = height > width
    size = round(height * (0.042 if portrait else 0.055))
    margin_v = round(height * (0.22 if portrait else 0.07))
    rgb = highlight.lstrip("#")
    bgr = rgb[4:6] + rgb[2:4] + rgb[0:2]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00{bgr},&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{max(2, size // 14)},1,2,{round(width * 0.08)},{round(width * 0.08)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for line in lines:
        parts = []
        for i, w in enumerate(line):
            # \k counts centiseconds until the next word lights, so silences stay on the previous word.
            nxt = line[i + 1].start if i + 1 < len(line) else w.end
            parts.append(f"{{\\k{max(1, round((nxt - w.start) * 100))}}}{w.text.strip()}")
        events.append(f"Dialogue: 0,{_ts_ass(line[0].start)},{_ts_ass(_end(lines, line))},Default,,0,0,0,,{' '.join(parts)}")
    out.write_text(header + "\n".join(events) + "\n")


def _end(lines: list[list[Word]], line: list[Word], hold: float = 0.15) -> float:
    """Hold a line briefly after its last word, but never into the next line, or the renderer stacks the two."""
    i = lines.index(line)
    end = line[-1].end + hold
    if i + 1 < len(lines):
        end = min(end, lines[i + 1][0].start - 0.01)
    return end


def write_srt(lines: list[list[Word]], out: Path) -> None:
    blocks = []
    for i, line in enumerate(lines, 1):
        text = " ".join(w.text.strip() for w in line)
        blocks.append(f"{i}\n{_ts_srt(line[0].start)} --> {_ts_srt(_end(lines, line))}\n{text}\n")
    out.write_text("\n".join(blocks))
