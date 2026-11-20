# fal.ai: Kling video, ElevenLabs sound effects, voice cloning, cheaper image edits

fal.ai hosts hundreds of media models behind one key and one queue API. Use it for what OpenRouter doesn't
carry: Kling video, realistic sound effects and ambience, voice cloning and expressive speech, and cheaper
4K image edits. Everything goes through `vg fal`; the key is `FAL_KEY` in `$VG_HOME/.env` (see
`references/setup.md`) and is never printed.

```bash
vg fal check                                   # is a key configured (never shows it)
vg fal schema fal-ai/elevenlabs/sound-effects/v2   # the input fields, types, defaults (no key needed, free)
vg fal price  fal-ai/kling-video/v2.5-turbo/pro/image-to-video   # fal's published unit price (needs the key)
vg fal run MODEL -o out.mp4 [-p text|@file] [--prompt-key text] [--image a.png [--image b.png]] \
    [-f field=local.wav] [-a key=json] [-s key=string]
```

## Before every paid call

1. **Read the schema.** Field names differ between models, and a wrong name is an HTTP 422 (not billed):
   `prompt` vs `text`, `image_url` vs `image_urls` (a list), `tail_image_url` vs `end_image_url`, and some
   numbers are strings (Kling's `duration` is `"5"` or `"10"`). `vg fal schema` prints them.
2. **Price it.** `vg fal price` (the pricing API answers only with a key; without one it says "not
   published" for everything). Multiply by length or count, add about 50% for retakes, and tell the person
   paying before you run it.
3. **Record it.** fal returns no charge per call, so `vg` estimates one from the unit price (per second of
   output, or per image) and logs it in the local ledger; `vg spend` adds it up. Prices per character or per
   compute-second can't be estimated from the output and show as unreported. fal.ai/dashboard/usage is the
   bill of record.

## How `vg fal run` maps flags to the request

| Flag | Goes into | Notes |
|---|---|---|
| `-p "text"` or `-p @file.txt` | `prompt` | `--prompt-key text` for models that want `text` |
| `--image a.png` | `image_url` | `--image-key` renames it |
| second `--image b.png` | `tail_image_url` | `--end-image-key end_image_url` for Veo and others |
| `--image-key image_urls` | a list of every `--image` | nano-banana / Gemini edit endpoints |
| `-f audio_url=ref.wav` | that field, as a data URI | voice references, source audio, extra images |
| `-a key=value` | that field, JSON-parsed | `10` → number, `true` → boolean, `'["a","b"]'` → list |
| `-s key=value` | that field, always a string | `-s duration=10` for Kling |

Local files go up inline as data URIs. That's fine for stills and short audio; shrink 4K stills first
(`ffmpeg -i k1.jpg -vf scale=1920:-1 -q:v 2 k1_small.jpg`), and give a long video by URL instead.

Each run writes `<out>.fal-job.json` (request id, status URL) and `<out>.fal-result.json` (the raw result)
next to the output and downloads every media file in the result (`out.mp4`, `out-2.mp4`, …). If a job times
out locally it may still finish and bill: the status URL in the job file still answers. Don't share those
JSON files; the URLs in them point at your generated media.

## Tested endpoints and what worked

Prices are fal's published rates when tested (late 2026); check with `vg fal price` before you rely on one.

### Video

| Endpoint | Fields that worked | Price |
|---|---|---|
| `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | `prompt`, `image_url` (start), `tail_image_url` (end), `duration` "5"/"10", `negative_prompt` | $0.07/s |
| `fal-ai/kling-video/v2.5-turbo/pro/text-to-video` | `prompt`, `aspect_ratio` "16:9"/"9:16"/"1:1", `duration`, `negative_prompt` | $0.07/s |
| `fal-ai/kling-video/v3/pro/image-to-video` | (priced, not run) | $0.14/s |
| `fal-ai/veo3.1/fast/first-last-frame-to-video` | (priced, not run) | $0.15/s |

```bash
vg fal run fal-ai/kling-video/v2.5-turbo/pro/image-to-video -o clips/s02.mp4 \
  -p @prompts/v-s02.txt --image kf/s02-start.jpg --image kf/s02-end.jpg -s duration=10 \
  -a negative_prompt='"face, eyes, mouth, text, blur, distortion, low quality"'
```

- **Kling 2.5 turbo pro vs Veo 3.1 fast**: Kling is cheaper ($0.07/s vs $0.10/s), takes 5 or 10 s, keeps an
  illustrated or painterly style well, and lands on a given end frame. Veo is better at photoreal faces and
  native sound. Both are good at first-and-last-frame shots.
- `negative_prompt` matters with Kling. A faint ring inside a flower's centre became a face; the fix was to
  retouch the keyframe and add "never has a face: plain round disc" to the prompt plus
  `face, eyes, mouth, smile, facial features` to the negative prompt.
- Text-to-video plates (fireflies, embers, ink, aurora) are literal: "fireflies" gave insects. Ask for "softly
  out of focus warm bokeh … no flames leaping … no people", and expect about one bad take in two.
  Contact-sheet every take before using it (`references/critic.md`).

### Sound effects and ambience

| Endpoint | Fields | Price |
|---|---|---|
| `fal-ai/elevenlabs/sound-effects/v2` | **`text`** (not `prompt`), `duration_seconds` 0.5–22, `prompt_influence` 0–1, `loop` | $0.002/s |

```bash
vg fal run fal-ai/elevenlabs/sound-effects/v2 -o sfx/rain.mp3 --prompt-key text \
  -p "steady soft rain on a window at night, a few drips, no music, no thunder" -a duration_seconds=10 -a prompt_influence=0.5
```

- A 22 s ambience bed costs about $0.04. For one-shots (a struck bowl, a kalimba pluck, a door), 3–6 s with
  `prompt_influence` 0.7 follows the words most closely; make 3–6 candidates and choose.
- **A seamless loop from two takes**: crossfade take A into take B over 3 s, cut the first 3 s, crossfade the
  tail back into the head. Two 22 s takes gave a 38 s loop. Or ask for `loop: true`.
- A music model (Lyria) can't make ambience: rain, forest or shore always came back with a beat or a pad.
  Use this endpoint, or a real field recording. An LLM listening check ("Is there ANY music? YES or NO") is a
  quick test (`references/audio.md`).
- Rated by ear and by a listening model: city rain and rainforest were good, a shoreline never was; a real
  recording beats it for waves.

### Voices

Only clone a voice with the speaker's explicit permission, and keep cloned voices for the use they agreed
to. Voice IDs are tied to your fal account; don't share them.

| Endpoint | Fields | Price | Use |
|---|---|---|---|
| `fal-ai/minimax/voice-clone` | `audio_url` (40–80 s of clean speech), `noise_reduction`, `need_volume_normalization`, `accuracy` 0.8, `model` "speech-02-hd", `text` (a preview line) | $1.50 per clone | Returns `custom_voice_id`; save it |
| `fal-ai/minimax/speech-02-hd` | `text`, `voice_setting: {voice_id, speed, vol, pitch, emotion}`, `output_format` "url", `language_boost` | $0.10 / 1000 chars | Lines in the cloned voice |
| `fal-ai/elevenlabs/tts/eleven-v3` | `text` with bracket directions (`[sighs]`, `[quietly]`), `voice` (a stock name), `stability` 0.3 | $0.10 / 1000 chars | The most expressive performance |
| `resemble-ai/chatterboxhd/speech-to-speech` | `source_audio_url`, `target_voice_audio_url`, `high_quality_audio` | small | Turns a performance into a target voice |
| `fal-ai/chatterbox/text-to-speech` | `text`, `audio_url` (reference), `exaggeration` 0.4, `cfg` 0.5 | $0.025 / 1000 chars | Quick zero-shot clone |
| `fal-ai/vibevoice/7b` | `script`, `speakers` | | Very slow (4 short lines took over 10 minutes) |

```bash
vg fal run fal-ai/minimax/voice-clone -o voice/clone.mp3 -f audio_url=voice/sample.wav \
  -a noise_reduction=true -a need_volume_normalization=true -a accuracy=0.8 -s model=speech-02-hd \
  -s text="Hi, this is a quick test of the cloned voice."
# custom_voice_id is in voice/clone.fal-result.json
vg fal run fal-ai/minimax/speech-02-hd -o voice/l01.mp3 --prompt-key text -p @lines/l01.txt \
  -a voice_setting='{"voice_id":"<custom_voice_id>","speed":1.0,"emotion":"neutral"}' -s output_format=url
```

What was learned about making a voice sound alive:

- **Identity**: MiniMax clones were closest to the real speaker (speaker-embedding similarity 0.86–0.95).
- **Delivery**: clone lines can sound flat. Widening the pitch contour afterwards didn't help. What won a blind
  listening test against a dozen alternatives was **ElevenLabs v3 performing the line** in a stock voice,
  with bracket directions and `stability` 0.3, then **ChatterboxHD speech-to-speech** converting it into the
  target voice (`-f source_audio_url=perf.mp3 -f target_voice_audio_url=real_sample.wav -a high_quality_audio=true`).
  Check the transcript afterwards: no bracket direction may be spoken aloud.
- **Check every line** by transcript (`vg transcribe`): "3:14 AM" was read as "three, fourteen"; writing
  "Three-fourteen a.m." fixed it. Check identity with a speaker-embedding comparison (resemblyzer:
  `uv run --with resemblyzer --with numpy --with "setuptools<70" python …`; same speaker ≥ 0.85, different
  speakers about 0.6). An LLM listener once heard one person in a different mood as two people.
- **In the room**: dry clones sound like a studio. A gentle EQ (cut about 320 Hz, lift 2.9 kHz and above 5.5
  kHz), a small synthetic room (wet 0.12–0.2) and `loudnorm=I=-19` made them sit in a scene.
- **Capture**: a reference recorded on a laptop mic with the browser's echo cancellation, noise suppression and
  auto-gain off (`getUserMedia({audio:{echoCancellation:false, noiseSuppression:false, autoGainControl:false}})`)
  was good enough. Split speakers by word timings, high-pass at 70 Hz, light denoise (`afftdn=nr=10`), 50–80 ms
  fades on each cut, 0.4 s gaps, `loudnorm=I=-18`.

### Images

| Endpoint | Fields | Price |
|---|---|---|
| `fal-ai/nano-banana-pro/edit` (the same model as OpenRouter's Gemini 3 Pro Image) | `prompt`, `image_urls` (a list), `resolution` "4K", `aspect_ratio`, `output_format` "png" | $0.15 per image |

```bash
vg fal run fal-ai/nano-banana-pro/edit -o kf/room-props.png --image-key image_urls --image kf/room_small.jpg \
  -p "Edit this photograph. Keep everything exactly as it is. The ONLY change: a closed laptop on the bedside table." \
  -s resolution=4K -s aspect_ratio=16:9 -s output_format=png
```

At 4K this is cheaper than OpenRouter ($0.15 vs about $0.24), for the same model. At 2K OpenRouter is
cheaper (about $0.14).

## When something fails

| Error | Fix |
|---|---|
| `submit HTTP 422 … "loc":["body","text"],"msg":"Field required"` | Wrong field name: `--prompt-key text`; check `vg fal schema` |
| `422` on `duration` | Kling wants a string: `-s duration=10` |
| `price: not published` for every model | `FAL_KEY` isn't set, or a typo in the id |
| `401` / `403` | Key wrong or revoked; make a new one at fal.ai/dashboard/keys |
| A safety-checker refusal | Reword; don't disable the checker |
| Very slow jobs | Some models queue for minutes; `--timeout` raises the wait; the job file has the status URL |
