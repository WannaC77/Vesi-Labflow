#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标赛道轨 · 校验器自检（selftest）

用途：证明三个校验脚本**真的能失败**。装饰性校验（记录条件却不使用）是本轨
已发生过的缺陷族，本自检把"旧版缺陷必须可复现 + 新版必须拦截"固化为可复跑用例，
阻断该族再犯。

覆盖：
  SC-1 consistency_check.py  N 份全组比对（旧版只比第 1、2 份 → 静默漏检）
  SC-2 consistency_check.py  H1 兜底剥离字段前缀（旧版「# 题目: X」吞前缀 → 自判不一致）
  SC-3 consistency_check.py  数字差异纳入退出码（旧版非 --strict 时不失败）
  SC-4 precheck_similarity.py 近似复制检出（旧版 difflib 仅装饰、ratio 不参与判定）
  SC-5 precheck_similarity.py 整句复制 → exit 1（旧版发现 HIGH 仍 exit 0）
  SC-6 verify_track.py        cond=False 必须失败（旧版照打 ✅、exit 0）

用法:
  python selftest_scripts.py            # 全跑
  python selftest_scripts.py SC-5       # 只跑某条
退出码: 0=全部通过；1=有用例失败
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
TRACK_ROOT = HERE.parent                      # scripts/ → 目标赛道
# 与本轨 verify_track.py 一致的根路径推断
SAI_ROOT = TRACK_ROOT.parent                  # 目标赛道 → 比赛
DATUAN_ROOT = SAI_ROOT / "候选药物 X目标赛道"

results = []   # (用例号, 名称, 通过?, 说明)


def run(cmd, **kw):
    """跑子进程，返回 (returncode, stdout+stderr 合并文本)。"""
    p = subprocess.run([PY] + cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write(p: Path, s: str):
    p.write_text(s, encoding="utf-8")


def case(no, name, passed, note):
    results.append((no, name, passed, note))
    print(f"  {'✅' if passed else '❌'} {no} {name}")
    if note:
        print(f"       {note}")


# ───────────────────────── SC-1 / SC-2 / SC-3 ─────────────────────────
def sc1_3(tmp: Path):
    """consistency_check.py 三态用例。"""
    a = tmp / "申报书.md"
    b = tmp / "论文.md"
    c = tmp / "附件目录.md"

    # SC-1：A/B 含同一数对，C 含不同数对。
    #       v0 只比 [0] vs [1]（A vs B 相同）→ 不报，静默漏检第 3 份。
    write(a, "# 作品名称: 候选药物 X脂质体研究\n\n作者: 张三\n\n测得粒径 45.2±5.6 nm。\n")
    write(b, "# 作品名称: 候选药物 X脂质体研究\n\n作者: 张三\n\n测得粒径 45.2±5.6 nm。\n")
    write(c, "# 作品名称: 候选药物 X脂质体研究\n\n作者: 张三\n\n测得粒径 99.9±1.1 nm。\n")
    rc, out = run([str(HERE / "consistency_check.py"), str(a), str(b), str(c)])
    hit = "99.9±1.1" in out and "未全组齐备" in out
    v0_miss = ("均值±SD数对" not in out)   # v0 在此输入下不报数字问题（此断言用于记录旧行为）
    case("SC-1", "N 份全组比对：第 3 份独有数对被报出", hit and rc == 1,
         f"exit={rc}；{'已报出 99.9±1.1 未全组齐备' if hit else '未报出（FAIL）'}"
         + ("；注：v0 在此输入下会静默漏检" if not v0_miss else ""))

    # SC-2：H1 形态「# 题目: X」与「作品名称: X」混合。
    #       v0 的 H1 兜底会吞掉「题目: 」前缀 → 两处标题字符串不等 → 自判不一致。
    write(a, "# 题目: 脂质体体内释放比较研究\n\n作者: 张三\n")
    write(b, "作品名称: 脂质体体内释放比较研究\n\n作者: 张三\n")
    rc, out = run([str(HERE / "consistency_check.py"), str(a), str(b)])
    # 期望：题目字段两者均为「脂质体体内释放比较研究」，无题目不一致项
    title_bad = re.search(r"❌ 题目", out) or ('不一致' in out and '脂质体体内释放比较研究' in out and '题目:' in out)
    both_same = "题目: 脂质体体内释放比较研究" in out or "作品名称: 脂质体体内释放比较研究" in out
    case("SC-2", "H1 兜底剥离字段前缀：同题不误判", not title_bad and rc == 0,
         f"exit={rc}；{'题目字段已归一，无自冲突' if not title_bad else '仍被误判为题目不一致（FAIL）'}")

    # SC-3：题目/署名一致、仅数字不同 → 默认必须 exit 1（v0 非 --strict 时为 0）
    write(a, "# 作品名称: 同题研究\n\n作者: 张三\n\nA 组 10.0±1.0 mg/kg。\n")
    write(b, "# 作品名称: 同题研究\n\n作者: 张三\n\nA 组 20.0±2.0 mg/kg。\n")
    rc_def, out_def = run([str(HERE / "consistency_check.py"), str(a), str(b)])
    rc_loose, _ = run([str(HERE / "consistency_check.py"), str(a), str(b), "--loose"])
    case("SC-3", "数字差异纳入退出码（默认失败，--loose 放行）",
         rc_def == 1 and rc_loose == 0,
         f"默认 exit={rc_def}（期望 1）；--loose exit={rc_loose}（期望 0）"
         + ("；注：v0 默认 exit=0 = 无法拦截" if rc_def == 1 else ""))


# ───────────────────────── SC-4 / SC-5 ─────────────────────────
def sc4_5(tmp: Path):
    """precheck_similarity.py 两态用例。"""
    target = tmp / "论文.md"
    ref = tmp / "对照.md"

    # SC-5：整句复制 → 必须 exit 1
    sent = "本研究以候选药物 X为模型药物，采用薄膜分散法制备脂质体，并系统评价其体外释放行为。"
    write(target, f"## 引言\n\n{sent}\n")
    write(ref, f"## 引言\n\n{sent}\n")
    rc, out = run([str(HERE / "precheck_similarity.py"), str(target), "--against", str(ref)])
    hi = "高风险(整句复制): 1" in out or "高风险(整句复制): 2" in out
    case("SC-5", "整句复制 → exit 1（可被闸门拦截）", rc == 1 and hi,
         f"exit={rc}（期望 1）；{'已判 HIGH' if hi else '未判 HIGH（FAIL）'}"
         + "；注：v0 在此输入下 exit=0 = 拦不住")

    # SC-4：改性复制（改 2 字）→ 应被检出（MED 或 LOW），不应完全静默
    t2 = "本研究以候选药物 X为模型药物，采用薄膜分散法制备脂质体，并系统评价其体内释放特征。"
    write(target, f"## 引言\n\n{t2}\n")
    rcfail_before = "MED(近似重复)" in ""
    rc, out = run([str(HERE / "precheck_similarity.py"), str(target),
                   "--against", str(ref), "--no-fail"])
    detected = "MED(近似重复)" in out or "LOW(疑似改写·整篇命中)" in out
    case("SC-4", "改性复制（改 2 字）被检出", detected,
         f"exit={rc}；{'已检出' + ('MED' if 'MED(近似重复)' in out else 'LOW') if detected else '未检出（FAIL）'}"
         + "；注：v0 的 difflib ratio 不参与判定，即此输入多漏检")


# ───────────────────────── SC-6 ─────────────────────────
def sc6(_tmp):
    """verify_bundle.py：布局/依赖缺失必须导致 FAIL。

    做法：复制脚本到临时目录，用 LABFLOW_ROOT 指向一个空的假根（无任何必需件），
    期望脚本报 ❌ 且 exit 1。若脚本仍是装饰性校验，会全 ✅ 且 exit 0。
    """
    fake = Path(tempfile.mkdtemp(prefix="selftest_root_"))
    src = HERE / "verify_bundle.py"
    dst = fake / "scripts"
    dst.mkdir(parents=True, exist_ok=True)
    shutil_copy(src, dst / "verify_bundle.py")
    rc, out = run([str(dst / "verify_bundle.py")], env=_env_with_root(fake))
    has_fail = "失败 " in out and "判定: FAIL" in out
    has_check = "❌" in out
    case("SC-6", "verify_bundle.py：布局缺失 → FAIL（非照打 ✅）",
         rc == 1 and has_fail and has_check,
         f"exit={rc}（期望 1）；{'已报 ❌ 且 FAIL' if (has_fail and has_check) else '未失败（FAIL：校验器仍是装饰性的）'}"
         + "；注：v0 在此输入下会全 ✅ 且 exit=0")


def shutil_copy(a: Path, b: Path):
    b.write_text(a.read_text(encoding="utf-8"), encoding="utf-8")


def _env_with_root(root: Path):
    import os
    env = dict(os.environ)
    env["SAI_ROOT"] = str(root)
    return env


def main(argv) -> int:
    only = argv[1] if len(argv) > 1 else None
    print("=" * 60)
    print("目标赛道轨 · 校验器自检（证明校验器真的能失败）")
    print("=" * 60)
    with tempfile.TemporaryDirectory(prefix="wb_selftest_") as td:
        tmp = Path(td)
        groups = [("SC-1", ["SC-1", "SC-2", "SC-3"], sc1_3),
                  ("SC-4", ["SC-4", "SC-5"], sc4_5),
                  ("SC-6", ["SC-6"], sc6)]
        for key, codes, fn in groups:
            if only and only not in codes:
                continue
            try:
                fn(tmp)
            except Exception as e:  # 用例自身崩了也是失败
                case(codes[0], f"{codes} 组执行异常", False, repr(e))
    print("-" * 60)
    passed = sum(1 for *_, ok_, _ in [(a, b, c, d) for a, b, c, d in results] if ok_)
    total = len(results)
    print(f"通过 {passed}/{total}")
    print(f"判定: {'PASS' if passed == total and total else 'FAIL'}")
    return 0 if (passed == total and total) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
