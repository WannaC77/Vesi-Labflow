# -*- coding: utf-8 -*-
"""示例 2 —— 统计管线：两组比较（合成数据）。

合成数据：两组各 8 个观测值（纯合成，无真实数据）。
运行：python examples/stats_demo.py
判据：统计管线 rc=0 且输出非空 → rc=0；缺依赖按约 rc=3。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GROUP_A = [12.4, 13.1, 11.8, 14.2, 12.9, 13.6, 12.1, 13.3]
GROUP_B = [15.2, 16.8, 14.9, 17.1, 15.9, 16.2, 15.5, 16.9]


def tree() -> Path:
    cands = []
    env = os.environ.get("LABFLOW_ROOT")
    if env:
        cands.append(Path(env))
    cands += list(Path(__file__).resolve().parents)
    for c in cands:
        if (c / "tools").is_dir() and (c / "workflows").is_dir():
            return c
    raise SystemExit("[错误] 未找到工具树：请在仓库根运行，或设置 LABFLOW_ROOT。")


def main() -> int:
    t = tree()
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "two_groups.csv"
        rows = ["value,group"] + ["%s,A" % v for v in GROUP_A] + ["%s,B" % v for v in GROUP_B]
        csv.write_text(chr(10).join(rows) + chr(10), encoding="utf-8")
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        p = subprocess.run([sys.executable, str(t / "tools" / "stats_pipeline.py"),
                            str(csv), "--value", "value", "--group", "group"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env)
    out = p.stdout or ""
    print(out[-2600:], end="")
    if p.returncode == 3:
        print("[提示] 依赖缺失未执行：pip install vesi-labflow[all]")
        return 3
    if p.returncode != 0:
        print((p.stderr or "")[-1200:], file=sys.stderr, end="")
        return p.returncode
    if not out.strip():
        print("[示例] FAIL：统计管线无输出", file=sys.stderr)
        return 1
    print("[示例] stats_demo 完成 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
