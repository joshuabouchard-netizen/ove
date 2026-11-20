# Voice-over with emotion

Flat narration is what gives most AI video away. Direct the voice the way you would direct an actor: one short
delivery note per line or scene, written for what that moment is doing.

## Gemini TTS (default)

`vg tts` uses `google/gemini-3.8-flash-lite-tts`, which takes a free-text delivery note in `--style`. Stage
directions in brackets inside the text (`[whispers]`) are read aloud, not obeyed; put all direction in `--style`.
(The model answers in raw PCM; `vg` converts it to mp3.)

```bash
vg tts @vo/v1.txt -o vo/v1 --voice Sulafat \
  --style "Warm, curious lecturer opening a favourite lecture. Unhurried and quietly delighted. Light emphasis on 'no heart and no pump'."
vg tts @vo/w5.txt -o vo/w5 --voice Fenrir \
  --style "High-energy trailer narrator. Tense build on 'Pull too hard', a sharp hit on 'snaps', then hushed and amazed."
```

A good note names a **register** (lecturing, confiding, trailer), an **emotion** and its strength, a **pace**,
and where the weight or pause falls. Keep one shared base description across all lines and vary only the
emotion, so the narrator stays one person.

Voices: Charon (informative), Sadaltager (knowledgeable, fast), Gacrux (mature), Rasalgethi, Iapetus (clear);
warmer: Sulafat, Achird; brighter and energetic: Puck, Fenrir, Aoede.

## Choosing a voice

Audition two or three voices on the first line (pennies each) and measure them:
`ffprobe -v error -show_entries format=duration -of csv=p=0 vo/aud-Sulafat.mp3`. Words ÷ seconds × 60 gives
the pace: about 150 words a minute suits an explainer, about 165–180 an energetic short; 200 is too fast. You
can't hear the takes, so say which you picked and why, and name the files so the user can listen.

## Check every take

Transcribe each line (`vg transcribe vo/w3.mp3 -o vo/w3-words.json`, under a cent) and compare it with the
script. A voice sometimes says the wrong word ("yanks" came out heard as "yikes"); re-voice that line with a
note on the word ("pronounce 'yanks' crisply, rhyming with 'thanks'") and check again. Numbers come back as
digits ("30-story"), which is a transcription habit, not an error.

## Fitting the timing

1. Split the narration into `vo/<line>.txt`, one per line or scene, and voice them in parallel.
2. Measure each file; those durations are the real shot lengths.
3. A take a little long or short: `ffmpeg -i in.mp3 -af atempo=1.08 out.mp3` (stay within 0.9–1.1); beyond
   that, re-voice with a different pace note. Scale that line's word timings by the same factor.
4. In `edit.yaml`, place each file with `role: voice` and leave 0.3–0.6 s between lines. Cut shots on word
   boundaries from the per-line transcripts: a cut lands on the word it illustrates when the shot starts at
   `at + word.start`.

## Fallback voice

`microsoft/mai-voice-2` works when Gemini is unavailable and takes a named style:

```bash
vg tts @vo/s01.txt -o vo/s01 --model microsoft/mai-voice-2 --voice en-US-Harper:MAI-Voice-2 --style excited
```

Which style names work depends on the voice; a 400 means try another name or drop `--style`.
