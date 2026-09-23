#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按相对坐标裁剪并放大（图中细节核对辅助）。

用法:
  python crop_zoom.py <img> <x0> <y0> <x1> <y1> <scale> <out>
    x0/y0/x1/y1：相对坐标（0–1，相对图像宽高；左上 → 右下）
    scale      ：放大倍数（> 0）
    out        ：输出图片路径
退出码: 0 = 成功；2 = 用法 / 输入错误（缺参、文件不存在）；3 = 缺 Pillow（未执行，非通过）
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:          # 延迟到 main 判定，保证无 Pillow 环境 --help 仍可用（rc=0）
    Image = None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="crop_zoom.py", description="按相对坐标裁剪并放大（图中细节核对辅助）")
    ap.add_argument("img", help="输入图片")
    ap.add_argument("x0", type=float, help="左上 x（相对 0–1）")
    ap.add_argument("y0", type=float, help="左上 y（相对 0–1）")
    ap.add_argument("x1", type=float, help="右下 x（相对 0–1）")
    ap.add_argument("y1", type=float, help="右下 y（相对 0–1）")
    ap.add_argument("scale", type=float, help="放大倍数（> 0）")
    ap.add_argument("out", help="输出图片路径")
    a = ap.parse_args(argv)
    if Image is None:
        print("缺依赖：Pillow 未安装（pip install Pillow）→ 未执行（rc=3）")
        return 3
    if not os.path.isfile(a.img):
        print("输入错误：图片不存在或不是普通文件 → %s" % a.img)
        return 2
    if a.scale <= 0:
        print("输入错误：scale 必须 > 0 → %s" % a.scale)
        return 2
    im = Image.open(a.img)
    W, H = im.size
    box = (int(a.x0 * W), int(a.y0 * H), int(a.x1 * W), int(a.y1 * H))
    t = im.crop(box)
    t = t.resize((int(t.width * a.scale), int(t.height * a.scale)), Image.LANCZOS)
    t.save(a.out)
    print("crop", box, "->", t.size, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
