"""Assemble a video from a YAML edit list: render with ffmpeg, export OpenTimelineIO.

The YAML is the agent-friendly source of truth. The .otio written next to the
render carries the same edit for an NLE (Resolve, Premiere via adapters) when a
human wants to take over. Schema:

    size: [1920, 1080]
    fps: 30
    fit: cover            # cover (crop to fill) | pad (letterbox)
    loudness: -14         # integrated LUFS target for the mix; null to skip
    captions: captions.ass  # optional, burned in last
    video:                # one track, laid end to end
      - src: clips/s01.mp4
        in: 0.0           # source in-point, seconds
        dur: 5.0          # timeline duration; images need it, videos default to the rest
        motion: zoom-in   # images only: zoom-in | zoom-out | pan-left | pan-right | none
        audio: false      # keep the clip's own sound
        gain_db: 0
        transition: 0.5   # crossfade from the previous item, seconds
    audio:
      - src: vo/narration.wav
        at: 0.0           # timeline start, seconds
        in: 0.0
        dur: null
        gain_db: 0
        role: voice       # voice | music | sfx. Music ducks under voice.
        fade_in: 0
        fade_out: 0

Paths are relative to the YAML file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from tqdm import tqdm

from .media import duration, has_audio, is_image, run

MOTIONS = {
    # zoompan expressions; `on` is the output frame number, `d` the frame count
    "zoom-in": ("1+0.12*on/{d}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "zoom-out": ("1.12-0.12*on/{d}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pan-left": ("1.1", "(iw-iw/zoom)*(1-on/{d})", "ih/2-(ih/zoom/2)"),
    "pan-right": ("1.1", "(iw-iw/zoom)*on/{d}", "ih/2-(ih/zoom/2)"),
    "none": ("1", "0", "0"),
}


@dataclass
class VideoItem:
    src: Path
    dur: float
    start: float = 0.0  # timeline position, filled in by layout()
    src_in: float = 0.0
    motion: str = "zoom-in"
    audio: bool = False
    gain_db: float = 0.0
    transition: float = 0.0


@dataclass
class AudioItem:
    src: Path
    at: float = 0.0
    src_in: float = 0.0
    dur: float | None = None
    gain_db: float = 0.0
    role: str = "voice"
    fade_in: float = 0.0
    fade_out: float = 0.0


@dataclass
class Edit:
    root: Path
    width: int
    height: int
    fps: int
    fit: str
    loudness: float | None
    captions: Path | None
    video: list[VideoItem] = field(default_factory=list)
    audio: list[AudioItem] = field(default_factory=list)

    @property
    def total(self) -> float:
        last = self.video[-1]
        return last.start + last.dur


def load(path: Path) -> Edit:
    spec = yaml.safe_load(path.read_text())
    root = path.parent
    w, h = spec.get("size", [1920, 1080])
    edit = Edit(
        root=root,
        width=int(w),
        height=int(h),
        fps=int(spec.get("fps", 30)),
        fit=spec.get("fit", "cover"),
        loudness=spec.get("loudness", -14),
        captions=root / spec["captions"] if spec.get("captions") else None,
    )
    for i, v in enumerate(spec.get("video", [])):
        src = root / v["src"]
        if not src.exists():
            raise FileNotFoundError(f"video[{i}]: {src}")
        src_in = float(v.get("in", 0))
        if v.get("dur") is not None:
            dur = float(v["dur"])
        elif is_image(src):
            raise ValueError(f"video[{i}]: image {src.name} needs a dur")
        else:
            dur = duration(src) - src_in
        edit.video.append(
            VideoItem(
                src=src,
                dur=dur,
                src_in=src_in,
                motion=v.get("motion", "zoom-in"),
                audio=bool(v.get("audio", False)),
                gain_db=float(v.get("gain_db", 0)),
                transition=float(v.get("transition", 0)) if i else 0.0,
            )
        )
    for i, a in enumerate(spec.get("audio", [])):
        src = root / a["src"]
        if not src.exists():
            raise FileNotFoundError(f"audio[{i}]: {src}")
        edit.audio.append(
            AudioItem(
                src=src,
                at=float(a.get("at", 0)),
                src_in=float(a.get("in", 0)),
                dur=float(a["dur"]) if a.get("dur") is not None else None,
                gain_db=float(a.get("gain_db", 0)),
                role=a.get("role", "voice"),
                fade_in=float(a.get("fade_in", 0)),
                fade_out=float(a.get("fade_out", 0)),
            )
        )
    if not edit.video:
        raise ValueError("edit has no video items")
    layout(edit)
    return edit


def layout(edit: Edit) -> None:
    """Place items end to end, overlapping by each crossfade."""
    t = 0.0
    for item in edit.video:
        if item.transition >= item.dur:
            raise ValueError(f"{item.src.name}: transition {item.transition}s is not shorter than dur {item.dur}s")
        item.start = t - item.transition
        t = item.start + item.dur


def _frame_filter(edit: Edit) -> str:
    w, h = edit.width, edit.height
    if edit.fit == "pad":
        return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"


def _segment(edit: Edit, item: VideoItem, out: Path) -> None:
    """Render one item to a silent, uniform segment of exactly item.dur seconds."""
    w, h, fps = edit.width, edit.height, edit.fps
    if is_image(item.src):
        frames = round(item.dur * fps)
        z, x, y = (e.format(d=frames) for e in MOTIONS[item.motion])
        # Upscale first so zoompan has pixels to spare and doesn't jitter.
        vf = (
            f"{_frame_filter(edit).replace(f'{w}:{h}', f'{w * 2}:{h * 2}')},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},format=yuv420p"
        )
        cmd = ["ffmpeg", "-loop", "1", "-i", str(item.src), "-vf", vf, "-frames:v", str(frames)]
    else:
        vf = f"{_frame_filter(edit)},fps={fps},format=yuv420p,setsar=1"
        cmd = ["ffmpeg", "-ss", f"{item.src_in}", "-t", f"{item.dur}", "-i", str(item.src), "-vf", vf]
        # A source shorter than dur holds its last frame rather than shortening the edit.
        cmd[-1] += f",tpad=stop_mode=clone:stop_duration={item.dur}"
        cmd += ["-t", f"{item.dur}"]
    run([*cmd, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", str(out)])


def audio_graph(edit: Edit, *, first_input: int = 0, roles: set[str] | None = None,
                loudness: bool = True, limiter: bool = True) -> tuple[list[str], list[str], str | None]:
    """ffmpeg inputs and filter lines that mix the edit's audio into one labelled stream.

    Every source is trimmed, gained, faded and delayed to its timeline slot. Music ducks under voice.
    `roles` keeps only those roles (voice, music, sfx; a clip's own sound counts as sfx), which is how
    `vg mixcheck` renders stems. Returns (inputs, graph, output label or None when there is no audio).
    """
    inputs: list[str] = []
    graph: list[str] = []
    groups: dict[str, list[str]] = {"voice": [], "music": [], "sfx": []}
    n = first_input

    def add_audio(src: Path, src_in: float, dur: float | None, at: float, gain: float, fin: float, fout: float, role: str):
        nonlocal n
        if roles is not None and role not in roles:
            return
        inputs.extend(["-i", str(src)])
        label = f"[a{n}]"
        chain = [f"atrim=start={src_in}" + (f":duration={dur}" if dur else ""), "asetpts=PTS-STARTPTS"]
        chain.append("aformat=sample_rates=48000:channel_layouts=stereo")
        if gain:
            chain.append(f"volume={gain}dB")
        if fin:
            chain.append(f"afade=t=in:d={fin}")
        if fout:
            length = dur if dur else duration(src) - src_in
            chain.append(f"afade=t=out:st={max(length - fout, 0)}:d={fout}")
        ms = int(at * 1000)
        chain.append(f"adelay={ms}|{ms}")
        graph.append(f"[{n}:a]{','.join(chain)}{label}")
        groups.setdefault(role, []).append(label)
        n += 1

    for item in edit.video:
        if item.audio and has_audio(item.src):
            add_audio(item.src, item.src_in, item.dur, item.start, item.gain_db, 0, 0, "sfx")
    for a in edit.audio:
        add_audio(a.src, a.src_in, a.dur, a.at, a.gain_db, a.fade_in, a.fade_out, a.role)

    def mix(labels: list[str], name: str) -> str | None:
        if not labels:
            return None
        if len(labels) == 1:
            return labels[0]
        graph.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0[{name}]")
        return f"[{name}]"

    voice = mix(groups.pop("voice"), "voice")
    music = mix(groups.pop("music"), "music")
    rest = [lbl for labels in groups.values() for lbl in labels]
    if voice and music:
        # sidechaincompress stops when its key ends, so pad the voice to the full length or the music dies with the last word
        graph.append(f"{voice}apad=whole_dur={edit.total:.3f},asplit=2[voicemix][voicekey]")
        graph.append(f"{music}[voicekey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked]")
        stems = ["[voicemix]", "[ducked]", *rest]
    else:
        stems = [s for s in (voice, music) if s] + rest
    if not stems:
        return inputs, graph, None

    final = mix(stems, "mix") if len(stems) > 1 else stems[0]
    post = ["apad", f"atrim=duration={edit.total:.3f}"]
    if loudness and edit.loudness is not None:
        post.append(f"loudnorm=I={edit.loudness}:TP=-1.5:LRA=11")
    post.append("aresample=48000")
    if limiter:
        # single-pass loudnorm lets sharp transients (impacts, snaps) overshoot its true-peak target; catch them
        post.append("alimiter=limit=0.84:attack=1:release=50:level=disabled")
    graph.append(f"{final}{','.join(post)}[aout]")
    return inputs, graph, "[aout]"


def render_audio(edit: Edit, out: Path, *, roles: set[str] | None = None, loudness: bool = True, limiter: bool = True) -> Path | None:
    """Mix only the edit's audio to a WAV (no video). Returns None when the selection has no audio."""
    inputs, graph, aout = audio_graph(edit, roles=roles, loudness=loudness, limiter=limiter)
    if not aout:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", *inputs, "-filter_complex", ";".join(graph), "-map", aout, "-c:a", "pcm_s16le",
         "-t", f"{edit.total:.3f}", str(out)])
    return out


def render(edit: Edit, out: Path, *, captions: bool = True) -> Path:
    build = out.parent / f".{out.stem}-build"
    build.mkdir(parents=True, exist_ok=True)
    segs = []
    for i, item in enumerate(tqdm(edit.video, desc="segments", unit="clip")):
        seg = build / f"seg{i:03d}.mp4"
        _segment(edit, item, seg)
        segs.append(seg)

    inputs: list[str] = []
    for s in segs:
        inputs += ["-i", str(s)]
    # Every segment gets the same timebase as concat's output (AVTB), or a later xfade refuses to mix them.
    graph: list[str] = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[s{i}]" for i in range(len(segs))]

    # Video: chain segments with xfade where a transition is set, concat otherwise.
    cur = "[s0]"
    for i in range(1, len(segs)):
        item = edit.video[i]
        nxt = f"[v{i}]"
        if item.transition > 0:
            graph.append(f"{cur}[s{i}]xfade=transition=fade:duration={item.transition}:offset={item.start:.3f},settb=AVTB{nxt}")
        else:
            graph.append(f"{cur}[s{i}]concat=n=2:v=1:a=0{nxt}")
        cur = nxt
    if captions and edit.captions:
        esc = str(edit.captions).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        graph.append(f"{cur}ass='{esc}'[vcap]")
        cur = "[vcap]"
    vout = cur

    a_inputs, a_graph, aout = audio_graph(edit, first_input=len(segs))
    inputs += a_inputs
    graph += a_graph
    n = len(segs) + len(a_inputs) // 2

    cmd = ["ffmpeg", *inputs, "-filter_complex", ";".join(graph), "-map", vout]
    if aout:
        cmd += ["-map", aout, "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(edit.fps)]
    cmd += ["-movflags", "+faststart", "-t", f"{edit.total:.3f}", str(out)]
    print(f"mixing {len(segs)} clips, {n - len(segs)} audio sources → {out} ({edit.total:.1f}s)")
    run(cmd)
    return out


def to_otio(edit: Edit, out: Path) -> Path:
    import opentimelineio as otio

    rate = edit.fps

    def rt(seconds: float) -> otio.opentime.RationalTime:
        return otio.opentime.RationalTime(round(seconds * rate), rate)

    def clip(src: Path, src_in: float, dur: float, name: str) -> otio.schema.Clip:
        return otio.schema.Clip(
            name=name,
            media_reference=otio.schema.ExternalReference(target_url=str(src.resolve())),
            source_range=otio.opentime.TimeRange(rt(src_in), rt(dur)),
        )

    tl = otio.schema.Timeline(name=out.stem)
    v1 = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    for item in edit.video:
        if item.transition:
            half = rt(item.transition / 2)
            v1.append(otio.schema.Transition(in_offset=half, out_offset=half))
        v1.append(clip(item.src, item.src_in, item.dur, item.src.stem))
    tl.tracks.append(v1)

    for role in sorted({a.role for a in edit.audio}):
        track = otio.schema.Track(name=role, kind=otio.schema.TrackKind.Audio)
        cursor = 0.0
        for a in sorted((a for a in edit.audio if a.role == role), key=lambda a: a.at):
            if a.at > cursor:
                track.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(rt(0), rt(a.at - cursor))))
            dur = a.dur if a.dur else duration(a.src) - a.src_in
            track.append(clip(a.src, a.src_in, dur, a.src.stem))
            cursor = max(cursor, a.at) + dur
        tl.tracks.append(track)

    otio.adapters.write_to_file(tl, str(out))
    return out
