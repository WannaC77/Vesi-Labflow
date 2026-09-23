#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 docx 全文转储（段落 + 表格）→ txt，供逐字审计 / 交付前对质。

用法:
  python dump_docx_full.py <file.docx> <out.txt>
退出码: 0 = 成功；2 = 用法 / 输入错误（缺参、文件不存在）；3 = 缺 python-docx（未执行，非通过）
"""
import argparse
import io
import os
import sys


def iter_block_items(parent):
    from docx.document import Document as _Doc
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.ns import qn
    if isinstance(parent, _Doc):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._tc
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)


def dump(path, out):
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc = Document(path)
    lines = []
    ti = 0
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            t = block.text.strip()
            st = block.style.name if block.style is not None else ''
            if t:
                lines.append(f"[P|{st}] {t}")
            else:
                lines.append("[P|empty]")
        else:
            ti += 1
            lines.append(f"=== TABLE {ti} ({len(block.rows)}x{len(block.columns)}) ===")
            for ri, row in enumerate(block.rows):
                cells = []
                seen = set()
                for c in row.cells:
                    if id(c._tc) in seen:
                        continue
                    seen.add(id(c._tc))
                    cells.append(c.text.replace('\n', ' / ').strip())
                lines.append(f"  R{ri}: " + " | ".join(cells))
            lines.append(f"=== /TABLE {ti} ===")
    io.open(out, 'w', encoding='utf-8').write("\n".join(lines))
    print("wrote", out, len(lines), "lines")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dump_docx_full.py", description="docx 全文转储（段落 + 表格）→ txt")
    ap.add_argument("path", help="输入 .docx")
    ap.add_argument("out", help="输出 .txt")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.path):
        print("输入错误：文件不存在或不是普通文件 → %s" % a.path)
        return 2
    try:
        import docx  # noqa: F401
    except ImportError:
        print("缺依赖：python-docx 未安装（pip install python-docx）→ 未执行（rc=3）")
        return 3
    dump(a.path, a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
