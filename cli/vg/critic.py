"""Facts about a rendered video for an agent to judge. No pass/fail rules here.

Writes a folder with contact sheets, per-shot frames and a markdown report of
what ffmpeg measured: loudness, silences, black and frozen stretches, scene
cuts, and (when a script is given) how the spoken words line up with it.
"""

from __future__ import annotations

import difflib
import re
import subprocess
from pathlib import Path

from .media import duration, probe, run


def _detect(path: Path, vf: str | None, af: str | None) -> str:
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path)]
    if vf:
        cmd += ["-vf", vf]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "null", "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def _spans(log: str, start_key: str, end_key: str) -> list[tuple[float, float]]:
    starts = [float(x) for x in re.findall(rf"{start_key}:\s*([\d.]+)", log)]
    ends = [float(x) for x in re.findall(rf"{end_key}:\s*([\d.]+)", log)]
    return list(zip(starts, ends))


def contact_sheets(path: Path, out: Path, *, every: float, cols: int = 4, rows: int = 3) -> list[Path]:
    """Tile one frame every `every` seconds into sheets with timestamps burned in."""
    pattern = out / "sheet-%02d.jpg"
    stamp = "drawtext=text='%{pts\\:hms}':x=10:y=10:fontsize='min(w/12,h/14)':fontcolor=white:box=1:boxcolor=black@0.6"
    vf = f"fps=1/{every},{stamp},scale=480:-2,tile={cols}x{rows}:padding=4:color=black"
    run(["ffmpeg", "-i", str(path), "-vf", vf, "-q:v", "3", str(pattern)])
    return sorted(out.glob("sheet-*.jpg"))


def scene_frames(path: Path, out: Path, *, threshold: float = 0.3) -> list[tuple[float, Path]]:
    """One full-size frame just after each detected cut, plus the first frame."""
    log = _detect(path, f"select='eq(n,0)+gt(scene,{threshold})',showinfo", None)
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", log)]
    frames = []
    for i, t in enumerate(times):
        f = out / f"shot-{i:02d}-{t:06.2f}s.jpg"
        run(["ffmpeg", "-ss", f"{t + 0.25:.2f}", "-i", str(path), "-frames:v", "1", "-q:v", "2", str(f)])
        frames.append((t, f))
    return frames


def _norm(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def script_diff(script: str, heard: str) -> tuple[float, list[str]]:
    """Word-level agreement between the intended script and the transcript."""
    a, b = _norm(script), _norm(heard)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    notes = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            notes.append(f"{op}: script «{' '.join(a[i1:i2])}» → heard «{' '.join(b[j1:j2])}»")
    return sm.ratio(), notes


def report(path: Path, out: Path, *, every: float, transcript: str | None, script: str | None) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    info = probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = duration(path)

    lines = [f"# Critic facts: {path.name}", ""]
    lines.append(f"- Duration: {dur:.2f}s")
    if v:
        lines.append(f"- Video: {v['width']}x{v['height']} {v.get('codec_name')} @ {v.get('r_frame_rate')} fps")
    lines.append(f"- Audio: {a['codec_name'] + ' ' + a.get('sample_rate', '') + ' Hz' if a else 'NONE'}")

    if a:
        log = _detect(path, None, "ebur128=peak=true")
        summary = log[log.rfind("Summary:") :]
        integ = re.search(r"I:\s*(-?[\d.]+) LUFS", summary)
        peak = re.search(r"Peak:\s*(-?[\d.]+) dBFS", summary)
        lra = re.search(r"LRA:\s*(-?[\d.]+) LU", summary)
        lines.append(
            f"- Loudness: integrated {integ.group(1) if integ else '?'} LUFS, "
            f"true peak {peak.group(1) if peak else '?'} dBFS, range {lra.group(1) if lra else '?'} LU "
            "(web norm is about -14 LUFS, peak under -1 dBFS)"
        )
        sil = _spans(_detect(path, None, "silencedetect=noise=-40dB:d=0.8"), "silence_start", "silence_end")
        lines.append(f"- Silences over 0.8s: {', '.join(f'{s:.1f}–{e:.1f}s' for s, e in sil) or 'none'}")

    black = _spans(_detect(path, "blackdetect=d=0.3:pix_th=0.10", None), "black_start", "black_end")
    lines.append(f"- Black stretches over 0.3s: {', '.join(f'{s:.1f}–{e:.1f}s' for s, e in black) or 'none'}")
    frozen = _spans(_detect(path, "freezedetect=n=0.003:d=1.5", None), "freeze_start", "freeze_end")
    lines.append(f"- Frozen stretches over 1.5s: {', '.join(f'{s:.1f}–{e:.1f}s' for s, e in frozen) or 'none'}")

    shots = scene_frames(path, out)
    cuts = [t for t, _ in shots]
    gaps = [b - a for a, b in zip(cuts, [*cuts[1:], dur])]
    lines.append(f"- Shots detected: {len(shots)}; lengths {', '.join(f'{g:.1f}s' for g in gaps)}")
    sheets = contact_sheets(path, out, every=every)

    lines += ["", "## Look at these", ""]
    lines += [f"- Contact sheet: `{s}`" for s in sheets]
    lines += [f"- Shot at {t:.2f}s: `{f}`" for t, f in shots]

    if transcript:
        lines += ["", "## What the audio says", "", transcript.strip()]
    if transcript and script:
        ratio, notes = script_diff(script, transcript)
        lines += ["", f"## Script vs heard (word agreement {ratio:.0%})", ""]
        lines += [f"- {n}" for n in notes[:60]] or ["- no differences"]

    md = out / "report.md"
    md.write_text("\n".join(lines) + "\n")
    return md


def _rms_windows(path: Path, window: float = 0.5) -> list[float]:
    """RMS level in dBFS for each `window`-second slice (whatever the file's sample rate)."""
    rate = int(next(s for s in probe(path)["streams"] if s["codec_type"] == "audio")["sample_rate"])
    log = _detect(path, None, f"asetnsamples={int(rate * window)},astats=metadata=1:reset=1,"
                              "ametadata=print:key=lavfi.astats.Overall.RMS_level")
    vals = []
    for m in re.finditer(r"RMS_level=(-?[\d.]+|-inf)", log):
        vals.append(-120.0 if m.group(1) == "-inf" else float(m.group(1)))
    return vals


def mixcheck(edit_path: Path, out: Path, *, window: float = 0.5, low_db: float = 4.0) -> Path:
    """How far the voice sits above everything else, measured where the voice is speaking.

    Renders the voice alone and the full mix with loudness processing off, subtracts one from the other to
    get the music and effects exactly as they sit under the voice (ducking included), and compares levels
    window by window. Writes a markdown report and returns its path.
    """
    from vg import timeline

    out.mkdir(parents=True, exist_ok=True)
    edit = timeline.load(edit_path)
    voice = timeline.render_audio(edit, out / "stem-voice.wav", roles={"voice"}, loudness=False, limiter=False)
    full = timeline.render_audio(edit, out / "stem-mix.wav", loudness=False, limiter=False)
    if not voice or not full:
        raise ValueError("the edit needs at least one `role: voice` item and something else to compare against")
    residual = out / "stem-bed.wav"
    run(["ffmpeg", "-i", str(full), "-i", str(voice), "-filter_complex",
         "[1:a]volume=-1[inv];[0:a][inv]amix=inputs=2:normalize=0[r]", "-map", "[r]", str(residual)])
    v, b = _rms_windows(voice, window), _rms_windows(residual, window)
    rows, gaps = [], []
    for i, (vv, bb) in enumerate(zip(v, b)):
        if vv <= -45:  # not speaking in this window
            continue
        gap = vv - bb
        gaps.append(gap)
        if gap < low_db:
            rows.append(f"| {i * window:6.1f}s | {vv:6.1f} | {bb:6.1f} | {gap:+5.1f} |")
    avg = sum(gaps) / len(gaps) if gaps else float("nan")
    lines = [f"# Mix check: {edit_path.name}", "",
             f"- Voice above music and effects, averaged while speaking: **{avg:+.1f} dB** "
             f"over {len(gaps)} windows of {window}s (aim for about +10 dB or more).",
             f"- Windows under +{low_db:g} dB: {len(rows)}. Each is a place a word may be masked: "
             "an effect on a word, a loud music hit, or just the gap between two lines.",
             "", "| at | voice dBFS | bed dBFS | gap dB |", "|---|---|---|---|", *rows, "",
             f"Stems: `{voice.name}`, `{residual.name}` (music + effects as heard under the voice), `{full.name}`."]
    md = out / "mixcheck.md"
    md.write_text("\n".join(lines) + "\n")
    return md
