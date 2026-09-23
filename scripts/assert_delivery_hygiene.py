#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付件卫生断言（V-T1-6 · 2026-09-20）——任何 Word 再保存之后必跑。

用法：
    python assert_delivery_hygiene.py <file.docx> [<file.docx> ...] [--expect <md5>=<路径> ...]
    python assert_delivery_hygiene.py --help
    输出：逐件 Heading/TOC/updateFields/表数/字面标记/页脚域 状态 + md5。
    exit 0 = 全部卫生项通过（结构断言）+ md5 与 --expect 相符（若给出）；1 = 有 FAIL；
         2 = 用法 / 输入错误（缺参、文件不存在）

背景：实测 Word 再保存会（a）把 Heading styleId 规范化（1/2/3）；（b）丢失
settings.xml 的 updateFields；（c）（本项目实测）页脚 PAGE 域重复仍会被渲染成
「第 11 页」。本脚本把这些做成可复跑的断言，防止「交付件被静默改坏」。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import zipfile
from collections import Counter


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(path: str) -> dict:
    out = {"path": path, "md5": md5(path), "fails": [], "warns": []}
    z = zipfile.ZipFile(path)
    names = z.namelist()
    doc = z.read("word/document.xml").decode("utf-8")
    styles = z.read("word/styles.xml").decode("utf-8")
    settings = z.read("word/settings.xml").decode("utf-8") if "word/settings.xml" in names else ""

    # Heading styleId 定义与引用
    ids = {}
    for k in ("heading 1", "heading 2", "heading 3"):
        ids[k] = re.findall(r'w:styleId="([^"]+)"[^>]*>\s*<w:name w:val="' + k + '"', styles)
    out["heading_defs"] = ids
    refs = Counter(re.findall(r'<w:pStyle w:val="([^"]+)"', doc))
    out["heading_refs"] = {k: v for k, v in refs.items() if k in ("Heading1", "Heading2", "Heading3", "1", "2", "3")}
    if not ids["heading 1"]:
        out["fails"].append("Heading 1 样式定义缺失")
    elif ids["heading 1"][0] != "Heading1":
        out["warns"].append("Heading1 styleId 非标准命名（当前 %s）——Word 归一化，渲染通常无碍" % ids["heading 1"][0])

    # updateFields
    uf = "w:updateFields" in settings
    out["update_fields"] = uf
    if not uf:
        out["warns"].append("settings.xml 无 updateFields（打开时不会自动刷新域；如已定稿可接受，再编辑前先回补）")

    # TOC / 域 / 表格 / 字面标记
    out["toc_fields"] = doc.count('TOC \\o')
    if out["toc_fields"] == 0:
        out["fails"].append("无 TOC 域")
    out["tables"] = len(re.findall(r"<w:tbl>", doc))
    star = doc.count("**")
    out["literal_asterisks"] = star
    if star:
        out["fails"].append("字面 ** 残留 %d 处" % star)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))))
    out["cjk"] = cjk

    # 页脚/页眉域
    footers = {}
    for n in names:
        if re.search(r"(header|footer)\d*\.xml$", n):
            x = z.read(n).decode("utf-8")
            footers[n] = [i.strip() for i in re.findall(r"<w:instrText[^>]*>([^<]*)</w:instrText>", x)]
    out["fields_in_headers_footers"] = footers
    for n, instr in footers.items():
        if instr.count("PAGE") > 1:
            out["fails"].append("%s 含 %d 个 PAGE 域（重复 → 渲染成「第 11 页」）" % (n, instr.count("PAGE")))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="assert_delivery_hygiene.py",
                                 description="交付件卫生断言（Heading / TOC / updateFields / 表数 / 字面标记 / 页脚域）")
    ap.add_argument("paths", nargs="+", help="待检 .docx（可多件）")
    ap.add_argument("--expect", nargs="*", default=[], metavar="MD5=PATH",
                    help="期望 md5 对（形如 <md5>=<路径>，可给多组）")
    a = ap.parse_args(argv)
    expects = {}
    for spec in a.expect:
        if "=" in spec:
            m, p = spec.split("=", 1)
            expects[p] = m
    missing = [p for p in a.paths if not os.path.isfile(p)]
    if missing:
        print("输入错误：文件不存在或不是普通文件 → %s" % ", ".join(missing))
        return 2
    bad = False
    for p in a.paths:
        r = audit(p)
        print("===== %s =====" % p)
        print("  md5 =", r["md5"])
        print("  Heading 定义:", r["heading_defs"], "| 引用:", r["heading_refs"])
        print("  updateFields:", r["update_fields"], "| TOC 域:", r["toc_fields"],
              "| tables:", r["tables"], "| 字面**:", r["literal_asterisks"], "| 汉字:", r["cjk"])
        print("  页眉/页脚域:", r["fields_in_headers_footers"])
        for w in r["warns"]:
            print("  [WARN]", w)
        for f in r["fails"]:
            print("  [FAIL]", f)
        if p in expects:
            ok = r["md5"] == expects[p]
            print("  [%s] md5 与期望一致（expect %s）" % ("OK" if ok else "FAIL", expects[p][:12]))
            if not ok:
                bad = True
        if r["fails"]:
            bad = True
    print("\n%s" % ("HYGIENE PASS" if not bad else "HYGIENE HAS FAILURES"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
