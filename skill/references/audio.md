# Music, sound effects and the mix

## Music

```bash
vg music "Curious, gentle; light pizzicato strings and soft marimba over felt piano, about 90 bpm, sparse enough to sit under a narrator, ends on a soft resolved chord. Instrumental, no vocals." -o music/bed
vg music @prompts/music.txt -o music/bed --model google/lyria-3-pro-preview     # a full track, about 60 s, $0.08
```

The default `google/lyria-3-clip-preview` makes 30 s for $0.04; `lyria-3-pro-preview` a full track. Describe
the mood, instruments, tempo and shape ("opens on a huge hit, builds, a half-second dropout around 25 s, slams
back in, ends on one final hit with a ringing tail"). Lyria rarely puts events at the exact second you ask, so
edit the track to the picture rather than the other way round.

### Fitting a track to the edit

Map where the track's loud moments are, then splice. Measure in windows of a fixed number of samples, and take
the sample rate from the file: music often comes back at 44.1 kHz, and a window sized for 48 kHz silently
stretches every timestamp by 9%.

```bash
rate=$(ffprobe -v error -select_streams a -show_entries stream=sample_rate -of csv=p=0 music/bed.mp3)
ffmpeg -i music/bed.mp3 -af "asetnsamples=$((rate/2)),astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level" -f null - 2>&1 \
  | grep RMS_level | awk -F= '{printf "%.1f:%.0f ", (NR-1)*0.5, $2}'
```

- **Land the last hit on the end card**: keep the track from 0 to a point under the narration, and crossfade
  into its final section so the hit lands where the end card starts:
  `[0]atrim=0:38.6,asetpts=PTS-STARTPTS[a];[0]atrim=start=51.7,asetpts=PTS-STARTPTS[b];[a][b]acrossfade=d=0.6:c1=tri:c2=tri`
  (here source 56.0 s lands at 42.3 s). Put the splice under the voice, where it is masked.
- **A dramatic cut to silence** (a snap, a reveal): `volume='if(between(t,29.32,30.0),0,1)':eval=frame`, with a
  sound effect filling the gap so the mix never goes dead.
- **Let the natural ending ring out**: start the track early enough that its own decay covers the closing beat;
  a hard `fade_out` on a loud passage sounds cut off.

### Longer, gentler music: fal's ElevenLabs Music

For a calm piece of a few minutes (slow strings, felt piano, ambient), `fal-ai/elevenlabs/music` ($0.60 a minute)
beat Lyria and Stable Audio 2.5 in a blind listening test (Stable Audio sounded synthetic). It refuses any prompt that
names an artist or a piece ("in the style of Max Richter" fails): describe the instruments, tempo, harmony and
shape instead ("slow sustained string quartet, low cello pedal, suspended chords that resolve late, no percussion").
Master with the kit's `calm_master.sh` (-26 LUFS) for anything people fall asleep to.

### Sound baths and room ambience

- **A sound bath that loops**: generate a few long bowl, gong and drone takes (ElevenLabs sound effects), then
  compose the bath in code: one drone bed plus struck bowls tuned to a pentatonic set over one root, placed at
  irregular times. Write the strike times to JSON so touch pulses or visuals can follow them.
- **Quiet ambience** (a room tone, a fridge hum, a TV through a wall) at -40 to -46 dBFS: set it with linear gain
  on the samples, not loudness normalisation, which pumps up the noise floor or lands 25 dB too quiet.
- **UI sounds** (a tap, a send): synthesise them soft and short (peak about -30 dBFS, lowpassed); generated
  "click" effects come back too bright and too loud next to a voice.

## Sound effects

- **Synthesised, free**: `vg sfx` lists the presets (impact, whoosh, thud, riser, snap, tick, zap, button,
  chime); `vg sfx riser -o sfx/riser.wav`. Good for punctuation: a whoosh on a camera move, a thud under
  kinetic type, a riser into a hit, a button on the end card.
- **Generated, realistic**: rain, a room, a crowd, an engine, a struck bowl, through fal (about $0.002/s; the
  field is `text`, not `prompt`):
  `vg fal run fal-ai/elevenlabs/sound-effects/v2 -o sfx/rain.mp3 --prompt-key text -p "soft rain on a window at night, no music" -a duration_seconds=10`.
  Loops, one-shots and choosing between takes: `references/fal.md`.
- You can't listen, so check an effect's shape before using it: render a spectrogram of all of them in a row
  (`ffmpeg ... concat ... showspectrumpic=s=1400x300:legend=0:scale=log:fscale=log`) and look.

## The mix

In `edit.yaml`, voice is `role: voice`, music `role: music`, effects `role: sfx`. `vg assemble` ducks music
under the voice (sidechain compression), normalises loudness to -14 LUFS, and limits peaks. Starting levels
that have worked: music `gain_db: -12`; effects that land on words -8 to -12; effects in gaps -2 to -6.

Effects are not ducked. A riser or a snap on the very word it illustrates ("and it **snaps**") drowns the word;
lower it, or move it to just after the word. Check with:

```bash
vg mixcheck edit.yaml -o out/mixcheck      # voice above music+effects, averaged while speaking, and the weak windows
```

Aim for the voice about 10 dB or more above everything else while speaking. The low windows it lists are either
an effect on a word (fix), a loud music hit (lower the music or move the hit), or the gap between two lines
(fine). `vg mixcheck` is free and doesn't render video.
