"""Submit one H3 job to the local sglang server. Usage: [DUR=seconds] run_h3b.py TASK PROMPT_FILE SEED OUT.mp4 [IMAGE]
DUR (env, default 8) sets target.duration_seconds; must match the timecodes in the prompt."""
import sys, os, json, time, urllib.request
URL = "http://localhost:30010/v1/videos"
task, pfile, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
img = sys.argv[5] if len(sys.argv) > 5 else None
dur = float(os.environ.get("DUR", "8")); dur = int(dur) if dur.is_integer() else dur
body = {"task": task, "prompt": open(pfile).read().strip(),
        "conditions": [{"type": "image", "uri": "file://" + img, "role": "keyframe", "frame_index": 0}] if img else [],
        "target": {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": dur}, "seed": seed}
def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=600)
vid = json.load(call(URL, body))["id"]; t0 = time.time()
while True:
    st = json.load(call(f"{URL}/{vid}")); s = st.get("status")
    if s in ("completed", "failed", "error", "cancelled"): break
    time.sleep(15)
if s == "completed":
    tmp = out + ".part"; open(tmp, "wb").write(call(f"{URL}/{vid}/content").read()); os.replace(tmp, out)
else:
    print("detail:", json.dumps(st)[:500], flush=True)
print(s, f"dur={dur}s", f"{time.time()-t0:.0f}s", out, flush=True)
