---
name: acestep-score
description: Generate instrumental film-score cues of exact length with ACE-Step 1.5 (open weights) from plain-language briefs — setup with uv, cue list with seconds and BPM, two takes per cue, and how to lay cues on a cut. Use for 配乐, BGM, score, soundtrack cue, 音乐.
---

# ACE-Step 1.5 score

## Setup
```bash
git clone https://github.com/ace-step/ACE-Step-1.5 && cd ACE-Step-1.5 && uv sync
hf download ACE-Step/Ace-Step1.5 --local-dir $VC_MODELS/Ace-Step1.5
ln -s $VC_MODELS/Ace-Step1.5 checkpoints          # turbo DiT + 5Hz LM 1.7B + VAE + text embedder
```

## Brief → cue
Write each cue as a paragraph a composer would understand: tempo, key, meter, instrumentation, shape over time,
what to avoid ("no drums", "no accordion", "chamber strings, not full orchestra"). Reuse one short motif across cues
(e.g. a three-note descent) so the score reads as one piece. It goes in the cue's todo folder as `2-*.txt`.

## Run
```bash
cd ACE-Step-1.5 && VC_TODO=… CUDA_VISIBLE_DEVICES=6 uv run python ../scripts/music_ace.py cues.tsv   # <id>\t<seconds>\t<bpm>
```
~20 s per cue for two takes. The LM backend is `pt` (no vllm dependency). Outputs are peak-normalised to −1 dB.

## Laying it on the cut
- Size each cue to its section with a few seconds of slack; cut at the next section with a 2–3 s fade.
- For a cue that climaxes, pick the file offset so the climax lands on the picture's peak.
- Mix at about −23 LUFS and duck ~6 dB under narration (film-assembly does both).
- A "single held note" ending can be taken from the tail of the last cue.
