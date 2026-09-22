# -*- coding: utf-8 -*-
"""通用 docx 全文转储（段落 + 表格），保存到 txt 供审计。"""
import sys, io, os
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

def iter_block_items(parent):
    from docx.document import Document as _Doc
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

if __name__ == '__main__':
    dump(sys.argv[1], sys.argv[2])
