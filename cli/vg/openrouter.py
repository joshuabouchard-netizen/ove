"""OpenRouter media endpoints: images, video jobs, speech, transcription, music, video review.

One key (OPENROUTER_API_KEY in the environment or VG_HOME/.env, default ~/video-gen/.env) reaches every
model. Request shapes were checked against the live API; AGENTS.md lists what an account's Zero Data
Retention setting blocks.
"""

from __future__ import annotations

import base64
import mimetypes
import time
from pathlib import Path

import httpx
from tqdm import tqdm

from vg import config, costs

BASE = "https://openrouter.ai/api/v1"


def _key() -> str:
    return config.require("OPENROUTER_API_KEY")


def _client(timeout: float = 300) -> httpx.Client:
    return httpx.Client(base_url=BASE, headers={"Authorization": f"Bearer {_key()}"}, timeout=timeout)


class OpenRouterError(RuntimeError):
    pass


def _check(r: httpx.Response) -> httpx.Response:
    if r.status_code >= 400:
        msg = r.text[:1500]
        if "zdr-violation" in msg or "ZDR violation" in msg:
            msg = (
                "Blocked by the account's Zero Data Retention setting (openrouter.ai/settings/privacy). "
                "This model has no ZDR endpoint. See AGENTS.md, 'Zero Data Retention'.\n" + msg[:400]
            )
        raise OpenRouterError(f"HTTP {r.status_code}: {msg}")
    return r


def _post(c: httpx.Client, path: str, body: dict, *, model: str, op: str) -> httpx.Response:
    """A paid request. An answer that worked is recorded by the caller, which knows its units; one that was refused,
    or that never came back (and may have been billed all the same), is recorded here before the error is raised."""
    try:
        r = c.post(path, json=body)
    except httpx.HTTPError as error:
        costs.attempt("ove", "openrouter", model=model, op=op, error=type(error).__name__)
        raise
    if r.status_code >= 400:
        costs.attempt("ove", "openrouter", model=model, op=op, status=r.status_code, body=r.text)
    return _check(r)


def data_uri(path: str | Path) -> str:
    """Local file → data URI; http(s) URLs pass through."""
    s = str(path)
    if s.startswith(("http://", "https://", "data:")):
        return s
    mime = mimetypes.guess_type(s)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(Path(s).read_bytes()).decode()}"


def _image_parts(paths: list[str]) -> list[dict]:
    return [{"type": "image_url", "image_url": {"url": data_uri(p)}} for p in paths]


# ---------------------------------------------------------------- images


def image(
    prompt: str,
    out: Path,
    *,
    model: str,
    refs: list[str],
    aspect_ratio: str | None,
    resolution: str | None,
    quality: str | None,
    n: int = 1,
) -> tuple[list[Path], float]:
    body: dict = {"model": model, "prompt": prompt, "n": n}
    if refs:
        body["input_references"] = _image_parts(refs)
    for k, v in (("aspect_ratio", aspect_ratio), ("resolution", resolution), ("quality", quality)):
        if v:
            body[k] = v
    with _client() as c:
        data = _post(c, "/images", body, model=model, op="image").json()
    paths = []
    for i, item in enumerate(data["data"]):
        ext = (item.get("media_type") or "image/png").split("/")[-1].replace("jpeg", "jpg")
        p = out.with_suffix(f".{ext}") if n == 1 else out.with_name(f"{out.stem}-{i + 1}.{ext}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(item["b64_json"]))
        paths.append(p)
    costs.usage("ove", "openrouter", data.get("usage"), model=model, op="image", units=n, unit="images")
    return paths, float(data.get("usage", {}).get("cost") or 0)


# ---------------------------------------------------------------- video


def video_models() -> list[dict]:
    with _client(60) as c:
        data = _check(c.get("/videos/models")).json()
    return data.get("data", data)


def video(
    prompt: str,
    out: Path,
    *,
    model: str,
    duration: int,
    aspect_ratio: str,
    resolution: str,
    audio: bool,
    first_frame: str | None,
    last_frame: str | None,
    refs: list[str],
    seed: int | None,
    poll: float = 10,
    timeout: float = 1800,
) -> tuple[Path, float]:
    body: dict = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "generate_audio": audio,
    }
    frames = []
    for img, kind in ((first_frame, "first_frame"), (last_frame, "last_frame")):
        if img:
            frames.append({"type": "image_url", "image_url": {"url": data_uri(img)}, "frame_type": kind})
    if frames:
        body["frame_images"] = frames
    if refs:
        # Ignored by the API when frame_images is also set; the CLI refuses that combination.
        body["input_references"] = _image_parts(refs)
    if seed is not None:
        body["seed"] = seed

    with _client() as c:
        job = _post(c, "/videos", body, model=model, op="video").json()
        jid = job["id"]
        start = time.time()
        with tqdm(desc=f"{model} {jid[:8]}", bar_format="{desc}: {elapsed} {postfix}") as bar:
            while True:
                st = _check(c.get(f"/videos/{jid}")).json()
                bar.set_postfix_str(st["status"])
                if st["status"] == "completed":
                    costs.usage("ove", "openrouter", st.get("usage"), model=model, op="video",
                                units=duration, unit="video_s")
                    break
                if st["status"] in ("failed", "cancelled", "expired"):  # accepted, then not made: its usage, if it has any, is kept
                    costs.attempt("ove", "openrouter", model=model, op="video", status=200, reported=st.get("usage"),
                                  outcome="error", error=st["status"], units=duration, unit="video_s")
                    raise OpenRouterError(f"video job {jid} {st['status']}: {st.get('error') or st}")
                if time.time() - start > timeout:  # still running there: it may finish and be billed with nobody to fetch it
                    costs.attempt("ove", "openrouter", model=model, op="video", outcome="no_answer", error="timeout",
                                  units=duration, unit="video_s")
                    raise OpenRouterError(f"video job {jid} still {st['status']} after {timeout:.0f}s")
                time.sleep(poll)
        out.parent.mkdir(parents=True, exist_ok=True)
        with c.stream("GET", f"/videos/{jid}/content", params={"index": 0}) as r:
            if r.status_code >= 400:
                r.read()
                _check(r)
            with out.open("wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
    return out, float((st.get("usage") or {}).get("cost") or 0)


# ---------------------------------------------------------------- speech


def speech(text: str, out: Path, *, model: str, voice: str, style: str | None) -> Path:
    """Text → audio. Style goes where each provider reads it.

    Gemini reads free-text direction ("warm, unhurried, a little amused").
    Azure MAI voices take a named style ("excited", "sad"...), and which names
    work depends on the voice.
    """
    out = out.with_suffix(".mp3")
    # Gemini TTS only answers in raw PCM (24 kHz, 16-bit, mono); it is converted to mp3 below.
    pcm = model.startswith("google/")
    body: dict = {"model": model, "input": text, "voice": voice, "response_format": "pcm" if pcm else "mp3"}
    if style:
        if model.startswith("google/"):
            body["provider"] = {"options": {"google-ai-studio": {"speech_metadata": {"style": style}}}}
        elif model.startswith("microsoft/"):
            body["provider"] = {"options": {"azure": {"style": style}}}
        elif model.startswith("openai/"):
            body["provider"] = {"options": {"openai": {"instructions": style}}}
    with _client() as c:
        audio = _post(c, "/audio/speech", body, model=model, op="speech").content
    # The speech endpoint answers with audio and no usage block, so the row carries the characters sent.
    costs.record("ove", "openrouter", model=model, op="speech", units=len(text), unit="chars", usd=None)
    out.parent.mkdir(parents=True, exist_ok=True)
    if pcm:
        from .media import run

        raw = out.with_suffix(".pcm")
        raw.write_bytes(audio)
        run(["ffmpeg", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(raw), "-b:a", "192k", str(out)])
        raw.unlink()
    else:
        out.write_bytes(audio)
    return out


# ---------------------------------------------------------------- transcription


def transcribe(path: Path, *, model: str) -> dict:
    """Audio or video → {"text", "words": [{"text", "start", "end"}]}. Video is stripped to mp3 first."""
    from .media import run

    src = path
    if path.suffix.lower() not in {".mp3", ".wav", ".m4a", ".flac", ".ogg"}:
        src = path.with_name(f".{path.stem}-asr.mp3")
        run(["ffmpeg", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(src)])
    body = {
        "model": model,
        "input_audio": {"data": base64.b64encode(src.read_bytes()).decode(), "format": src.suffix[1:]},
        "response_format": "verbose_json",
        "timestamp_granularities": ["word", "segment"],
    }
    with _client(600) as c:
        data = _post(c, "/audio/transcriptions", body, model=model, op="transcribe").json()
    costs.usage("ove", "openrouter", data.get("usage"), model=model, op="transcribe")
    words = [{"text": w["word"].strip(), "start": w["start"], "end": w["end"]} for w in data.get("words", [])]
    if not words:
        raise OpenRouterError(f"{model} returned no word timestamps; use openai/whisper-large-v3")
    return {"text": data.get("text", ""), "words": words, "model": model}


# ---------------------------------------------------------------- music


def music(prompt: str, out: Path, *, model: str) -> Path:
    """Lyria via chat completions. Audio output must be streamed: the SSE deltas carry base64 audio chunks."""
    import json

    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "modalities": ["text", "audio"], "stream": True}
    chunks: list[bytes] = []
    seen: set[str] = set()
    usage = None
    with _client(600) as c, c.stream("POST", "/chat/completions", json=body) as r:
        if r.status_code >= 400:
            r.read()
            costs.attempt("ove", "openrouter", model=model, op="music", status=r.status_code, body=r.text)
            _check(r)
        for line in r.iter_lines():
            if not line.startswith("data:") or line.strip() == "data: [DONE]":
                continue
            ev = json.loads(line[5:])
            usage = ev.get("usage") or usage
            for ch in ev.get("choices", []):
                delta = ch.get("delta") or ch.get("message") or {}
                seen.update(delta)
                parts = [delta.get("audio") or {}]
                if isinstance(delta.get("content"), list):
                    parts += [p.get("input_audio") or p.get("audio") or {} for p in delta["content"]]
                for p in parts:
                    if p.get("data"):
                        chunks.append(base64.b64decode(p["data"]))
    costs.usage("ove", "openrouter", usage, model=model, op="music")
    if not chunks:
        raise OpenRouterError(f"no audio in stream; delta keys seen: {sorted(seen)}")
    audio = b"".join(chunks)
    out.parent.mkdir(parents=True, exist_ok=True)
    head = audio[:4]
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        out = out.with_suffix(".mp3")
    elif head == b"RIFF":
        out = out.with_suffix(".wav")
    elif head == b"OggS":
        out = out.with_suffix(".ogg")
    elif head == b"fLaC":
        out = out.with_suffix(".flac")
    else:
        out = out.with_suffix(".raw")  # unknown container: inspect before use
    out.write_bytes(audio)
    print(f"cost ${float((usage or {}).get('cost') or 0):.4f}", file=__import__('sys').stderr)
    return out


# ---------------------------------------------------------------- review


def review_video(path: Path, prompt: str, *, model: str) -> str:
    """Send a (small) video to a Gemini model and return its critique."""
    size = path.stat().st_size
    if size > 45_000_000:
        raise OpenRouterError(f"{path.name} is {size / 1e6:.0f} MB; make a 720p proxy first (vg review does)")
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "video_url", "video_url": {"url": data_uri(path)}},
                ],
            }
        ],
    }
    with _client(600) as c:
        data = _post(c, "/chat/completions", body, model=model, op="review").json()
    costs.usage("ove", "openrouter", data.get("usage"), model=model, op="review")
    return data["choices"][0]["message"]["content"]
