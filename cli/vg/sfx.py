"""Sound effects synthesised with ffmpeg: no samples, no licences, no cost. 48 kHz stereo WAV.

Good enough for punctuation under an edit (impacts, whooshes, risers, a snap). For realistic foley or
ambience (rain, a room, a crowd) use a generator instead: `vg fal run fal-ai/elevenlabs/sound-effects`.
"""

from __future__ import annotations

from pathlib import Path

from vg.media import run

R = 48000

# name -> (description, ffmpeg arguments after the leading `ffmpeg`, before the output path)
PRESETS: dict[str, tuple[str, list[str]]] = {
    "impact": ("falling sub thump with a short bright splash, 1.4 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.95*sin(2*PI*(70*t-22*t*t))*exp(-5*t):s={R}:d=1.4",
        "-f", "lavfi", "-i", f"anoisesrc=d=0.35:c=white:r={R}:a=0.6",
        "-filter_complex", "[1]highpass=f=1200,afade=t=out:st=0:d=0.35[n];[0][n]amix=inputs=2:normalize=0,"
                           "aformat=channel_layouts=stereo,alimiter=limit=0.95"]),
    "whoosh": ("pink-noise swell for camera moves and transitions, 1.0 s", [
        "-f", "lavfi", "-i", f"anoisesrc=d=1.0:c=pink:r={R}:a=0.9",
        "-af", "highpass=f=250,lowpass=f=5000,volume='sin(PI*t/1.0)^3':eval=frame,afade=t=out:st=0.85:d=0.15,"
               "aformat=channel_layouts=stereo,volume=2.2"]),
    "thud": ("tight sub hit under kinetic type, 0.6 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.95*sin(2*PI*58*t)*exp(-9*t)+0.3*sin(2*PI*180*t)*exp(-30*t):s={R}:d=0.6",
        "-af", "aformat=channel_layouts=stereo,alimiter=limit=0.95"]),
    "riser": ("accelerating upward sweep with noise, building into a hit, 2.3 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.35*(t/2.3)^2*sin(2*PI*(180*t+260*t*t)):s={R}:d=2.3",
        "-f", "lavfi", "-i", f"anoisesrc=d=2.3:c=pink:r={R}:a=0.5",
        "-filter_complex", "[1]highpass=f=800,volume='(t/2.3)^3':eval=frame[n];[0][n]amix=inputs=2:normalize=0,"
                           "aformat=channel_layouts=stereo,volume=1.6"]),
    "snap": ("sharp crack and a long sub drop, 1.6 s", [
        "-f", "lavfi", "-i", f"anoisesrc=d=0.08:c=white:r={R}:a=1.0",
        "-f", "lavfi", "-i", f"aevalsrc=0.95*sin(2*PI*(120*t-38*t*t))*exp(-1.6*t):s={R}:d=1.6",
        "-filter_complex", "[0]highpass=f=2500,afade=t=out:st=0.0:d=0.08,apad=whole_dur=1.6[c];[c][1]amix=inputs=2:"
                           "normalize=0,aformat=channel_layouts=stereo,alimiter=limit=0.95"]),
    "tick": ("tiny bright click for a UI tap or a counter, 0.15 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.6*sin(2*PI*3200*t)*exp(-60*t):s={R}:d=0.15",
        "-af", "aformat=channel_layouts=stereo"]),
    "zap": ("rising double chirp with a noise burst, 0.6 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.5*sin(2*PI*(300*t+2400*t*t))*exp(-3.5*t)+0.25*sin(2*PI*(600*t+4800*t*t))*exp(-5*t):s={R}:d=0.6",
        "-f", "lavfi", "-i", f"anoisesrc=d=0.3:c=white:r={R}:a=0.4",
        "-filter_complex", "[1]highpass=f=3000,afade=t=out:st=0:d=0.3,apad=whole_dur=0.6[n];[0][n]amix=inputs=2:"
                           "normalize=0,aformat=channel_layouts=stereo"]),
    "button": ("big sub hit with a long tail for an end card, 2.5 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.95*sin(2*PI*(62*t-8*t*t))*exp(-2.2*t)+0.25*sin(2*PI*124*t)*exp(-4*t):s={R}:d=2.5",
        "-af", "aformat=channel_layouts=stereo,alimiter=limit=0.95"]),
    "chime": ("soft two-note chime for a gentle notification, 2.0 s", [
        "-f", "lavfi", "-i", f"aevalsrc=0.3*sin(2*PI*880*t)*exp(-2.5*t)+0.22*sin(2*PI*1318.5*(t-0.18))*exp(-2.5*(t-0.18))*gte(t\\,0.18):s={R}:d=2.0",
        "-af", "aformat=channel_layouts=stereo,afade=t=out:st=1.6:d=0.4"]),
}


def generate(preset: str, out: Path) -> Path:
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; one of: {', '.join(PRESETS)}")
    out = Path(out).with_suffix(".wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", *PRESETS[preset][1], str(out)])
    return out
