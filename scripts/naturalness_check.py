#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多赛道 · 写作自然度质检（五指标）

方法思维借鉴开源 chinese-academic-paper-writing 的 ai_detector（连接词/句首重复/
段落方差/禁用词量化），代码为本轨自研，纯标准库、零依赖。

用途（T3/T5）：让「本人重写后的稿子」读起来像人写的。铁律 6 边界：
质检是自然度自查，不是规避学术诚信审查的工具。

用法:
  python naturalness_check.py 论文.md [更多.md ...]
  python naturalness_check.py --help                # usage（rc=0）

输出: 每文件五指标得分 + 风险行清单（启发式阈值，非硬标准）
退出码: 0 = 成功（质检只做提示，不判失败）；2 = 用法 / 输入错误（缺参、文件不存在）
"""
import argparse
import re
import sys
import statistics
from pathlib import Path

# ---- 词表（启发式，可按项目增删）----
CLICHES = [  # AI 套话
    "综上所述", "总而言之", "总的来说", "不难发现", "众所周知", "值得注意的是",
    "值得一提的是", "毋庸置疑", "显而易见", "在当今社会", "随着科技的发展",
    "随着社会的进步", "在当今时代", "扮演着", "发挥着重要作用", "日益",
    "愈发", "至关重要", "具有重要意义", "不言而喻", "由此可见", "事实上",
    "然而值得注意的是", "从某种意义上说",
]
CONNECTIVES = [  # 逻辑连接词（正常使用无妨，过密提示流水账）
    "然而", "因此", "此外", "同时", "并且", "但是", "不过", "总之",
    "首先", "其次", "最后", "一方面", "另一方面", "不仅", "而且",
    "进而", "从而", "与此同时", "除此之外", "总的来说", "也就是说",
]
TEMPLATE_OPENERS = ["首先", "其次", "再次", "最后", "第一", "第二", "第三"]  # 模板化段落引导

SENT_SPLIT = re.compile(r"[^。！？；\n]+[。！？；]?")
PARA_SPLIT = re.compile(r"\n\s*\n")


def sentences(text: str) -> list:
    return [s.strip() for s in SENT_SPLIT.findall(text) if len(s.strip()) >= 4]


def paragraphs(text: str) -> list:
    return [p.strip() for p in PARA_SPLIT.split(text) if len(p.strip()) >= 20]


def count_hits(text: str, words: list) -> dict:
    hits = {}
    for w in words:
        n = text.count(w)
        if n:
            hits[w] = n
    return hits


def top_starting_bigrams(sents: list, topn: int = 3) -> list:
    """句首重复检测：统计句首 2 字词频"""
    freq = {}
    for s in sents:
        key = s[:2]
        if key and not key[0].isdigit():
            freq[key] = freq.get(key, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: -x[1])
    return [(k, v) for k, v in ranked if v >= 3][:topn]


def check_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    sents = sentences(text)
    paras = paragraphs(text)
    n_sent = len(sents)
    n_para = len(paras)
    total_chars = len(re.sub(r"\s", "", text))

    print(f"\n===== {path.name} ({total_chars}字, {n_sent}句, {n_para}段) =====")

    # ① 套话密度（每千字命中次数）
    clich = count_hits(text, CLICHES)
    clich_n = sum(clich.values())
    clich_rate = clich_n / max(total_chars / 1000, 1)
    flag1 = "⚠️ 偏高" if clich_rate >= 1.0 else ("参考" if clich_rate >= 0.5 else "ok")
    print(f"① 套话密度: {clich_n} 次 / {clich_rate:.2f}‰千字 [{flag1}]")
    if clich:
        print("   命中: " + ", ".join(f"{w}×{n}" for w, n in sorted(clich.items(), key=lambda x: -x[1])[:6]))

    # ② 连接词密度（每句连接词数）
    conn = count_hits(text, CONNECTIVES)
    conn_n = sum(conn.values())
    conn_rate = conn_n / max(n_sent, 1)
    flag2 = "⚠️ 过密(流水账感)" if conn_rate >= 0.6 else ("参考" if conn_rate >= 0.35 else "ok")
    print(f"② 连接词密度: {conn_n} 次 / {conn_rate:.2f}/句 [{flag2}]")

    # ③ 句首重复（Top 句首词，>=3 次才报）
    tops = top_starting_bigrams(sents)
    flag3 = "⚠️ 有重复" if tops else "ok"
    print(f"③ 句首重复: {tops if tops else '无'} [{flag3}]")

    # ④ 段落长度方差（变异系数 <0.35 提示段落过匀、模板感；纯参考）
    if n_para >= 3:
        plens = [len(p) for p in paras]
        mean = statistics.mean(plens)
        cv = statistics.stdev(plens) / mean if mean else 0
        flag4 = "参考:段落过匀?" if cv < 0.35 else "ok"
        print(f"④ 段落长度: 均值{mean:.0f}字 变异系数{cv:.2f} [{flag4}]")
    else:
        flag4 = "n/a"
        print("④ 段落长度: 段落过少，跳过")

    # ⑤ 模板化段落（段首为 首先/其次/第一… 引导的列举结构）
    tpl = [p[:24] for p in paras if any(p.startswith(o) for o in TEMPLATE_OPENERS)]
    flag5 = "⚠️ 存在模板段" if tpl else "ok"
    print(f"⑤ 模板化段落: {len(tpl)} 段 {tpl[:3]} [{flag5}]")

    # 风险行定位（套话/超长机械列举行）
    risky = []
    for i, s in enumerate(sents, 1):
        hitw = [w for w in CLICHES if w in s and len(w) >= 4]
        if hitw:
            risky.append((i, s[:50], hitw[:3]))
    if risky:
        print("   风险句:")
        for i, s, w in risky[:8]:
            print(f"   L{i:>4} {s}… ← {'/'.join(w)}")
    print(f"   判定: {'建议人工过一遍风险句' if (flag1 != 'ok' or flag2 != 'ok' or flag3 != 'ok' or flag5 != 'ok') else '无明显 AI 味信号'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="naturalness_check.py", description="写作自然度质检（五指标：套话/连接词/句首重复/段长方差/模板段）")
    ap.add_argument("paths", nargs="+", help="待检 .md（可多份）")
    a = ap.parse_args(argv)
    missing = [p for p in a.paths if not Path(p).is_file()]
    if missing:
        print("输入错误：文件不存在或不是普通文件 → %s" % ", ".join(missing))
        return 2
    for p in a.paths:
        check_file(Path(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
