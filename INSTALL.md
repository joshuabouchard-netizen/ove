# Installing OVE

For a person, or for a Claude Code agent asked to set it up. About ten minutes, most of it creating two
accounts; nothing needs admin rights.

## 1. Install

```bash
git clone https://github.com/joshuabouchard-netizen/ove ~/ove && ~/ove/install.sh
```

The installer adds what's missing (uv, ffmpeg, Manim, Node, yt-dlp, Magic Wormhole) through uv and pixi,
installs the `vg` command from `~/ove/cli`, links the skill to `~/.claude/skills/ove`, creates `~/ove/.env`
(mode 600, never committed), adds the tool paths to `~/.zshenv`, and runs `vg doctor`. An older media-gen or
video-gen install is retired: its skill moves to `~/ove/skill-backups/` and its keys are carried over.
`--minimal` installs only uv and ffmpeg. Re-running updates in place; `cd ~/ove && git pull` fetches updates.

## 2. Keys

```bash
vg keys open openrouter     # opens: add credit, Privacy (turn OFF Zero Data Retention), create a key
vg keys paste openrouter    # after copying the key: saves it from the clipboard, clears it, tests it
vg keys open fal && vg keys paste fal
vg keys status
```

Only the last four characters of a key are ever shown. Give the OpenRouter key a weekly limit. With Zero Data
Retention on, video and music models are refused (images, voice, transcription and review still work).

## 3. Check and use

`vg doctor` (all required lines OK) and `vg spend` (usage, balance, the local ledger). Then ask Claude for
something: "make a 30-second 9:16 explainer about why the sky is blue". It writes a design doc and a cost
estimate first and waits for a yes before spending more than a few cents.

Offline tests, free: `cd ~/ove/cli && uv run --extra test pytest tests -q`.

## Uninstall

```bash
uv tool uninstall ove
rm ~/.claude/skills/ove && rm -rf ~/ove      # this also deletes your .env and spend ledger
```
