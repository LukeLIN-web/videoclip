"""Submit one H3 job to the local sglang server. Usage: run_h3b.py TASK PROMPT_FILE SEED OUT.mp4 [IMAGE]"""
import sys, json, time, urllib.request
URL = "http://localhost:30010/v1/videos"
task, pfile, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
img = sys.argv[5] if len(sys.argv) > 5 else None
body = {"task": task, "prompt": open(pfile).read().strip(),
        "conditions": [{"type": "image", "uri": "file://" + img, "role": "keyframe", "frame_index": 0}] if img else [],
        "target": {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": 8}, "seed": seed}
def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=600)
vid = json.load(call(URL, body))["id"]; t0 = time.time()
while True:
    st = json.load(call(f"{URL}/{vid}")); s = st.get("status")
    if s in ("completed", "failed", "error", "cancelled"): break
    time.sleep(15)
if s == "completed":
    open(out, "wb").write(call(f"{URL}/{vid}/content").read())
print(s, f"{time.time()-t0:.0f}s", out, flush=True)
