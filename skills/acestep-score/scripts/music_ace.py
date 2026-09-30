"""Instrumental score cues with ACE-Step 1.5 (turbo DiT + 5Hz LM 1.7B). Run from inside the ACE-Step-1.5 checkout
with `uv run python music_ace.py CUES.tsv`, after `ln -s <models>/Ace-Step1.5 checkpoints`.

CUES.tsv lines: <id>\t<seconds>\t<bpm>   — the caption is $VC_TODO/<id>-*/2-*.txt (plain-language brief)
Output: $VC_TODO/<id>-*/ACE_take0.flac, ACE_take1.flac (2 takes per cue; cues that already have ACE_* are skipped)
"""
import sys, os, glob, time
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

todo = os.environ["VC_TODO"]
cues = [l.rstrip("\n").split("\t") for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
here = os.getcwd()
dit = AceStepHandler(); dit.initialize_service(project_root=here, config_path="acestep-v15-turbo", device="cuda")
lm = LLMHandler(); lm.initialize(checkpoint_dir=os.path.join(here, "checkpoints"), lm_model_path="acestep-5Hz-lm-1.7B", backend="pt", device="cuda")
for cid, sec, bpm in cues:
    d = glob.glob(f"{todo}/{cid}-*/")[0]
    if glob.glob(d + "ACE_*"): print(cid, "skip"); continue
    caption = open(glob.glob(d + "2-*.txt")[0], encoding="utf-8").read().strip()
    t0 = time.time()
    res = generate_music(dit, lm, GenerationParams(caption=caption, lyrics="[Instrumental]", instrumental=True,
                                                   duration=float(sec), bpm=int(bpm)),
                         GenerationConfig(batch_size=2, audio_format="flac"), save_dir=d)
    if not res.success: print(cid, "FAILED", res.error, flush=True); continue
    for i, a in enumerate(res.audios):
        os.rename(a["path"], f"{d}ACE_take{i}.flac")
    print(cid, "ok", len(res.audios), "takes", f"{time.time() - t0:.0f}s", flush=True)
print("MUSIC_DONE")
