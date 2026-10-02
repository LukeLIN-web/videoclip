"""Assemble a rough cut from a JSON shot list. Self-contained: numpy, scipy, opencv, ffmpeg, and grade.sh next to this file.

usage: python3 assemble.py TIMELINE.json OUT_DIR        (graded segments are cached in OUT_DIR/seg/<id>.mov — delete
                                                         one to redo that shot; copy unchanged ones between versions)
TIMELINE.json:
{
  "shots": [
    {"id": "S04", "kind": "clip", "src": "wall.mp4", "ss": 0, "sdur": 8, "dur": 14,     # retime 8 s of source to 14 s
     "amb": -32,                      # keep the clip's own sound as a bed at this LUFS (omit/null = mute)
     # framing: any source narrower than 2:1 (9:16 phone, 16:9 H3, 4:3) defaults to "fit" = the WHOLE frame over a blurred
     # fill; "zoom": 1.1 (<= 1.15) tightens it a little, "y": -1 top .. 1 bottom picks what survives. "fit": "cover"
     # (2.39 crop, grade flag -y picks the band) keeps only 74% of a 16:9 frame's height and must carry "tight": "<why>".
     "grade": ["-y", "0.2"],          # extra grade.sh flags
     "vo": [["lines/VO01a.wav", 0.8, "中文", "English"]],   # [file, offset in shot, subtitle zh, subtitle en]
     "card": ["chapter_alpha.mov", 0.5]},                  # alpha overlay [file, offset in shot]
    {"id": "S09", "kind": "still", "src": "photo.jpg", "dur": 13,
     "kb": [[0, 1.0, 0.5, 0.5], [9, 1.12, 0.6, 0.45], [10.5, 1.0, 0.5, 0.5]]},   # keyframes [t, zoom, cx, cy]
     # stills narrower than 2:1 default to "fit": whole photo, zoom relative to fit-height, over a blurred fill.
     # "fit": "cover" = 2.39 crop: a 4:3 photo keeps 56% of its height AT ZOOM 1.0, a 3:4 one 31% -> needs "tight".
    {"id": "S02", "kind": "ui", "src": "title.mov", "wav": "title.wav", "ss": 1, "dur": 8},
    {"id": "S12", "kind": "clip", "src": "nave.mp4", "sdur": 7, "dur": 7, "silence": true},   # only room tone survives
    {"id": "S25", "kind": "montage", "dur": 8, "cuts": [["S10", 4, 1.2], ["S08", 2, 0.5]]}    # [shot, t in its seg, len]
  ],
  "cues": [["score/A.flac", "S02", 0, "S06", 2.0]],   # [file, first shot, offset into file, stop at start of shot, fade-out s]
  "fade_out": 1.2, "target_lufs": -18, "vo_lufs": -16, "music_lufs": -23, "duck_db": -6
}
Framing gate (runs before anything is built): for every still/clip, the part of the SOURCE visible at its tightest
moment must be >= 80% of its width and of its height and zoom <= 1.15, else the build stops — unless the shot carries
"tight": "<why, and that the user asked for it>". Report in OUT_DIR/framing.tsv.
Writes OUT_DIR/cut.mp4 (H.264 1920x804 24 fps + AAC), cut_mix.wav, cut.srt, timeline.json (real start times).
"""
import os, sys, json, math, subprocess
import numpy as np
import cv2
from scipy.signal import butter, sosfilt
from scipy.ndimage import maximum_filter1d, uniform_filter1d

W, H, FPS, SR = 1920, 804, 24, 48000
GRADE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grade.sh")
PRORES = ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"]


def run(cmd): subprocess.run(cmd, check=True)
def db(x): return 10 ** (x / 20)
def probe_dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
def has_audio(p): return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip())
def ease(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ audio helpers
def load_audio(path, dur=None):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    if dur is not None:
        n = int(round(dur * SR)); a = np.vstack([a, np.zeros((max(0, n - len(a)), 2), np.float32)])[:n]
    return a


def write_wav(path, buf):
    tmp = path + ".f32"; buf.astype("<f4").tofile(tmp)
    run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", tmp, "-c:a", "pcm_s24le", path]); os.remove(tmp)


def lufs(buf):
    tmp = "/tmp/_assemble_meas.wav"; write_wav(tmp, buf)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    os.remove(tmp); js = json.loads(out[out.rindex("{"):out.rindex("}") + 1]); return float(js["input_i"])


def at_lufs(a, target):
    li = lufs(a); return a * db(target - li) if np.isfinite(li) else a


def declick(a, name=""):
    """TTS takes carry pops / ticks outside the speech (CosyVoice: a -3 dBFS burst at 0 s, a 0 dBFS click in the lead-in
    silence — heard by the user as a lighter flick). On a 10 ms grid: (1) silence the lead-in before the first sustained
    speech (>= 150 ms above median-20 dB; a TTS onset burst lasts ~100 ms), backing off to the last window under -50 dBFS so a soft consonant survives,
    20 ms fade-in; (2) mute isolated bursts (<= 40 ms) between >= 100 ms of near-silence; (3) cap any window > 12 dB
    over the speech median at median + 6 dB. Prints what it touched."""
    a = a.copy(); k = int(0.01 * SR); n = len(a) // k
    if n < 20: return a
    pk = np.abs(a[:n * k]).max(1).reshape(n, k).max(1) + 1e-9; d = 20 * np.log10(pk)
    med = np.median(d[d > -40]) if (d > -40).any() else -20
    g = np.ones(n, np.float32); fixed = []
    run6 = np.convolve(d > med - 20, np.ones(15), "valid") >= 15
    first = int(np.argmax(run6)) if run6.any() else 0
    while first > 0 and d[first - 1] >= -50: first -= 1
    if first > 0 and (d[:first] > -55).any(): fixed.append(f"lead-in 0-{first * 0.01:.2f}s")
    g[:max(0, first - 2)] = 0.0
    quiet = d < -50; i = first
    while i < n:
        if quiet[i]: i += 1; continue
        j = i
        while j < n and not quiet[j]: j += 1
        if j - i <= 4 and i >= 10 and j + 10 <= n and quiet[i - 10:i].all() and quiet[j:j + 10].all():
            g[i:j] = 0.0; fixed.append(f"tick {i * 0.01:.2f}s")
        i = j
    hot = d > med + 12; g[hot] = np.minimum(g[hot], db(med + 6) / pk[hot]); fixed += [f"hot {i * 0.01:.2f}s" for i in np.nonzero(hot)[0]]
    if fixed: print(f"  declick {name}:", ", ".join(fixed))
    env = np.interp(np.arange(n * k), np.arange(n) * k + k / 2, uniform_filter1d(g, 2))
    env[:first * k] = np.minimum(env[:first * k], np.clip((np.arange(first * k) - (first - 2) * k) / (2 * k), 0, 1))
    a[:n * k] *= env[:, None].astype(np.float32); return a


def click_scan(mix, top=6):
    """QA: the sharpest transients in the final mix (2 ms high-passed RMS vs its 200 ms neighbourhood). Look up each
    hit's source (timeline.json): a VO take outside its speech = artifact; a score attack after a rest = fine."""
    h = sosfilt(butter(4, 2500, "hp", fs=SR, output="sos"), mix.mean(1)); w = int(0.002 * SR); n = len(h) // w
    e = np.sqrt((h[:n * w].reshape(n, w) ** 2).mean(1)); r = e / (np.convolve(e, np.ones(100) / 100, "same") + 1e-6)
    hits = []
    for i in np.argsort(r)[::-1]:
        t = i * w / SR
        if all(abs(t - x) > 1 for x, _ in hits): hits.append((t, r[i]))
        if len(hits) >= top: break
    print("click scan:", ", ".join(f"{int(t // 60)}:{t % 60:05.2f} x{v:.0f}" for t, v in hits))


def room_tone(n, rms_db=-50.0):
    """never digital silence: cinemas read 0 dBFS-silence as a projection fault"""
    x = np.random.default_rng(50).standard_normal((n, 2)).astype(np.float32)
    x = sosfilt(butter(1, 900, fs=SR, output="sos"), x, axis=0)
    x = sosfilt(butter(2, 40, btype="high", fs=SR, output="sos"), x, axis=0)
    return (x * db(rms_db) / np.sqrt((x ** 2).mean())).astype(np.float32)


# ------------------------------------------------------------------ framing
# Zoom is judged against the SOURCE, never against a 2.39 cover-crop. A 4:3 photo cover-cropped to 2.39 shows 56% of its
# height at "zoom 1.0"; a 4:3 photo cropped to 16:9 for H3 and then to 2.39 shows the same 56%; a 9:16 clip at x1.35 shows
# 74%. Every one of those was called "放大太大了" — the Ken Burns numbers were small, the crop under them was not.
MIN_VIS, MAX_ZOOM, MAX_MAG = 0.80, 1.15, 1.5


def probe_wh(p, still):
    if still: h, w = cv2.imread(p, cv2.IMREAD_COLOR).shape[:2]; return w, h          # imread applies EXIF orientation
    st = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                             "stream=width,height:stream_side_data=rotation", "-of", "json", p]))["streams"][0]
    rot = next((abs(int(d.get("rotation", 0))) for d in st.get("side_data_list", []) if "rotation" in d), 0)
    return (st["height"], st["width"]) if rot % 180 == 90 else (st["width"], st["height"])   # ffmpeg autorotates


def clip_fit(s, iw, ih):
    """(mode, zoom, y) for a clip; legacy "vert": y means fit"""
    if s.get("vert") is not None: return "fit", s.get("zoom", 1.0), s["vert"]
    return s.get("fit") or ("fit" if iw / ih < 2.0 else "cover"), s.get("zoom", 1.0), s.get("y", 0.0)


def framing(s):
    """visible fraction of the source (width, height) at the tightest moment, and output px per source px"""
    still = s["kind"] == "still"; iw, ih = probe_wh(s["src"], still)
    if still:
        mode = s.get("fit") or ("fit" if iw / ih < 2.0 else "cover")
        z = max(k[1] for k in s.get("kb", [[0, 1.06]]))
    else:
        mode, z, _ = clip_fit(s, iw, ih)
    sc = (H / ih if mode == "fit" else max(W / iw, H / ih)) * z
    return dict(id=s["id"], src=f"{iw}x{ih}", mode=mode, zoom=z, vis_w=min(1, W / (sc * iw)), vis_h=min(1, H / (sc * ih)), mag=sc)


def framing_gate(shots, out_dir):
    rows, bad = [], []
    for s in shots:
        if s["kind"] not in ("still", "clip"): continue
        r = framing(s); rows.append(r)
        flag = r["zoom"] > MAX_ZOOM or min(r["vis_w"], r["vis_h"]) < MIN_VIS
        if flag and not s.get("tight"): bad.append(r)
        print(f"  frame {r['id']:>6} {r['src']:>10} {r['mode']:5} zoom {r['zoom']:.2f}  shows {r['vis_w']:4.0%} w x {r['vis_h']:4.0%} h"
              f"  {r['mag']:.2f} px/px" + ("  TIGHT: " + s["tight"] if flag and s.get("tight") else "  << TOO TIGHT" if flag else "")
              + ("  << upscaled, soft: regenerate/replace" if r["mag"] > MAX_MAG else ""))
    with open(os.path.join(out_dir, "framing.tsv"), "w") as fh:
        fh.write("id\tsrc\tmode\tzoom\tvis_w\tvis_h\tpx_per_px\n")
        for r in rows: fh.write(f"{r['id']}\t{r['src']}\t{r['mode']}\t{r['zoom']:.2f}\t{r['vis_w']:.2f}\t{r['vis_h']:.2f}\t{r['mag']:.2f}\n")
    if bad: sys.exit(f"framing gate: {', '.join(r['id'] for r in bad)} show less than {MIN_VIS:.0%} of the source or zoom > "
                     f"{MAX_ZOOM}. Use the default fit / lower zoom, or add \"tight\": \"<reason>\" if the user asked for it.")


# ------------------------------------------------------------------ picture
def kb_at(keys, t):
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t <= t1:
            e = ease((t - t0) / max(t1 - t0, 1e-6)); return [x + (y - x) * e for x, y in zip(a, b)]
    return keys[-1][1:]


def blur_fill(img):
    """cover-fit, heavily blurred, desaturated and dimmed copy of img at W x H (float32)"""
    ih, iw = img.shape[:2]; c = max(W / iw, H / ih)
    bg = cv2.resize(img, (round(iw * c), round(ih * c)), interpolation=cv2.INTER_AREA)
    y0, x0 = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2; bg = bg[y0:y0 + H, x0:x0 + W]
    bg = cv2.GaussianBlur(cv2.resize(bg, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 10)
    bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    g = bg.mean(axis=2, keepdims=True); return np.clip(g + (bg - g) * 0.7 - 46, 0, 255)


def ken_burns(src, out, dur, keys, fit=None):
    img = cv2.cvtColor(cv2.imread(src, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    ih, iw = img.shape[:2]
    fit = fit or ("fit" if iw / ih < 2.0 else "cover")
    s0 = H / ih if fit == "fit" else max(W / iw, H / ih); bg = blur_fill(img) if fit == "fit" else None
    k = s0 * max(z for _, z, *_ in keys)
    if k < 1: img = cv2.resize(img, (round(iw * k), round(ih * k)), interpolation=cv2.INTER_AREA); s0 /= k; ih, iw = img.shape[:2]
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-"] + PRORES + [out], stdin=subprocess.PIPE)
    ones = np.ones((ih, iw), np.float32)
    for f in range(int(round(dur * FPS))):
        z, cx, cy = kb_at(keys, f / FPS); s = s0 * z
        if s * iw <= W: cx = 0.5
        else: cx = min(max(cx, W / (2 * s * iw)), 1 - W / (2 * s * iw))
        if s * ih <= H: cy = 0.5
        else: cy = min(max(cy, H / (2 * s * ih)), 1 - H / (2 * s * ih))
        M = np.float32([[s, 0, W / 2 - s * cx * iw], [0, s, H / 2 - s * cy * ih]])
        if bg is None:
            fr = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        else:
            fg = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
            a = cv2.warpAffine(ones, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
            fr = np.clip(fg * a + bg * (1 - a) + 0.5, 0, 255).astype(np.uint8)
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()


def atempo(r):
    parts = []
    while r < 0.5: parts.append("atempo=0.5"); r /= 0.5
    while r > 2.0: parts.append("atempo=2.0"); r /= 2.0
    return ",".join(parts + [f"atempo={r:.5f}"])


def build(s, seg):
    out = f"{seg}/{s['id']}.mov"
    if os.path.exists(out): return out
    k = s["kind"]
    if k == "ui":
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(s.get("ss", 0)), "-i", s["src"], "-vf", "fps=24,format=yuv422p10le,setsar=1",
             "-an"] + PRORES + ["-t", str(s["dur"]), out]); return out
    if k == "black":
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x010101:s={W}x{H}:r=24:d={s['dur']}"] + PRORES + [out]); return out
    tmp = f"{seg}/{s['id']}_pre.mov"
    if k == "still":
        ken_burns(s["src"], tmp, s["dur"], s.get("kb", [[0, 1.0, 0.5, 0.5], [s["dur"], 1.06, 0.5, 0.5]]), s.get("fit"))
    else:
        f = s["dur"] / s["sdur"]; vf = f"setpts=(PTS-STARTPTS)*{f:.6f}"; a = has_audio(s["src"])
        iw, ih = probe_wh(s["src"], False); mode, z, y = clip_fit(s, iw, ih)
        if mode == "fit":               # whole frame (x zoom) over a blurred, darkened copy of itself
            fh = 2 * round(H * max(z, 1.0) / 2); fw = 2 * round(iw * fh / ih / 2); cw = min(fw, W)
            vf += (f",split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40,"
                   f"eq=brightness=-0.18:saturation=0.7[bg];[b]scale={fw}:{fh}:flags=lanczos,crop={cw}:{H}:(iw-{cw})/2:(ih-{H})*(0.5+({y})/2)[fg];"
                   f"[bg][fg]overlay=(W-w)/2:0,setsar=1[vout]")
            v = ["-filter_complex", "[0:v]" + vf, "-map", "[vout]"] + (["-map", "0:a:0"] if a else [])
        else:
            v = ["-vf", vf]
        au = ["-af", atempo(1 / f), "-c:a", "pcm_s24le", "-ar", "48000"] if a else ["-an"]
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(s.get("ss", 0)), "-t", str(s["sdur"]), "-i", s["src"]] + v + au
            + ["-c:v", "prores_ks", "-profile:v", "3", "-t", str(s["dur"]), tmp])
    run([GRADE, "-c", "prores"] + s.get("grade", []) + [tmp, out]); os.remove(tmp)
    return out


def srt_time(t):
    ms = int(round(t * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# ------------------------------------------------------------------ main
def main(tl_path, out_dir):
    tl = json.load(open(tl_path, encoding="utf-8")); shots = tl["shots"]
    out_dir = os.path.abspath(out_dir)   # concat.txt resolves relative paths against its own directory
    seg = os.path.join(out_dir, "seg"); os.makedirs(seg, exist_ok=True)
    framing_gate(shots, out_dir)
    for s in shots:
        s["seg"] = None if s["kind"] == "montage" else build(s, seg)
        # lay the timeline on REAL lengths: retimed clips come out ~1 frame short and planned lengths drift
        s["real"] = s["dur"] if s["seg"] is None else probe_dur(s["seg"])
    start, t = {}, 0.0
    for s in shots: start[s["id"]] = t; t += s["real"]
    total = t; by = {s["id"]: s for s in shots}
    lst = os.path.join(out_dir, "concat.txt")
    with open(lst, "w") as fh:          # ProRes is intra-only, so concat inpoint/outpoint is frame-accurate
        for s in shots:
            if s["kind"] == "montage":
                for sid, a, d in s["cuts"]: fh.write(f"file '{by[sid]['seg']}'\ninpoint {a:.4f}\noutpoint {a + d:.4f}\n")
            else:
                fh.write(f"file '{s['seg']}'\n")
    base = os.path.join(out_dir, "base.mov"); run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])

    n = int(round(total * SR)); vo, mus, fx = (np.zeros((n, 2), np.float32) for _ in range(3))
    F = int(0.05 * SR); rin = (np.sin(np.linspace(0, math.pi / 2, F)) ** 2)[:, None]
    def place(bus, a, t0):
        i = int(round(t0 * SR)); a = a[:max(0, n - i)]; bus[i:i + len(a)] += a
    subs = []
    for s in shots:
        t0 = start[s["id"]]
        for f, off, *txt in s.get("vo", []):
            a = at_lufs(declick(load_audio(f), os.path.basename(f)), tl.get("vo_lufs", -16)); place(vo, a, t0 + off)
            subs.append((t0 + off, t0 + off + len(a) / SR, txt))
        if s["kind"] == "ui" and s.get("wav"):
            a = load_audio(s["wav"], s["dur"] + s.get("ss", 0))[int(s.get("ss", 0) * SR):]; a[:F] *= rin; a[-F:] *= rin[::-1]; place(fx, a, t0)
        if s["kind"] == "clip" and s.get("amb") is not None and has_audio(s["seg"]):
            a = load_audio(s["seg"], s["real"])
            if np.abs(a).max() > 1e-5: a = at_lufs(a, s["amb"]); a[:F] *= rin; a[-F:] *= rin[::-1]; place(fx, a, t0)
    for f, s0, off, s1, fo in tl.get("cues", []):
        L = start[s1] - start[s0]; a = load_audio(f, off + L)[int(off * SR):]
        a = at_lufs(a, tl.get("music_lufs", -23))[: int(L * SR)]
        k = int(fo * SR); a[-k:] *= (np.linspace(1, 0, k) ** 2)[:, None]; a[:F] *= rin; place(mus, a, start[s0])
    act = uniform_filter1d(maximum_filter1d((np.abs(vo).max(1) > db(-45)).astype(np.float32), int(0.4 * SR)), int(0.15 * SR))
    mus *= (1 - (1 - db(tl.get("duck_db", -6))) * act)[:, None]            # music ducks under narration
    for s in shots:
        if s.get("silence"):
            i, j = int(start[s["id"]] * SR), int((start[s["id"]] + s["real"]) * SR)
            for b in (vo, mus, fx): b[i:j] = 0
    mix = vo + mus + fx; mix *= db(tl.get("target_lufs", -18) - lufs(mix))
    lim = db(-1.5); hot = np.abs(mix) > lim * 0.7
    mix[hot] = np.sign(mix[hot]) * (lim * 0.7 + lim * 0.3 * np.tanh((np.abs(mix[hot]) - lim * 0.7) / (lim * 0.3)))
    mix += room_tone(n)
    fo = tl.get("fade_out", 0)
    if fo: k = int(fo * SR); mix[-k:] *= (np.linspace(1, 0, k) ** 2)[:, None]
    click_scan(mix)
    wav = os.path.join(out_dir, "cut_mix.wav"); write_wav(wav, mix)

    with open(os.path.join(out_dir, "cut.srt"), "w", encoding="utf-8") as fh:
        for i, (a, b, txt) in enumerate(sorted(subs, key=lambda x: x[0]), 1):
            fh.write(f"{i}\n{srt_time(a)} --> {srt_time(b + 0.3)}\n" + "\n".join(txt) + "\n\n")

    ins = ["-i", base]; fc = "[0:v]format=yuv444p10le[v0]"; k = 0
    for s in shots:
        if s.get("card"):
            k += 1; ins += ["-i", s["card"][0]]
            fc += f";[{k}:v]setpts=PTS-STARTPTS+{start[s['id']] + s['card'][1]:.4f}/TB[o{k}];[v{k - 1}][o{k}]overlay=format=auto:eof_action=pass[v{k}]"
    fc += (f";[v{k}]fade=t=out:st={total - fo:.3f}:d={fo}" if fo else f";[v{k}]null") + ",format=yuv420p[v]"
    out = os.path.join(out_dir, "cut.mp4")
    run(["ffmpeg", "-y", "-v", "error"] + ins + ["-i", wav, "-filter_complex", fc, "-map", "[v]", "-map", f"{k + 1}:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
         "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "256k", "-r", "24", "-movflags", "+faststart",
         "-t", f"{total:.3f}", out])
    json.dump(start, open(os.path.join(out_dir, "timeline.json"), "w"), indent=1)
    print(f"-> {out}  ({total:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
