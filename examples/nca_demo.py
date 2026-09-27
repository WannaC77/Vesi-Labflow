# -*- coding: utf-8 -*-
"""示例 1 —— NCA（非房室分析）合成数据跑通。

合成数据：单个体、单次给药（剂量 5 单位）的浓度-时间曲线（纯合成，无真实数据）。
运行：python examples/nca_demo.py
判据：nca rc=0 且输出含 AUC → rc=0；缺依赖按约 rc=3。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DATA = [  # (时间 h, 浓度 单位/mL) —— 合成
    (0.083, 118.4), (0.25, 96.8), (0.5, 78.2), (1.0, 61.5), (2.0, 44.9),
    (4.0, 31.7), (6.0, 22.6), (8.0, 16.1), (12.0, 8.3), (24.0, 2.0),
]


def tree() -> Path:
    """定位工具树：LABFLOW_ROOT 优先；否则从本文件向上找（仓库 checkout 或安装包 _tree）。"""
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
        csv = Path(td) / "pk_synth.csv"
        lines = ["time,conc"] + ["%s,%s" % (a, b) for a, b in DATA]
        csv.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        p = subprocess.run([sys.executable, str(t / "tools" / "nca.py"),
                            "--file", str(csv), "--time", "time", "--conc", "conc",
                            "--dose", "5"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env)
    print(p.stdout[-2000:], end="")
    if p.returncode == 3:
        print("[提示] 依赖缺失未执行：pip install vesi-labflow[all]")
        return 3
    if p.returncode != 0:
        print(p.stderr[-1200:], file=sys.stderr, end="")
        return p.returncode
    if "AUC" not in p.stdout:
        print("[示例] FAIL：nca 输出未见 AUC", file=sys.stderr)
        return 1
    print("[示例] nca_demo 完成 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
