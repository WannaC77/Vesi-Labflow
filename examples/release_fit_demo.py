# -*- coding: utf-8 -*-
"""示例 3 —— 释放曲线拟合（合成数据）。

合成数据：0-24 h 累积释放率曲线（纯合成，无真实数据）。
运行：python examples/release_fit_demo.py
判据：拟合 rc=0 且输出非空 → rc=0；缺依赖按约 rc=3。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RELEASE = [  # (时间 h, 累积释放 %)
    (0.0, 0.0), (0.5, 12.6), (1.0, 24.1), (2.0, 41.8), (4.0, 63.5),
    (6.0, 76.2), (8.0, 84.0), (12.0, 91.3), (24.0, 96.8),
]


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
        csv = Path(td) / "release_synth.csv"
        rows = ["time,release"] + ["%s,%s" % (a, b) for a, b in RELEASE]
        csv.write_text(chr(10).join(rows) + chr(10), encoding="utf-8")
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        p = subprocess.run([sys.executable, str(t / "tools" / "release_fit.py"),
                            "--file", str(csv), "--time", "time", "--release", "release"],
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
        print("[示例] FAIL：拟合无输出", file=sys.stderr)
        return 1
    print("[示例] release_fit_demo 完成 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
