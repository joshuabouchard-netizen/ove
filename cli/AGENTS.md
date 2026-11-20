# vg: the CLI behind OVE (Ops Video Editor)

The procedure lives in the skill (`SKILL.md` and `references/`). This directory is the code it calls: model
calls through OpenRouter and fal.ai, ffmpeg assembly with an OpenTimelineIO export, word-timed captions, Creative
Commons footage through yt-dlp, HTML rendering, synthesised sound effects, and the critic's fact reports.

```bash
vg --help                         # once installed (uv tool install -e <this dir>)
uv run --project <this dir> vg --help   # without installing
```

| Module | Does |
|---|---|
| `vg/config.py` | `VG_HOME` (default `~/ove`), reading keys from the environment or `VG_HOME/.env` |
| `vg/keys.py` | hands-free key setup: open the account pages, save a key from the clipboard, test it |
| `vg/costs.py` | the local spend ledger, `VG_HOME/costs.jsonl`: one line per paid call or failed attempt |
| `vg/openrouter.py` | images, video jobs (submit, poll, download), TTS (PCM → mp3), word-timestamp STT, Lyria music (streamed), Gemini video review |
| `vg/fal.py` | fal.ai queue API: submit, poll, download every media URL; unit prices; input schemas from fal's OpenAPI |
| `vg/timeline.py` | `edit.yaml` → ffmpeg render (xfades on a common timebase, Ken Burns stills, ducked music, loudnorm then a limiter, burned captions), `.otio`, and `render_audio` for stems |
| `vg/captions.py` | words → karaoke ASS and SRT; each line ends before the next starts |
| `vg/words.py` | caption timings per voice file, shifted to where the edit places it (robust under music) |
| `vg/footage.py` | yt-dlp search with YouTube's CC filter, section download, `credits.json` |
| `vg/critic.py` | contact sheets, shot frames, loudness, silence/black/freeze detection, script-vs-heard diff, `mixcheck` (voice vs everything else, per window) |
| `vg/media.py` | probing, `black_borders` (letterboxed images), `overlay` (alpha overlay on a clip, holding a short base) |
| `vg/html.py` | headless Chrome screenshot of a page (local file with `?query`, or URL) at any size and scale |
| `vg/sfx.py` | ffmpeg-synthesised effects: impact, whoosh, thud, riser, snap, tick, zap, button, chime |
| `vg/doctor.py` | install check: ffmpeg and the filters `vg` needs, keys present (never shown), optional tools |

Scripts emit facts; the agent judges.

## Keys and privacy

- `OPENROUTER_API_KEY` and `FAL_KEY` live in `VG_HOME/.env` (mode 600) or the environment. Never print, log or
  commit them; `vg doctor`, `vg spend` and `vg fal check` report presence only.
- If the OpenRouter account has **Zero Data Retention** enforced (openrouter.ai/settings/privacy), models without
  a ZDR endpoint return 404 and `vg` says so. As of late 2026 the image models, Whisper, MAI voice and Gemini
  review had ZDR endpoints; video generation and Lyria did not. Either turn enforcement off for media work or use
  the models that pass.
- fal writes `<out>.fal-job.json` and `<out>.fal-result.json` beside outputs; they hold request ids and media
  URLs. Don't commit or share them.

## Environment notes

- ffmpeg needs libass (captions), xfade, zoompan, sidechaincompress, loudnorm, alimiter. `vg doctor` checks.
  Without admin rights on a Mac: `pixi global install ffmpeg` (the conda-forge build has them all).
- Manim: `pixi global install manim` or `uv tool install manim` (needs cairo and pango). No LaTeX is assumed.
- Chrome or Chromium for `vg html` (set `VG_CHROME` if it isn't found).
- yt-dlp (`uv tool install yt-dlp`). YouTube may bot-check an IP: then metadata and downloads need
  `VG_HOME/.youtube-cookies.txt`.
- PATH for agent shells goes in `~/.zshenv`, not `~/.zshrc` (non-interactive shells skip `.zshrc`).

## Testing

```bash
uv run --project . --extra test pytest tests -q      # offline: ffmpeg and Chrome, no keys, no cost
```

The offline tests cover the config and ledger, caption timing, crossfades after cuts, music after the voice
ends, the limiter, stems and mixcheck, `words` from an edit, sfx presets, black-border detection, overlays,
HTML rendering and the fal argument mapping. They run in an isolated `VG_HOME` with keys cleared.

Live check after changing model code (about $0.40): one 2K image, a TTS line, a transcription, a 30 s Lyria
clip, a short `vg critic` with review, and a 3 s fal sound effect. Quote the cost to the account owner first.
