# Costs: prices, estimates and tracking

Prices change; these are what calls actually cost in late 2026. `vg` prints each OpenRouter call's charge,
`vg fal price <endpoint>` prints fal's published price, and `vg spend` sums what has been spent. Re-check a
price before quoting a large job.

## What things cost

| Call | Model | Cost seen |
|---|---|---|
| Image or keyframe, any aspect, with or without references | `google/gemini-3-pro-image` | $0.13–0.14 each |
| Video, 1080p, silent | `google/veo-3.1` | $0.20 per second ($0.80 for 4 s, $1.20 for 6 s) |
| Video, 1080p, silent, fast | `google/veo-3.1-fast` | $0.10 per second |
| Video, 720p | `bytedance/seedance-2.5` | about $0.23 per second ($0.93 for 4 s, $1.85 for 8 s) |
| Video with native sound | Veo 3.1 | about double the silent price |
| Voice-over line | `google/gemini-3.8-flash-lite-tts` | well under a cent |
| Word-timed transcript | `openai/whisper-large-v3` | well under a cent |
| Music, 30 s clip | `google/lyria-3-clip-preview` | $0.04 |
| Music, full track (about 60 s) | `google/lyria-3-pro-preview` | $0.08 |
| A second opinion on a render | `google/gemini-3.1-pro-preview` | cents |
| Kling image-to-video, Kling edits, sound effects | fal.ai | `vg fal price <endpoint>`; billed by fal, not OpenRouter |
| Sound effects made with `vg sfx`, motion graphics, HTML renders, every ffmpeg step | local | free |

Refused jobs ("high load", "in flight budget exhausted", a Zero Data Retention 404) are not billed. A job that
was accepted and then failed or timed out may be; the ledger logs those as failed attempts.

## Estimating a job

Add up: keyframes and stills × $0.14 × about 2 for retries; clip seconds × the rate × about 1.5; fal jobs at
their published price × 1.5; music and voice in cents. Real examples:

- A 45 s calm explainer (5 keyframes, 3 Veo clips, Manim diagrams, voice, music, critic): about $4.70.
- A 45 s action cut (9 keyframes, 6 clips mostly on Seedance, voice, music, synthesised effects): about $7.70.
- A set of four photoreal stills from a person's photos, two takes each, plus fixes: about $1.70.
- Twelve logo and mood images for brand directions: about $1.60.

## Tracking spend

- `vg spend` prints OpenRouter's usage for the key (today, this week, the cap if the key has one), the account
  balance with a warning under $10, and the local ledger for the last 7 days by provider.
- The ledger (`VG_HOME/costs.jsonl`) has one line per paid call with the provider's charge where it gives one.
  fal returns no charge per call, so `vg` logs an estimate from the unit price (seconds of output × rate, or
  per image); its bill of record is fal.ai/dashboard/usage.
- OpenRouter's dashboard lags a few minutes behind; the sum of the charges `vg` printed is current.
