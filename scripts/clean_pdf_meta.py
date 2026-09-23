#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 元数据清理工具（S7 匿名合规配套）

PDF 文件自带元数据（作者/创建者/标题等），常默认携带电脑用户名或真实姓名——
这是评审匿名规则下最容易被忽略的泄密点。

用法:
    python clean_pdf_meta.py <input.pdf> [-o output.pdf]

行为:
    - 若无 -o，生成 <原名>_clean.pdf（不动原文件）
    - 清空 Author / Creator / Producer / Title / Subject / Keywords / CreationDate 等

依赖:
    pypdf —— 未安装时自动提示安装命令:
uv pip install --python <venv>/python.exe pypdf
      （或: pip install pypdf）
"""
import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="清除 PDF 元数据（匿名合规）")
    ap.add_argument("pdf", help="输入 PDF 路径")
    ap.add_argument("-o", "--out", default=None, help="输出路径（默认: <原名>_clean.pdf）")
    args = ap.parse_args()

    src = Path(args.pdf)
    if not src.exists():
        print(f"输入错误：文件不存在或不是普通文件 → {src}")
        sys.exit(2)

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("缺依赖：pypdf 未安装（pip install pypdf）→ 未执行（rc=3）")
        sys.exit(3)

    out = Path(args.out) if args.out else src.with_name(src.stem + "_clean" + src.suffix)

    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # 清空元数据（pypdf: 赋空字符串会移除该字段）
    meta = {}
    for k in ("/Title", "/Author", "/Subject", "/Keywords", "/Creator",
              "/Producer", "/CreationDate", "/ModDate"):
        meta[k] = ""
    writer.add_metadata(meta)

    with open(out, "wb") as f:
        writer.write(f)

    # 验证：读回并打印剩余元数据
    check = PdfReader(str(out))
    md = check.metadata
    leftover = {k: v for k, v in (md or {}).items() if v}
    print(f"✅ 已生成清理版: {out}")
    if leftover:
        print(f"⚠️ 仍有元数据残留: {leftover}（请人工确认这些字段不泄密）")
    else:
        print("✅ 元数据已全部清空")
    print("\n建议: 用 PDF 阅读器打开检查一遍正文内容与页面缩略图，确认无水印/标识。")


if __name__ == "__main__":
    main()
