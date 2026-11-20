# Motion graphics: Manim and Hyperframes

Use code-drawn graphics wherever the picture is a diagram, a chart, text, an equation, a UI or a process. They
are exact, free, re-renderable after a script change, and never hallucinate a label. AI video is for things a
camera would film.

| Need | Tool |
|---|---|
| Diagrams, molecules, processes, charts being drawn, kinetic type, counters | Manim |
| Kinetic type, titles, lower-thirds, UI mock-ups, layouts with CSS | Hyperframes, or an HTML page (`references/layout.md`) |

`examples/the-climb/scenes.py` is a working set of scenes from a finished 45 s explainer: a chain of molecules
yanked upward with camera shake, slammed kinetic type, a counter overlay, a snap with a flash and shockwave, a
spike flying off a scale, and an end card. It reads its lengths from `timing.json` and renders standalone.

## Manim

```bash
manim -ql --format mp4 -o s04-preview scenes.py S04                                  # 480p15 preview, seconds
manim -qh --fps 30 -r 1920,1080 --format mp4 -o s04 scenes.py S04                    # final, 1080p30
manim -qh --fps 30 -r 1920,1080 -t --format mov -o o08 scenes.py O08                 # transparent overlay
```

Output lands in `media/videos/<file>/<quality>/`; copy it into `clips/`. Iterate at `-ql`, make a contact sheet
of the preview (4 fps, `tile=6x3`) and look at it, then render once at `-qh`.

- **Time scenes to the voice from a file.** Keep each scene's length, and the moments things must land, in a
  small JSON (`timing.json`: `{"T03": 2.6, "T03_hits": [0.57, 1.59]}`), computed from the voice-over's word
  timings. Scenes read it and pad to their length with a slow push-in rather than a frozen hold. When a line is
  re-voiced, update the JSON and re-render; nothing else changes.
- **Energy** for an action cut: text that slams in (scale from 1.9× and transparent to full size in 0.14 s with
  `rush_into`), a decaying camera shake on each hit (a `MovingCameraScene` with a seeded random offset that
  shrinks to zero), speed lines streaking past, a white flash that fades out on a snap. Use seeded randomness
  so re-renders match.
- **No LaTeX** unless installed: `Tex`, `MathTex` and `DecimalNumber` fail looking for `latex`. Write maths with
  Unicode in `Text` (`x² + y²`), and make a counter with a `ValueTracker` and
  `always_redraw(lambda: Text(f"{int(v.get_value())} m"))`.
- **Camera-frame updaters** only run when the frame is in the scene: `self.add(self.camera.frame)`.
- **`self.wait(0)`** raises; only wait when the remaining time is positive.
- **Text fits**: big kinetic type overflows the frame easily, and the frame is smaller still if you zoomed the
  camera; `VGroup(a, b).arrange(DOWN).scale_to_fit_width(11.5)` keeps a two-line card inside it.
- **Match the palette** to the rest of the video with `config.background_color`; a deep colour with one bright
  accent for the subject (water in cyan, the sun in yellow) reads well behind captions.
- Install without admin rights: `pixi global install manim` (brings cairo and pango). Fonts are any installed
  system font through Pango (`Text(..., font="Avenir Next", weight=HEAVY)` on a Mac).

## Overlays

Counters, titles and labels that sit on a generated clip: render the scene with `-t --format mov` (it keeps an
alpha channel) and composite with `vg overlay base.mp4 overlay.mov -o out.mp4 --dur 4.5`. Keep them clear of
the caption area, and label what a picture is honestly: a generated redwood is "the height of the tallest tree
on Earth", not that tree by name.

## Hyperframes (HTML → MP4, via `pnpm dlx hyperframes`)

HeyGen's framework: a composition is an HTML page with GSAP (or CSS/WAAPI) animations that the renderer seeks
frame by frame in headless Chrome.

```bash
cd <project>/graphics && pnpm dlx hyperframes init s05-title
cd s05-title && pnpm dlx hyperframes lint && pnpm dlx hyperframes render -o ../../clips/s05.mp4
pnpm dlx hyperframes render --format webm -o overlay.webm   # transparent, for lower-thirds
pnpm dlx hyperframes docs                                   # the composition contract, offline
```

Hyperframes publishes its own agent skills (`pnpm dlx hyperframes skills update` in the graphics folder). Don't
use its `tts`, `transcribe` or `cloud` commands: voice, transcription and rendering go through the rest of this
skill. Keep compositions deterministic: no unseeded `Math.random()`, no network fetches at render time.
