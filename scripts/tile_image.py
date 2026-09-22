# -*- coding: utf-8 -*-
"""把图片切成 3x2 瓦片并 2 倍放大，逐片 OCR（用于核对图中具体数字）。"""
import sys, os, subprocess, pathlib
from PIL import Image

img = sys.argv[1]
outdir = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "audit" / "tiles"
outdir.mkdir(parents=True, exist_ok=True)
im = Image.open(img)
W, H = im.size
print("size:", W, H)
rows, cols = 3, 2
n = 0
for r in range(rows):
    for c in range(cols):
        box = (int(c * W / cols), int(r * H / rows), int((c + 1) * W / cols), int((r + 1) * H / rows))
        t = im.crop(box)
        t = t.resize((t.width * 2, t.height * 2), Image.LANCZOS)
        p = outdir / f"{pathlib.Path(img).stem}_t{r}{c}.png"
        t.save(p)
        n += 1
        print("tile", r, c, p)
print("total", n)
