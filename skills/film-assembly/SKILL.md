---
name: film-assembly
description: Build a graded rough cut (1920x804 2.39:1, 24 fps) from a JSON shot list — film-look grade, retiming, every source shown WHOLE over a blurred fill by default (framing gate: ≥80% of the source visible, zoom ≤1.15), gentle Ken Burns, VO de-click + click scan, montage cuts, VO/music/ambience mix with ducking and room tone, silence beats, bilingual SRT, fade-out; segments cached per shot. Use for 剪辑, 粗剪, rough cut, assemble, 调色, 混音, and for revising a cut from timecoded notes.
---

# Film assembly

`scripts/assemble.py TIMELINE.json OUT_DIR` — the schema is in its docstring. `scripts/grade.sh` is the look
(lifted blacks, teal shadows / amber highlights, halation, vignette, animated 35mm grain, ProRes out); it cover-scales
and crops any input to 1920×804 (`-y/-x` pick the crop position). Run both on the GPU server, not a laptop — grading
30 shots is CPU-bound for tens of minutes.

## Framing: the user's most repeated note is "放大太大了" — for photos AND videos, in every film
**Reflection.** Each time it was "fixed" by lowering the Ken Burns numbers (8× → 2.5× → 1.6× → 1.1×) and it came back,
because the zoom was measured against the wrong thing. "1.0" meant *cover-fit to 2.39*, and that crop is the blow-up:

| source → 2.39 frame | visible part of the source at "zoom 1.0" |
|---|---|
| 4:3 photo, cover | 56% of the height (the user sees a ~1.8× crop) |
| 3:4 portrait, cover | 31% of the height |
| 4:3 photo → 16:9 first frame for H3 → cover | 75% × 74% = 56% of the height, plus H3's own push-in, plus 768→804 px upscale |
| 9:16 phone clip at ×1.35 over blur (the old "whole frame") | 74% of the height |

**Rule: zoom is judged against the source.** At the tightest moment of every shot the frame shows **≥ 80% of the
source's width and height**, Ken Burns/static zoom ≤ 1.15. So anything narrower than 2:1 (9:16, 3:4, 4:3, 16:9 — photos
and video alike) is shown **whole over a blurred fill** — `fit`, now the default in `assemble.py` for stills and clips.
Cover-cropping to 2.39 is an exception that needs `"tight": "<reason>"` and the user's say-so; it is never the default
because it "looks more cinematic".
- `assemble.py` enforces this before building (framing gate) and writes `OUT_DIR/framing.tsv` (visible w/h %, px per
  source px). Read it like the click scan: fix every `<< TOO TIGHT` and `upscaled, soft` line before the user sees the cut.
- The gate can't see crops made upstream or zoom generated inside a video. Those are checked by hand:
  a first frame cropped from a photo (outpaint instead — ../qwen-outpaint), and an H3 take whose last frame is
  pushed in vs its first (compare frame 0 and the last frame of the part you use, against the photo).
- A narrow strip that must fill the 2.39 frame is a sign the shot needs a different source or an outpaint, not a crop.

## Shot rules that came from user notes
| situation | do | not |
|---|---|---|
| 9:16 phone clip | default `fit`: whole frame over a blurred, darkened copy | a 2.39 strip (24% of its height, 1.8× upscaled); ×1.35 (cuts 26%) |
| 16:9 / H3 clip | default `fit`: whole frame, blurred side fill | cover to 2.39 (cuts 26% of the height, on top of any crop before H3) |
| still (any shape < 2:1) | default `fit`, Ken Burns 1.0 → 1.06–1.12, never above 1.15 | cover-fit — at "1.0" a 4:3 photo is already a 1.8× crop; film A v4/v5 and film B v1 all drew "放大太大" |
| detail the user asked to see | `"tight": "user asked for the signature"` + a zoom/crop that still reads | silently pushing into a detail |
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
2. Find the cause first (source res, crop factor *including crops made before generation*, zoom, H3 push-in, drift,
   generated sound). For any "too zoomed" note, read `framing.tsv` and fix the whole class of shots, not the one named — then the fix. Report as a table.
3. Copy unchanged `seg/*.mov` into the new version's seg folder; delete only the changed ones; rebuild.
4. After an interrupted build, check the newest segment decodes to the end before trusting the cache.

## QA before showing anyone
- Every VO take goes through `declick()` (built into assemble.py): TTS takes routinely carry an onset pop and ticks in
  their lead-in silence/pauses — VO07a of film A had a 0 dBFS click the user heard as a lighter at 1:33. Read the
  `declick` log; if a take needed a `hot` cap, prefer its twin take.
- Read the `click scan` line after the mix: map each hit to its shot/source; anything that is not a score attack or a
  consonant gets fixed before the user hears it. Don't rely on the user to find clicks.
- `framing.tsv`: no `TOO TIGHT` / `upscaled` lines left unexplained. Then a contact sheet that puts **each source next to
  its tightest frame in the cut** (stills and clips, incl. the last used frame of each H3 take) — compare what is lost.
- One mid-frame per shot on a labelled contact sheet (catches wrong crops — a tilt framed on empty sky).
- Per-shot RMS of the mix: silent beats ≈ −50 dB, VO shots ≈ −17…−20 dB; integrated ≈ −18 LUFS, peak ≤ −1 dBTP.
- Faces: every recognisable passer-by blurred or cropped out; note what is still open.
- **Show cuts in the browser, never as files to open.** VS Code's media preview fails over Remote-SSH for every
  format tried (H.264+AAC/MP3, VP9 and VP8 WebM, even a 30 s clip). Copy [scripts/review/](scripts/review/)
  (`index.html` + `serve.py`) into the cut folder, write `<cut>.vtt` from the SRT
  (`WEBVTT` header, `,` → `.` in timecodes), start `python3 serve.py 8765` in a tmux window that stays up, and tell the
  user to forward 8765 and open `http://localhost:8765/?cut=<cut>`. They pause, type, press Enter; each note carries
  its timecode and the on-screen subtitle and is written to `notes/<cut>.md` — read that file to start the next revision.
