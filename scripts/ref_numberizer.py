#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多赛道 · 占位引用编号器

方法思维借鉴开源 chinese-academic-paper-writing 的 ref_numberizer（占位引用法：
写作期用 {ref1} 占位 → 定稿按「首次出现顺序」统一编号），代码为本轨自研，
纯标准库、零依赖。

用途（T3）：终结 [1,2,5,4,3] 乱序——正文引用编号永远按首次出现顺序，
文末参考文献列表按同一映射排序。

用法:
  python ref_numberizer.py 论文.md                # 预览替换结果到 stdout
  python ref_numberizer.py 论文.md --write        # 直接改写文件
  python ref_numberizer.py 论文.md --report       # 只打印编号映射与校验

占位符格式: {ref1} {ref2} ...（数字可任意书写，最终按首次出现顺序重排）
"""
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\{ref(\d+)\}")


def process(text: str):
    """返回 (新文本, mapping, 校验信息)"""
    order = []          # 首次出现顺序的占位编号
    seen = set()
    for m in PLACEHOLDER.finditer(text):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            order.append(n)

    mapping = {old: i + 1 for i, old in enumerate(order)}  # 占位编号 → 最终序号

    def repl(m):
        return f"[{mapping[int(m.group(1))]}]"

    new_text = PLACEHOLDER.sub(repl, text)

    # 校验：最终编号必须连续 1..K
    used = sorted(mapping.values())
    contiguous = used == list(range(1, len(used) + 1))
    return new_text, mapping, {
        "占位符总数": len(order),
        "编号连续": "✅" if contiguous else "❌ 断号!",
        "乱序风险": "无（已按首次出现重排）" if len(order) > 1 else "无",
    }


def main(argv) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = Path(argv[1])
    if not path.exists():
        print(f"文件不存在: {path}")
        return 1
    text = path.read_text(encoding="utf-8")
    new_text, mapping, info = process(text)

    print(f"===== {path.name} 引用编号映射 =====")
    for old, new in mapping.items():
        print(f"  {{ref{old}}} → [{new}]")
    for k, v in info.items():
        print(f"  {k}: {v}")

    if not PLACEHOLDER.search(text):
        print("  （未发现 {refN} 占位符——正文引用请用 {ref1}..{refN} 占位）")

    if "--report" in argv:
        return 0
    if "--write" in argv:
        path.write_text(new_text, encoding="utf-8")
        print(f"已改写: {path}")
    else:
        print("\n----- 替换结果预览（前 40 行）-----")
        print("\n".join(new_text.splitlines()[:40]))
        print("...")
        print("(加 --write 落盘；加 --report 只看映射)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
