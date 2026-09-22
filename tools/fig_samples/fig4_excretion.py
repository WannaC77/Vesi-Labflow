# -*- coding: utf-8 -*-
"""fig4_excretion.py —— 累积排泄率曲线（样例）

用途 / Purpose
    排泄主图样例：累积排泄率（% of dose）随时间——胆汁 / 尿 / 粪 / 总量 四条途径 × 两组。
    1×2 面板：(a) 胆汁 + 尿（主要消除途径）｜(b) 粪 + 总回收率。
输入 / Input
    无外部输入——合成数据（numpy 固定 seed；用饱和指数模型生成单调累积曲线）。
输出 / Output
    _out/fig4_excretion.png / .pdf / .svg
    stdout：72 h 各途径累积值与总回收率（两组）
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from style_vesi import apply_style, save_fig, COLORS, LINESTYLES, MARKERS, legend

SEED = 20260924
TIMES_H = np.array([0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 24.0, 36.0, 48.0, 60.0, 72.0])

# 途径：(键, 展示名, 平台值 %，速率常数, 组别差异标识)
ROUTES = [
    ("bile", "Biliary", 38.0, 0.22),
    ("urine", "Urinary", 22.0, 0.30),
    ("feces", "Fecal", 26.0, 0.10),
]
GROUP_FACTOR = {"liposomal": 1.0, "free": 1.18}      # 游离药组排泄略快（示意）


def synth(rng):
    """合成累积排泄率曲线：y = plateau * (1 - exp(-k t)) * 组因子 * 微小噪声。"""
    out = {}
    for name in ("liposomal", "free"):
        curves = {}
        for key, _label, plateau, k in ROUTES:
            y = GROUP_FACTOR[name] * plateau * (1.0 - np.exp(-k * TIMES_H))
            y = y * np.exp(rng.normal(0.0, 0.015, size=y.shape))     # 微小测量噪声
            y[0] = 0.0
            curves[key] = y
        curves["total"] = curves["bile"] + curves["urine"] + curves["feces"]
        out[name] = curves
    return out


def main():
    apply_style()
    rng = np.random.default_rng(SEED)
    d = synth(rng)
    style_map = {
        ("liposomal", "bile"): (COLORS["blue"], "-"),
        ("liposomal", "urine"): (COLORS["blue"], "--"),
        ("free", "bile"): (COLORS["brick"], "-"),
        ("free", "urine"): (COLORS["brick"], "--"),
        ("liposomal", "feces"): (COLORS["green"], "-"),
        ("free", "feces"): (COLORS["green"], "--"),
        ("liposomal", "total"): (COLORS["violet"], "-"),
        ("free", "total"): (COLORS["violet"], "--"),
    }

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.1), sharex=True)
    panels = (
        (axes[0], ("bile", "urine"), "(a) Biliary and urinary excretion"),
        (axes[1], ("feces", "total"), "(b) Fecal excretion and total recovery"),
    )
    for ax, keys, title in panels:
        for key in keys:
            for gi, gname in enumerate(("liposomal", "free")):
                color, ls = style_map[(gname, key)]
                ax.plot(TIMES_H, d[gname][key], color=color, ls=ls,
                        marker=MARKERS[gi], ms=4.0, mfc="white", mew=1.0,
                        label=f"{key.capitalize()} - {'Liposomal' if gname == 'liposomal' else 'Free drug'}")
        ax.set_xlabel("Time after administration (h)")
        ax.set_title(title, fontsize=10.5)
        ax.set_ylim(bottom=0)
        legend(ax, ncol=2)
    axes[0].set_ylabel("Cumulative excretion (% of dose)")
    fig.suptitle("Cumulative excretion profiles, mean (synthetic demo data)", y=1.02, fontsize=11)
    save_fig(fig, "fig4_excretion")

    # ---- 关键数值（尾部打印）----
    for gname in ("liposomal", "free"):
        c = d[gname]
        print(f"[fig4] {gname:>9}: bile = {c['bile'][-1]:.1f}% | urine = {c['urine'][-1]:.1f}% | "
              f"feces = {c['feces'][-1]:.1f}% | total = {c['total'][-1]:.1f}% of dose @72 h")
    lipo, free = d["liposomal"], d["free"]
    print(f"[fig4] total recovery ratio (liposomal / free) = {lipo['total'][-1] / free['total'][-1]:.3f}")
    print(f"[fig4] route share (liposomal): bile {lipo['bile'][-1] / lipo['total'][-1] * 100:.1f}% | "
          f"urine {lipo['urine'][-1] / lipo['total'][-1] * 100:.1f}% | "
          f"feces {lipo['feces'][-1] / lipo['total'][-1] * 100:.1f}%")
    print(f"[fig4] seed = {SEED}; n = 5/group (curves = group mean)")


if __name__ == "__main__":
    main()
