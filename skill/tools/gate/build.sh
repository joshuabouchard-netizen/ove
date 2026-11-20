#!/bin/bash
# Build the hostable site: copy the built site into site/ and add the password gate. Run before every deploy.
# Usage: ./build.sh [SRC]    (SRC defaults to ../dist next to this folder)
set -eo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:-$HERE/../dist}
[ -d "$SRC" ] || { echo "no site to publish at $SRC (pass the folder as the first argument)" >&2; exit 1; }
SRC=$(cd "$SRC" && pwd)
cd "$HERE"
mkdir -p site
rsync -a --delete --exclude '.DS_Store' --exclude '_worker.js' "$SRC/" site/
cp _worker.js site/_worker.js
BIG=$(find site -type f -size +24M)
if [ -n "$BIG" ]; then
  echo "WARNING: Cloudflare Pages allows at most 25 MiB per file. Too big:" >&2
  echo "$BIG" | sed 's/^/  /' >&2
fi
echo "site/ ready: $(du -sh site | cut -f1), $(find site -type f | wc -l | tr -d ' ') files"
