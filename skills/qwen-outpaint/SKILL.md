---
name: qwen-outpaint
description: Widen portrait (3:4, 9:16) and 4:3 photos to 16:9 with Qwen-Image-2.1 (open weights, diffusers) without changing a single original pixel — grey-pad canvas, fill-only-the-grey prompt, original pasted back with a feathered seam. Use for 扩宽, outpaint, extend photo to widescreen, first frames for image-to-video.
---

# Qwen-Image-2.1 outpaint

## Setup
- Weights: `hf download Qwen/Qwen-Image-2.1 --local-dir $VC_MODELS/Qwen-Image-2.1` (~40 GB).
- Needs `QwenImage21Pipeline` from diffusers **main** and `transformers>=5.17`. Put them in a venv layered on an
  existing torch env (`python -m venv --system-site-packages venv_qwen`), don't upgrade the base env.
- One GPU per job, ~50 s at 2752×1536 on an H100.

## Why this recipe
The edit call takes `image=` and a prompt but **no mask**. So:
1. scale the photo to the target height (1536) and centre it on a 2752×1536 canvas of flat grey (128,128,128);
2. prompt: "The center of this image is a real photograph; the flat grey areas on the left and right are empty. Fill
   only the grey areas … Do not change the photograph in the center." + the scene-specific description;
3. paste the original back over the centre with a 48 px Gaussian-feathered seam → the photo is untouched by construction.
`OUT_raw.png` keeps the model's output for inspection.

## Run
`VC_TODO=… VC_MODELS=… VC_PY=venv_qwen/bin/python scripts/run_qwen.sh GPU ID SEED`
→ `$VC_TODO/<ID>-*/Qwen_seed<SEED>.png`. Run 2+ seeds: roughly 1 take in 6 returns the grey untouched.

## Picking
Check the seams at full size, perspective continuity (symmetric naves stay symmetric), and that the extension adds no
people or text. Prefer the take whose sides are plausible but quiet — invented detail attracts the eye.
