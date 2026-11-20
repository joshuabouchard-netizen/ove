#!/usr/bin/env bash
# Install OVE (Ops Video Editor): the `ove` skill for Claude Code and its `vg` command. No sudo; safe to re-run.
#
#   git clone https://github.com/joshuabouchard-netizen/ove ~/ove && ~/ove/install.sh
#
# By default it installs everything (uv, ffmpeg, Manim, Node, yt-dlp) where missing, without admin rights.
#   --minimal   only uv and ffmpeg
#
# Layout: ~/ove holds the code (a git repo, so your Claude's improvements are versioned), .env (your keys,
# never committed) and costs.jsonl (the spend ledger). ~/.claude/skills/ove is a link to ~/ove/skill, so an
# improvement Claude makes to the skill takes effect at once. Re-running never touches .env.
# Environment: VG_HOME (default ~/ove), SKILLS_DIR (default ~/.claude/skills).
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
VG_HOME="${VG_HOME:-$HOME/ove}"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
EXTRAS=1
for arg in "$@"; do
  case "$arg" in
    --minimal) EXTRAS=0 ;;
    --deps|--extras) ;;  # accepted for compatibility; everything is the default now
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '\n== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
export PATH="$HOME/.local/bin:$HOME/.pixi/bin:$PATH"
STAMP=$(date +%Y%m%d-%H%M%S)

say "tools"
have uv || curl -LsSf https://astral.sh/uv/install.sh | sh
if ! have ffmpeg || { [ "$EXTRAS" = 1 ] && ! { have manim && have node; }; }; then
  have pixi || curl -fsSL https://pixi.sh/install.sh | bash
fi
have ffmpeg || pixi global install ffmpeg
if [ "$EXTRAS" = 1 ]; then
  have manim || pixi global install manim
  have node || pixi global install nodejs
  have yt-dlp || uv tool install yt-dlp
  have wormhole || uv tool install magic-wormhole
fi
echo "uv $(uv --version | cut -d' ' -f2) · $(ffmpeg -hide_banner -version | head -1 | cut -d' ' -f1-3)"

# PATH for Claude Code's shells, which read ~/.zshenv (not ~/.zshrc)
if ! grep -qs 'OVE: tool paths' "$HOME/.zshenv" && ! grep -qsE '^export PATH=.*\.local/bin.*\.pixi/bin' "$HOME/.zshenv"; then
  printf '\n# OVE: tool paths for every shell, including Claude Code'"'"'s\nexport PATH="$HOME/.local/bin:$HOME/.pixi/bin:$PATH"\n' >> "$HOME/.zshenv"
  echo "added the tool paths to ~/.zshenv"
fi

say "OVE -> $VG_HOME"
if [ "$(cd "$KIT" && pwd -P)" != "$(mkdir -p "$VG_HOME" && cd "$VG_HOME" && pwd -P)" ]; then
  rsync -a --delete --exclude .git --exclude .env --exclude costs.jsonl --exclude skill-backups \
    --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude .youtube-cookies.txt \
    "$KIT/" "$VG_HOME/"
  echo "copied from $KIT"
fi
for old in media-gen video-gen; do uv tool uninstall "$old" >/dev/null 2>&1 || true; done
uv tool install --force --editable "$VG_HOME/cli" >/dev/null
echo "vg installed: $(command -v vg)"

if [ ! -f "$VG_HOME/.env" ]; then
  cp "$VG_HOME/cli/.env.example" "$VG_HOME/.env"
  for old in "$HOME/media-gen/.env" "$HOME/video-gen/.env"; do   # carry keys over from an earlier install, silently
    if [ -f "$old" ]; then
      python3 - "$old" "$VG_HOME/.env" <<'PY'
import sys
old, new = open(sys.argv[1]).read().splitlines(), sys.argv[2]
vals = {}
for l in old:
    if "=" in l and not l.lstrip().startswith("#"):
        k, v = l.split("=", 1); k = k.strip().removeprefix("export ").strip()
        if v.strip(): vals[k] = v.strip()
out = [f"{l.split('=',1)[0]}={vals[l.split('=',1)[0]]}" if "=" in l and not l.lstrip().startswith("#") and l.split("=",1)[0] in vals else l
       for l in open(new).read().splitlines()]
open(new, "w").write("\n".join(out) + "\n")
print("keys carried over from", sys.argv[1], ":", ", ".join(k for k in ("OPENROUTER_API_KEY", "FAL_KEY") if k in vals) or "none")
PY
      break
    fi
  done
fi
chmod 600 "$VG_HOME/.env"

say "skill -> $SKILLS_DIR/ove"
mkdir -p "$SKILLS_DIR"
for name in ove media-gen video-gen; do
  target="$SKILLS_DIR/$name"
  if [ -L "$target" ]; then
    [ "$name" = ove ] || { rm "$target"; echo "removed the old $name link"; }
  elif [ -e "$target" ]; then
    mkdir -p "$VG_HOME/skill-backups"
    mv "$target" "$VG_HOME/skill-backups/$name-$STAMP"   # outside the skills folder, so it never loads twice
    echo "moved the old $name skill to $VG_HOME/skill-backups/$name-$STAMP"
  fi
done
ln -sfn "$VG_HOME/skill" "$SKILLS_DIR/ove"
echo "linked $SKILLS_DIR/ove -> $VG_HOME/skill"

if have git; then
  cd "$VG_HOME"
  [ -d .git ] || { git init -q && echo "started version history in $VG_HOME"; }
  if git config user.email >/dev/null 2>&1 && [ -n "$(git status --porcelain)" ]; then
    git add -A && git commit -qm "OVE installed or updated ($STAMP)" && echo "recorded this install in git"
  fi
fi

say "check"
VG_HOME="$VG_HOME" vg doctor || true
cat <<EOF

Next (Claude does these with you):
  vg keys open openrouter   then   vg keys paste openrouter
  vg keys open fal          then   vg keys paste fal
  vg keys status
EOF
