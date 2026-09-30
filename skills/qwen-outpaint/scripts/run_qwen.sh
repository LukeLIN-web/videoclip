#!/bin/bash
# run_qwen.sh GPU ID SEED -> $VC_TODO/<ID>-*/Qwen_seed<SEED>.png
# Needs: VC_TODO (todo root with <ID>-name/ folders holding 1-input.jpg + 2-prompt.txt), VC_MODELS, VC_PY (python with diffusers dev)
set -euo pipefail; HERE=$(cd "$(dirname "$0")" && pwd)
d=$(ls -d "${VC_TODO:?}"/$2-*/ | head -1)
src=$(ls "$d"/1-* | grep -i -E '\.(jpe?g|png)$' | head -1); prompt=$(ls "$d"/2-*.txt | head -1)
CUDA_VISIBLE_DEVICES=$1 "${VC_PY:-python3}" "$HERE/qwen_outpaint.py" "$src" "$prompt" "$3" "$d/Qwen_seed$3.png" > "$d/qwen_seed$3.log" 2>&1
