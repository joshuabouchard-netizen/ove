"""Synthesized haptic pulses, voiced so laptop speakers can carry them.

uv run --with numpy --with scipy python tools/haptics.py PRESET -o out.wav [--curve out.json] [--bed music.wav] [--at 3 11]
uv run --with numpy --with scipy python tools/haptics.py --list

Laptop speakers barely reproduce a 40-60 Hz pulse, so every preset keeps its low fundamental, adds the 2x-5x
harmonics that let the ear infer that pitch, and adds a faint 170-260 Hz band of noise, like a phone buzzing
on a table. Output is 48 kHz stereo 16-bit. On its own the pulse peaks at 0.8; with --bed it peaks at 0.16 and
is mixed into the bed (decoded with ffmpeg) at each --at time. --curve writes the pulse's intensity at 60 fps,
{"fps": 60, "curve": [0..1, ...]}, on the same timeline, to drive an on-screen nudge.
Drum knobs: --f0 (50-58 Hz), --attack (0.006-0.045 s), --decay (0.26-0.7 s), --wet (0-1). --f0 also works
for the other presets.
"""
import argparse, json, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
HARM = [(1, .6), (2, 1), (3, .7), (4, .45), (5, .25)]
rng = np.random.default_rng(7)


def secs(d):
    return np.arange(int(d * SR)) / SR


def voice(env, freq):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, env.shape)) / SR
    x = sum(a * np.sin(k * ph) for k, a in HARM)
    x = x + sosfilt(butter(2, [170, 260], "bandpass", fs=SR, output="sos"), rng.standard_normal(len(env))) * 2.2
    return x * env


def place(total, hits):
    x, e = np.zeros(int(total * SR)), np.zeros(int(total * SR))
    for at, (hx, he), amp in hits:
        i = int(at * SR); k = min(len(hx), len(x) - i)
        x[i:i + k] += hx[:k] * amp
        e[i:i + k] = np.maximum(e[i:i + k], he[:k] * amp)
    return x, e


def tap(a):
    f0 = a.f0 or 150
    def hit(dur):
        t = secs(dur * 2); env = np.minimum(1, t / .012) * np.exp(-t / (dur * .45))
        return voice(env, f0), env
    return place(0.8, [(0, hit(.20), 1), (.27, hit(.13), .6)])


def heartbeat(a):
    f0 = a.f0 or 55
    def beat(dur):
        t = secs(dur); env = np.sin(np.pi * t / dur) ** 2
        return voice(env, f0), env
    return place(2.4, [(b + dt, beat(dur), amp) for b in (0, 1.15) for dt, dur, amp in [(0, .16, 1), (.22, .12, .55)]])


def purr(a):
    t = secs(2.2)
    env = np.sin(np.pi * t / t[-1]) ** 2 * (.7 + .3 * np.sin(2 * np.pi * 24 * t))
    return voice(env, a.f0 or 48), env


def breath(a):
    t = secs(9.0)
    env = np.where(t < 3, (t / 3) ** 1.5, np.cos(np.pi / 2 * np.clip((t - 3) / 6, 0, 1)) ** 2)
    return voice(env, a.f0 or 42), env


def room(seconds=3.2, tau=0.75, cutoff=1400):
    t = secs(seconds); lp = butter(2, cutoff, "low", fs=SR, output="sos")
    ir = np.stack([sosfilt(lp, rng.standard_normal(len(t))) * np.exp(-t / tau) for _ in range(2)], 1)
    return ir / (np.abs(ir).sum(0).max() / 6)


def drum(a):
    f0, attack, decay = a.f0 or 56, a.attack, a.decay
    def body(f, drop=.3):
        t = secs(max(1.4, decay * 6)); env = np.minimum(1, t / attack) * np.exp(-t / decay)
        return voice(env, f * (1 + drop * np.exp(-t / .05))), env
    x, e = place(0.5 + max(1.4, decay * 6), [(0, body(f0), 1), (.5, body(f0 - 2, .25), .62)])
    ir = room()
    wet = np.stack([fftconvolve(x, ir[:, c]) for c in range(2)], 1)
    dry = np.vstack([np.stack([x, x], 1), np.zeros((len(ir) - 1, 2))])
    return dry * (1 - a.wet) + wet * a.wet, e


PRESETS = {
    "tap": (tap, "a soft double tap, 150 Hz"),
    "heartbeat": (heartbeat, "a slow resting lub-dub, twice, 55 Hz"),
    "purr": (purr, "a low hum that swells and settles with a 24 Hz flutter, 48 Hz"),
    "breath": (breath, "a breath to follow: 3 s in, 6 s out, 42 Hz"),
    "drum": (drum, "a deep drum and a softer second hit at +0.5 s, in a dark wet room, ~56 Hz"),
}


def load_bed(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset", nargs="?", choices=PRESETS)
    ap.add_argument("-o", "--out")
    ap.add_argument("--curve", help="write the 60 fps intensity curve here (JSON)")
    ap.add_argument("--bed", help="music or ambience to mix the pulse into")
    ap.add_argument("--at", type=float, nargs="+", default=[3.0], help="seconds into the bed where the pulse lands")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--f0", type=float)
    ap.add_argument("--attack", type=float, default=.008)
    ap.add_argument("--decay", type=float, default=.34)
    ap.add_argument("--wet", type=float, default=.5)
    a = ap.parse_args()
    if a.list:
        for k, (_, d) in PRESETS.items():
            print(f"{k:10} {d}")
        return
    if not a.preset or not a.out:
        ap.error("give a PRESET and -o out.wav (or --list)")
    x, env = PRESETS[a.preset][0](a)
    x = x if x.ndim == 2 else np.stack([x, x], 1)
    env = env / env.max()
    if a.bed:
        out = load_bed(a.bed)
        curve = np.zeros(len(out))
        x *= 0.16 / np.abs(x).max()
        for at in a.at:
            j = int(at * SR)
            if j >= len(out):
                sys.exit(f"--at {at} is past the end of the bed")
            k, m = min(len(x), len(out) - j), min(len(env), len(out) - j)
            out[j:j + k] += x[:k]
            curve[j:j + m] = np.maximum(curve[j:j + m], env[:m])
        if np.abs(out).max() > 0.97:
            out *= 0.97 / np.abs(out).max()
            print("bed + pulse was hot; scaled to a 0.97 peak", file=sys.stderr)
    else:
        out = x * 0.8 / np.abs(x).max()
        curve = np.concatenate([env, np.zeros(len(out) - len(env))])
    fade = int(0.005 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wavfile.write(a.out, SR, (out * 32767).round().clip(-32768, 32767).astype(np.int16))
    if a.curve:
        with open(a.curve, "w") as f:
            frames = np.pad(curve, (0, -len(curve) % (SR // 60))).reshape(-1, SR // 60).max(1)
            json.dump({"fps": 60, "curve": [round(float(v), 3) for v in frames]}, f)
    print(f"{a.out}: {a.preset}, {len(out) / SR:.2f} s, peak {20 * np.log10(np.abs(out).max()):.1f} dBFS")


if __name__ == "__main__":
    main()
