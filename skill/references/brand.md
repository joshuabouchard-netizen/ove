# Brand directions: logos, mood photography, mockups, boards

How to take a business from "we need a look" to a set of named directions someone can choose between, with
exact type on every asset. The rule that makes it work: **money goes on imagery only**. The model makes marks
and photographs; every letter, swatch label, card and poster is HTML rendered with headless Chrome, for free,
and is spelled right.

Templates: `examples/brand/mockups.html` (one file renders lockups, type specimens, business cards, social
posts and posters for any direction) and `examples/brand/board.html` (a side-by-side comparison board).

## 1. Diverge: six directions

Give each direction a name, a craft tradition, a palette (names and hex) and a type pairing. Spread them
wide: a classic one, a minimal one, a bold editorial one, a hand-made one, a luxurious one, a strange one.
Then one prompt file per asset: `prompts/<n>-logo.txt` (1:1) and `prompts/<n>-mood.txt` (16:9).

**Logo prompt** = a shared prefix + one `Style:` sentence + the no-text suffix:

> A professional brand logo mark for a premium {BUSINESS TYPE}, centered on a plain flat background with
> generous empty margin, vector-like, crisp, balanced and symmetrical, elegant and refined, not cartoonish,
> not cute, no clip-art feel, no human face.
> Style: fine-line copperplate engraving, like a 19th-century botanical plate, antique gold ink on parchment.
> Absolutely no text, no letters, no words, no numbers, no watermark anywhere in the image.

Style sentences that gave classy results: "single continuous thin monoline, uniform line weight, one accent
leaf"; "high-end linocut cleaned up as a vector, carved in negative space"; "Japanese sumi-e ink brush, few
confident strokes"; "metallic gold foil on deep midnight navy, thin double ring, art-deco precision";
"concentric topographic contour lines like tree growth rings"; "cyanotype sun-print on textured watercolour
paper, Prussian blue".

**Mood photograph prompt**: "Editorial photograph of {room, props, light}. Palette: a, b, c, d. Quiet,
timeless, refined. Shallow depth of field." plus "Only hands are visible, no faces" when people appear (no
uncanny faces, no likeness questions) and the no-text suffix with "no logos". A shared base sentence with a
per-direction `Setting:` gives a matching series across directions.

When the first round reads "safe" or dated, push it: "contemporary fashion-editorial photograph, direct
on-camera flash, crisp hard shadows, saturated chartreuse backdrop, sculptural plinth, medium format"; "minimal
overhead still life, objects arranged in a precise dotted pattern forming {shape}, lots of negative space".
Bolder type helps as much as bolder pictures.

```bash
# six at a time (more trips OpenRouter's in-flight limit); a log per image, the exit code echoed
for f in prompts/*.txt; do n=$(basename $f .txt); case $n in *logo) a=1:1;; *) a=16:9;; esac; echo "$n $a"; done \
 | xargs -P 6 -n 2 sh -c 'vg image "@prompts/$0.txt" -o img/$0.png --aspect $1 > img/$0.log 2>&1; echo "$0 exit $?"'
grep -L "cost" img/*.log        # the ones that failed; re-run them one at a time
```

Twelve images (six marks, six photographs) cost about $1.60.

## 2. Look, then lay it out

Make thumbnails and a contact sheet and look at every image before anyone else does:

```bash
ffmpeg -y -loglevel error -i t/1.png -i t/2.png -i t/3.png -i t/4.png -i t/5.png -i t/6.png \
  -filter_complex "[0]scale=-1:400,setsar=1[a];[1]scale=-1:400,setsar=1[b];[2]scale=-1:400,setsar=1[c];[3]scale=-1:400,setsar=1[d];[4]scale=-1:400,setsar=1[e];[5]scale=-1:400,setsar=1[f];[a][b][c]hstack=3[r1];[d][e][f]hstack=3[r2];[r1][r2]vstack" sheet.png
```

(`hstack` needs equal heights and `vstack` equal widths: scale first.)

**Blending a raster mark into a layout without cutting it out**: sample the mark's background colour and use
that exact hex as the HTML ground, then feather the square's edge with a radial mask.

```bash
ffmpeg -loglevel error -i img/1-logo.png -vf "crop=40:40:30:30,scale=1:1:flags=area" -f rawvideo -pix_fmt rgb24 - | xxd -p   # e.g. faf0d9
```
```css
.mark { object-fit: cover; -webkit-mask-image: radial-gradient(circle, #000 58%, transparent 71%); mask-image: radial-gradient(circle, #000 58%, transparent 71%); }
```

Re-sample whenever a mark is regenerated; the ground shifts a little each time.

**The mockup engine** (`examples/brand/mockups.html`): one tokens object per direction (name, tagline, ground,
ink, accent, fonts, mark and photo paths) and one renderer per asset, chosen by the URL:

| `?a=` | Size | What |
|---|---|---|
| `lockup` | 1600×900 | mark + wordmark + tagline |
| `type` | 1600×900 | type specimen: "Aa", font names, tagline, body sample |
| `cardfront`, `cardback` | 1050×600 | business card, 3.5×2 in at 300 dpi |
| `social` | 1080×1350 | a 4:5 post: photo, tagline, small lockup |
| `poster` | 1240×1754 | A-series poster: photo, centred lockup, details |

```bash
for d in 1 2 3 4 5 6; do for a in lockup type cardfront cardback social poster; do
  case $a in card*) s=1050x600;; social) s=1080x1350;; poster) s=1240x1754;; *) s=1600x900;; esac
  vg html "examples/brand/mockups.html?d=$d&a=$a" -o mockups/$d-$a.png --size $s &
done; wait; done
```

Change a contact line once in the tokens and re-render; nothing is re-generated.

**The board** (`examples/brand/board.html`): a 3×2 grid, one card per direction: name, mark + live-type
wordmark, a photo strip, swatches with names and hex, and short Style / Feel / Type notes plus a **Watch:**
line naming each direction's risk. Render it at 2400 px wide and send it with a table and one question:
"which, or which mix?".

## 3. Converge

- **Redraw a weak mark** with the old one as a reference: "Redraw this logo mark more refined. Keep {what
  works}. Change {what doesn't}." This fixed two marks out of three.
- **When the reference carries the flaw back** (toe dots kept returning on a foot mark), drop the reference and
  describe the geometry outright, with negatives in capitals and hex colours: "one continuous sole shape, toes
  merged into a rounded top edge, NO toes and NO toe dots at all, terracotta (#A84A2E) on sand (#DEB679)".
- **Never ask for seals, stamps or badges**: the model fills them with invented characters even when told not
  to. Draw them in SVG if they're wanted.
- **Feet and bodies** in marks: separate toe dots read as a cute footprint icon.

## 4. Make it scale

A generated mark is a 1024 px raster with fine detail that fills in at favicon size. Say so in the notes,
and offer a code-drawn version for the small sizes:

- **Letter substitution**: a word set in a heavy grotesque with two letters swapped for SVG shapes (two
  mirrored foot soles as the "oo"), each about 0.62 em tall and sitting just below the baseline.
- **Halftone fill**: build a `Path2D` of the shape, keep grid points inside it with `ctx.isPointInPath`, size
  each dot from a few Gaussians (darker where the weight is), and emit `<circle>`s into an SVG.
- **Procedural growth**: a seeded random generator and a recursive branching function that emits tapered
  curves. The seed keeps it identical on every render.

Iterate a drawn mark by rendering, cropping and looking: a toe-less sole "looked like a vase", toes as
ovals "looked like a bird", one dot per toe with the big toe in the accent colour read as a foot. Crop small
details before showing anyone (`sips -c 560 420 --cropOffset 150 280 in.png --out crop.png` on a Mac, or
ffmpeg's `crop`).

## 5. Present it

A deck of three slides per direction works: a **hero** (a full-bleed photo with a bottom gradient, a small
tracked kicker "Direction 01", a big serif title, one sentence), **identity** (lockup, type specimen, four
swatches with names and hex), and **in use** (business cards, a social post, a poster). Add a cover, "what the
brand needs to do", an overview of every lockup, and the questions for the person deciding. Build it as HTML
slides (`references/layout.md`) or PowerPoint (`references/prototypes.md`), using JPEGs (photos at q82 and 1920
px, mockups at q85 and 1600 px) to keep it light.

Cost of a whole exploration of this kind: about 27 kept images for about $3.60; every layout render free.
