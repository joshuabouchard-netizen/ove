# Setup, keys and install problems

`INSTALL.md` at the top of the kit is the install procedure. This file is for an agent working on a machine
where it is (or should be) installed.

## Check first

```bash
vg doctor        # ffmpeg and the filters vg uses, keys present or missing (never shown), optional tools
vg spend         # OpenRouter's own usage for the key, the account balance, and vg's local ledger
```

`vg doctor` exits non-zero when something required is missing; its MISSING lines say what breaks without it.

## Where things live

- **The code** is `~/ove` (a git repository): `~/ove/cli` is installed as a `uv tool` in editable mode, so
  editing the source changes `vg` at once, and `~/.claude/skills/ove` links to `~/ove/skill`.
- **`VG_HOME`** (default `~/ove`; an older `~/media-gen` or `~/video-gen` with a `.env` is used while `~/ove`
  doesn't exist) holds `.env` with the keys, `costs.jsonl` (the spend ledger) and an
  optional `.youtube-cookies.txt`. Set `VG_HOME` to keep these elsewhere.
- **Keys** are read from the environment first, then `VG_HOME/.env`:
  - `OPENROUTER_API_KEY`: required. One key reaches the image, video, voice, transcription, music and review
    models.
  - `FAL_KEY`: optional. Kling and other fal.ai models, generated sound effects.
  Never print a key, paste one into chat, or put one in a file anyone else will see. The easy way:
  `vg keys open openrouter` opens the account pages; the person copies the key; `vg keys paste openrouter`
  saves it from the clipboard and tests it. Or they paste it into `.env` themselves, or send it with Magic Wormhole
  (`wormhole send --text ...` on their side, `wormhole receive <code>` piped straight into `.env` on yours).
  `read -s` in a terminal works for typing a key without echoing it, but only in a real terminal: an agent's
  shell has no keyboard, and a paste that lands twice doubles the key (a 146-character "key" is a 73-character
  one pasted twice).

## The OpenRouter account

- **Zero Data Retention** (openrouter.ai/settings/privacy) must be off for media. With it on, every video
  model, several image models and the music models answer 404, which `vg` reports as "Blocked by the account's
  Zero Data Retention setting". Text models and Gemini image still work, so the symptom is "some things work".
- **The balance and the key's cap are separate.** A key can have a weekly limit and still fail because the
  account behind it is out of credit; the error then names `openrouter_credits`. `vg spend` shows both.
- Audio calls (voice, transcription, music) are refused when the balance is under about $0.50.
- Too many jobs in flight at once answers `HTTP 402 in_flight_budget_exhausted`; six images in parallel is
  safe, nine was not.

## Machines without Homebrew

Everything installs without admin rights: `uv` from astral.sh into `~/.local/bin`, and ffmpeg (with libass),
Manim, Node and poppler from conda-forge through `pixi` into `~/.pixi/bin`. Put both folders on `PATH` in
`~/.zshenv` (not `~/.zshrc`), so agents' non-interactive shells find them too.

## When the network blips

A DNS failure (`nodename nor servname provided`) or a hang is the machine's network, not the provider. Check
with `curl -s -o /dev/null -w '%{http_code}' https://openrouter.ai/api/v1/models` and retry; a failed job was
not billed unless the provider accepted it.
