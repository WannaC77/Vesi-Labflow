#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内部版实验记录 → 匿名提交版 转写工具（S4 工作流配套）

用法:
    python transcribe_record.py <内部版.md> [--out <输出目录>] [--replace 旧=新 ...]

功能:
    1. 解析内部版 YAML frontmatter（不依赖 pyyaml，纯标准库）
    2. 生成匿名提交版 markdown 骨架：标题 / 摘要占位 / 匿名正文 / 心得占位
    3. 身份信息处理:
       - operator / data_file / linked_record 整条剥离
       - 批号 BATCH-xxx → 「本批次」，试剂货号 → 「所用试剂（批次见方法）」
       - --replace 参数可追加自定义替换（如 仪器型号=仪器）
    4. 输出到 _提交/ 目录（或 --out 指定目录）

注意:
    - 摘要与心得是「探究思维」展示，脚本只留占位，须由本人撰写（铁律 6）。
    - PDF 元数据清理见同目录 clean_pdf_meta.py（导出 PDF 后执行）。
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# frontmatter 中会被剥离的字段（身份/内部信息）
STRIP_FIELDS = {"operator", "data_file", "linked_record", "author", "status", "instrument"}
# 会被转换的字段（批号 → 匿名表述）
BATCH_RE = re.compile(r"\bBATCH-[A-Za-z0-9]+", re.IGNORECASE)
LOT_RE = re.compile(r"\b[A-Z0-9]{3,}-\d{4,}[A-Z0-9]*\b")  # 试剂货号样式，保守匹配


def parse_frontmatter(text: str):
    """解析 --- 包裹的 YAML frontmatter，返回 (fields: dict, body: str)。纯正则，够用即可。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
    return fields, m.group(2)


def anonymize_body(body: str, replaces: list) -> str:
    """正文匿名化：批号→本批次、货号→所用试剂、自定义替换。"""
    out = body
    out = BATCH_RE.sub("本批次", out)
    out = LOT_RE.sub("所用试剂（批次见方法）", out)
    for old, new in replaces:
        out = out.replace(old, new)
    # 常见实验室用语清洗（保守）
    out = out.replace("本实验室", "本研究").replace("本课题组", "本研究")
    out = out.replace("我们组", "本研究").replace("我组", "本研究")
    return out


def build_title(fields: dict, date_str: str) -> str:
    """从 type + batch 生成匿名标题。"""
    ftype = fields.get("type", "实验")
    batch = fields.get("batch", "")
    entity = "本批次" if batch else ""
    return f"{ftype}实验——{entity}（{date_str}）"


def main():
    ap = argparse.ArgumentParser(description="内部版实验记录 → 匿名提交版转写")
    ap.add_argument("md", help="内部版 markdown 路径")
    ap.add_argument("--out", default=None, help="输出目录（默认: 输入文件同级 _提交/）")
    ap.add_argument("--replace", action="append", default=[], metavar="旧=新",
                    help="自定义替换，可多次（如 --replace 'Zetasizer=粒度仪'）")
    args = ap.parse_args()

    src = Path(args.md)
    if not src.exists():
        print(f"输入错误：文件不存在或不是普通文件 → {src}")
        sys.exit(2)
    text = src.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)

    if not fields:
        print("输入错误：该文件没有 YAML frontmatter——确认是内部版记录（见 S4 双层结构）？")
        sys.exit(2)

    # 输出目录
    if args.out:
        out_dir = Path(args.out)
    else:
        out_dir = src.parent.parent / "_提交"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 记录日期：优先 frontmatter date，缺省用今天
    date_str = fields.get("date") or f"{datetime.now():%Y-%m-%d}"

    # 标题
    title = build_title(fields, date_str)
    out_name = f"{date_str}-{fields.get('type', '实验')}-提交版.md"
    out_path = out_dir / out_name

    replaces = []
    for r in args.replace:
        if "=" in r:
            replaces.append(r.split("=", 1))
    # data_file 字样在正文中的残留也匿名化
    anon_body = anonymize_body(body, replaces)
    anon_body = anon_body.replace("data_file", "原始数据文件")

    # 组装提交版
    out = f"""【标题】{title}

【摘要】（本人撰写：目的 → 方法 → 结果 → 下一步，3-5 句，评委 20 秒能懂）

【正文/附件】（以下为内部版正文的匿名转写，数据/图表须核对后附 PDF ≤20MB）

{anon_body.strip()}

【心得】（本人撰写：踩了什么坑/发现了什么/为什么这么做，1-3 句）

---
<!-- 转写自: {src.name} | 生成时间: {datetime.now():%Y-%m-%d %H:%M} -->
"""
    out_path.write_text(out, encoding="utf-8")
    print(f"✅ 已生成提交版骨架: {out_path}")

    # 身份剥离提示
    stripped = [f for f in STRIP_FIELDS if f in fields]
    print(f"\n已剥离字段: {', '.join(stripped) if stripped else '(无)'}")
    if "operator" in fields:
        print("  - operator 已剥离（提交版不署名）")
    if "data_file" in fields:
        print("  - data_file 已剥离（原始数据路径属内部信息）")
    print("""
⚠️ 后续步骤（人工）:
  1. 撰写【摘要】与【心得】（探究思维展示，勿流水账）
  2. 核对正文匿名：批号/货号/实验室痕迹/人脸照片/水印
  3. 导出 PDF（≤20MB），执行: python clean_pdf_meta.py <导出的.pdf>
  4. 当日 23:59:59 前上传报名系统
""")


if __name__ == "__main__":
    main()
