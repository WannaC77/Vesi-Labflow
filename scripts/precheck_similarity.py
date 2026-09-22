#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标赛道轨 · 句级重复预检（两段式查重的第一段）

方法思维借鉴开源 antiplag/PaperCash 的「先预检、后官方」思路与字符/语义相似度
分层（精确匹配 → 近似匹配），代码为本轨自研：规范化整句精确匹配 + **句级**
8-gram 候选召回 + difflib 句对句复核，纯标准库、零依赖。

用途（T5）：提交官方查重前自查——重点是**三轨同源文档的独立成文检查**
（目标赛道论文 vs 目标赛道结题/目标赛道文档的主观句重复 = 一稿多投/重复申报风险）。
客观句（方法学参数、数据表、试剂清单）重复属正常，报告区分标注。

**定位声明（v1 起必须随输出出现）**：本工具是可机械判定的**抽查级**预检，
非全文查重引擎；放行必须以官方查重报告为准。

v1 相对 v0 的修复（2026-09-18）：
  G1 v0 的 difflib ratio 只写进打印字符串、不参与判定（源码自承「只做展示」）。
     v1 改为**句对句**比对，ratio ≥ RATIO_HIT 才判 MED——ratio 真正参与分支。
  G2 v0 的 MED 判定实为「规范化句 vs 整篇文档」的 8-gram 命中率（粗比）。
     v1 建**句级倒排索引**，候选是句子而非整篇，命中率语义恢复为「句内 n-gram 覆盖」，
     再用 ratio 精判。整篇粗比退为兜底路径（整篇命中且句级无候选时提示）。
  G3 v0 发现 HIGH 仍 return 0 → 自动化闸门无法拦截。v1 返回
     `1 if (HIGH 数 > 0) else 0`（MED 不致命，只在报告中列出）。

用法:
  python precheck_similarity.py 目标.md --against 对照1.md [对照2.md ...]
  python precheck_similarity.py 目标.md --against 对照1.md --no-fail
    （--no-fail：仅报告不失败，用于探索性自查）

输出: 高风险(整句复制) / 中风险(近似重复) 句子清单 + 主观/客观提示
退出码: 0=无 HIGH；1=存在 HIGH（整句复制）；2=参数/文件错误
"""
import difflib
import re
import sys
from pathlib import Path

SENT_SPLIT = re.compile(r"[^。！？；\n]+[。！？；]?")
NORM = re.compile(r"[\s\u3000a-zA-Z0-9%#()（）\[\]【】·:：,，.．/\\-]+")  # 规范化剔除

MIN_SENT_LEN = 20      # 规范化后短于此长度的句子不查
NGRAM_K = 8            # 句级 shingle 长度
MED_HIT_RATIO = 0.5    # 句级 n-gram 命中率阈值
RATIO_HIT = 0.75       # difflib 句对句 ratio 阈值（G1：真正参与判定）
REF_WINDOW = 3         # 命中命中的对照句左右邻域并入比较窗（供 ratio 使用）


def norm(s: str) -> str:
    return NORM.sub("", s)


def to_sentences(text: str) -> list:
    out = []
    for s in SENT_SPLIT.findall(text):
        s = s.strip()
        n = norm(s)
        if len(n) >= MIN_SENT_LEN:  # 太短的句子不查（无意义）
            out.append((s, n))
    return out


def shingles(norm_s: str, k: int = NGRAM_K) -> set:
    return {norm_s[i:i + k] for i in range(len(norm_s) - k + 1)} if len(norm_s) >= k else {norm_s}


def index_docs(ref_paths: list):
    """返回 (docs_整篇规范化 dict, sent_index: n-gram → [(对照文件, 句序, 规范化句)], ref_sents dict)"""
    docs, sent_index, ref_sents = {}, {}, {}
    for p in ref_paths:
        t = Path(p).read_text(encoding="utf-8")
        docs[p] = norm(t)
        sents = to_sentences(t)
        ref_sents[p] = sents
        for idx, (_, ns) in enumerate(sents):
            for g in shingles(ns):
                sent_index.setdefault(g, []).append((p, idx))
    return docs, sent_index, ref_sents


def check_sentence(s, ns, docs, sent_index, ref_sents):
    """返回 (风险级, 对照文件, 相似度, 说明)

    G1/G2：候选来自句级倒排索引；ratio 参与判定。
    """
    # 1) 精确：整句规范化后出现在对照文档（整篇子串命中）
    for fp, nt in docs.items():
        if ns in nt:
            return "HIGH(整句复制)", fp, 1.0, "整句规范化后原样出现在对照文档"

    # 2) 近似：句级 n-gram 候选召回 → ratio 精判
    grams = shingles(ns)
    cand = {}
    for g in grams:
        for fp, idx in sent_index.get(g, ()):
            cand[(fp, idx)] = cand.get((fp, idx), 0) + 1
    if cand and len(grams) >= 5:
        (bfp, bidx), hit = max(cand.items(), key=lambda kv: kv[1])
        if hit / max(len(grams), 1) >= MED_HIT_RATIO:
            # 并入邻域句构造比较窗（改写常跨句；邻域亦使 ratio 对整段搬运敏感）
            window = ref_sents.get(bfp, [])
            lo = max(0, bidx - REF_WINDOW)
            hi = min(len(window), bidx + REF_WINDOW + 1)
            ctx = "".join(n for _, n in window[lo:hi])
            ratio = difflib.SequenceMatcher(None, ns, ctx).ratio()
            if ratio >= RATIO_HIT:
                return ("MED(近似重复)", bfp,
                        round(ratio, 2),
                        f"句级 n-gram 命中 {hit}/{len(grams)}，ratio={ratio:.2f}")
            # 3) 兜底：句级未过 ratio 但整篇命中率仍高 → 提示（不判 MED）
            whole_hit = sum(1 for g in grams if g in docs.get(bfp, "")) / max(len(grams), 1)
            if whole_hit >= MED_HIT_RATIO:
                return ("LOW(疑似改写·整篇命中)", bfp,
                        round(whole_hit, 2),
                        f"句级 ratio 未过（{ratio:.2f}），但整篇 n-gram 命中 {whole_hit:.2f}")
    return None, None, None, None


SUBJECTIVE = re.compile(r"(本研究|我们|本文|结果表明|我们认为|综上|因此|为了|旨在|创新|相比|提示|说明)")

LOCATE_NOTE = ("判读: 本工具为**抽查级**预检（可机械判定的整句/近似匹配），非全文查重引擎；"
               "放行必须依据官方查重报告。")


def main(argv) -> int:
    no_fail = "--no-fail" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) < 2 or "--against" not in argv:
        print(__doc__)
        return 2
    target = args[0]
    ai = argv.index("--against")
    refs = [a for a in argv[ai + 1:] if not a.startswith("--")]
    if not refs:
        print("未提供对照文件（--against 后应为 ≥1 个文件）")
        return 2
    if not Path(target).exists():
        print(f"目标文件不存在: {target}")
        return 2
    for r in refs:
        if not Path(r).exists():
            print(f"对照文件不存在: {r}")
            return 2

    text = Path(target).read_text(encoding="utf-8")
    docs, sent_index, ref_sents = index_docs(refs)
    sents = to_sentences(text)

    print(f"===== 预检: {target} vs {len(refs)} 份对照 =====")
    if not sents:
        print("（目标文件中无 ≥%d 字的句子，无可比对内容）" % MIN_SENT_LEN)
        print(LOCATE_NOTE)
        return 0
    hi = me = lo = 0
    for s, ns in sents:
        level, fp, sim, why = check_sentence(s, ns, docs, sent_index, ref_sents)
        if level is None:
            continue
        kind = "主观句⚠️" if SUBJECTIVE.search(s) else "客观句(参考)"
        if level.startswith("HIGH"):
            mark, hi = "❌", hi + 1
        elif level.startswith("MED"):
            mark = "▲" if kind.startswith("主观") else "·"
            me += 1
        else:
            mark, lo = "△", lo + 1
        print(f"{mark} [{level}] {kind} {Path(fp).name} sim={sim}")
        print(f"      {why}")
        print(f"      {s[:80]}")
    print(f"----- 高风险(整句复制): {hi} | 中风险(近似): {me} | 提示(疑似改写): {lo} -----")
    print("判读: 主观句(引言/讨论/结论)重复=一稿多投风险，必须改写；")
    print("      客观句(方法学/数据表述)重复=标注引用即可，正常。")
    print(LOCATE_NOTE)

    # G3：HIGH 必须能拦住闸门
    if hi and not no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
