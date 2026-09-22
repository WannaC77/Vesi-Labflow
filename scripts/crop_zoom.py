# -*- coding: utf-8 -*-
"""按相对坐标裁剪并放大。用法: python crop_zoom.py <img> <x0> <y0> <x1> <y1> <scale> <out>"""
import sys
from PIL import Image
img, x0, y0, x1, y1, scale, out = sys.argv[1], *map(float, sys.argv[2:6]), float(sys.argv[6]), sys.argv[7]
im = Image.open(img)
W, H = im.size
box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
t = im.crop(box)
t = t.resize((int(t.width * scale), int(t.height * scale)), Image.LANCZOS)
t.save(out)
print("crop", box, "->", t.size, out)
