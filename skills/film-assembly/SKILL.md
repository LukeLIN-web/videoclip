---
name: film-assembly
description: Build a graded rough cut (1920x804 2.39:1, 24 fps) from a JSON shot list — film-look grade, retiming, vertical phone footage over a blurred fill, gentle Ken Burns on stills (portraits whole over a blurred fill), VO de-click + click scan, montage cuts, VO/music/ambience mix with ducking and room tone, silence beats, bilingual SRT, fade-out; segments cached per shot. Use for 剪辑, 粗剪, rough cut, assemble, 调色, 混音, and for revising a cut from timecoded notes.
---

# Film assembly

`scripts/assemble.py TIMELINE.json OUT_DIR` — the schema is in its docstring. `scripts/grade.sh` is the look
(lifted blacks, teal shadows / amber highlights, halation, vignette, animated 35mm grain, ProRes out); it cover-scales
and crops any input to 1920×804 (`-y/-x` pick the crop position). Run both on the GPU server, not a laptop — grading
30 shots is CPU-bound for tens of minutes.

## Shot rules that came from user notes
| situation | do | not |
|---|---|---|
| 9:16 phone clip | `"vert": y` — whole frame ×1.35 centred over a blurred, darkened copy | a 2.39 strip (≈1.8× blow-up) |
| portrait (3:4) still | default `fit`: whole photo, zoom vs fit-height (1.0–1.12), over a blurred fill | cover-crop to 2.39 — only ~31% of the height survives; "放大太大" |
| landscape still | keyframed Ken Burns vs cover-fit, mostly 1.0–1.15×, push to a detail ≤ 1.6× | 2.5× (still "too zoomed" in 为君载 v4), 8× "into the brushstrokes" |
| sound design for an object on screen (candle, lighter…) | real recorded sound, or nothing | synthesized noise ticks — read as a lighter flick / glitch |
| generated push-in that drifts | use the first seconds, retimed longer | the whole take |
| low-res or wrong-orientation source | regenerate at the right aspect | upscale a crop |
| a shot that must be silent | `"silence": true` (room tone survives) | digital zero |
| a clip with a wrong-sounding bed | omit `amb` | trust generated sound |
Check each source's resolution/orientation (`ffprobe`) before placing it.

## Timeline
- Segment lengths are measured after building; the timeline is laid on real lengths (retimed clips lose ~1 frame
  each — 0.6 s drift over a film otherwise). VO, cues, cards and subtitles follow the real starts.
- Narration drives shot length: if a line is longer than its shot, lengthen the shot or pick the shorter take; don't
  let it spill into a silent beat or a shot that must have no VO.
- Montage entries cut straight from other shots' graded segments (ProRes is intra-only, so concat in/out points are exact).
- End on a picture, not a card, when that is the ending: `"fade_out": 1.2` fades picture and sound together.

## Revising
1. Map each note's timecode to a shot with `OUT_DIR/timeline.json`.
2. Find the cause first (source res, crop factor, zoom, drift, generated sound) — then the fix. Report as a table.
3. Copy unchanged `seg/*.mov` into the new version's seg folder; delete only the changed ones; rebuild.
4. After an interrupted build, check the newest segment decodes to the end before trusting the cache.

## QA before showing anyone
- Every VO take goes through `declick()` (built into assemble.py): TTS takes routinely carry an onset pop and ticks in
  their lead-in silence/pauses — VO07a of 为君载 had a 0 dBFS click the user heard as a lighter at 1:33. Read the
  `declick` log; if a take needed a `hot` cap, prefer its twin take.
- Read the `click scan` line after the mix: map each hit to its shot/source; anything that is not a score attack or a
  consonant gets fixed before the user hears it. Don't rely on the user to find clicks.
- Contact sheet must include a frame of every still at its tightest zoom — compare visible area to the photo.
- One mid-frame per shot on a labelled contact sheet (catches wrong crops — a tilt framed on empty sky).
- Per-shot RMS of the mix: silent beats ≈ −50 dB, VO shots ≈ −17…−20 dB; integrated ≈ −18 LUFS, peak ≤ −1 dBTP.
- Faces: every recognisable passer-by blurred or cropped out; note what is still open.
