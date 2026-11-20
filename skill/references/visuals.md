# Keyframes, references and video clips

## Consistency comes from reference images

Models don't remember what they drew last time. Every recurring character, place, vehicle or prop gets a
**reference sheet** before any keyframe is made:

```bash
vg image "Reference sheet: <description>. Front view and three-quarter view side by side on a plain light-grey background, identical subject in both views, even studio light, <style line>" -o refs/hero --aspect 16:9
vg image "Location plate: <description>, wide establishing view, <time of day>, <style line>" -o refs/place
```

Look at each sheet, regenerate until it's right, then attach it to **every** keyframe that features that
subject (`--ref refs/hero.png --ref refs/place.png`). Keep a style line (palette, medium, lens, light, grain)
in `brief.md` and paste it into every prompt verbatim. For other ways to use references (a style from a
document, a person's likeness), see `references/images.md`.

## Keyframes

One per shot, at the project aspect ratio, described like a film still: subject, action caught mid-moment,
framing, camera height, lens feel, light, style line. End with "No text, no letters, no logos".

```bash
vg image @prompts/kf-s03.txt -o kf/s03 --aspect 16:9 --ref refs/hero.png --ref refs/place.png
```

`google/gemini-3-pro-image` (the default, about $0.14) keeps subjects consistent from references and edits
well. Look at every keyframe before moving on: the keyframe becomes the clip's first frame, so a flaw here is a
flaw in the whole shot. `vg image` warns about black bars baked into a frame; regenerate those.

## Video models

`vg models` prints the live list with durations, sizes and prices.

| | Veo 3.1 (`google/veo-3.1`, `-fast`, `-lite`) | Seedance 2.5 (`bytedance/seedance-2.5`) |
|---|---|---|
| Best at | Realism, faces, detailed close-ups, native sound | Motion: first-person flights, splashes, physics, fast camera moves |
| Durations | 4, 6, 8 s | 4–30 s |
| Sizes | 720p, 1080p, 4K; 16:9 and 9:16 | 480p, 720p (scaled up by `vg assemble`) |
| Frames | first and last | first and last |
| Price | $0.20/s at 1080p silent; fast $0.10/s; lite $0.05/s | about $0.23/s at 720p |

- Seedance where motion is the point; Veo where a face or a fine texture is.
- Veo is often refused with "the service is currently experiencing high load". Refused jobs aren't billed.
  `vg video` retries twice by default; add `--fallback bytedance/seedance-2.5` to switch model when Veo stays
  busy (it drops to 720p automatically).
- Test a prompt on `veo-3.1-fast` or `-lite` at 720p, then render the keeper on the full model.
- Square or 4:5 from Veo: generate 16:9 or 9:16 and let `fit: cover` crop it; frame the keyframe for the crop.
- Leave `--no-audio` (the default) unless the shot needs its own sound; it halves the Veo price.
- Kling (through fal) is the other strong option for realistic motion from a still: `references/fal.md`.

## Prompting a clip

The keyframe already fixes the look, so the prompt is about **what changes**: the action, the camera move and
the pace. One action per clip.

> The drop falls and smashes into the soil, a crown splash erupting outward, soil grains and droplets flying
> and sparkling in the hard backlight. Extreme slow motion. Static camera.

> FPV rocketing straight up the glowing green tube at tremendous speed, the ribbed walls streaking past, the
> bright opening above rushing closer, a slight barrel roll.

Name camera moves plainly: static, slow push-in, pull-back, pan left, tilt up, tracking alongside, orbit,
handheld, crane up, FPV dive. Say the speed. Don't ask for a cut inside a clip.

```bash
vg video @prompts/v-s03.txt -o clips/s03.mp4 --first kf/s03.png --duration 4 --fallback bytedance/seedance-2.5
vg video @prompts/v-s05.txt -o clips/s05.mp4 --model bytedance/seedance-2.5 --first kf/s05.png --last kf/s05-end.png --duration 8 --resolution 720p
```

A first and last frame make a transition inside one clip (inside a leaf → bursting out into the sky); you can
then use two different stretches of the same clip in two places in the edit (`in:` and `dur:` in `edit.yaml`).

## Using what comes back

Make a timestamped contact sheet of each clip (`references/critic.md`) and find the best stretch: generated
clips often have a slow start, a dark middle or a white flash; use `in:` to start where it gets good. A clip
shorter than its slot holds its last frame. Regenerate rather than paper over a warped hand or a face that
changes.
