---
name: cosyvoice-narration
description: Generate every narration line of a film in one stable cloned voice with Fun-CosyVoice3-0.5B-2512 (open weights) — zero-shot from a single reference clip and its exact transcript, two takes per line, QA by duration. Use for 旁白, 配音, voice-over, TTS, narration consistency.
---

# CosyVoice3 narration

## Setup
- Code: `git clone --recursive https://github.com/FunAudioLLM/CosyVoice` (the Matcha-TTS submodule is required).
- Weights: `hf download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local-dir $VC_MODELS/Fun-CosyVoice3-0.5B-2512`.
- First run downloads the wetext text-normaliser from ModelScope.

## Voice
One reference clip (5–10 s, clean, the delivery you want for the whole film) plus its **exact** transcript. If the
reference came from another TTS, reuse the line it was generated from — ASR transcripts drift (钟面 → 窗面).
CosyVoice3's prompt text must be prefixed `You are a helpful assistant.<|endofprompt|>` (the script does it).

## Run
```bash
REF_WAV=ref.wav REF_TEXT="…exact words…" VC_MODELS=… CUDA_VISIBLE_DEVICES=7 \
python scripts/tts_cosy3.py lines.tsv out_dir/      # lines.tsv: <id>\t<text>
```
Two takes per line (`<id>a.wav` seed 0, `<id>b.wav` seed 1), 1–2 s each; existing files are skipped.
"synthesis text too short than prompt" is a warning, not an error.

## QA
- List every take's duration side by side: a take much shorter than its twin (5.8 s vs 8.6 s) has usually dropped words.
- Listen to all of them (or transcribe) before the cut — nobody else will catch a mispronounced place name.
- Pick per line by fit to the picture, not only quality: a shorter take can keep a line from spilling into a shot that
  must stay silent.
