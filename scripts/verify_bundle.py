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
退出码: 0 = 无失败项；1 = 存在失败项；2 = 用法错误

设计要点（可失败性）：
  · 判定**只**由条件真假决定，打印符号与判定完全一致（禁止「照打 ✅」的装饰性校验）；
  · 缺失项按 level 归入 warn 或 fail；存在 fail 即 exit 1；
  · 全程不写盘、不联网、不依赖第三方包。
"""
import argparse
import os
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

ok, warn, fail = [], [], []


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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify_bundle.py", add_help=True)
    ap.add_argument("--root", default=None, help="仓根（缺省：脚本位置反推 / LABFLOW_ROOT）")
    a = ap.parse_args(argv)
    root = resolve_root(a.root)

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

    # 7) 包内路径卫生（轻量自检：不得出现本机绝对路径）
    pat_bad = []
    for p in list(root.rglob("*.md")) + list(root.rglob("*.py")) + list(root.rglob("*.yaml")):
        if ".git" in p.parts:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        if ("C:" + chr(92) + "Users") in t or ("C:" + "/Users") in t or ("Desktop" + chr(92) + "比赛") in t:
            pat_bad.append(str(p.relative_to(root)))
    check("包内无本机绝对路径残留", not pat_bad, detail="命中: %s" % pat_bad[:5])

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
