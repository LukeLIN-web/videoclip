#!/bin/bash
# h3_batch.sh JOBS.tsv PROMPT_DIR [SEEDS] — sequential H3 batch (localhost:30010). JOBS.tsv: ID<TAB>task<TAB>has_image.
# Duration per job: the "**N 秒**" in the folder's 3-notes.txt (fallback 8). Output $VC_TODO/<ID>-*/H3_seed<N>.mp4, existing skipped.
set -uo pipefail; HERE=$(cd "$(dirname "$0")" && pwd); JOBS=$1; PD=$2; SEEDS=${3:-"0 1"}
IN=${VC_WORK:?}/h3_inputs; mkdir -p "$IN"
until curl -s -m5 localhost:30010/health | grep -q ok; do sleep 20; done
for seed in $SEEDS; do
  while IFS=$'\t' read -r id task img; do
    [ -z "$id" ] && continue
    d=$(ls -d "${VC_TODO:?}/$id"-*/ | head -1); out="${d}H3_seed$seed.mp4"
    [ -s "$out" ] && { echo "skip $id seed$seed"; continue; }
    dur=$(grep -oE '\*\*[0-9]+ 秒\*\*' "${d}3-notes.txt" | head -1 | grep -oE '[0-9]+'); dur=${dur:-8}
    im=""
    if [ "$img" = 1 ]; then
      src=$(ls "$d"1-* | grep -i -E '\.(jpe?g|png)$' | head -1); im="$IN/$id.jpg"
      [ -n "$src" ] || { echo "$id: NO FIRST FRAME"; continue; }
      [ -s "$im" ] || ffmpeg -nostdin -v error -y -i "$src" -vf "scale=-2:768" -q:v 2 "$im"
    fi
    echo -n "$(date +%T) $id seed$seed dur$dur: "
    DUR=$dur python3 "$HERE/run_h3b.py" "$task" "$PD/$id.txt" "$seed" "$out" $im </dev/null 2>&1 | tail -2 | tr '\n' ' '; echo
  done < "$JOBS"
done
echo BATCH_DONE
