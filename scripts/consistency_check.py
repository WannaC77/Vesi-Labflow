#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多赛道 · 三处口径一致性核验（申报书 / 论文 / 附件）

用途（T4/T5 · 作品完整性审查员作业面）：四件套中「作品名称 / 作者 / 指导教师 /
关键统计数字」必须在申报书、论文、附件目录三处一致——题目三处同题、
数据三处同值、署名三处一致。评审/查重环境下，三处口径打架是头号扣分点。

v1 实现：通用 markdown 字段提取（官方申报书模板到手后，可按其字段结构调整提取规则）。
纯标准库、零依赖。**数字比对纳入失败判定**（v0 默认仅提示 = 无法自动化拦截）。

v1 相对 v0 的修复（2026-09-18）：
  F1 数字比对由「只比第 1、2 份」改为「N 份全组口径」——v0 硬编码 pair_sets[0]/[1]，
     第 3 份及以后的文件参与提取、参与打印、却不参与比对（静默漏检）。
  F2 数字差异默认纳入失败判定（exit 1）；草稿期可用 --loose 退回提示模式。
  F3 题目提取：H1 兜底不再吞掉「题目: / 作品名称:」前缀——v0 会把「# 题目: X」
     整体作为标题，与「作品名称: X」形态被判为不一致（同一文档自相冲突）。

用法:
  python consistency_check.py 申报书.md 论文.md 附件目录.md [文件4.md ...] [--loose]
  输出: 逐字段全组比对报告；不一致时 exit 1（--loose 时数字差异降为提示）
"""
import re
import sys
from pathlib import Path

# ---- 字段提取规则 ----
# 题目优先级：①「题目/作品名称:」引导行 ② 表格字段（作品名称/题目）③ H1
# （H1 可能是文档类型名如「附件材料」，故排最后；F3：H1 命中后需剥离字段前缀）
TITLE_LINE = re.compile(r"^(?:题目|作品名称|论文题目)[:：]\s*(.+)$", re.M)
TITLE_H1 = re.compile(r"^#+\s*(.+)$", re.M)
# F3：H1 行内可能仍带字段前缀（如「# 题目: X」），剥离后再与其他形态比较
H1_PREFIX = re.compile(r"^(?:题目|作品名称|论文题目)[:：]\s*")
AUTHOR_RES = re.compile(r"^(?:作者|完成人)[:：]\s*(.+)$", re.M)
ADVISOR_RES = re.compile(r"^(?:指导教师|指导老师|导师)[:：]\s*(.+)$", re.M)
TABLE_FIELD = re.compile(r"^\|\s*(题目|作品名称|作者|指导教师|导师)\s*\|\s*([^|]+?)\s*\|", re.M)
NUM_PAIR = re.compile(r"(\d+(?:\.\d+)?)\s*[±±]\s*(\d+(?:\.\d+)?)")  # 均值±SD
NUM_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(%|mg/kg|mg/mL|μg/mL|ng/mL|h|min|nm|kDa|mL)")


def extract_fields(text: str) -> dict:
    title = None
    author = None
    advisor = None
    m = TITLE_LINE.search(text)          # ① 引导行
    if m:
        title = m.group(1).strip()
    m = AUTHOR_RES.search(text)
    if m:
        author = m.group(1).strip()
    m = ADVISOR_RES.search(text)
    if m:
        advisor = m.group(1).strip()
    for m in TABLE_FIELD.finditer(text):  # ② 表格字段（未提取到的字段才用）
        k, v = m.group(1), m.group(2).strip()
        if k in ("题目", "作品名称") and not title:
            title = v
        elif k == "作者" and not author:
            author = v
        elif k in ("指导教师", "导师") and not advisor:
            advisor = v
    if not title:                        # ③ H1（最后兜底）
        for m in TITLE_H1.finditer(text):
            cand = m.group(1).strip()
            cand = H1_PREFIX.sub("", cand).strip()   # F3：剥离可能的字段前缀
            if cand:
                title = cand
                break
    pairs = sorted({(a, b) for a, b in NUM_PAIR.findall(text)})
    units = sorted({(n, u) for n, u in NUM_UNIT.findall(text)})
    return {"题目": title, "作者": author, "指导教师": advisor,
            "均值±SD数对": pairs, "带单位数值": units}


def compare(fields_list, names):
    """返回 problems 列表；每项为 (key, detail)。

    F1：数字比对采用「N 份全组口径」——任一数对未被全部文件覆盖即报。
    """
    problems = []
    for key in ("题目", "作者", "指导教师"):
        vals = {f[key] for f in fields_list}
        vals.discard(None)
        if len(vals) > 1:
            problems.append((key, vals))

    # ---- F1 数字全组比对（v0 只比 pair_sets[0] vs [1]）----
    pair_sets = [set(f["均值±SD数对"]) for f in fields_list]
    uni = set().union(*pair_sets) if pair_sets else set()
    if len(pair_sets) >= 2 and uni:
        for pair in sorted(uni):
            held = [n for n, s in zip(names, pair_sets) if pair in s]
            if 0 < len(held) < len(pair_sets):
                missing = [n for n, s in zip(names, pair_sets) if pair not in s]
                problems.append((
                    "均值±SD数对未全组齐备",
                    f"{pair[0]}±{pair[1]} 出现在 {held}，缺失于 {missing}",
                ))
    return problems


def main(argv) -> int:
    loose = "--loose" in argv          # F2：草稿期可用 --loose 退回提示模式
    strict = "--strict" in argv        # 兼容旧调用（v0 的 --strict 现为默认行为）
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if len(paths) < 2:
        print(__doc__)
        return 1
    names, fields = [], []
    for p in paths:
        fp = Path(p)
        if not fp.exists():
            print(f"文件不存在: {p}")
            return 1
        names.append(fp.name)
        fields.append(extract_fields(fp.read_text(encoding="utf-8", errors="ignore")))

    print(f"===== 全组一致性核验（{len(paths)} 份）: {' vs '.join(names)} =====")
    for n, f in zip(names, fields):
        print(f"\n[{n}]")
        for k in ("题目", "作者", "指导教师"):
            print(f"  {k}: {f[k] or '（未提取到）'}")
        print(f"  均值±SD数对: {len(f['均值±SD数对'])} 个 | 带单位数值: {len(f['带单位数值'])} 个")

    problems = compare(fields, names)
    print("\n----- 比对结果 -----")
    if not problems:
        print(f"✅ 全组一致（{len(paths)} 份：题目/署名无差异；均值±SD 数对全组齐备）")
        return 0
    bad = False
    for key, detail in problems:
        is_num = key.startswith("均值")
        if is_num and loose:
            print(f"⚠️ [参考·--loose] {key}: {detail}")
        else:
            bad = True
            print(f"❌ {key}: {detail}")
    print("判读: 题目/署名不一致 = 必须修；"
          f"数字数对未全组齐备 = 必须修（--loose 草稿期可降为提示）。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
