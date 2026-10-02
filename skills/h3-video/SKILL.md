---
name: h3-video
description: Generate 4–15 s video clips with native stereo sound from MiniMax H3 (open weights) served by sglang — image-to-video from a first frame (fl2va) or text-to-video (t2va), Context-IR prompt format, stable serving flags, sequential batch over todo folders. Use for photo→video shots, AI shots with sound, H3, 海螺, 图生视频, 文生视频.
---

# MiniMax H3 video

Chosen over Wan2.2 A14B in a bake-off on the hardest shots: it held on-screen text and architecture lines, runs
8 s / 24 fps / 768p **with sound** in ~4 min on 4×H100 (Wan: 5 s, 16 fps, silent, ~35 min).

## Serve: start before, stop after (the GPUs are shared)
**Start the server right before an H3 batch and stop it as soon as the batch is done and the takes are checked.** Don't leave it
holding 4×H100 overnight or between phases. Revision rounds start it again (weights take ~12 min to load, so batch regenerations).
```bash
scripts/h3_serve.sh start    # checks the GPUs are free, launches detached, waits for /health (H3_GPUS=0,1,2,3 by default)
scripts/h3_serve.sh status
scripts/h3_serve.sh stop     # SIGTERM by pidfile, waits, prints GPU memory; never kill -9
```
It wraps the one serving command that is stable:
```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
sglang serve --model-path $H3_MODEL --model-variant fl2va \
  --num-gpus 4 --ulysses-degree 4 --performance-mode speed --host 0.0.0.0 --port 30010 \
  --text-encoder-cpu-offload --vae-tiling          # without these two: rank-0 OOM in VAE decode -> NCCL hang -> dead server
```
Health: `curl localhost:30010/health`. The fl2va variant also serves t2va.

## Framing (the user's recurring note: "视频放大太大了")
- **The first frame is the whole photo.** Don't crop a 4:3 photo to a 16:9 band for the first frame (it drops 25% of
  the height before H3 even starts, and the cut crops again). Outpaint it to 16:9 with ../qwen-outpaint, or use a
  16:9/wider photo. In the cut the clip is shown whole (film-assembly `fit`), so no further crop is needed.
- **No push-in unless the shot asks for one.** Write the camera as locked-off or a slow lateral drift/pan; H3 keeps
  pushing and a take ends 1.3–2× tighter than its first frame. If a push is wanted, say "barely perceptible".
- When picking a take, compare its **last used frame** with the photo: if it shows < 80% of what the photo shows, use an
  earlier part of the take, or the other seed.

## Prompt
Rewrite the brief into H3's Context-IR format — see [references/prompt-format.md](references/prompt-format.md).
A plain Veo-style prompt works worse; the `Audio:` line becomes `overall_soundscape` / `non_diegetic_music`.

## Run
- One job: `DUR=7 python3 scripts/run_h3b.py fl2va PROMPT.txt SEED OUT.mp4 /abs/first_frame.jpg` (`DUR` sets seconds, default 8;
  it must match the timecodes in the prompt; output is written via `.part` then renamed, so a killed job leaves no half file)
  (`t2va` and no image for text-to-video — `fl2va` rejects an empty condition list with HTTP 400).
- Batch: `VC_WORK=… VC_TODO=… scripts/h3_batch.sh jobs.tsv prompts/ "0 1"` — `jobs.tsv`: `ID<TAB>task<TAB>has_image`,
  first frame = the folder's `1-*` image resized to 768 px high, duration = the `**N 秒**` in the folder's `3-notes.txt` (fallback 8), output `$VC_TODO/<ID>-*/H3_seed<N>.mp4`, existing
  outputs skipped (so re-running the same batch fills gaps). Runs seed 0 for every shot first, then seed 1.
- Images go in as `file://` URIs of paths on the server. 4K inputs OOM — always downscale.

- Measured length runs a little over the request ("7 s" → 7.29 s): build the cut from measured lengths.
- Run one batch at a time — two copies of the same batch racing on one folder overwrite each other's takes.

## Picking takes
- Contact-sheet frames 0 / 96 / 190 per take. Check on-screen text letter by letter.
- Push-ins keep going and can end somewhere new (a different street, sharp faces): use the first seconds slowed down.
- Its sound is good ambience but not always the sound you asked for (a clock "tick" can read as a lighter) — listen.
- It sometimes improves on the brief (a phone screen showing the basilica behind it); keep those.
