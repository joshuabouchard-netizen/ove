# Example: "The Climb", a 45-second action explainer

A finished short about how water climbs a plant (no heart, no pump: evaporation pulls a chain of molecules up
the stem). It was the second version: the first was a calm narrated lecture over diagrams and came out
boring, so this one follows a single drop on a ride, with fast cuts, slammed type, a driving score and sound
design. It cost about $9 on OpenRouter; every graphic and sound effect was free.

| File | What it is |
|---|---|
| `script.md` | The brief: the idea, the narration (111 words at about 165 wpm), the shot list, sound, the cost estimate |
| `narration.txt` | The words as spoken, for `vg critic --script` |
| `prompts/kf-*.txt` | Keyframe prompts (one film still per shot) |
| `prompts/v-*.txt` | Clip prompts: only what moves, the camera and the pace |
| `prompts/music.txt` | The Lyria prompt (shape: hit, build, dropout, slam back, final hit) |
| `scenes.py` + `timing.json` | All the Manim graphics; scene lengths and hit times come from `timing.json` |
| `edit.yaml` | The final timeline: clips cut on word boundaries, six voice files, music, 15 sound effects with levels |

To rebuild it (about $9–12; quote it first):

```bash
mkdir -p climb && cd climb && cp -r <skill>/examples/the-climb/* .
# voice: audition on line 1, then one file per sentence group (w1..w6), each checked by transcript
vg tts "This drop of water is about to climb your plant, with no heart and no pump." -o vo/w1 --voice Puck --style "energetic, excited, a touch of trailer-narrator drama"
vg transcribe vo/w1.mp3 -o vo/w1.words.json   # word timings: cut on word boundaries, fill timing.json
# keyframes, then clips (Seedance for the FPV flights, Veo for close-ups)
vg image @prompts/kf-k1.txt -o kf/k1 --aspect 16:9
vg video @prompts/v-k1.txt -o clips/k1.mp4 --first kf/k1.png --duration 4 --fallback bytedance/seedance-2.5
# graphics: timing.json first (from the word timings), then
manim -qh --fps 30 -r 1920,1080 --format mp4 -o t03 scenes.py T03         # and T07 T09 T10 T11 T13 T14 T16
manim -qh --fps 30 -r 1920,1080 -t --format mov -o o08 scenes.py O08      # overlays: O01 (title), O08 (counter)
vg overlay clips/k6.mp4 media/videos/scenes/1080p30/o08.mov -o clips/k6c.mp4 --dur 4.5
# sound
vg music @prompts/music.txt -o music/bed --model google/lyria-3-pro-preview
for s in impact whoosh thud riser snap tick zap button; do vg sfx $s -o sfx/$s.wav; done
# put it together and check it
vg assemble edit.yaml -o out/draft.mp4 --no-captions
vg words edit.yaml -o out/words.json                       # per voice file, placed where the edit puts it
vg captions out/words.json --video out/draft.mp4 -o captions.ass
vg assemble edit.yaml -o out/the-climb.mp4
vg mixcheck edit.yaml -o out/mixcheck
vg critic out/the-climb.mp4 --script narration.txt --words out/words.json -o out/critic
```

The music was spliced so its last hit lands on the end card and cut to silence for the snap
(`references/audio.md`); `music/bed-edit.wav` in `edit.yaml` is that edited file.
