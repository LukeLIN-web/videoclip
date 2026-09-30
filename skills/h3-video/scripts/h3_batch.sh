#!/bin/bash
# h3_batch.sh JOBS.tsv PROMPT_DIR [SEEDS]  — sequential H3 batch against a running sglang server (localhost:30010).
# JOBS.tsv lines: ID<TAB>task(fl2va|t2va)<TAB>has_image(0/1). Output: $VC_TODO/<ID>-*/H3_seed<N>.mp4 (existing files skipped).
# First frame: the folder's 1-* image, resized to 768p high. PROMPT_DIR/<ID>.txt holds the Context-IR prompt.
set -uo pipefail; HERE=$(cd "$(dirname "$0")" && pwd); JOBS=$1; PD=$2; SEEDS=${3:-"0 1"}
IN=${VC_WORK:?}/h3_inputs; mkdir -p "$IN"
until curl -s -m5 localhost:30010/health | grep -q ok; do sleep 20; done
for seed in $SEEDS; do
  while IFS=$'\t' read -r id task img; do
    d=$(ls -d "${VC_TODO:?}/$id"-*/ | head -1); out="$d/H3_seed$seed.mp4"
    [ -s "$out" ] && { echo "skip $id seed$seed"; continue; }
    im=""
    if [ "$img" = 1 ]; then
      src=$(ls "$d"/1-* | grep -i -E '\.(jpe?g|png)$' | head -1); im="$IN/$id.jpg"
      # -nostdin: without it ffmpeg eats the next line of JOBS.tsv from the while-read loop
      [ -s "$im" ] || ffmpeg -nostdin -v error -y -i "$src" -vf "scale=-2:768" -q:v 2 "$im"
    fi
    echo -n "$id seed$seed: "
    python3 "$HERE/run_h3b.py" "$task" "$PD/$id.txt" "$seed" "$out" $im 2>&1 | tail -1
  done < "$JOBS"
done
echo BATCH_DONE
