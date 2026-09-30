---
name: h3-video
description: Generate 4–15 s video clips with native stereo sound from MiniMax H3 (open weights) served by sglang — image-to-video from a first frame (fl2va) or text-to-video (t2va), Context-IR prompt format, stable serving flags, sequential batch over todo folders. Use for photo→video shots, AI shots with sound, H3, 海螺, 图生视频, 文生视频.
---

# MiniMax H3 video

Chosen over Wan2.2 A14B in a bake-off on the hardest shots: it held on-screen text and architecture lines, runs
8 s / 24 fps / 768p **with sound** in ~4 min on 4×H100 (Wan: 5 s, 16 fps, silent, ~35 min).

## Serve (4 GPUs, one-time)
```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
sglang serve --model-path $VC_MODELS/MiniMax-H3 --model-variant fl2va \
  --num-gpus 4 --ulysses-degree 4 --performance-mode speed --host 0.0.0.0 --port 30010 \
  --text-encoder-cpu-offload --vae-tiling          # without these two: rank-0 OOM in VAE decode -> NCCL hang -> dead server
```
Health: `curl localhost:30010/health`. Weights load in ~12 min. The fl2va variant also serves t2va.

## Prompt
Rewrite the brief into H3's Context-IR format — see [references/prompt-format.md](references/prompt-format.md).
A plain Veo-style prompt works worse; the `Audio:` line becomes `overall_soundscape` / `non_diegetic_music`.

## Run
- One job: `python3 scripts/run_h3b.py fl2va PROMPT.txt SEED OUT.mp4 /abs/first_frame.jpg`
  (`t2va` and no image for text-to-video — `fl2va` rejects an empty condition list with HTTP 400).
- Batch: `VC_WORK=… VC_TODO=… scripts/h3_batch.sh jobs.tsv prompts/ "0 1"` — `jobs.tsv`: `ID<TAB>task<TAB>has_image`,
  first frame = the folder's `1-*` image resized to 768 px high, output `$VC_TODO/<ID>-*/H3_seed<N>.mp4`, existing
  outputs skipped (so re-running the same batch fills gaps). Runs seed 0 for every shot first, then seed 1.
- Images go in as `file://` URIs of paths on the server. 4K inputs OOM — always downscale.

## Picking takes
- Contact-sheet frames 0 / 96 / 190 per take. Check on-screen text letter by letter.
- Push-ins keep going and can end somewhere new (a different street, sharp faces): use the first seconds slowed down.
- Its sound is good ambience but not always the sound you asked for (a clock "tick" can read as a lighter) — listen.
- It sometimes improves on the brief (a phone screen showing the basilica behind it); keep those.
