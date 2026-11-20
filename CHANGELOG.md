# Changelog

## 2.1.0 (November 2026): OVE

- Renamed **OVE (Ops Video Editor)**: the skill is `ove`, the home is `~/ove`, a git repository on GitHub.
- One-line install: `git clone … ~/ove && ~/ove/install.sh` installs every tool by default, links the skill
  (so improvements take effect at once), adds tool paths to `~/.zshenv`, retires older installs and carries
  their keys over.
- `vg keys open | paste | status`: hands-free key setup from the clipboard; keys are never shown.
- The skill now holds the first-run setup, the design-doc-first method, and the rules for growing OVE (lessons
  into references, fixes into `vg` with tests, commits).

## 2.0.0 (November 2026): media-gen

Renamed from **video-gen** (Daniel Reid Cahn's original skill and `vg` CLI). This release draws on several
real projects: a calm explainer, an action re-cut of it, slide art in a given illustration style, film-still
and doll portraits from personal photos, six-direction brand explorations, and an interactive product-concept
demo with a phone composite, cloned voices and generated ambience.

### Skill

- `SKILL.md` is now a router: one table sends each kind of job to its reference.
- New references:
  - `images.md`: style from a document, likeness from photos, edits, left and right, black bars;
  - `layout.md`: exact text in HTML;
  - `brand.md`;
  - `prototypes.md`: page-to-video, phone composites, review pages, PowerPoint, private hosting;
  - `fal.md`;
  - `costs.md`;
  - `setup.md`;
  - `troubleshooting.md`.
- Rewritten references: `script.md` (lecture vs ride registers, word budgets), `voice.md` (auditions,
  transcript checks), `audio.md` (fitting a track to the cut, sound effects, mix levels), `critic.md` (reading
  the reports, second-opinion false positives), `visuals.md` (retries and fallback, using stretches of a clip),
  `motion-graphics.md` (timing files, energy, overlays, no-LaTeX).
- `examples/the-climb/`: a complete 45 s action explainer: script, prompts, standalone Manim scenes, edit list
  with sound design.
- `examples/brand/`: mockup engine (lockup, type specimen, cards, social post, poster) and a comparison board,
  driven by one tokens file.
- `tools/`:
  - `capture.py`: deterministic page to video, stills and audio;
  - `key_screen.py`: green-screen phone fit with a CSS homography;
  - `haptics.py`: audible haptic sounds plus intensity curves;
  - `calm_master.sh`;
  - `review/`: a Love/Maybe/Not choice page;
  - `pptx_autoplay.py`: video slides that play;
  - `gate/`: a Cloudflare Pages password gate with byte ranges.

### CLI (`vg`)

- **New commands:**
  - `doctor`: install and key check;
  - `spend`: OpenRouter usage, balance and the local ledger;
  - `words`: caption timings from each voice file;
  - `mixcheck`: voice against everything else, per window;
  - `html`: headless Chrome render, with query strings;
  - `sfx`: nine synthesised effects;
  - `overlay`: an alpha overlay on a clip;
  - `borders`: letterbox detection;
  - `fal run | price | schema | check`.
- `vg fal run`:
  - `--prompt-key` (for `text` endpoints);
  - `-f key=file` (data URIs);
  - `-s key=string`;
  - list-valued image fields;
  - spend logged.
- `vg video`: retries on "high load" and `--fallback` to another model.
- `vg image`: warns about black bars baked into a frame.
- `vg critic --words` uses per-file word timings instead of transcribing the mix.
- `VG_HOME` (default `~/media-gen`) holds `.env` and `costs.jsonl`. Keys come from the environment or `.env`
  and are never printed.
- **Fixes:**
  - Gemini TTS: requests PCM and converts it;
  - Lyria: streams;
  - crossfades after a plain cut: common timebase;
  - music no longer stops dead when the narration ends;
  - a limiter after loudnorm (true peak under -1 dBFS);
  - caption lines never overlap;
  - RMS windows sized from the file's sample rate.
- An offline pytest suite (no keys, no cost).
- `install.sh`: idempotent, no sudo, optional dependency install through uv and pixi.
