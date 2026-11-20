"""vg — the helper CLI behind OVE (Ops Video Editor): images, video, voice, music, captions, assembly and checks.

Run `vg <command> --help`. `vg doctor` checks the install; `vg spend` shows what has been spent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from . import captions as cap
from . import config
from . import costs
from . import critic as crit
from . import doctor as doc
from . import fal as falmod
from . import keys as keysmod
from . import footage as foot
from . import html as htmlmod
from . import openrouter as orr
from . import sfx as sfxmod
from . import timeline
from . import words as wordsmod
from .media import black_borders, overlay as overlay_media, probe, run

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)
footage_app = typer.Typer(no_args_is_help=True, help="Real Creative Commons clips via yt-dlp.")
app.add_typer(footage_app, name="footage")
fal_app = typer.Typer(no_args_is_help=True, help="fal.ai models (Kling, Veo, Wan, Hailuo video; video edits; images; ElevenLabs SFX) via fal's queue API.")
app.add_typer(fal_app, name="fal")
keys_app = typer.Typer(no_args_is_help=True, help="Set up API keys hands-free: open the account pages, then save a key from the clipboard.")
app.add_typer(keys_app, name="keys")

Out = Annotated[Path, typer.Option("-o", "--out", help="Output path.")]


def _text(arg: str) -> str:
    """Accept literal text or @path/to/file.txt."""
    return Path(arg[1:]).read_text().strip() if arg.startswith("@") else arg


@app.command()
def image(
    prompt: Annotated[str, typer.Argument(help="Prompt, or @file.txt")],
    out: Out,
    ref: Annotated[list[str], typer.Option("--ref", help="Reference image (repeatable, up to 16) for consistency or editing.")] = [],
    model: str = "google/gemini-3-pro-image",
    aspect: Annotated[Optional[str], typer.Option(help="e.g. 16:9, 9:16, 1:1, 4:5")] = None,
    resolution: Annotated[Optional[str], typer.Option(help="1K | 2K | 4K")] = None,
    quality: Annotated[Optional[str], typer.Option(help="low | medium | high | xhigh | max")] = None,
    n: int = 1,
):
    """Generate a keyframe or reference image."""
    paths, cost = orr.image(_text(prompt), out, model=model, refs=ref, aspect_ratio=aspect, resolution=resolution, quality=quality, n=n)
    for p in paths:
        typer.echo(p)
        if bars := black_borders(p):
            typer.echo(f"warning: {p.name} has black bars baked in (left/right/top/bottom px {bars}); "
                       "regenerate asking for a full-bleed frame with no borders", err=True)
    typer.echo(f"cost ${cost:.4f}", err=True)


@app.command()
def video(
    prompt: Annotated[str, typer.Argument(help="Prompt, or @file.txt")],
    out: Out,
    model: str = "google/veo-3.1",
    duration: int = 8,
    aspect: str = "16:9",
    resolution: str = "1080p",
    audio: Annotated[bool, typer.Option("--audio/--no-audio", help="Native generated sound (dialogue, ambience).")] = False,
    first: Annotated[Optional[str], typer.Option(help="Image to start exactly on.")] = None,
    last: Annotated[Optional[str], typer.Option(help="Image to end exactly on.")] = None,
    ref: Annotated[list[str], typer.Option("--ref", help="Loose subject/style reference (not with --first/--last).")] = [],
    seed: Optional[int] = None,
    retries: Annotated[int, typer.Option(help="Resubmit this many times if the provider refuses with 'high load' (refused jobs are not billed).")] = 2,
    fallback: Annotated[Optional[str], typer.Option(help="Model to switch to once retries run out, e.g. bytedance/seedance-2.5.")] = None,
):
    """Generate one clip (async job; polls until done, then downloads)."""
    import time

    if ref and (first or last):
        raise typer.BadParameter("--ref is ignored when --first/--last are set; bake the reference into the keyframe instead")
    tries = [model] * (retries + 1) + ([fallback] if fallback else [])
    for i, m in enumerate(tries):
        try:
            path, cost = orr.video(
                _text(prompt), out, model=m, duration=duration, aspect_ratio=aspect,
                resolution=resolution if not m.startswith("bytedance/") or resolution in ("480p", "720p") else "720p",
                audio=audio, first_frame=first, last_frame=last, refs=ref, seed=seed,
            )
            break
        except orr.OpenRouterError as e:
            busy = "high load" in str(e).lower() or "overloaded" in str(e).lower() or "try again" in str(e).lower()
            if not busy or i == len(tries) - 1:
                raise
            nxt = tries[i + 1]
            typer.echo(f"{m} is overloaded; retrying with {nxt} in 20 s", err=True)
            time.sleep(20)
    typer.echo(path)
    typer.echo(f"cost ${cost:.4f}", err=True)


@app.command()
def models():
    """Video models on OpenRouter with durations, sizes and price SKUs (live)."""
    for m in orr.video_models():
        skus = m.get("pricing_skus") or {}
        price = ", ".join(f"{k}={v}" for k, v in skus.items()) or "?"
        typer.echo(f"{m['id']}\n  durations {m.get('supported_durations')}  res {m.get('supported_resolutions')}"
                   f"  aspect {m.get('supported_aspect_ratios')}  frames {m.get('supported_frame_images')}"
                   f"  audio {m.get('generate_audio')}\n  price {price}")


@app.command()
def tts(
    text: Annotated[str, typer.Argument(help="Narration, or @file.txt")],
    out: Out,
    model: str = "google/gemini-3.8-flash-lite-tts",
    voice: str = "Charon",
    style: Annotated[Optional[str], typer.Option(help="Delivery direction. Gemini: free text. Azure: a named style.")] = None,
):
    """Speak narration (always mp3)."""
    typer.echo(orr.speech(_text(text), out, model=model, voice=voice, style=style))


@app.command()
def music(
    prompt: Annotated[str, typer.Argument(help="Mood, genre, tempo, instruments, 'no vocals'")],
    out: Out,
    model: str = "google/lyria-3-clip-preview",
):
    """Background music (Lyria: clip = 30 s, pro = full track)."""
    typer.echo(orr.music(_text(prompt), out, model=model))


@app.command()
def transcribe(
    media: Path,
    out: Out,
    model: str = "openai/whisper-large-v3",
):
    """Word-timed transcript of any audio or video → JSON {text, words:[{text,start,end}]}."""
    data = orr.transcribe(media, model=model)
    out.write_text(json.dumps(data, indent=1))
    typer.echo(f"{out} ({len(data['words'])} words)")


@app.command()
def captions(
    words: Annotated[Path, typer.Argument(help="JSON from `vg transcribe`")],
    video: Annotated[Path, typer.Option(help="The video they are for (sets size and, with --burn, the input).")],
    out: Annotated[Path, typer.Option("-o", "--out", help="Output .ass (an .srt is written next to it).")],
    burn: Annotated[Optional[Path], typer.Option(help="Also burn them into this output video.")] = None,
    max_words: Annotated[Optional[int], typer.Option(help="Default 4 for portrait, 7 for landscape.")] = None,
    font: str = "DejaVu Sans",
    highlight: Annotated[str, typer.Option(help="RGB hex for the spoken word.")] = "FFD34E",
):
    """Word-timed subtitles: karaoke-highlighted ASS plus a plain SRT."""
    v = next(s for s in probe(video)["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])
    per = max_words or (4 if h > w else 7)
    lines = cap.group(cap.load_words(words), max_words=per, max_chars=per * 7)
    cap.write_ass(lines, out, width=w, height=h, font=font, highlight=highlight)
    cap.write_srt(lines, out.with_suffix(".srt"))
    typer.echo(f"{out} + {out.with_suffix('.srt').name}: {len(lines)} lines")
    if burn:
        esc = str(out.resolve()).replace(":", "\\:").replace("'", "\\'")
        run(["ffmpeg", "-i", str(video), "-vf", f"ass='{esc}'", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-c:a", "copy", "-movflags", "+faststart", str(burn)])
        typer.echo(burn)


@app.command()
def assemble(
    edit: Annotated[Path, typer.Argument(help="Edit list YAML (schema: `vg assemble --schema`).")] = Path("edit.yaml"),
    out: Out = Path("out/final.mp4"),
    no_captions: Annotated[bool, typer.Option("--no-captions", help="Skip burning the captions file named in the edit.")] = False,
    schema: Annotated[bool, typer.Option("--schema", help="Print the edit-list schema and exit.")] = False,
):
    """Render the edit list to MP4 with ffmpeg, and write the same edit as .otio."""
    if schema:
        typer.echo(timeline.__doc__)
        raise typer.Exit()
    e = timeline.load(edit)
    out.parent.mkdir(parents=True, exist_ok=True)
    timeline.render(e, out, captions=not no_captions)
    otio_path = timeline.to_otio(e, out.with_suffix(".otio"))
    typer.echo(f"{out}\n{otio_path}")


@app.command()
def critic(
    video: Path,
    out: Annotated[Path, typer.Option("-o", "--out", help="Folder for the report and frames.")] = Path("critic"),
    script: Annotated[Optional[Path], typer.Option(help="The narration text, to diff against what is heard.")] = None,
    every: Annotated[float, typer.Option(help="Seconds between contact-sheet frames.")] = 2.0,
    review: Annotated[bool, typer.Option("--review/--no-review", help="Also have Gemini watch a 720p proxy.")] = True,
    review_model: str = "google/gemini-3.1-pro-preview",
    words: Annotated[Optional[Path], typer.Option("--words", help="Use this words.json as what is heard (e.g. from `vg words`) instead of transcribing the mix; free.")] = None,
):
    """Collect facts about a render for you to judge: frames, loudness, gaps, transcript vs script, a second pair of eyes.

    With --no-review and --words it makes no paid calls at all.
    """
    out.mkdir(parents=True, exist_ok=True)
    transcript = None
    if words:
        transcript = json.loads(words.read_text())["text"]
    elif any(s["codec_type"] == "audio" for s in probe(video)["streams"]):
        words = out / "heard.json"
        data = orr.transcribe(video, model="openai/whisper-large-v3")
        words.write_text(json.dumps(data, indent=1))
        transcript = data["text"]
    md = crit.report(video, out, every=every, transcript=transcript, script=script.read_text() if script else None)
    if review:
        proxy = out / "proxy.mp4"
        run(["ffmpeg", "-i", str(video), "-vf", "scale=-2:'min(720,ih)'", "-c:v", "libx264", "-crf", "30",
             "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k", str(proxy)])
        prompt = (
            "You are a strict video editor reviewing a draft. List concrete problems with timestamps: "
            "AI-generation artefacts (warped hands or faces, morphing objects, garbled text), characters or "
            "props that change between shots, cuts that land mid-word or mid-action, picture that does not "
            "match what the narrator is saying, audio problems (clipping, music drowning the voice, abrupt "
            "starts or ends), captions that are wrong or badly placed, and pacing that drags or rushes. "
            "Then say what works. Be specific; do not pad."
        )
        text = orr.review_video(proxy, prompt, model=review_model)
        with md.open("a") as f:
            f.write(f"\n## Second opinion ({review_model} watched a 720p proxy)\n\n{text}\n")
    typer.echo(md)


@footage_app.command("search")
def footage_search(
    query: str,
    limit: int = 8,
    any_license: Annotated[bool, typer.Option("--any-license", help="Drop YouTube's Creative Commons filter.")] = False,
):
    """Search YouTube (Creative Commons only by default); each hit's licence is confirmed from its metadata."""
    for r in foot.search(query, limit=limit, cc_only=not any_license):
        typer.echo(f"{r['url']}  [{r['license'] or 'no licence field'}]  {r['duration']}s  {r['height']}p\n"
                   f"  {r['title']} — {r['channel']}")


@footage_app.command("get")
def footage_get(
    url: str,
    out: Out,
    start: Annotated[Optional[float], typer.Option(help="Section start, seconds.")] = None,
    end: Annotated[Optional[float], typer.Option(help="Section end, seconds.")] = None,
    max_height: int = 1080,
    credits: Annotated[Path, typer.Option(help="Attribution log to append to.")] = Path("credits.json"),
):
    """Download a section and log its attribution."""
    typer.echo(foot.download(url, out, start=start, end=end, max_height=max_height, credits=credits))


@fal_app.command("run")
def fal_run(
    model: Annotated[str, typer.Argument(help="fal endpoint id, e.g. fal-ai/kling-video/v3/pro/image-to-video")],
    out: Out,
    prompt: Annotated[Optional[str], typer.Option("--prompt", "-p", help="Prompt text or @file.txt")] = None,
    prompt_key: Annotated[str, typer.Option(help="Input field the prompt goes in: 'prompt' for most models, 'text' for ElevenLabs SFX/TTS and MiniMax speech-02")] = "prompt",
    image: Annotated[Optional[list[Path]], typer.Option("--image", help="Local image(s), sent as data URIs")] = None,
    file: Annotated[Optional[list[str]], typer.Option("--file", "-f", help="key=path: send a local file (audio, image) as a data URI in that field, repeatable")] = None,
    image_key: Annotated[str, typer.Option(help="Input field for the first image")] = "image_url",
    end_image_key: Annotated[str, typer.Option(help="Input field for a second image, e.g. tail_image_url / end_image_url")] = "tail_image_url",
    arg: Annotated[Optional[list[str]], typer.Option("--arg", "-a", help="Extra input key=value; the value is parsed as JSON when it can be (10 -> number, true -> boolean), repeatable")] = None,
    sarg: Annotated[Optional[list[str]], typer.Option("--str", "-s", help="Extra input key=value always sent as a string (Kling's duration=10), repeatable")] = None,
    timeout: Annotated[int, typer.Option(help="Seconds to wait for the job")] = 1800,
):
    """Run one fal model and download what it returns. Prints the request id and fal's published unit price."""
    args: dict = {}
    if prompt: args[prompt_key] = _text(prompt)
    if image_key.endswith("_urls"):          # list-valued field (nano-banana edit's image_urls): every image goes in it
        args[image_key] = [falmod.data_uri(img) for img in image or []]
    else:
        for i, img in enumerate(image or []):
            args[image_key if i == 0 else end_image_key] = falmod.data_uri(img)
    for kv in file or []:
        k, path = kv.split("=", 1)
        args[k] = falmod.data_uri(path)
    for kv in arg or []:
        k, v = kv.split("=", 1)
        try: args[k] = json.loads(v)
        except json.JSONDecodeError: args[k] = v
    for kv in sarg or []:
        k, v = kv.split("=", 1)
        args[k] = v
    p = falmod.price(model)
    typer.echo(f"price: {p}" if p else "price: not published by the API; check fal.ai/models/<id> or fal.ai/dashboard/usage")
    for path in falmod.run(model, args, out, timeout_s=timeout):
        typer.echo(path)


@fal_app.command("price")
def fal_price(model: Annotated[str, typer.Argument(help="fal endpoint id")]):
    """fal's published unit price for one endpoint."""
    typer.echo(falmod.price(model) or "not published by the API; see fal.ai/models")


@fal_app.command("schema")
def fal_schema(model: Annotated[str, typer.Argument(help="fal endpoint id")]):
    """The endpoint's input fields (name, type, default, required) from fal's published OpenAPI. No key needed."""
    lines = falmod.schema(model)
    if not lines:
        raise typer.Exit(f"no schema found for {model}; check the id at fal.ai/models")
    for line in lines: typer.echo(line)


@fal_app.command("check")
def fal_check():
    """Whether a FAL_KEY is configured (never prints it)."""
    typer.echo("FAL_KEY configured" if falmod.has_key() else f"FAL_KEY missing: add FAL_KEY=... to {config.env_file()}")



@keys_app.command("open")
def keys_open(provider: Annotated[str, typer.Argument(help="openrouter or fal")]):
    """Open the pages where the person adds credit and creates a key (in their default browser)."""
    if provider not in keysmod.PROVIDERS:
        raise typer.BadParameter("openrouter or fal")
    for i, (what, url) in enumerate(keysmod.open_pages(provider), 1):
        typer.echo(f"{i}. {what}: {url}")
    typer.echo(f"When the key is copied, run: vg keys paste {provider}")


@keys_app.command("paste")
def keys_paste(provider: Annotated[str, typer.Argument(help="openrouter or fal")]):
    """Save the key on the clipboard to .env, clear the clipboard, and test it. Shows only the last 4 characters."""
    if provider not in keysmod.PROVIDERS:
        raise typer.BadParameter("openrouter or fal")
    value = keysmod.read_clipboard()
    if why := keysmod.problem(provider, value):
        raise typer.Exit(typer.echo(f"not saved: {why}") or 1)
    name = keysmod.PROVIDERS[provider]["env"]
    keysmod.save(name, value)
    keysmod.clear_clipboard()
    ok, detail = keysmod.check(provider)
    typer.echo(f"{name} saved ({keysmod.masked(value)}) to {config.env_file()}: {detail}")
    if ok is False:
        raise typer.Exit(1)


@keys_app.command("status")
def keys_status():
    """Which keys are set and whether each one works (never shows a key)."""
    for provider, info in keysmod.PROVIDERS.items():
        ok, detail = keysmod.check(provider)
        typer.echo(f"{info['env']:<20} {keysmod.masked(config.secret(info['env'])):<8} {detail}")


@app.command()
def doctor():
    """Check the install: ffmpeg and its filters, keys (present or not, never shown), optional tools."""
    lines, ok = doc.report()
    for ln in lines:
        typer.echo(ln)
    typer.echo("\nall required pieces present" if ok else "\nsomething required is missing (see MISSING above)")
    raise typer.Exit(0 if ok else 1)


@app.command()
def spend(days: Annotated[int, typer.Option(help="Window for the local ledger summary.")] = 7):
    """What has been spent: OpenRouter's own figures for the key and account, plus vg's local ledger (fal included)."""
    import datetime as dt

    import httpx

    key = config.secret("OPENROUTER_API_KEY")
    if key:
        h = {"Authorization": f"Bearer {key}"}
        try:
            k = httpx.get("https://openrouter.ai/api/v1/key", headers=h, timeout=20).json().get("data", {})
            c = httpx.get("https://openrouter.ai/api/v1/credits", headers=h, timeout=20).json().get("data", {})
            cap = (f"of ${k['limit']:.0f} {k.get('limit_reset') or 'total'} cap, ${k['limit_remaining']:.2f} left"
                   if k.get("limit") else "(no cap on this key)")
            typer.echo(f"OpenRouter key: today ${k.get('usage_daily') or 0:.2f} · this week ${k.get('usage_weekly') or 0:.2f} {cap}")
            if c:
                bal = c["total_credits"] - c["total_usage"]
                typer.echo(f"OpenRouter account balance: ${bal:.2f}" + ("  (low: under $10)" if bal < 10 else ""))
        except (httpx.HTTPError, KeyError, ValueError) as e:
            typer.echo(f"OpenRouter: could not read usage ({type(e).__name__})")
    else:
        typer.echo("OpenRouter: no key configured")
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    recent = [r for r in costs.rows() if dt.datetime.fromisoformat(r["at"]) >= since]
    by: dict[str, list] = {}
    for r in recent:
        by.setdefault(r.get("provider", "?"), []).append(r)
    typer.echo(f"Local ledger, last {days} days ({config.home() / 'costs.jsonl'}):")
    if not recent:
        typer.echo("  nothing logged")
    for prov, rs in sorted(by.items()):
        known = sum(r["usd"] for r in rs if r.get("usd") is not None)
        unknown = sum(1 for r in rs if r.get("usd") is None)
        failed = sum(1 for r in rs if not r.get("ok", True))
        extra = f", {unknown} calls without a reported charge" if unknown else ""
        typer.echo(f"  {prov}: ${known:.2f} reported over {len(rs)} calls{extra}{f', {failed} failed' if failed else ''}")
    if "fal" in by:
        typer.echo("  fal amounts are estimates from unit prices; its bill of record is fal.ai/dashboard/usage")


@app.command()
def words(
    edit: Annotated[Path, typer.Argument(help="edit.yaml whose `role: voice` items to transcribe")] = Path("edit.yaml"),
    out: Out = Path("out/words.json"),
    refresh: Annotated[bool, typer.Option(help="Re-transcribe even when a cached <file>.words.json exists.")] = False,
):
    """Caption timings from each voice file, shifted to where the edit places it (robust under music and SFX)."""
    data = wordsmod.from_edit(edit, refresh=refresh)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1))
    typer.echo(f"{out} ({len(data['words'])} words)")


@app.command()
def mixcheck(
    edit: Annotated[Path, typer.Argument(help="edit.yaml to measure")] = Path("edit.yaml"),
    out: Annotated[Path, typer.Option("-o", "--out", help="Folder for the stems and the report.")] = Path("out/mixcheck"),
):
    """How far the voice sits above music and effects, window by window (free; ffmpeg only)."""
    md = crit.mixcheck(edit, out)
    typer.echo(md.read_text())


@app.command()
def html(
    page: Annotated[str, typer.Argument(help="HTML file or URL")],
    out: Out,
    size: Annotated[str, typer.Option(help="CSS pixels WxH")] = "1920x1080",
    scale: Annotated[float, typer.Option(help="Device scale; 2 gives a crisp 2x render")] = 1.0,
    wait: Annotated[int, typer.Option(help="Milliseconds for fonts and scripts to settle")] = 4000,
):
    """Render an HTML page to PNG with headless Chrome: exact text, layouts, lockups, bubbles, cards."""
    w, h = (int(v) for v in size.lower().split("x"))
    typer.echo(htmlmod.render(page, out, width=w, height=h, scale=scale, wait_ms=wait))


@app.command()
def sfx(
    preset: Annotated[Optional[str], typer.Argument(help="Preset name; omit to list them")] = None,
    out: Annotated[Optional[Path], typer.Option("-o", "--out", help="Output .wav")] = None,
):
    """Synthesise a sound effect with ffmpeg (impact, whoosh, thud, riser, snap, tick, zap, button, chime). Free."""
    if not preset:
        for name, (desc, _) in sfxmod.PRESETS.items():
            typer.echo(f"{name:<8} {desc}")
        return
    typer.echo(sfxmod.generate(preset, out or Path(f"sfx/{preset}.wav")))


@app.command()
def overlay(
    base: Annotated[Path, typer.Argument(help="Clip or still underneath")],
    over: Annotated[Path, typer.Argument(help="Transparent overlay: .mov/.webm with alpha, or a PNG")],
    out: Out,
    size: Annotated[str, typer.Option(help="Output WxH")] = "1920x1080",
    fps: int = 30,
    dur: Annotated[Optional[float], typer.Option(help="Output length; a shorter base holds its last frame")] = None,
):
    """Composite a title, counter, lower-third or UI over a generated clip."""
    w, h = (int(v) for v in size.lower().split("x"))
    typer.echo(overlay_media(base, over, out, size=(w, h), fps=fps, dur=dur))


@app.command()
def borders(images: Annotated[list[Path], typer.Argument(help="Images or clips to check")]):
    """Flag black bars baked into generated images (they carry into every clip made from them)."""
    bad = 0
    for img in images:
        bars = black_borders(img)
        bad += bool(bars)
        typer.echo(f"{img}: " + (f"BARS left/right/top/bottom px {bars}" if bars else "full frame"))
    raise typer.Exit(1 if bad else 0)

def main():
    try:
        app()
    except (orr.OpenRouterError, RuntimeError, FileNotFoundError, ValueError) as e:
        typer.echo(f"error: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
