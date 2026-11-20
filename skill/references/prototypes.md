# Prototypes, demos and presentations: browser pages that become video, decks and shareable sites

For a product concept, an app feature demo or an interactive pitch: build it as a web page, render it to video
frame by frame, composite it into generated real-world footage, and deliver it as a video, a PowerPoint or a
password-protected site. The pieces below were all used end to end on one concept demo.

Generic tools are in `tools/`: `capture.py` (page → video, stills, audio), `key_screen.py` (green-screen phone
fit), `haptics.py` (audible haptic sounds), `review/` (a choice page), `pptx_autoplay.py` (video slides that
play), and `gate/` (password-protected hosting).

## The core rule

**Never let an image or video model draw UI or text.** Video models redraw screens: they invented a heartbeat
line, extra buttons and a clock. Generate only the real-world plate (the hand, the room, the light) with a
green screen where the screen goes, render the interface exactly in HTML, and put it on top. AI footage is
for organic texture (ink, aurora, fireflies, embers, rain on glass), kept behind the exact line work.

Measure the real thing when there is one: take positions, sizes, line widths and colours from a screen
recording or screenshots, in points, and replay recorded motion rather than approximating it.

## 1. A page that renders deterministically

The page draws from a time value instead of the clock, so any frame can be rendered at any moment:

```js
window.renderAt = (t) => { /* draw everything for time t (seconds) */ };
document.fonts.ready.then(() => { window.__ready = true; });
// optional: the same audio graph rendered offline, streamed back in chunks
window.renderAudio = async (send) => {
  const ctx = new OfflineAudioContext(2, 48000 * DUR, 48000);
  buildGraph(ctx); const buf = await ctx.startRendering();
  /* interleave to Int16, send 5 s base64 chunks: await send(b64) */
};
```

A `?capture=1` query turns off live playback and UI chrome. Then:

```bash
uv run --with playwright python tools/capture.py stills  shots/ 5 40 120 --page demo.html          # PNGs at 5, 40, 120 s
uv run --with playwright python tools/capture.py video   out/demo.mp4 0 90 --page demo.html --fps 30 --size 1920x1080
uv run --with playwright python tools/capture.py audio   out/demo.wav --page demo.html --duration 90
```

(First run: `uv run --with playwright python -m playwright install chromium`, or pass `--channel chrome` to
use the installed Chrome.)

- Each frame: `renderAt(i/fps)`, screenshot as JPEG, piped into ffmpeg. Chrome sometimes throws "Unable to
  capture screenshot" under load; `capture.py` retries each frame up to 5 times.
- Long renders: split into time ranges, run 3 processes at once (more makes Chrome fail), check each part's
  frame count with `ffprobe -count_frames`, re-render only missing tails, join with the concat demuxer.
  Expect about 4 frames per second per process at 2560×1440.
- A heavy blur on every element every frame is very slow: blur once into an offscreen canvas layer.
- Mux the offline audio and normalise loudness with two-pass loudnorm (`references/audio.md`).

Touch indicators for a demo: a 44 px circle (`rgba(120,120,128,.32)` fill, `1.5px solid rgba(255,255,255,.75)`
border) at each scripted touch, fading in over 80 ms and out over 300 ms with a slight scale; also one per key
while "typing".

## 2. A real phone in a real hand

1. **Generate the plate with a green screen** (Gemini image, 16:9, 4K):

   > Photorealistic night-time photograph, 16:9. First-person view from the pillow: a person lies flat on
   > their back… Their hand holds a modern smartphone (thin dark frame, very slim bezels) upright above their
   > chest… facing the camera straight-on and flat to the lens, centred, filling about 75 percent of the frame
   > height. The phone screen is a uniform solid pure green (#00FF00) with no reflections, glare or icons, with
   > sharp clean edges and correct rounded corners. Warm light from a bedside lamp… Natural skin, real camera
   > grain, shallow depth of field. No text, no logos.

   Keep the phone big (75–90% of the frame height) or it looks like a toy. Variants (lamp on, covers up,
   empty room) are edits of the same photo: "Edit this photograph. Keep the hand, the phone, the green
   screen… exactly as they are, in exactly the same positions, with the same camera. [one change]".
2. **Key and fit**: `uv run --with opencv-python-headless --with numpy python tools/key_screen.py plate.jpg out/phone`
   finds the green, fits the four screen corners to sub-pixel accuracy (a line fitted to the middle of each
   side, so rounded corners don't pull it), despills green off the fingers, and writes `phone_bg.jpg`,
   `phone_ov.png` (the photo with the screen cut out, so fingers stay above the screen) and `phone.json` (the
   corner quad).
3. **Put the HTML screen on the quad** with a CSS `matrix3d` homography (solve the 8×8 system from the
   screen's corners to the quad; `tools/key_screen.py` prints the CSS too). Grow the quad about 1% to tuck under
   the bezel. Stack: background photo, screen DOM, overlay PNG, a little screen-light spill on the hand
   (`mix-blend-mode: screen`).
4. **Motion** (picking the phone up): a first-and-last-frame video clip between two stills with the screen
   kept "pure flat bright green the whole time", then key every frame, smooth the quads over time
   (Savitzky–Golay, window 15), and in the page lock the screen to the video frame with
   `video.requestVideoFrameCallback((now, md) => draw(md.mediaTime))`. Keep the screen dark while the phone
   moves and wake it when it settles: tracking jitter shows most on a lit screen. One continuous generated
   take beats two stitched ones; the seam always shows.
5. Write the overlay video with alpha as VP9: `-c:v libvpx-vp9 -pix_fmt yuva420p -b:v 6M -auto-alt-ref 0`.
   Check the real page, not the asset: a fix applied to the background layer but not the overlay showed up
   as two right feet.

## 3. Organic motion plates

- Edit the screen into a **clean plate** (no UI, no line), animate it (Veo 9:16 8 s with `--first`, or Kling
  text-to-video 10 s), then slow it down with motion interpolation:
  `-vf "scale=720:1280,setpts=3.6*PTS,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1"` (factor 3.6–6).
- An opening that lands on the loop: first frame "empty", last frame the loop's first frame, then ease out
  with a quadratic slow-down `setpts='(1.3*T+0.17*T*T)/TB'` and crossfade into the loop.
- Over busy footage, give drawn lines a crisp white core, a tight halo and a faint dark edge.

## 4. Sound locked to picture

- **Music-driven events**: compute the track's loudness envelope at 60 fps, find the swells
  (`scipy.signal.find_peaks(env, distance=4*fps, prominence=0.05)`), choose the excerpt whose swells land where
  you need them, and write a JSON (`{"fps", "env", "events"}`) the page reads to drive colour, speed and pulses.
  `librosa.beat.beat_track` gives the tempo; put hits on downbeats.
- **Audible haptics** (`tools/haptics.py`): a phone's vibration is inaudible on laptop speakers. Keep the low
  fundamental (42–150 Hz), add harmonics 2–5× so the ear infers the pitch, and add band-passed noise at
  170–260 Hz (a phone rattling on a wooden table). Presets: double tap, heartbeat, purr, breath, deep drum.
  Each writes a 60 fps intensity curve for the visual.
- **Gentle music** for calm or sleep content: decode in float, `adeclip`, a high-shelf cut, gentle compression,
  two-pass `loudnorm=I=-26:TP=-6`, then `alimiter=limit=0.5` (`tools/calm_master.sh`). Avoid sharp attacks.
- **Loudness targets** that worked: narrated video -14 LUFS; deck videos about -21 (no jumps between slides);
  calm beds -26; voices on their own -19; ambience loops RMS -24 dBFS.
- Synthesised "typing clicks" sound fake; leave them out.
- Before asking someone to choose a sound, level-match every option and give them play buttons.

## 5. Letting someone choose: review pages

`tools/review/build.py items.json -o review/index.html` makes a page with, per item, a video or image, an
optional audio player (only one plays at a time), **Love it / Maybe / Not this** buttons and a note box. Choices
persist in the browser, and a sticky **Copy my picks** button puts plain text on the clipboard
(`- Warm room: LOVE (brighter lamp)`) for the person to paste back into the chat.

- Shrink media first (JPEG 2400 px, MP3 instead of WAV); one folder went from 69 MB to a few.
- Check the page with headless screenshots at desktop (1440) and phone (390) widths before sending it.
- Several rounds narrow it: six looks, eight sounds, four feels → four picks → the final.

## 6. PowerPoint with videos that actually play

python-pptx's `add_movie` makes a slide whose video waits for a click, and some builders add a click effect
that fails on macOS PowerPoint. `tools/pptx_autoplay.py` builds slides from PNGs and MP4s and rewrites each video
slide's timing so the video **plays when the slide appears**
(`uv run --with python-pptx --with lxml python tools/pptx_autoplay.py slides.json -o deck.pptx`, where
`slides.json` lists `{"image": "s1.png", "notes": "..."}` and `{"video": "clip.mp4", "poster": "p.png"}` entries):

```xml
<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
<p:video><p:cMediaNode vol="100000"><p:cTn id="2" fill="hold" display="0"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>
<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cMediaNode></p:video></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>
```

Also: remove any empty `r:id=""` on `a:hlinkClick`, layer nothing over the video, give each video a poster
frame, and render the designed slides as PNGs from HTML (exact fonts). Open the file in PowerPoint to check it;
a slideshow can't be screen-captured without permission, so ask a person to confirm playback.

## 7. A live presentation in the browser

- One page at a fixed stage (2560×1440) scaled to the window; `#N` in the URL jumps to a slide (add a
  `hashchange` listener), arrows and space advance, story beats advance on click.
- To work from `file://` (double-click to open, no server): pack audio as lazily loaded `<script>` files that
  set base64 data URIs, and decode with `ctx.decodeAudioData(await (await fetch(uri)).arrayBuffer())`.
- Crossfade-loop music: about 9 s before the end, ramp the old source down over 6 s and start a new one at an
  earlier musical point.
- Rename changed assets (`clip_v2.mp4`) instead of overwriting, or the browser cache serves the old one.
- Web fonts need one online load first; say so to whoever presents offline.
- **Test it headlessly before calling it done**: Playwright clicks through the story, collects page errors and
  console errors, screenshots key moments into a contact sheet, and records the page's actual audio by
  connecting a `MediaStreamDestination` to the master gain and running `MediaRecorder` on it, then a listening
  model or `vg critic` checks it. Say plainly what you couldn't verify (sound through speakers, a PowerPoint
  slideshow).
- Common bugs: an overlay with `pointer-events: auto` on a hidden slide swallowing clicks (use `''`, and
  `pointer-events: none` on decorative images); a negative `dt` on the first animation frame; a focused button
  re-activated by the space bar (`blur()` after click); a video waiting for `loadeddata` that already fired
  (start on `seeked`, `canplay` or `loadeddata`, with a timeout).

## 8. Sharing it privately

`tools/gate/` is a password gate for Cloudflare Pages (free; Netlify's and Vercel's password protection are
on paid plans): every request needs a cookie derived from a secret password, unauthenticated HTML requests
get a login page and everything else gets 401, `/__leave` signs out, robots are refused, and media gets byte-
range responses so Safari plays video. See `tools/gate/README.md`. Pages has a 25 MiB per-file limit;
`build.sh` warns about larger files.

The account login and the password are the owner's to type: `npx wrangler login`, then
`npx wrangler pages secret put SITE_PASSWORD --project-name <name>`. Test locally first with
`npx wrangler pages dev site` (restart it after changing the worker; it doesn't reload).

## 9. An interactive demo people play themselves

The pattern: photoreal scenes as stills, the
app as live HTML mapped onto the phone screen, and a small point-and-click layer on top.

- **Branching talk without a tree explosion**: each path has its own first two turns, then all paths share the
  rest. Give every user reply two or three replies from the app, chosen at random and shuffle the suggested replies, so each
  run differs. Keep the script in one JSON file; voice every line from it and check every file with Whisper.
- **Hotspots belong on the object** (the fridge door, the papers), never on the floor beside it, and labels must
  not cross another ring. Check a screenshot of every choice screen.
- **Captions read as subtitles**: centred, borderless serif with a shadow, not a card in a corner.
- **Test every path headless** with Playwright (`--disable-audio-output`; run at most two at once or the machine
  stalls and timers drift); give every spoken line a fallback timeout so a stalled audio clock can't hang a run.
- **Then have a vision model critique stills of every beat as an investor would** (`look.py`), and fix what it
  finds that you can see yourself; it also invents problems, so check each claim on the frame.
