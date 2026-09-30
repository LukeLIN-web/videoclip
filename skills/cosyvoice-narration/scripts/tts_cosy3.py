"""Narration with Fun-CosyVoice3-0.5B-2512, zero-shot cloned from one reference clip.
Usage: VC_MODELS=/path/to/models REF_WAV=ref.wav REF_TEXT="exact words of ref.wav" python tts_cosy3.py LINES.tsv OUT_DIR
  LINES.tsv: <id>\t<text> per line. 2 takes per line: <id>a.wav (seed 0), <id>b.wav (seed 1); existing files are skipped.
  Run from a dir containing the CosyVoice repo checkout (git clone --recursive https://github.com/FunAudioLLM/CosyVoice)."""
import sys, os, time
sys.path[:0] = ["CosyVoice", "CosyVoice/third_party/Matcha-TTS"]
import torch, torchaudio
from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.utils.common import set_all_random_seed
tsv, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
REF_WAV = os.environ["REF_WAV"]
REF_TXT = "You are a helpful assistant.<|endofprompt|>" + os.environ["REF_TEXT"]
tts = AutoModel(model_dir=os.path.join(os.environ["VC_MODELS"], "Fun-CosyVoice3-0.5B-2512"))
for line in open(tsv, encoding="utf-8"):
    vid, text = line.rstrip("\n").split("\t", 1)
    for take, seed in (("a", 0), ("b", 1)):
        path = f"{out}/{vid}{take}.wav"
        if os.path.exists(path): continue
        set_all_random_seed(seed); t0 = time.time()
        wav = torch.cat([j["tts_speech"] for j in tts.inference_zero_shot(text, REF_TXT, REF_WAV, stream=False)], dim=1)
        torchaudio.save(path, wav, tts.sample_rate)
        print(vid, take, f"{wav.shape[1]/tts.sample_rate:.1f}s audio", f"{time.time()-t0:.0f}s", flush=True)
print("TTS_DONE")
