---
name: ove
description: "OVE (Ops Video Editor). Make finished media with AI and code: narrated videos and explainers, action shorts, product and prototype demo videos, still images (posters, slide art, characters, photo edits, film-still or doll versions of a person from their own photos), brand directions with logos and mockups, voice-over, music, sound effects, captions, and a quality check. Use when the user asks for a video, reel, trailer, animatic, image, illustration, poster, logo, mood board, brand look, voice-over, soundtrack, captions, or a check of a render, or mentions OVE."
---

# OVE: Ops Video Editor

OVE is a general-purpose production system: videos, images, interactive demos, brands and decks, about
anything. It grows: every project should leave it a little better (see "Growing OVE" below).

Two tools do the work:

- **`vg`**, a small CLI (installed with this skill; `vg --help`). It calls the models (OpenRouter for images,
  video, voice, transcription, music and review; fal.ai for Kling video, sound effects and more), and runs
  ffmpeg for cutting, mixing, captions and checks. `vg doctor` says what is installed and which keys are set.
- **Code you write in the project**: HTML/CSS rendered with `vg html` for any text, layout or UI that must be
  exact, Manim for diagrams and kinetic type, ffmpeg for anything `vg` doesn't wrap.

Image and video models are good at pictures and bad at lettering, counting, left and right, and holding a
detail steady. Generate what a camera would see; draw what must be exact.

## First run, and whenever something is missing

Run `vg doctor`. If `vg` isn't found or anything is missing, set it up for the person with as little work for
them as possible:

1. Install: if `~/ove` doesn't exist, `git clone https://github.com/joshuabouchard-netizen/ove ~/ove`; then
   run `~/ove/install.sh` (no admin rights; installs every tool and links this skill). Re-running is safe.
2. Keys: the person makes two accounts; you do the rest. Run `vg keys open openrouter`, which opens the pages
   to add credit, turn off Zero Data Retention and create a key; tell them in two short lines what to click,
   suggest a weekly limit on the key, and ask them to copy the key and say "done". Then `vg keys paste
   openrouter` saves it from the clipboard (only the last 4 characters are ever shown). Same for `fal`.
   Never ask anyone to paste a key into the chat, and never type a password or card number yourself.
3. `vg keys status`, `vg doctor`, `vg spend`. Then save the person's standing rules to memory: their spending
   cap, "report every paid step", and anything private (whose voices may be cloned, what stays internal).
4. Offer a first small project so they see it work: "a 20-second 9:16 explainer about anything you like".

Optional connections, only when a project needs them: Claude in Chrome (account dashboards, Figma, playtesting
in the person's own browser), the Claude app's connectors (Slack, Google Drive, Notion, Linear, Figma, Gmail:
ask before searching company sources), Cloudflare for private shareable demos (`tools/gate/README.md`).

## Money

Every model call costs the user money. Before a paid step, say what it will cost (`references/costs.md` has the
prices and how to estimate); after it, say what it cost and the running total. `vg spend` shows OpenRouter's own
figures for the key and the account balance, plus a local ledger that includes fal jobs. Ask before anything
that would take the account near zero or past a cap the user has set.

## Pick the job

| The user wants | Read |
|---|---|
| A narrated video, explainer, short or trailer | the pipeline below, then the references it names |
| A still: poster, slide art, character, a photo edit, a person restyled as a character or a doll | `references/images.md` |
| Text, a layout, a title card, speech bubbles, lower-thirds, a UI over generated art | `references/layout.md` |
| A logo, brand directions, mockups, a brand book | `references/brand.md` |
| A product, app or prototype demo video; an ambient or generative piece | `references/prototypes.md` |
| Diagrams, charts, kinetic type, animated explainers | `references/motion-graphics.md` |
| Kling or another fal.ai model; sound effects from a generator | `references/fal.md` |
| Music, sound effects, mixing, levels | `references/audio.md` |
| A check of a render, or of a mix | `references/critic.md` |
| Something failed | `references/troubleshooting.md` |
| First run, keys, install problems | `references/setup.md` |

## The video pipeline

**brief → script → references → keyframes → voice → animatic → clips and graphics → music and effects →
assemble → captions → critic → deliver.** Each arrow is a checkpoint where changing course is cheaper than at
the next one. The expensive step, video clips, comes after the user has seen the words and the pictures.

0. **Brief.** You need the subject and audience, the aspect ratio (16:9, 9:16, 1:1, 4:5), the length, and the
   style (look, voice, music mood). Ask for what's missing in one message. Make a project folder at
   `~/videos/<yyyy-mm-dd>-<slug>/` with `kf/ refs/ clips/ vo/ music/ sfx/ graphics/ out/` and write `brief.md`.
1. **Script and shot list.** `references/script.md`. Send the script, the shot list and a cost estimate, and
   wait for a yes before spending more than a few cents.
2. **References and keyframes.** `references/visuals.md`. A reference sheet for every recurring character,
   place and prop first, then one keyframe per shot with those references attached.
3. **Voice-over.** `references/voice.md`. One call per line or scene with its own delivery note; check each
   take by transcribing it; the measured durations are the real shot lengths.
4. **Animatic.** Build `edit.yaml` (`vg assemble --schema`) with each keyframe as a still timed to its line
   and render `vg assemble edit.yaml -o out/animatic.mp4`. The whole film at almost no cost; fix pacing here.
5. **Clips, graphics, footage.** Replace stills shot by shot: AI clips (`references/visuals.md`, `references/fal.md`),
   motion graphics (`references/motion-graphics.md`), Creative Commons footage (`references/footage.md`).
   Look at a contact sheet of every clip before accepting it.
6. **Music and effects.** `references/audio.md`.
7. **Assemble and caption.**
   ```bash
   vg assemble edit.yaml -o out/draft.mp4 --no-captions
   vg words edit.yaml -o out/words.json        # caption timings from each voice file, placed on the timeline
   vg captions out/words.json --video out/draft.mp4 -o captions.ass
   vg assemble edit.yaml -o out/final.mp4      # edit.yaml names captions.ass
   ```
   Fix misheard words in `out/words.json` before rendering captions.
8. **Critic.** `references/critic.md`: `vg critic`, `vg mixcheck`, and your own eyes on the contact sheets.
9. **Deliver.** The final render, the `.srt`, credits for any footage, and the total spend.

`examples/the-climb/` is a complete 45 s short to copy from (script, prompts, Manim scenes, edit list, sound
design); `examples/brand/` has the brand mockup and board templates; `tools/` has the prototype helpers
(page-to-video capture, green-screen phone fit, review pages, PowerPoint autoplay, audible haptics, a
password gate for sharing).

## Start every project with a design doc

Before spending anything, write `brief.md` in the project folder and get a yes: **What** (one paragraph:
deliverable, audience, length, how it will be shown), **Look and sound** (in words), **Beats** (in order, each
with timing and the exact on-screen words), **Branches** (a table, if the viewer chooses), **Production** (every
asset to generate, count × price, an estimate inside the cap) and **Open items** (what only the person can
supply). Keep `spend.md` (each paid step and a running total) and `PROGRESS.md` (built, tested, open) beside
it. Every note the person gives updates the doc first, then the build. Save each good state as a named,
standalone version (V1.0, V1.1) and never overwrite one. A new session starts by reading these three files.

## Growing OVE

OVE lives in `~/ove`, a git repository: the skill is `~/ove/skill` (linked into Claude's skills folder) and
the tool is `~/ove/cli` (installed in editable mode). Improving them takes effect at once. At the end of
every project, and whenever something failed and was fixed:

- Put the lesson where the next project will find it: a failure and its fix in
  `references/troubleshooting.md`, a prompt that worked in the reference for that kind of job, a new kind of
  job as a new reference plus a row in "Pick the job" above. Write the lesson, not the story: what to do,
  what to avoid, the numbers that worked.
- When a tool fell short, fix `vg` in `~/ove/cli` or add a script to `tools/`, add an offline test in
  `cli/tests/`, and run `cd ~/ove/cli && uv run --extra test pytest tests -q`.
- Note it in `CHANGELOG.md` and commit (`cd ~/ove && git add -A && git commit -m "..."`). `.env` and the
  spend ledger are git-ignored; never commit a key, a person's voice, or anything private.
- Updates from the original: `cd ~/ove && git pull` merges them with local improvements.

## People, voices and rights

Make a likeness, a doll or a cloned voice of a real person only from material they supplied or agreed to, and
keep it to the use they agreed to. Don't put real brands' logos on generated products; invent packaging. Label
generated pictures honestly ("the height of the tallest tree", not a named tree that wasn't filmed). Credit
Creative Commons footage (`references/footage.md`).

## Habits that save money and time

- Look at every generated image and clip yourself before building on it. A flaw in a keyframe is a flaw in
  every clip made from it.
- Never let the script, the voice and the edit drift apart: when a line changes, re-voice it, re-measure,
  update `edit.yaml`, in that order.
- Run paid jobs a few at a time (about six images, three or four videos): more at once and providers start
  refusing. Run them in background shells, each with its own log, and check every exit code.
- Video models ignore negative prompts and count badly, and image models garble text and confuse left and
  right. Avoid shots whose meaning depends on an exact count, readable text or which side something is on;
  draw those, or fix them in a second pass (`references/images.md` has the tricks).
- In zsh, a list of flags in one variable stays one argument (`$FACE` → `"--ref a --ref b"`), and `$x:a` or
  `$x:l` are path and case modifiers. Use arrays (`refs=(--ref a.png --ref b.png)`, then `"${refs[@]}"`) and
  write `${x}` before a colon.
