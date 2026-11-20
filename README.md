# OVE (Ops Video Editor): a Claude Code system for making videos, images, interactive demos and brands with AI

Ask Claude Code for "a 45-second explainer about how plants drink", "brand directions for a small studio",
"a poster from these photos" or "a demo video of this app idea", and it follows a tested procedure: it writes
the script and a cost estimate first, then makes the pictures, the voice, the music and the graphics, puts
them together with ffmpeg, and checks the result before handing it over.

It has two parts:

- **`skill/`**: the instructions Claude follows (`SKILL.md`, a router to `references/`), plus `examples/`
  and `tools/`. It includes the rules for growing OVE: each project's lessons go back into it.
- **`cli/`**: `vg`, a small Python command-line tool that makes every model call and every ffmpeg render, logs
  what each call cost, and checks its own work.

## What it can make

| | How |
|---|---|
| Narrated explainers, shorts, trailers | script → keyframes → voice → animatic → clips and graphics → music and effects → captions → critic |
| Action cuts | fast FPV clips, slammed kinetic type with camera shake, synthesised whooshes and hits, a spliced score |
| Still images | posters, slide art in a given style, characters, photo edits, a person as a film still or a boxed doll from their own photos |
| Exact text over art | speech bubbles, titles, labels and layouts set in HTML and rendered by headless Chrome |
| Brand directions | six directions of logo marks and mood photography, then lockups, cards, posters and a comparison board, all with real type |
| Product and app demos | a web page rendered frame by frame to video, composited into a generated photo of a phone in a hand |
| Sound | voice-over (with transcript checks), music with Lyria, synthesised and generated sound effects, voice cloning (with consent) |
| Review and delivery | choice pages ("Love it / Maybe / Not"), PowerPoint decks whose videos autoplay, a password gate for private sharing |

## Models and cost

Everything runs on two accounts you pay for yourself:

- **OpenRouter** (required): Gemini 3 Pro Image (about $0.14 per image), Veo 3.1 and Seedance video ($0.10–0.23
  per second), Gemini TTS (cents), Whisper (cents), Lyria music ($0.04–0.08 a track), Gemini video review.
- **fal.ai** (optional): Kling 2.5 video ($0.07/s), ElevenLabs sound effects ($0.002/s), MiniMax voice
  cloning, cheaper 4K image edits.

A finished 45 s explainer with generated clips cost about $9; a round of brand directions about $2–4; anything
made of code (graphics, layouts, mockups, sound effects) is free. The skill quotes the cost before each paid
step and reports what it spent. `vg spend` shows your balance and a local ledger.

## Install

Give your Claude Code this one line, or run it yourself:

```bash
git clone https://github.com/joshuabouchard-netizen/ove ~/ove && ~/ove/install.sh
```

Then ask Claude to "set up OVE". It opens the two account pages (OpenRouter, required; fal.ai, recommended),
you copy each key once, and it saves and tests them with `vg keys paste`. Details: [INSTALL.md](INSTALL.md).

## Credits

Built on **video-gen** by Daniel Reid Cahn: the original skill and `vg` CLI (OpenRouter calls, the edit-list
renderer, captions, Creative Commons footage, the critic). This version adds fal.ai, the fixes and lessons from
several real projects, images, brands, prototypes, the examples and tools, and an offline test suite. See
[CHANGELOG.md](CHANGELOG.md).

Prices and model names were checked in November 2026; providers change both often. `vg models` and
`vg fal price` show current ones.
