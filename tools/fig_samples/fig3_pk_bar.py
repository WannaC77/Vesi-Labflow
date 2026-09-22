# -*- coding: utf-8 -*-
"""fig3_pk_bar.py —— PK 参数柱状图（样例 · 含误差棒）

用途 / Purpose
    非房室 PK 参数组间对比样例：1×3 面板——(a) AUC/Cmax（对数轴）｜(b) t1/2/MRT｜(c) CL/Vd；
    两组并排柱 + 误差棒（SD）+ 显著性标注。单位逐项写在刻度标签内（不用双 Y 轴）。
输入 / Input
    无外部输入——合成数据（numpy 固定 seed）。
输出 / Output
    _out/fig3_pk_bar.png / .pdf / .svg
    stdout：各参数 mean ± SD 与组间比值
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from style_vesi import apply_style, save_fig, sig_bar, GROUP_COLORS, legend

SEED = 20260923
N_REP = 5

# 参数表：(展示名, 主单位, 脂质体组均值, 游离药组均值, 相对 SD, 是否对数轴)
PARAMS = [
    ("AUC$_{0-72h}$", "h$\\cdot\\mu$g/mL", 1250.0, 95.0, 0.18, True),
    ("C$_{max}$", "$\\mu$g/mL", 42.0, 61.0, 0.15, True),
    ("t$_{1/2}$", "h", 24.5, 6.2, 0.20, False),
    ("MRT", "h", 31.0, 8.4, 0.19, False),
    ("CL", "mL/h/kg", 4.8, 58.0, 0.22, False),
    ("V$_{d}$", "mL/kg", 165.0, 480.0, 0.24, False),
]


def synth(rng):
    """按参数表生成两组 mean ± sd（对数正态个体，再算 SD）。"""
    out = []
    for label, unit, m_lipo, m_free, cv, log_scale in PARAMS:
        row = {"label": label, "unit": unit, "log": log_scale}
        for name, mu in (("liposomal", m_lipo), ("free", m_free)):
            indiv = mu * np.exp(rng.normal(0.0, cv, size=N_REP))
            row[name] = (float(indiv.mean()), float(indiv.std(ddof=1)))
        out.append(row)
    return out


def _panel(ax, rows, title, annotate=True):
    x = np.arange(len(rows), dtype=float)
    w = 0.36
    for k, (name, label) in enumerate((("liposomal", "Liposomal"), ("free", "Free drug"))):
        means = np.array([r[name][0] for r in rows])
        sds = np.array([r[name][1] for r in rows])
        ax.bar(x + (k - 0.5) * w, means, width=w, yerr=sds, capsize=2.6,
               color=GROUP_COLORS[name], edgecolor="black", linewidth=0.5,
               label=f"{label} (n={N_REP}, mean $\\pm$ SD)", zorder=3,
               error_kw={"elinewidth": 0.9, "ecolor": "#222222"})
    ax.set_xticks(x, [f"{r['label']}\n({r['unit']})" for r in rows])
    ax.set_title(title, fontsize=10.5)
    ax.margins(x=0.06)
    if any(r["log"] for r in rows):
        ax.set_yscale("log")
    if annotate:
        top = max(max(r["liposomal"][0], r["free"][0]) for r in rows)
        for i, r in enumerate(rows):
            y = max(r["liposomal"][0] + r["liposomal"][1], r["free"][0] + r["free"][1])
            sig_bar(ax, i - 0.18, i + 0.18, y * 1.12, "**", h=y * 0.04)
        ax.set_ylim(top=top * 2.6 if any(r["log"] for r in rows) else top * 1.45)


def main():
    apply_style()
    rng = np.random.default_rng(SEED)
    rows = synth(rng)

    fig, axes = plt.subplots(1, 3, figsize=(11.4, 4.1))
    _panel(axes[0], rows[0:2], "(a) Exposure (log scale)")
    _panel(axes[1], rows[2:4], "(b) Residence time")
    _panel(axes[2], rows[4:6], "(c) Clearance and volume")
    axes[0].set_ylabel("Value (log scale)")
    legend(axes[0])
    fig.suptitle("PK parameter comparison, mean $\\pm$ SD (synthetic demo data; * p<0.05, ** p<0.01)",
                 y=1.02, fontsize=11)
    save_fig(fig, "fig3_pk_bar")

    # ---- 关键数值（尾部打印）----
    for r in rows:
        lipo, free = r["liposomal"], r["free"]
        ratio = lipo[0] / free[0] if free[0] else float("nan")
        print(f"[fig3] {r['label']:<12} liposomal = {lipo[0]:8.2f} +/- {lipo[1]:6.2f} | "
              f"free = {free[0]:8.2f} +/- {free[1]:6.2f} {r['unit']:<12} | ratio = {ratio:5.2f}")
    print(f"[fig3] n = {N_REP}/group; error bars = SD; seed = {SEED}")


if __name__ == "__main__":
    main()
