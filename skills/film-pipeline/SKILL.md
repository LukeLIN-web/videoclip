---
name: film-pipeline
description: End-to-end workflow for a 3–5 minute short film built from real photos/footage plus AI-generated shots, narration and score — screenplay, per-shot todo folders, generation on a remote GPU box, take selection, rough cut, revision loop. Use when the user asks to make/plan/cut a short film, 做短片, 写剧本, 分镜, 剪片子, 出片, or to continue such a project. Orchestrates the h3-video, qwen-outpaint, cosyvoice-narration, acestep-score and film-assembly skills; remote execution goes through humanize.
---

# Film pipeline

The brief this was distilled from is in [references/original-brief.md](references/original-brief.md).
Lessons that cost real time are in [references/lessons.md](references/lessons.md) — read it before starting.

## 0. Before writing anything
- Ask what is unclear (length, aspect, language, who is credited, what must not appear, e.g. faces).
- Inventory the material: photos, phone clips (note vertical vs horizontal, which ones have usable live sound),
  the source text. Real footage beats generated footage for anything the author actually saw.

## 1. Screenplay (strong model)
- A thesis the film overturns, a visual motif, a structure (e.g. the day as a circle). Shot table with timecodes,
  per shot: source (photo / photo→video / real clip / pure generation / UI), picture, sound, VO line (zh + en).
- Get a second, adversarial read (a separate reviewer agent) and fold the notes in; keep old versions
  (`screenplay-v2.md`, …) instead of overwriting.
- Credit every model that actually produced a shot, and update credits when the toolchain changes.

## 2. Todo folders (one per generation)
`todo/NN-<type>-<name>/` with `1-<input image>`, `2-<prompt>.txt`, `3-<notes>.txt` (tool, settings, which shot it feeds,
what depends on it). Dependencies are explicit: an outpaint feeds a video's first frame; a video waits for its image.
Outputs land in the same folder with the model in the name (`H3_seed0.mp4`, `Qwen_seed1.png`, `VO07a.wav`, `ACE_take0.flac`).
Rewrite `3-*.txt` whenever the workflow changes; keep the old one renamed rather than deleting it.

## 3. Generate (remote GPU box, driven through humanize)
| asset | skill | per item |
|---|---|---|
| widen portrait photos to 16:9 | ../qwen-outpaint/SKILL.md | ~50 s |
| photo→video / text→video, with sound | ../h3-video/SKILL.md | ~4 min |
| narration, one voice | ../cosyvoice-narration/SKILL.md | 1–2 s/line |
| score cues | ../acestep-score/SKILL.md | ~20 s/cue |
Two takes of everything. If choosing between models, bake off the 2–3 *hardest* shots (on-screen text, architecture
lines, an abstract transformation) and let the user decide — then stop testing.

## 4. Select
Look before you pick: first/middle/last-frame contact sheets per take, frame-by-frame for text and faces, durations of
every VO take (a take much shorter than its twin usually dropped words). Record the pick and the reason in `3-*.txt`.

## 5. Assemble — ../film-assembly/SKILL.md
Rough cut from a JSON shot list; CPU-heavy steps (grading, encodes) run on the remote box. Contact-sheet one frame per
shot and per-shot RMS before showing it to the user.

## 6. Revise from notes
Users give notes as timecodes ("50–55 s is blurry"). Map each timecode to the shot through the cut's timeline.json,
diagnose the cause (source resolution? crop factor? Ken Burns zoom? a generated sound?) before changing anything, and
answer in a table: time → shot → cause → fix. Only regrade the shots that changed; copy the rest of the cached segments
into the new version's folder first.
