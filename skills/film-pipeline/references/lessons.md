# Lessons (each one cost real time)

## Picture
- **Check source resolution and orientation before cutting.** A web-generated clip came back 720×1280 (portrait) because
  the aspect was wrong at generation time; a 2.39:1 strip of it is a 2.7× blow-up and looks like mush. Regenerate.
- **A 2.39 strip of a 9:16 phone video is a ~1.8× blow-up — "you can't see anything".** Show the vertical frame
  (×1.35) centred over a blurred, darkened copy of itself instead.
- **Ken Burns zoom tops out around 2–2.5×.** An 8× push into a painting read as "zoomed in too far". Same for photos of
  statues and people.
- **Generated push-ins drift.** Image-to-video models keep pushing and can arrive somewhere new — a café shot ended on
  a different street with sharp faces. Use the first part of the take, slowed, or go back to the still.
- **Retimed clips come out about a frame short.** Planned durations drifted 0.6 s over 30 shots; build the timeline
  from the segments' measured lengths.
- **Crop offsets are per shot.** "Keep the top" on a façade tilt gave a frame of pure sky; look at the source frames first.

## Sound
- **Generated production sound can be wrong in a way that is hard to see:** a "clock tick" in a video model's soundtrack
  sounded like a lighter. Listen to each clip bed, or mute it.
- **Never digital silence** — a −50 dBFS room tone under everything; a "silent" shot is room tone only.
- Loudness: VO −16 LUFS per line, music −23 LUFS ducked −6 dB under VO, clip beds ~−30 LUFS, mix −18 LUFS integrated.

## Generation
- H3 on 4 GPUs OOMs in VAE decode on rank 0 with default flags, then the other ranks hang until the NCCL watchdog kills
  the server. Serve with `--text-encoder-cpu-offload --vae-tiling`. Downscale first frames to 768p before submitting.
- H3 `fl2va` needs at least one image; text-to-video is `task: "t2va"`.
- Qwen-Image-2.1 edit has no mask input: pad to the target canvas with flat grey, ask it to fill only the grey, then
  paste the original back with a feathered seam. About 1 in 6 takes leaves the grey untouched — run 2+ seeds.
- `while read … done < jobs.tsv` with ffmpeg inside: ffmpeg eats stdin and truncates the next job id. Use `-nostdin`.
- Voice clones need the exact transcript of the reference clip.

## Process
- Remote work goes through humanize. Independent of the tool: start long jobs detached (`setsid … </dev/null >log 2>&1 &`)
  so a dropped connection doesn't kill them; bring bulk results back with one `rsync`; poll by artifacts (files,
  counts, DONE markers) with a bounded wait and match every terminal state.
- Never `pkill -f <pattern>` from a command line that itself contains the pattern — it kills your own shell. Match
  narrowly (`pgrep -f 'prompts/04[.]txt'`) and kill PIDs.
- Don't install into the user's existing envs: `python -m venv --system-site-packages` on top of the closest one and
  add what's missing; if pip has no network, pure-python packages can be copied from another env.
- CPU-heavy work (grading, rendering, encodes) belongs on the server, not the laptop.
- When a version changes only a few shots, copy the unchanged cached segments first; don't regrade everything.
- A killed job can leave a half-written segment that the cache then trusts — check the last file's duration/decode.
- Don't publish private data: this repo has no hosts, usernames, absolute paths or source-file names — keep it so.
