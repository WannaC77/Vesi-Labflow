# -*- coding: utf-8 -*-
"""按名称批量 OCR 图片（自备端点），输出到独立目录，避免并发覆盖。

用法:
    # 1) 配置端点（三种环境变量，全部由你自备；本仓库不内置任何端点/密钥/模型名）
    #    OCR_BASE_URL  = 你的 OpenAI 兼容端点基址，例如 https://your-endpoint.example/v1
    #    OCR_MODEL     = 你要使用的视觉模型名
    #    OCR_API_KEY   = 你的密钥
    # 2) 运行
    python batch_ocr.py <outdir> <img1> [img2] ...
    python batch_ocr.py --help

退出码: 0 = 全部完成 · 1 = 有图失败 · 2 = 用法/输入错误（缺参、图片不存在）·
        3 = 未配置端点（未执行，不伪造结果）

设计要点:
    · 逐图输出 <outdir>/<name>.txt；**已存在则跳过**（防覆盖、可断点续跑）
    · 单图失败写 [FAIL] 说明并继续下一张（批量不中断）
    · 不读取任何本机私有配置文件；端点/密钥只从环境变量取
"""
import argparse
import base64
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE_URL = os.environ.get("OCR_BASE_URL", "").rstrip("/")
MODEL = os.environ.get("OCR_MODEL", "")
API_KEY = os.environ.get("OCR_API_KEY", "")

PROMPT = ("请对这张科研示意图逐字转写其中的全部文字。要求：\n"
          "1) 按图的空间结构（分栏/分框/箭头顺序）组织，标明每个框的标题；\n"
          "2) 数字、单位（μL、μg/mL、ng/mL、nm、kDa、℃、×g、min、h）、上下标必须精确照抄，"
          "看不清写[?]，绝对不要猜测或纠错；\n"
          "3) 先给【本页要点】一句话，再给【全文转写】。")


def _missing_env():
    return [k for k, v in (("OCR_BASE_URL", BASE_URL), ("OCR_MODEL", MODEL), ("OCR_API_KEY", API_KEY)) if not v]


def ocr(img):
    """单图 OCR；失败返回 '[FAIL] ...'（不抛异常，批量不中断）"""
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    payload = {"model": MODEL, "temperature": 0.0, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,%s" % b64}},
        {"type": "text", "text": PROMPT}]}]}
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % API_KEY})
    try:
        r = urllib.request.urlopen(req, timeout=240)
        return json.loads(r.read().decode())["choices"][0]["message"]["content"]
    except Exception as e:                                    # noqa
        return "[FAIL] %s" % e


def main(argv=None):
    ap = argparse.ArgumentParser(prog="batch_ocr.py",
                                 description="按名称批量 OCR 图片（自备端点；逐图输出 <outdir>/<name>.txt，已存在则跳过）")
    ap.add_argument("outdir", help="输出目录")
    ap.add_argument("images", nargs="+", help="待识别图片（可多张）")
    a = ap.parse_args(argv)
    miss = _missing_env()
    if miss:
        print("[SKIP] 未配置 OCR 端点：缺少 " + ", ".join(miss))
        print("       请先设置环境变量（本仓库不内置端点/密钥/模型名），再重试。未执行（rc=3）")
        return 3
    missing_img = [p for p in a.images if not os.path.isfile(p)]
    if missing_img:
        print("输入错误：图片不存在或不是普通文件 → %s" % ", ".join(missing_img))
        return 2
    outdir = pathlib.Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fail = 0
    for img in a.images:
        stem = re.sub(r'[^\w\u4e00-\u9fff.-]', '_', pathlib.Path(img).stem)
        out = outdir / ("%s.txt" % stem)
        if out.exists():
            print("%s: 已存在，跳过（防覆盖） -> %s" % (stem, out), flush=True)
            continue
        txt = ocr(img)
        out.write_text(txt, encoding="utf-8")
        if txt.startswith("[FAIL]"):
            fail += 1
        print("%s: %d chars -> %s" % (stem, len(txt), out), flush=True)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
