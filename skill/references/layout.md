# Exact text and layouts: HTML over generated art

Image and video models garble words, so anything that must read exactly is set as live type in HTML/CSS and
rendered with headless Chrome:

```bash
vg html page.html -o out/slide.png --size 1920x1080 --scale 2     # a crisp 3840x2160 render
ffmpeg -i out/slide.png -vf scale=1920:1080:flags=lanczos out/slide-1080.png
```

`vg html` waits 4 s (`--wait`) for Google Fonts and scripts to settle and uses a throwaway Chrome profile.
Rendering at `--scale 2` and downscaling gives cleaner type than rendering at size.

## A page that composes art and words

A single HTML file per deliverable, at the exact pixel size of the output:

- `html, body { margin: 0; width: 1920px; height: 1080px; background: #f3f2ee; }` with the background set to
  the colour the result will sit on (sample it from the slide or page; see `references/images.md`).
- The generated art as an absolutely positioned `<img>`, scaled and cropped with a wrapper `div` of fixed size
  and `overflow: hidden`; crop off empty sky by shifting the image up inside it.
- A soft mask on the art's edges hides any seam between the art's paper and the page:
  `-webkit-mask-image: linear-gradient(to right, transparent 0, #000 40px, #000 calc(100% - 40px), transparent 100%)`,
  or a radial gradient for a logo mark.
- Text in a Google Font linked in `<head>`; slide-scale sizes are about 44–54 px at 1080p for body lines.
- Graphics (speech bubbles, arrows, underlines, counters) as inline SVG, so their strokes match the art's line
  weight (5–6 px black ink for bold line art).

## Placing things on the art

Guessing coordinates wastes renders. Render the art once with a labelled grid over it (a CSS
`linear-gradient` grid every 100 px plus small coordinate labels), look at it, and read off where each head,
edge and empty patch is. Keep the art's source coordinates in the page's script and convert with the same scale
and offset the page uses, so moving or resizing the art moves everything placed on it. A `#debug` URL hash that
draws dots on the targets helps check a layout.

Speech bubbles that read well: a rounded box with a 6 px ink outline, white fill, a short tail (about 120 px at
most) that points at the speaker and stops short of them, the text centred inside with even padding. Pick
which character says which line by pose (the one alone on the path says "stepping outside my comfort zone"),
and lay the bubbles out so no tail crosses another bubble, a face or a busy part of the art. Leave the corner
where a slide puts its own title empty.

## Overlays on video

Titles, counters, lower-thirds and UI that sit over a generated clip are rendered separately with a transparent
background (Manim with `-t --format mov`, or an HTML page captured frame by frame with a transparent
background) and composited:

```bash
vg overlay clips/redwood.mp4 graphics/counter.mov -o clips/redwood-c.mp4 --dur 4.5
```

A base clip shorter than `--dur` holds its last frame. Keep overlay text clear of where captions sit (the
bottom eighth of the frame).

## Delivering a slide image

A full-slide image for Google Slides or Keynote: 16:9 PNG on the slide's own background colour, with the slide's
title area left empty. The user drags it in, stretches it to the slide, and sends it to the back (Arrange →
Order → Send to back) so the slide's live title sits on top. Send the file itself; putting it in a Doc or Drive
means uploading the whole file through the chat and is slow.
