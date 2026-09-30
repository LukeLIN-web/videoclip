"""Outpaint a portrait photo to 16:9 with Qwen-Image-2.1, then paste the original back in the center.
Usage: VC_MODELS=/path/to/models qwen_outpaint.py SRC.jpg PROMPT.txt SEED OUT.png
  Writes OUT.png (original pixels restored in the center) and OUT_raw.png (model output as generated)."""
import os, sys, time, torch
from PIL import Image, ImageFilter
from diffusers import QwenImage21Pipeline
src, pfile, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
W, H = 2752, 1536
im = Image.open(src).convert("RGB")
im = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
x0 = (W - im.width) // 2
canvas = Image.new("RGB", (W, H), (128, 128, 128)); canvas.paste(im, (x0, 0))
prompt = ("The center of this image is a real photograph; the flat grey areas on the left and right are empty. "
          "Fill only the grey areas so the photograph continues seamlessly outward, matching its perspective, lighting, color, lens and grain. "
          "Do not change the photograph in the center. " + open(pfile).read().strip())
pipe = QwenImage21Pipeline.from_pretrained(os.path.join(os.environ["VC_MODELS"], "Qwen-Image-2.1"), torch_dtype=torch.bfloat16).to("cuda")
t0 = time.time()
gen = pipe(prompt=prompt, image=canvas, height=H, width=W, num_inference_steps=40,
           generator=torch.Generator("cuda").manual_seed(seed)).images[0].resize((W, H), Image.LANCZOS)
gen.save(out.replace(".png", "_raw.png"))
# restore original pixels in the center with a 48px feathered seam
f = 48; mask = Image.new("L", (W, H), 0); mask.paste(255, (x0 + f, 0, x0 + im.width - f, H))
mask = mask.filter(ImageFilter.GaussianBlur(f / 2))
Image.composite(canvas, gen, mask).save(out); print("saved", out, f"{time.time()-t0:.0f}s")
