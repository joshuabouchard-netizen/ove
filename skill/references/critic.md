# Checking a render

The checks write facts; you judge. Open the contact sheets and frames and look at them, read the numbers, then
fix and re-run.

```bash
vg critic out/final.mp4 --script narration.txt -o out/critic                       # transcribes the mix, Gemini review (cents)
vg critic out/final.mp4 --script narration.txt --words out/words.json --no-review   # free: no model calls
vg mixcheck edit.yaml -o out/mixcheck                                               # free: voice versus everything else
```

`report.md` lists duration and size, loudness (aim about -14 LUFS, true peak under -1 dBFS), silences over
0.8 s, black and frozen stretches, detected shots, contact sheets with timestamps, a frame after each cut, and
how the heard words compare with the script.

## Reading it

- **Script vs heard below 100%**: first find out whether the words are missing from the audio or from the
  transcript. Whisper transcribing a mix drops whole lines and mishears words under music and effects, so a
  gap there is often a transcription gap. `vg words` builds the transcript from each voice file instead and
  is what captions should use. When the mix really masks a word, `vg mixcheck` shows the window.
- **Frozen stretches** flag a still, a slow graphic with thin moving lines, or a held end card. Give holds a
  slow push-in; look at the frames before treating it as a fault.
- **Silences** at the end usually mean the music stopped early or never covered the closing beat.
- **Black stretches** at a cut mean a segment rendered short or a missing file.
- **Peaks above -1 dBFS** come from sharp effects; `vg assemble` limits them, so re-render.

## The second opinion

With `--review`, Gemini watches a 720p proxy and lists problems with timestamps. Treat each item as a lead to
check: it has reported dead silence where the mix was at -13 dB, called a deliberate rhetorical question mark
an error, and described sounds that aren't there. It is good at spotting warped hands, objects that change
between shots, and garbled text on screen; check those in the frames it names.

## Your own eyes

- A contact sheet of each clip before accepting it: `ffmpeg -i clip.mp4 -vf "fps=2,scale=400:-2,tile=8x2:padding=3" -frames:v 1 sheet.jpg`;
  add `drawtext=text='%{pts\:flt}':x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6` before `tile`
  to read off when something happens (the frame a drop hits the soil is where the impact sound goes).
- A frame at a caption's time, to check it isn't stacked with another or covering a label. When previewing a
  captions file on an uncaptioned render (`-vf ass=captions.ass`), seek after the input
  (`-i out.mp4 -ss 6`): seeking before it resets timestamps to zero, and the filter draws the wrong moment.
- When `ffmpeg hstack` refuses to tile images of different heights, scale each to the same height with
  `setsar=1` first.
