#!/bin/bash
# Calm master for ambient, sleep or meditation music: decode in float (hot swells never clip), drop 9 dB,
# repair flattened peaks, soften the top end, smooth only the big swells, two-pass loudnorm to a quiet
# target, then a limiter at -6 dBFS. Runs in macOS bash 3.2; needs ffmpeg and python3.
# Usage: tools/calm_master.sh IN OUT [LUFS=-26]    (.wav OUT is 16-bit PCM; other extensions use ffmpeg's default codec)
set -eo pipefail
if [ $# -lt 2 ]; then sed -n '2,5p' "$0" | sed 's/^# //'; exit 2; fi
IN=$1; OUT=$2; LUFS=${3:--26}
TMP=$(mktemp -d "${TMPDIR:-/tmp}/calm_master.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
LN="loudnorm=I=$LUFS:TP=-6:LRA=11"

measure() {
  ffmpeg -nostdin -hide_banner -nostats -i "$1" -af "$2:print_format=json" -f null - 2>"$TMP/m.txt"
  python3 -c '
import json, sys
t = open(sys.argv[1]).read(); d = json.loads(t[t.rindex("{"):t.rindex("}") + 1])
print(" ".join(d[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")))' "$TMP/m.txt"
}

ffmpeg -nostdin -y -v error -i "$IN" -vn \
  -af "aformat=sample_fmts=flt,volume=-9dB,adeclip,highshelf=f=6000:g=-3,acompressor=threshold=-22dB:ratio=2.5:attack=150:release=1200:makeup=1" \
  -c:a pcm_f32le "$TMP/pre.wav"

read -r I TP LRA TH OFF <<EOF
$(measure "$TMP/pre.wav" "$LN")
EOF
echo "after cleanup: $I LUFS, true peak $TP dBTP, LRA $LRA LU"

case "$OUT" in *.wav|*.WAV) CODEC="-c:a pcm_s16le" ;; *) CODEC="" ;; esac
ffmpeg -nostdin -y -v error -i "$TMP/pre.wav" \
  -af "$LN:measured_I=$I:measured_TP=$TP:measured_LRA=$LRA:measured_thresh=$TH:offset=$OFF:linear=true,alimiter=limit=0.5:level=false,aresample=48000" \
  $CODEC "$OUT"

read -r I TP LRA TH OFF <<EOF
$(measure "$OUT" "$LN")
EOF
echo "$OUT: $I LUFS integrated, true peak $TP dBTP, LRA $LRA LU (target $LUFS)"
