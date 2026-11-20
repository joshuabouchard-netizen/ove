#!/bin/bash
# Build, then publish site/ to Cloudflare Pages behind the password gate.
# Usage: ./deploy.sh PROJECT [SRC]   or   PROJECT=name ./deploy.sh [SRC]
# Needs, once: `npx wrangler login`, the Pages project, and its SITE_PASSWORD secret (see README.md).
set -eo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
if [ -z "${PROJECT:-}" ]; then PROJECT=${1:-}; [ $# -gt 0 ] && shift; fi
[ -n "$PROJECT" ] || { echo "usage: ./deploy.sh PROJECT [SRC]   (the Cloudflare Pages project name)" >&2; exit 2; }
"$HERE/build.sh" "$@"
cd "$HERE"
npx wrangler pages deploy site --project-name "$PROJECT" --branch main --commit-dirty=true
