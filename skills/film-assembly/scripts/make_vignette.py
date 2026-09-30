"""Generates the 16-bit vignette mask used by grade.sh (multiply blend)."""
import numpy as np, cv2, os
W, H = 1920, 804
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
nx = (x - W / 2) / (W / 2); ny = (y - H / 2) / (H / 2)
r = np.sqrt(nx ** 2 * 0.72 + ny ** 2 * 0.85)
v = np.clip(1 - 0.22 * np.clip(r, 0, 1.6) ** 2.4, 0, 1)
cv2.imwrite(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vignette_1920x804.png"),
            (np.dstack([v, v, v]) * 65535 + 0.5).astype(np.uint16))
print("vignette corner", v[0, 0], "edge", v[H // 2, 0])
