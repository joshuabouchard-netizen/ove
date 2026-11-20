"""Word timings for captions, built from each voice file instead of the finished mix.

Transcribing the final mix works until music or sound effects sit under the voice: Whisper then drops whole
lines or mishears words, and captions built from it lose them. Transcribing each voice-over file on its own
and shifting its words to where `edit.yaml` places it gives clean, complete timings. Each file's transcript
is cached next to it as `<file>.words.json`, so re-timing the edit costs nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from vg import openrouter as orr
from vg import timeline


def for_file(src: Path, *, model: str = "openai/whisper-large-v3", refresh: bool = False) -> dict:
    cache = src.with_name(src.name + ".words.json")
    if cache.exists() and not refresh and cache.stat().st_mtime >= src.stat().st_mtime:
        return json.loads(cache.read_text())
    data = orr.transcribe(src, model=model)
    cache.write_text(json.dumps(data, indent=1))
    return data


def from_edit(edit_path: Path, *, model: str = "openai/whisper-large-v3", refresh: bool = False) -> dict:
    """{"text", "words"} for every `role: voice` item in the edit, on the edit's timeline."""
    edit = timeline.load(edit_path)
    words = []
    for a in sorted((a for a in edit.audio if a.role == "voice"), key=lambda a: a.at):
        data = for_file(a.src, model=model, refresh=refresh)
        end = a.src_in + a.dur if a.dur else float("inf")
        for w in data["words"]:
            if w["start"] < a.src_in or w["start"] >= end:
                continue  # outside the part of the file the edit uses
            shift = a.at - a.src_in
            words.append({"text": w["text"], "start": round(w["start"] + shift, 3), "end": round(w["end"] + shift, 3)})
    words.sort(key=lambda w: w["start"])
    return {"text": " ".join(w["text"] for w in words), "words": words, "model": f"{model} (per voice file)"}
