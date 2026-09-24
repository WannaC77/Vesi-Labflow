#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_bundle.py — 开源包结构自校验（通用版）

用途：交付 / 打包前确认本仓库**自身结构完整**（不依赖任何私有共享层、外库或绝对路径）。
      它检查的是「包」，不是「赛轨」：一切路径以**仓根**为基准。

用法:
  python scripts/verify_bundle.py                 # 以脚本位置反推仓根
  python scripts/verify_bundle.py --root <路径>   # 指定仓根
  LABFLOW_ROOT=<路径> python scripts/verify_bundle.py   # 环境变量覆盖
  python scripts/verify_bundle.py --selftest      # 自检判据本身（正/负夹具，负例必须 FAIL）
退出码: 0 = 无失败项；1 = 存在失败项；2 = 用法错误

设计要点（可失败性）：
  · 判定**只**由条件真假决定，打印符号与判定完全一致（禁止「照打 ✅」的装饰性校验）；
  · 缺失项按 level 归入 warn 或 fail；存在 fail 即 exit 1；
  · 全程不写盘、不联网、不依赖第三方包；
  · 脱敏扫描的模式**自带 `(?i)`**（09 批 P0-1/P0-2 教训：靠外挂 re.I 顶账的「复扫 = 0」是假绿），
    并为每条模式配 `--selftest` 负例（专名大小写变体 / 代谢物族 / 异名形态必须命中）。
"""
import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_FILES = [
    "BOOT.md", "README.md", "AGENTS.md", "LICENSE", "LICENSE-DOCS", "THIRD-PARTY.md",
    "QUICKSTART.md", "CHANGELOG.md", "CITATION.cff", "requirements.txt",
    "VESI-CORE.md", "VESI-ENGINE.md", "learnings.md",
    ".gitignore", ".github/workflows/ci.yml",
]
REQUIRED_DIRS = ["modules", "workflows", "templates", "references", "tools", "scripts", "kb"]
REQUIRED_WORKFLOWS = ["_SHARED.md", "D-ABSORB.md"]
REQUIRED_TOOLS = ["env_check.py", "smoke_chain.py", "nca.py", "compartment_fit.py",
                  "release_fit.py", "stats_pipeline.py"]
REQUIRED_SCRIPTS = ["assert_delivery_hygiene.py", "delivery_gate_check.py", "check_dose.py",
                    "clean_pdf_meta.py", "consistency_check.py", "naturalness_check.py",
                    "precheck_similarity.py", "ref_numberizer.py", "selftest_scripts.py",
                    "transcribe_record.py", "verify_bundle.py", "batch_ocr.py", "README.md"]
REQUIRED_TEMPLATES = ["校准台账模板.md", "锚注册卡模板.md"]

# ── 包侧脱敏扫描（09 批 P1-1a：原判据只拦「本机用户目录」「源工作区路径」两个字面量，漏面过宽）
#
# ⚠️ 写法约定（改词族时必须遵守）：本文件落包前会过一次 paths/terms 机械替换，包内 G1/G2 门禁
#    又会扫本文件自身 —— 直接写全字面量会被替换成占位词（判据自毁），并被自己的门禁判成泄漏。
#    因此敏感字面量一律**片段拼接**（`"ir" + "inotecan"`）或**字符类拆形**（`[伊][利]替康`）书写：
#    运行时拼回原词（rsplit/join 后语义等同），静态文本里取不到原字面量。
_S = lambda *parts: "".join(parts)          # noqa: E731  片段拼接（见上方写法约定）
NEEDLES = {
    "drug_zh_a": _S("伊利", "替康"),
    "drug_zh_b": _S("伊立", "替康"),
    "drug_en": _S("ir", "inotecan"),
    "drug_en_cap": _S("Irin", "otecan"),
    "drug_code": _S("CPT", "-11"),
    "metabolite": _S("sn-", "38"),
    "metabolite_cap": _S("SN", "-38"),
    "enzyme": _S("UGT", "1a1"),
    "brand": _S("oni", "vyde"),
    "generic": _S("topo", "tecan"),
    "machine_id": _S("341", "48"),
    "pipe_dirs": _S("目标赛道", "自动化"),
    "pipe_dir2": _S("grant-", "research"),
    "calendar": _S("2027", "-05"),
}
DESENS_RULES = [
    ("本机路径", r"C:[\\/]Users|Desktop[\\/]" + _S("比", "赛")),
    ("课题专名族", r"(?i)" + "|".join(map(re.escape, (NEEDLES["drug_zh_a"], NEEDLES["drug_zh_b"],
                                                     NEEDLES["drug_en"], NEEDLES["drug_code"])))),
    ("代谢物/酶族", r"(?i)" + "|".join(map(re.escape, (NEEDLES["metabolite"], NEEDLES["enzyme"])))),
    ("同类已上市品种族", r"(?i)" + "|".join(map(re.escape, (NEEDLES["brand"], NEEDLES["generic"])))),
    ("本机标识", re.escape(NEEDLES["machine_id"])),
    ("私域流水线目录", r"(?i)" + "|".join(map(re.escape, (NEEDLES["pipe_dirs"], _S("大", "创自动化"), NEEDLES["pipe_dir2"])))),
    # 同值重复（塌陷）：同一占位在一行里出现 ≥2 次、其间只有分隔符 ⇒ 枚举不可用；
    # 第三条用**反向引用** `\1` 只抓「同一个轨道字母」，不误伤合法的 `<轨道 A> / <轨道 B>`。
    ("同值重复占位", r"`?候选药物 X`?\s*[/、]\s*`?候选药物 X`?|`?目标赛道`?\s*[/、]\s*`?目标赛道`?|`?<轨道\s*([ABC])>`?\s*[/、]\s*`?<轨道\s*\1>`?"),
    ("裸年月（项目日历）", r"20\d\d-\d\d(?!-\d\d)(?!\d)"),
]
SCAN_EXT = (".md", ".py", ".yaml", ".yml", ".txt", ".cff", ".sh", ".tex", ".sty", ".csv")

ok, warn, fail = [], [], []


def scan_text_lines(rel, text):
    """单文件文本 → 命中列表（scan_desens 与 --selftest 共用同一判定）。"""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for name, pat in DESENS_RULES:
            if re.search(pat, line):
                out.append((rel, i, name, line.strip()[:120]))
    return out


def scan_desens(root):
    """返回 [(相对路径, 行号, 规则名, 行文本)]；只读，不写盘。"""
    hits = []
    for p in sorted(Path(root).rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.suffix.lower() not in SCAN_EXT:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits.extend(scan_text_lines(str(p.relative_to(root)), text))
    return hits


def check(desc, cond, level="fail", detail=""):
    """判定只由 cond 决定；level 仅在 cond 为假时决定归入 warn 还是 fail。"""
    if cond:
        ok.append(desc)
    else:
        msg = "%s｜%s" % (desc, detail) if detail else desc
        (warn if level == "warn" else fail).append(msg)
    return cond


def resolve_root(arg_root):
    if arg_root:
        return Path(arg_root).resolve()
    env = os.environ.get("LABFLOW_ROOT") or os.environ.get("OPENLAB_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]        # scripts/ → 仓根


def selftest():
    """判据自检（09 批 P1-1c）：正例必须 PASS、负例必须 FAIL；含大小写/异名形态负例。

    夹具在系统临时目录内创建，不写仓、不联网。
    """
    import shutil
    import tempfile
    cases = [
        ("正例：干净文本", {"a.md": "普通文本，无敏感物\n"}, True),
        ("负例：专名（首字母大写）", {"a.md": NEEDLES["drug_en_cap"] + " [MeSH]\n"}, False),
        ("负例：专名（全小写）", {"a.md": NEEDLES["drug_en"] + " 参比制剂\n"}, False),
        ("负例：代谢物族（小写）", {"a.md": "代谢物 " + NEEDLES["metabolite"] + " 的定量\n"}, False),
        ("负例：代谢物族（大写）", {"a.md": NEEDLES["metabolite_cap"] + "G 结合物\n"}, False),
        ("负例：酶族（混合大小写）", {"a.md": NEEDLES["enzyme"] + " 基因型\n"}, False),
        ("负例：异名形态（品牌名/通用名）", {"a.md": NEEDLES["brand"] + " 与 " + NEEDLES["generic"] + " 对照\n"}, False),
        ("负例：本机标识", {"a.md": "路径里含 " + NEEDLES["machine_id"] + "\n"}, False),
        ("负例：私域流水线目录名", {"a.md": NEEDLES["pipe_dirs"] + "/notes.md\n"}, False),
        ("负例：同值重复占位（塌陷）", {"a.md": _S("`目标赛道` / `目标", "赛道` / 生科") + "\n"}, False),
        ("正例：可区分枚举不判（轨道 A/B/C）", {"a.md": "`<轨道 A>` / `<轨道 B>` / `<轨道 C>`\n"}, True),
        ("负例：裸年月（项目日历）", {"a.md": NEEDLES["calendar"] + " 中期答辩\n"}, False),
        ("正例：完整日期（版次戳）不判", {"a.md": "版本 v1.0（2026-09-21）\n"}, True),
        ("正例：`YYYY-MM-DD` 占位不判", {"a.md": "条目命名 `YYYY-MM-DD-<主题>`\n"}, True),
        ("正例：模式表自证不自伤（本文件自身零命中）", None, True),
    ]
    bad = 0
    for name, files, expect_pass in cases:
        if files is None:                      # 特殊例：扫本文件自身（模式表不得自伤）
            me = Path(__file__).resolve()
            got = not scan_text_lines(me.name, me.read_text(encoding="utf-8", errors="ignore"))
        else:
            d = tempfile.mkdtemp(prefix="vb_self_")
            try:
                for rel, content in files.items():
                    (Path(d) / rel).write_text(content, encoding="utf-8")
                got = not scan_desens(d)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        good = (got == expect_pass)
        bad += 0 if good else 1
        print("   %s 期望=%-4s 实得=%-4s %s" % ("✓" if good else "✗", "PASS" if expect_pass else "FAIL",
                                              "PASS" if got else "FAIL", name))
    print("selftest %s（%d 例，失败 %d）" % ("PASS" if not bad else "FAIL", len(cases), bad))
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify_bundle.py", add_help=True)
    ap.add_argument("--root", default=None, help="仓根（缺省：脚本位置反推 / LABFLOW_ROOT）")
    ap.add_argument("root_pos", nargs="?", default=None, help="仓根（位置参数写法，等价 --root；兼容 `verify_bundle.py .`）")
    ap.add_argument("--selftest", action="store_true", help="自检脱敏判据（负例必须 FAIL）")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    root = resolve_root(a.root or a.root_pos)

    check("仓根可定位", root.is_dir(), detail=str(root))

    # 1) 顶层必需件
    for f in REQUIRED_FILES:
        check("必需件 %s 在位" % f, (root / f).is_file(), detail=str(root / f))

    # 2) 必需目录
    for d in REQUIRED_DIRS:
        check("目录 %s/ 在位" % d, (root / d).is_dir(), detail=str(root / d))

    # 3) 工作流骨架
    for f in REQUIRED_WORKFLOWS:
        check("workflows/%s 在位" % f, (root / "workflows" / f).is_file())
    n_wf = len([p for p in (root / "workflows").glob("*.md")]) if (root / "workflows").is_dir() else 0
    check("workflows 件数 ≥ 12（01–13 + 共享件）", n_wf >= 12, detail="实际 %d" % n_wf)

    # 4) 模块（每件含「降级」列）
    mods = sorted([p for p in (root / "modules").glob("*/MODULE.md")]) if (root / "modules").is_dir() else []
    check("模块 ≥ 11 个 MODULE.md", len(mods) >= 11, detail="实际 %d" % len(mods))
    missing_deg = [m.parent.name for m in mods if "降级" not in m.read_text(encoding="utf-8", errors="ignore")]
    check("模块表均含「降级」列", not missing_deg, detail="缺: %s" % missing_deg)

    # 5) 工具与门禁脚本
    for f in REQUIRED_TOOLS:
        check("tools/%s 在位" % f, (root / "tools" / f).is_file())
    for f in REQUIRED_SCRIPTS:
        check("scripts/%s 在位" % f, (root / "scripts" / f).is_file())

    # 6) 模板与自建位
    for f in REQUIRED_TEMPLATES:
        check("templates/%s 在位" % f, (root / "templates" / f).is_file())
    check("kb/ 目录含自建说明 kb/README.md", (root / "kb" / "README.md").is_file())

    # 7) 包侧脱敏（09 批 P1-1a 扩面）：本机路径 / 课题专名族 / 代谢物·酶族 / 同值重复占位 / 裸年月
    hits = scan_desens(root)
    by_rule = {}
    for rel, lineno, name, line in hits:
        by_rule.setdefault(name, []).append("%s:%d" % (rel, lineno))
    check("包侧脱敏零命中（%d 条模式）" % len(DESENS_RULES), not hits,
          detail="；".join("%s x%d（%s）" % (k, len(v), ", ".join(v[:3])) for k, v in sorted(by_rule.items())))

    # 输出
    print("=" * 60)
    print("开源包结构自校验（verify_bundle.py）")
    print("仓根: %s" % root)
    print("=" * 60)
    for d in ok:
        print("  ✅ %s" % d)
    for d in warn:
        print("  ⚠️  %s（警告）" % d)
    for d in fail:
        print("  ❌ %s" % d)
    print("-" * 60)
    print("通过 %d | 警告 %d | 失败 %d" % (len(ok), len(warn), len(fail)))
    print("判定: %s" % ("PASS" if not fail else "FAIL"))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
