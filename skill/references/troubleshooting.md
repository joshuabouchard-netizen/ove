# When something fails

Errors as they appear, what causes them, and what fixes them.

## Model calls

| Error or symptom | Cause | Fix |
|---|---|---|
| 404, "Blocked by the account's Zero Data Retention setting" | ZDR is on for the OpenRouter account | Turn it off at openrouter.ai/settings/privacy, or use the models that have ZDR endpoints (Gemini image, MAI voice) |
| HTTP 402 naming `openrouter_credits`, or audio refused "requires at least $0.50 in balance" | The account is out of credit, whatever the key's own cap | The account owner adds credit; `vg spend` shows the balance |
| HTTP 402 `in_flight_budget_exhausted` | Too many jobs running at once | Run about six images or three or four videos at a time; re-run the failed ones |
| Video job "failed: the service is currently experiencing high load" | Provider busy (common on Veo) | Not billed. `vg video` retries; `--fallback bytedance/seedance-2.5` switches model |
| Gemini TTS 400 "only supports response_format=pcm" | An old `vg` | This `vg` asks for PCM and converts; reinstall |
| Lyria 400 "Audio output requires stream: true" | An old `vg` | This `vg` streams; reinstall |
| Lyria on OpenRouter: "no audio in stream" | The provider returned text only | Retry once; then use fal (`fal-ai/elevenlabs/music`) |
| ElevenLabs Music rejects the prompt | It names an artist or a piece | Describe instruments, tempo and shape instead |
| `nodename nor servname provided` | The machine's network | Retry; check `curl https://openrouter.ai/api/v1/models` |
| `vg` usage error, "No such option: --last kf/x.png" | zsh passed several flags as one word | Use an array, or write the flags out |
| An image comes back with black bars | The model composed a narrower picture inside the frame | Regenerate asking for a full-bleed frame; `vg borders` checks |
| Garbled or invented text in an image | Image models can't spell | Keep images text-free and set words in HTML (`references/layout.md`) |
| An edit changes the wrong side | Left/right confusion | Anchor to a feature, or mirror (`references/images.md`) |

## Rendering

| Error or symptom | Cause | Fix |
|---|---|---|
| ffmpeg "First input link main timebase … do not match … xfade timebase" | A crossfade after a plain cut (old `vg`) | Fixed in this `vg`: every segment gets the same timebase |
| Music stops dead when the narration ends | Sidechain compression ends with its key (old `vg`) | Fixed: the voice key is padded to the full length |
| True peak above -1 dBFS | Sharp effects overshoot single-pass loudnorm (old `vg`) | Fixed: a limiter follows loudnorm |
| Caption lines jump up or appear two at once | Lines held past the next line's start (old `vg`) | Fixed: each line ends before the next begins |
| `pad`: "Padded dimensions cannot be smaller than input" | Odd height with 4:2:0 video | Use even dimensions |
| `hstack` fails | Inputs of different heights | Scale each to the same height, `setsar=1` |
| A filter expression fails to parse, "No option name near …" | A comma inside a function like `gte(t,0.18)` | Escape it: `gte(t\,0.18)` |
| A clip is shorter than its slot | Generated clips are 4/6/8 s | It holds its last frame; `vg overlay --dur` does the same for overlays |

## Captions and checks

| Symptom | Cause | Fix |
|---|---|---|
| A whole line missing from the transcript or captions | Whisper on the full mix, under music and effects | `vg words edit.yaml` transcribes each voice file and places it |
| "everyone" for "every one", "30" for "thirty" | Transcription habit | Fix the word in `words.json` before `vg captions` |
| Transcript of a short excerpt is just "♪♪♪" | Whisper on music-heavy audio | Not evidence either way; use `vg words` or `vg mixcheck` |
| Measured timings are about 9% off | Analysis window sized for 48 kHz on a 44.1 kHz file | Size windows from the file's sample rate |

## Shell and system

| Symptom | Cause | Fix |
|---|---|---|
| `vg`, `ffmpeg` or `manim` not found in an agent's shell | PATH set in `~/.zshrc`, which non-interactive shells skip | Put it in `~/.zshenv` |
| `/path/48000=0.6` style errors | zsh read `$R:a` as a path modifier | Write `${R}:a` |
| A key file holds a 146-character key | The key was pasted twice | Keep the first half if both halves match; re-check with `vg spend` |
| `read -s` prompt in an agent's shell hangs or gets nothing | No keyboard in an agent's shell | Run it in the user's own terminal, or send the key with Magic Wormhole |
| Manim `DecimalNumber` or `MathTex` fails looking for `latex` | No LaTeX installed | Use `Text` with an f-string and a `ValueTracker` (`references/motion-graphics.md`) |
| Manim camera updater does nothing | The frame isn't in the scene | `self.add(self.camera.frame)` |
| Manim `wait()` "duration of 0" | A computed hold came out zero | Only wait when the remainder is positive |
