"""Offline tests: everything ffmpeg-only, plus the pure-Python pieces. Run: uv run --project cli --extra test pytest cli/tests"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from vg import captions, config, costs, critic, html, sfx, timeline, words
from vg import media as vgmedia
from tests.conftest import ff


def level(path: Path, start: float, dur: float) -> float:
    """Mean volume (dB) of a stretch of a file's audio."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(start), "-t", str(dur), "-i", str(path),
                          "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", out)
    return -120.0 if not m or m.group(1) == "-inf" else float(m.group(1))


def write_edit(d: Path, body: str) -> Path:
    p = d / "edit.yaml"
    p.write_text(body)
    return p


EDIT = """size: [640, 360]
fps: 30
loudness: -14
video:
  - {src: a.png, dur: 2, motion: zoom-in}
  - {src: clip.mp4, dur: 2}
  - {src: b.png, dur: 2.5, motion: pan-left, transition: 0.5}
audio:
  - {src: voice.wav, at: 0.5, role: voice}
  - {src: music.wav, at: 0, role: music, gain_db: -6}
"""


def test_config_reads_env_file(isolated_home, monkeypatch):
    (isolated_home / ".env").write_text("OPENROUTER_API_KEY='sk-test'\nFAL_KEY=\n")
    assert config.secret("OPENROUTER_API_KEY") == "sk-test"
    assert config.secret("FAL_KEY") is None
    monkeypatch.setenv("FAL_KEY", "from-env")
    assert config.secret("FAL_KEY") == "from-env"
    with pytest.raises(RuntimeError):
        monkeypatch.delenv("FAL_KEY")
        config.require("FAL_KEY")


def test_costs_ledger(isolated_home):
    costs.usage("t", "openrouter", {"cost": 0.13}, model="m", op="image")
    costs.attempt("t", "fal", model="k", op="run", status=500, body="x" * 5000)
    rows = costs.rows()
    assert rows[0]["usd"] == 0.13 and rows[0]["ok"] is True
    assert rows[1]["ok"] is False and "body" not in rows[1]


def test_caption_lines_never_overlap():
    ws = [captions.Word(t, s, s + 0.3) for t, s in [("One", 0.0), ("two.", 0.35), ("Three", 0.7), ("four.", 1.05)]]
    lines = captions.group(ws, max_words=4, max_chars=40)
    assert len(lines) == 2  # split at the full stop
    assert captions._end(lines, lines[0]) < lines[1][0].start  # held, but never into the next line


def test_render_crossfade_after_cut_and_music_after_voice(media):
    """Regressions: an xfade after a plain cut used to fail on mismatched timebases, and the ducked music
    used to stop dead when the voice ended (sidechaincompress ends with its key)."""
    edit = timeline.load(write_edit(media, EDIT))
    out = timeline.render(edit, media / "out" / "draft.mp4", captions=False)
    assert abs(vgmedia.duration(out) - edit.total) < 0.1
    # the voice ends at 2.5 s; the music must still be playing at the end of the edit
    assert level(out, 5.0, 1.0) > -60


def test_limiter_keeps_true_peak_down(media):
    ff("-f", "lavfi", "-i", "aevalsrc=0.99*sin(2*PI*80*t)*exp(-3*t):s=48000:d=1", str(media / "hit.wav"))
    body = EDIT + "  - {src: hit.wav, at: 3.0, role: sfx, gain_db: 6}\n"
    edit = timeline.load(write_edit(media, body))
    out = timeline.render(edit, media / "out" / "hot.mp4", captions=False)
    peak = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    assert float(re.search(r"max_volume: (-?[\d.]+) dB", peak).group(1)) <= -0.5


def test_render_audio_stems(media):
    edit = timeline.load(write_edit(media, EDIT))
    voice = timeline.render_audio(edit, media / "v.wav", roles={"voice"}, loudness=False, limiter=False)
    assert voice and level(voice, 0.6, 1.5) > -40 and level(voice, 4.0, 2.0) < -80
    assert timeline.render_audio(edit, media / "none.wav", roles={"sfx"}) is None


def test_mixcheck_reports_gap(media):
    md = critic.mixcheck(write_edit(media, EDIT), media / "mc")
    text = md.read_text()
    assert "Voice above music and effects" in text
    gap = float(re.search(r"\*\*([+-][\d.]+) dB\*\*", text).group(1))
    assert gap > 0  # the voice tone is louder than the music at -6 dB, ducked


def test_words_from_edit_uses_cache_and_offsets(media):
    (media / "voice.wav.words.json").write_text(json.dumps(
        {"text": "hello there", "words": [{"text": "hello", "start": 0.1, "end": 0.5}, {"text": "there", "start": 0.6, "end": 1.0}]}))
    data = words.from_edit(write_edit(media, EDIT))
    assert [w["text"] for w in data["words"]] == ["hello", "there"]
    assert data["words"][0]["start"] == pytest.approx(0.6)  # 0.1 + at 0.5


@pytest.mark.parametrize("name", list(sfx.PRESETS))
def test_sfx_presets(tmp_path, name):
    out = sfx.generate(name, tmp_path / name)
    assert out.exists() and vgmedia.duration(out) > 0.1
    assert vgmedia.probe(out)["streams"][0]["channels"] == 2


def test_black_borders(tmp_path):
    ff("-f", "lavfi", "-i", "color=c=0x8a6f4d:s=1200x676", "-vf", "pad=1600:676:200:0:black", "-frames:v", "1", str(tmp_path / "barred.png"))
    ff("-f", "lavfi", "-i", "testsrc=s=1600x900", "-frames:v", "1", str(tmp_path / "full.png"))
    assert vgmedia.black_borders(tmp_path / "barred.png") is not None
    assert vgmedia.black_borders(tmp_path / "full.png") is None


def test_overlay_holds_short_base(media, tmp_path):
    ff("-f", "lavfi", "-i", "color=c=white@0.0:s=640x360,format=rgba", "-vf", "drawbox=x=20:y=20:w=200:h=60:color=red@1:t=fill",
       "-frames:v", "1", str(tmp_path / "title.png"))
    out = vgmedia.overlay(media / "clip.mp4", tmp_path / "title.png", tmp_path / "comp.mp4", size=(640, 360), dur=4.5)
    assert abs(vgmedia.duration(out) - 4.5) < 0.1


@pytest.mark.skipif(not html.chrome_path(), reason="no Chrome/Chromium")
def test_html_render(tmp_path):
    page = tmp_path / "p.html"
    page.write_text("<html><body style='margin:0;background:#f3f2ee'><h1 style='font:64px serif'>Exact text</h1></body></html>")
    out = html.render(page, tmp_path / "p.png", width=800, height=450, scale=2)
    s = vgmedia.probe(out)["streams"][0]
    assert (int(s["width"]), int(s["height"])) == (1600, 900)


def test_fal_run_maps_flags_to_request(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from vg import cli, fal
    seen = {}
    monkeypatch.setattr(fal, "price", lambda model: None)
    monkeypatch.setattr(fal, "run", lambda model, args, out, timeout_s: seen.update(model=model, args=args) or [out])
    img = tmp_path / "a.png"; img.write_bytes(b"\x89PNG")
    ref = tmp_path / "ref.wav"; ref.write_bytes(b"RIFF")
    r = CliRunner().invoke(cli.app, ["fal", "run", "fal-ai/x", "-o", str(tmp_path / "o.mp3"), "-p", "rain", "--prompt-key", "text",
                                     "--image", str(img), "--image", str(img), "-f", f"audio_url={ref}",
                                     "-a", "duration_seconds=10", "-a", "loop=true", "-s", "duration=10"])
    assert r.exit_code == 0, r.output
    a = seen["args"]
    assert a["text"] == "rain" and "prompt" not in a
    assert a["image_url"].startswith("data:image/png;base64,") and a["tail_image_url"].startswith("data:image/png")
    assert a["audio_url"].startswith("data:audio/")
    assert a["duration_seconds"] == 10 and a["loop"] is True and a["duration"] == "10"


def test_fal_run_list_image_field(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from vg import cli, fal
    seen = {}
    monkeypatch.setattr(fal, "price", lambda model: None)
    monkeypatch.setattr(fal, "run", lambda model, args, out, timeout_s: seen.update(args=args) or [out])
    img = tmp_path / "a.png"; img.write_bytes(b"\x89PNG")
    r = CliRunner().invoke(cli.app, ["fal", "run", "fal-ai/y", "-o", str(tmp_path / "o.png"), "-p", "edit",
                                     "--image-key", "image_urls", "--image", str(img), "--image", str(img)])
    assert r.exit_code == 0, r.output
    assert isinstance(seen["args"]["image_urls"], list) and len(seen["args"]["image_urls"]) == 2


def test_home_falls_back_to_existing_video_gen(tmp_path, monkeypatch):
    from vg import config
    monkeypatch.delenv("VG_HOME", raising=False)
    monkeypatch.setattr(config.Path, "home", classmethod(lambda cls: tmp_path))
    assert config.home() == tmp_path / "ove"
    (tmp_path / "video-gen").mkdir(); (tmp_path / "video-gen" / ".env").write_text("X=1\n")
    assert config.home() == tmp_path / "video-gen"
    (tmp_path / "media-gen").mkdir(); (tmp_path / "media-gen" / ".env").write_text("X=1\n")
    assert config.home() == tmp_path / "media-gen"
    (tmp_path / "ove").mkdir()
    assert config.home() == tmp_path / "ove"


def test_html_render_passes_query_string(tmp_path):
    from vg import html as vghtml
    if not vghtml.chrome_path():
        pytest.skip("no Chrome")
    page = tmp_path / "q.html"
    page.write_text("<body style='margin:0'><script>document.body.style.background="
                    "new URLSearchParams(location.search).get('c')</script></body>")
    out = vghtml.render(f"{page}?c=%23ff0000", tmp_path / "q.png", width=200, height=100)
    px = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(out), "-vf", "crop=1:1:100:50", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    assert px[0] > 200 and px[1] < 40 and px[2] < 40


def test_secret_skips_empty_template_line(isolated_home):
    (isolated_home / ".env").write_text("# keys\nOPENROUTER_API_KEY=\nFAL_KEY=\nexport OPENROUTER_API_KEY='abc'\n")
    assert config.secret("OPENROUTER_API_KEY") == "abc"
    assert config.secret("FAL_KEY") is None


def test_fal_cost_estimate(media):
    from vg import fal
    assert abs(fal.estimate((0.07, "seconds"), [media / "clip.mp4"]) - 0.21) < 0.01
    assert fal.estimate((0.15, "images"), [media / "a.png", media / "b.png"]) == 0.3
    assert fal.estimate((0.1, "1000 characters"), [media / "voice.wav"]) is None
    assert fal.estimate(None, [media / "clip.mp4"]) is None


def test_keys_paste_saves_from_clipboard(isolated_home, tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from vg import cli, keys
    clip = tmp_path / "clip.txt"
    monkeypatch.setenv("VG_CLIPBOARD_CMD", f"cat {clip}")
    monkeypatch.setattr(keys, "check", lambda provider: (True, "works"))
    (isolated_home / ".env").write_text("# keys\nOPENROUTER_API_KEY=\nFAL_KEY=\n")
    clip.write_text("sk-or-v1-" + "a" * 40 + "\n")
    r = CliRunner().invoke(cli.app, ["keys", "paste", "openrouter"])
    assert r.exit_code == 0, r.output
    assert "…aaaa" in r.output and "sk-or-v1" not in r.output
    assert config.secret("OPENROUTER_API_KEY") == "sk-or-v1-" + "a" * 40
    assert (isolated_home / ".env").read_text().count("OPENROUTER_API_KEY=") == 1
    assert oct((isolated_home / ".env").stat().st_mode)[-3:] == "600"
    clip.write_text("not a key")
    r = CliRunner().invoke(cli.app, ["keys", "paste", "openrouter"])
    assert r.exit_code == 1 and "not saved" in r.output
    clip.write_text("abcd1234-0000-1111-2222-333344445555:" + "f" * 32)
    r = CliRunner().invoke(cli.app, ["keys", "paste", "fal"])
    assert r.exit_code == 0 and config.secret("FAL_KEY").endswith("ffff")
