# Still images: posters, slide art, characters, edits

`vg image` makes one image per call (about $0.14 with `google/gemini-3-pro-image`, the default). Reference
images (`--ref`, up to 14) carry a style, a character, a face or a product into the new image; the prompt says
what to make of them.

```bash
vg image @prompt.txt -o out/scene --aspect 16:9 --ref refs/style.png --ref refs/face-front.jpg
```

Sizes come back at about 1 megapixel: 1376×768 (16:9), 1024×1024 (1:1), 928×1152 (4:5), 768×1376 (9:16).
`vg image` warns when black bars are baked into the frame (a 4:3 picture padded to 16:9); regenerate those
asking for "a full-bleed widescreen frame filled edge to edge, no black borders", or the bars follow into
every clip made from it. `vg borders kf/*.png` checks a folder.

Two takes per prompt, run in parallel, cost little and usually give one clearly better; pick, say why, and
keep the other in the folder.

## Matching an existing style

To make new art in the style of something the user has (a document's illustration, a packet cover, a brand
pattern): render the page (`pdftoppm -f 1 -l 1 -r 300 -jpeg doc.pdf page`), crop just the art with ffmpeg
(`-vf crop=w:h:x:y`), and pass the crop as a reference: "a brand-new scene in the exact art style of the
reference: bold slightly wobbly ink outlines, flat fills, grey halftone dot shading". Describe the style in
words as well as attaching it; the model leans on both. Treat the reference as inspiration for style and
characters, not a layout to copy.

## A person, from their own photos

Only from photos of the person asking, or of someone who has agreed to it. Pick four or five clear, well-lit
shots from different angles (a front headshot, a three-quarter view, a smile), leave out any photo with another
person in it, and crop to the head and shoulders. Then describe the face to keep ("keep the face exactly: face
shape, skin tone and texture, eye colour, facial hair, same nose and brow", naming what you see) and everything to change.

- **Film-still look**: "an ultra-photorealistic cinematic film still, indistinguishable from a real frame of a
  big-budget live-action film … real skin texture with pores, real fabric and wig fibres, shallow depth of
  field, 35mm, subtle grain … an actual photograph of a real person on a real set, not an illustration or CGI".
  Attach stills from the film or character as style references after the face photos.
- **Doll or figure**: "a photorealistic product photograph of a collectible fashion doll of the person in the
  reference photos … glossy moulded vinyl, rooted hair fibres, real fabric weave, macro product lighting".
- **In its box, as if just bought**: "a casual smartphone photo of the doll still in its box on a kitchen
  counter in window light, reflections on the plastic window, a price sticker on the corner". Invent the box's
  wording (a name plus "Collector Edition"); never reproduce a real toy brand's logo or trade dress. Short box
  text renders cleanly; check every letter.

## Editing an image

Pass the image as the first reference and say what stays before what changes: "Edit the first image. Keep
everything exactly as it is: the face, the pose, the background, the lighting, the framing, any packaging and
text. Change only the hair: …". Give the change its own reference (a close-up crop of the hair or the makeup you
want) and describe it precisely. One change per edit holds best; several at once drift.

When an edit must add small things (a tote bag on two characters, a plane in the sky), say where in plain
spatial terms and keep everything else; ask for any added text to be short (a three-letter word printed on a tote rendered fine; sentences
won't).

## Left and right

Image models confuse left and right, and an edit that says "the left eye" often changes the other one. Two ways
through:

- **Anchor to a feature, not a side**: "move the zig-zag so it sits directly above the eye that has the black
  ring". The model finds features far more reliably than sides.
- **Mirror the image** (`ffmpeg -i in.png -vf hflip out.png`) when the only problem is the side something is
  on and the image has no text. Then fix anything else that should stay put with a feature-anchored edit.

## Fixing things after the model

- **Black bars**: regenerate (above); cropping loses the aspect.
- **A detail that keeps coming back** (a logo flaw, an extra limb): drop the reference that carries it and
  describe the shape exactly instead, with hex colours and what must not be there.
- **Seals, stamps and signs** come back with invented lettering, often fake characters in another script; avoid
  asking for them, or ask for a plain blank shape and add text in HTML.
- **Removing an element** from a plain background (a plane over sky): crop it out to keep it, then paint the
  patch with the background colour (`drawbox=x:y:w:h:color=0xF3F2EE@1:t=fill`).
- **Matching a background** to a page or slide: sample a patch of each with ffmpeg (`crop=20:20:x:y,scale=1:1`
  piped to `xxd -p` gives the hex), then multiply each channel to match
  (`colorchannelmixer=rr=1.0125:gg=1.0254:bb=1.0578`) and cap at the target
  (`lutrgb=r='min(val,243)':g='min(val,242)':b='min(val,238)'`). A soft edge mask in the layout hides any
  remaining seam (`references/layout.md`).

## Words in images

Keep generated images free of text ("No text, no letters, no logos anywhere" at the end of the prompt) and set
every word in HTML on top (`references/layout.md`). The exceptions that render reliably are short, bold words
on a clear surface: a two-word box title, a three-letter brand on a bag. Read every letter of anything you
keep.
