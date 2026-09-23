#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把图片切成瓦片并放大逐片落盘（用于核对图中具体数字 / 分区送 OCR）。

用法:
  python tile_image.py <img> [--rows 3] [--cols 2] [--scale 2] [--outdir <目录>]
    缺省输出目录：<系统临时目录>/tile_image/<图片名>/
退出码: 0 = 成功；2 = 用法 / 输入错误；3 = 缺 Pillow（未执行，非通过）
"""
import argparse
import os
import pathlib
import sys
import tempfile

try:
    from PIL import Image
except ImportError:          # 延迟到 main 判定，保证无 Pillow 环境 --help 仍可用（rc=0）
    Image = None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tile_image.py", description="图片切瓦片并放大（分区核对 / OCR 辅助）")
    ap.add_argument("img", help="输入图片")
    ap.add_argument("--rows", type=int, default=3, help="行数（缺省 3）")
    ap.add_argument("--cols", type=int, default=2, help="列数（缺省 2）")
    ap.add_argument("--scale", type=int, default=2, help="放大倍数（缺省 2）")
    ap.add_argument("--outdir", default="", help="输出目录（缺省：系统临时目录）")
    a = ap.parse_args(argv)
    if Image is None:
        print("缺依赖：Pillow 未安装（pip install Pillow）→ 未执行（rc=3）")
        return 3
    if not os.path.isfile(a.img):
        print("输入错误：图片不存在或不是普通文件 → %s" % a.img)
        return 2
    if a.rows < 1 or a.cols < 1 or a.scale < 1:
        print("输入错误：--rows / --cols / --scale 必须 ≥ 1")
        return 2
    stem = pathlib.Path(a.img).stem
    outdir = pathlib.Path(a.outdir) if a.outdir else pathlib.Path(tempfile.gettempdir()) / "tile_image" / stem
    outdir.mkdir(parents=True, exist_ok=True)
    im = Image.open(a.img)
    W, H = im.size
    print("size:", W, H)
    n = 0
    for r in range(a.rows):
        for c in range(a.cols):
            box = (int(c * W / a.cols), int(r * H / a.rows),
                   int((c + 1) * W / a.cols), int((r + 1) * H / a.rows))
            t = im.crop(box)
            t = t.resize((t.width * a.scale, t.height * a.scale), Image.LANCZOS)
            p = outdir / f"{stem}_t{r}{c}.png"
            t.save(p)
            n += 1
            print("tile", r, c, p)
    print("total", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
