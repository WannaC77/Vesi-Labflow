#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_manifest.py — 文档引用 ↔ 磁盘一致性自证（零第三方依赖，随包分发）

为什么要它：外部读者/代码 agent 跑不了本仓的开发管线，也没法一眼判断「文档里写的文件到底在不在」。
本工具把这件事变成一条可复跑命令：解析包内 *.md 的**路径形态引用**，逐条对质磁盘。

判据（只认「仓库内路径形态」的引用，避免把散文里提到的裸文件名当路径）：
  ① markdown 链接：`[文字](路径)`——跳过 http/https/mailto 与纯锚点；`../` 前缀会归一
  ② 行内代码里的**含斜杠**路径：`` `tools/env_check.py` `` / `` `workflows/` ``
解析顺序：**按 md 所在目录/仓根精确解析 → 包内唯一后缀匹配（简写引用，如 `figures/`、
`utils/plot_style.py`）**；两者都不中才判为缺件。

缺件 → FAIL（rc=1），打印「文件:行号 + 引用 + 期望路径」。分四类处理，全部**打印计数**（`-v` 打明细），
不做静默白名单：
  · **跨项目引用**（首段为 `数模/` / `Euler/` / `Vesi/` 等项目名）→ 判失败：本包内不存在该路径
  · **使用者自建/约定目录**（`编号-名称/`、`决策日志/`、`raw/`、`kb/` 自填位）→ 豁免（按设计不随包）
  · **运行时产物目录**（`_smoke_out/`）与**产物落点**（如 `申报书-初稿.md`）→ 豁免（跑起来才有）
  · **第三方模板位**（`paper-templates/国赛-CUMCM/` 与 `.cls` / `.sty`）→ 豁免（许可待核，具名外置）
  · **占位路径**（含 `<` `>`，如 `<共享层>/`、`<venv>`）→ 豁免（L2 自建位）

用法：
  python scripts/verify_manifest.py --root .         # rc: 0 通过 / 1 有缺件 / 2 用法错误
  python scripts/verify_manifest.py --selftest       # 自检（正例 + 负例；负例必须 FAIL）
  python scripts/verify_manifest.py --root . -v      # 打印全部豁免明细
"""
import argparse
import os
import re
import shutil
import sys
import tempfile

SKIP_DIRS = {".git", "__pycache__", "_smoke_out", ".venv", "venv", "node_modules", ".mypy_cache"}
EXT_RE = (r"md|py|yml|yaml|json|cff|txt|tex|cls|sty|bib|csv|tsv|xlsx|docx|pptx|pdf|png|svg|"
          r"jpg|jpeg|gif|zip|bat|sh|ps1|m|cpp|h|cfg|ini|toml|gitkeep")
CODE_PATH_RE = re.compile(r"^[\w.\-]+(?:/[\w.\-]+)+\.(?:" + EXT_RE + r")$", re.UNICODE)   # 含斜杠 + 扩展名
CODE_DIR_RE = re.compile(r"^[\w.\-]+(?:/[\w.\-]+)+/$", re.UNICODE)                       # ≥2 段 + 结尾 /
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?\s*\)")
CODE_SPAN_RE = re.compile(r"`([^`\n]{1,160})`")

# 跨项目引用：本包内不存在这些路径（姊妹项目各自的仓）
CROSS_SEGMENTS = {"数模", "Euler", "Vesi", "Euler-Modelforge", "Vesi-Labflow"}
# 具名豁免（逐条列明理由；只收「按设计不随包」的引用）
NAMED_EXEMPT = [
    (re.compile(r"(^|/)(issues|discussions|releases|pulls)$"), "平台内建路径（GitHub UI 页面）"),
    (re.compile(r"^security/advisories(/|$)"), "平台内建路径（安全披露）"),
    (re.compile(r"^templates-library/data/.+"), "运行数据位（随包仅 .gitkeep）"),
    (re.compile(r"(^|/)申报书-初稿\.md$"), "产物落点（使用者生成的初稿，不随包）"),
    (re.compile(r"^\d\d-[^/]+(/|$)"), "编号-名称目录约定（使用者自建的知识库/工作目录）"),
    (re.compile(r"(^|/)_smoke_out(/|$)"), "运行时产物目录（已 gitignore，跑完自检才有）"),
    (re.compile(r"^kb/"), "L2 自建位（kb/ 内容自填，按设计不随包）"),
    (re.compile(r"^paper-templates/国赛-CUMCM/"), "第三方模板位（许可待核，具名外置）"),
    (re.compile(r"\.(cls|sty)$"), "第三方 LaTeX 类文件（具名外置，见 THIRD-PARTY.md）"),
    (re.compile(r"^(决策日志|raw)/"), "使用者自建目录约定（决策日志 / 原始素材）"),
]


def norm_ref(ref):
    """归一：去锚点/查询串与首尾空白，反斜杠→正斜杠，剥掉前导 ../ 与 /。"""
    ref = ref.split("#", 1)[0].split("?", 1)[0].strip().replace("\\", "/")
    while ref.startswith("../"):
        ref = ref[3:]
    return ref.lstrip("/")


def build_index(root):
    """包内全部路径（目录带尾斜杠），用于后缀匹配。"""
    index, top = set(), set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        for d in dirnames:
            rel = ("%s/%s/" % (rel_dir, d)) if rel_dir != "." else (d + "/")
            index.add(rel)
            if rel_dir == ".":
                top.add(d)
        for fn in filenames:
            rel = ("%s/%s" % (rel_dir, fn)) if rel_dir != "." else fn
            index.add(rel)
            if rel_dir == ".":
                top.add(fn)
    return index, top


def iter_md(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                yield os.path.join(dirpath, fn)


def refs_in(text):
    """返回 [(行号, 引用串, 来源)]；行内代码只收「含斜杠」的路径形态。"""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in MD_LINK_RE.finditer(line):
            out.append((i, m.group(1), "link"))
        for m in CODE_SPAN_RE.finditer(line):
            tok = m.group(1).strip()
            if not tok or " " in tok or tok.startswith("-") or "/" not in tok:
                continue
            if CODE_PATH_RE.match(tok) or CODE_DIR_RE.match(tok):
                out.append((i, tok, "code"))
    return out


def resolve(ref, md, root, index):
    """→ ('exact'|'suffix'|'miss', 期望路径)"""
    cands = [os.path.normpath(os.path.join(os.path.dirname(md), ref)),
             os.path.normpath(os.path.join(root, ref))]
    for c in cands:
        if os.path.exists(c):
            return "exact", c
    for e in index:
        if e == ref or e.endswith("/" + ref):
            return "suffix", e
    return "miss", cands[0]


def check(root, verbose=False):
    root = os.path.abspath(root)
    index, top = build_index(root)
    missing, ex_detail = [], []
    n_exact = n_suffix = n_exempt = 0
    ex_counts = {}
    for md in iter_md(root):
        rel_md = os.path.relpath(md, root).replace("\\", "/")
        try:
            text = open(md, encoding="utf-8", errors="replace").read()
        except Exception as e:                                        # noqa
            missing.append(("%s:0" % rel_md, "<读取失败 %r>" % e, ""))
            continue
        for lineno, raw, _src in refs_in(text):
            if not raw or "://" in raw or raw.startswith("mailto:"):
                continue
            loc = "%s:%d" % (rel_md, lineno)
            if "<" in raw or ">" in raw:
                k = "占位路径（含 <>，L2 自建位）"
                ex_counts[k] = ex_counts.get(k, 0) + 1
                ex_detail.append((loc, raw, k))
                n_exempt += 1
                continue
            ref = norm_ref(raw)
            how, want = resolve(ref, md, root, index)
            if how == "exact":
                n_exact += 1
                continue
            if how == "suffix":
                n_suffix += 1
                continue
            first = ref.split("/")[0]
            if first in CROSS_SEGMENTS:
                missing.append((loc, raw, "跨项目引用（本包内不存在）"))
                continue
            hit = None
            for rx, why in NAMED_EXEMPT:
                if rx.search(ref):
                    hit = why
                    break
            if hit:
                ex_counts[hit] = ex_counts.get(hit, 0) + 1
                ex_detail.append((loc, raw, hit))
                n_exempt += 1
                continue
            missing.append((loc, raw, want))
    print("[verify_manifest] 检查引用 %d 条（精确 %d ｜ 简写匹配 %d）｜ 豁免 %d 条 ｜ 缺件 %d 条"
          % (n_exact + n_suffix + n_exempt + len(missing), n_exact, n_suffix, n_exempt, len(missing)))
    for k, v in sorted(ex_counts.items()):
        print("   ~ 豁免 %-46s ×%d" % (k, v))
    if verbose:
        for loc, raw, why in ex_detail:
            print("      %-28s %-40s ← %s" % (loc, raw, why))
    if missing:
        print("❌ 缺件（文档引用但磁盘不存在）：")
        for loc, raw, want in missing:
            print("   ✗ %-28s %-42s → %s" % (loc, raw, want))
        return 1
    print("✅ 通过：文档里引用的仓库内路径全部存在")
    return 0


def run(root, verbose=False):
    """与 CLI 同语义的入口（selftest 也走这条，保证「用法错误 → rc=2」被覆盖）。"""
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        print("ERROR: 根无效（不存在或不是目录）：%s" % root)
        return 2
    if not any(iter_md(root)):
        print("ERROR: 根内没有任何 *.md —— 确认 --root 指向包根（%s）" % root)
        return 2
    return check(root, verbose)


def selftest():
    cases = []

    def run_case(name, files, expect_rc, root_override=None):
        d = tempfile.mkdtemp(prefix="vm_")
        try:
            for rel, content in files.items():
                p = os.path.join(d, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8", newline="\n").write(content)
            rc = run(root_override or d)
            cases.append((name, "PASS" if rc == expect_rc else "FAIL",
                          "rc=%d（期望 %d）" % (rc, expect_rc)))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    run_case("正例：引用的文件都存在 → 通过",
             {"a.md": "见 `tools/x.py` 与 [说明](docs/y.md)\n",
              "tools/x.py": "print(1)\n", "docs/y.md": "# y\n"}, 0)
    run_case("正例：简写引用（唯一后缀）可解析 → 通过",
             {"a.md": "见 `utils/plot_style.py` 与 `figures/`\n",
              "templates-library/utils/plot_style.py": "x\n",
              "paper-templates/MCM/figures/a.pdf": "x\n"}, 0)
    run_case("负例：行内代码引用不存在 → 必须 FAIL",
             {"a.md": "见 `tools/none.py`\n", "tools/other.py": "print(1)\n"}, 1)
    run_case("负例：markdown 链接指向不存在 → 必须 FAIL",
             {"a.md": "[指南](docs/missing.md)\n"}, 1)
    run_case("负例：跨项目引用（数模/Euler/…）→ 必须 FAIL",
             {"a.md": "见 `数模/Euler/workflows/09-知识管理.md`\n", "tools/x.py": "x\n"}, 1)
    run_case("正例：占位/用户空间/具名豁免 → 通过",
             {"a.md": "`<共享层>/x.md` `templates-library/data/mine.csv` `01-文献调研/`\n"
                      "`templates/申报书线/申报书-初稿.md`\n"}, 0)
    run_case("正例：相对链接 ../ 归一后可解析 → 通过",
             {"sub/a.md": "[根自述](../README.md)\n", "README.md": "# r\n"}, 0)
    run_case("负例：包内顶层目录下的目录引用不存在 → 必须 FAIL",
             {"a.md": "见 `workflows/none/`\n"}, 1)
    run_case("负例：裸单段目录/文件名不算路径（不该被误判）→ 通过",
             {"a.md": "见 `env_check.py` 与 `concepts/`（散文里的裸名）\n"}, 0)
    run_case("负例：不存在的根 → rc=2",
             {"a.md": "x\n"}, 2, root_override=os.path.join(tempfile.gettempdir(), "__no_such_root_vm__"))
    run_case("负例：根内无 md → rc=2",
             {"x.txt": "no md here\n"}, 2)

    bad = [c for c in cases if c[1] != "PASS"]
    for name, verdict, detail in cases:
        print("  %s %-48s %s" % ("✓" if verdict == "PASS" else "✗", name, detail))
    print("[selftest] %d/%d %s" % (len(cases) - len(bad), len(cases), "OK" if not bad else "FAILED"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(prog="verify_manifest.py",
                                 description="文档引用 ↔ 磁盘一致性自证（rc: 0 通过 / 1 缺件 / 2 用法）")
    ap.add_argument("--root", default=".", help="包根（默认当前目录）")
    ap.add_argument("--selftest", action="store_true", help="自检（含必须失败的负例）")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印豁免明细")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return run(a.root, a.verbose)


if __name__ == "__main__":
    sys.exit(main())
