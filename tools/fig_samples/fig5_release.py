# -*- coding: utf-8 -*-
"""fig5_release.py —— 体外释放曲线（样例 · 含模型拟合线）

用途 / Purpose
    体外释放主图样例：实测点（两组） + 两条模型拟合线——一阶模型（全时程）与 Higuchi 模型
    （前期 sqrt(t) 线性段）；拟合参数与 R² 打印在 stdout，并标注在图上。
输入 / Input
    无外部输入——合成数据（numpy 固定 seed）；拟合为**纯 numpy** 实现（不依赖 scipy）。
输出 / Output
    _out/fig5_release.png / .pdf / .svg
    stdout：各模型参数、R²、t50（释放 50% 时间）
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from style_vesi import apply_style, save_fig, GROUP_COLORS, LINESTYLES, legend

SEED = 20260925
TIMES_H = np.array([0.0, 0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 24.0, 36.0, 48.0, 72.0])
HIGUCHI_CUT_H = 8.0        # Higuchi 线性段截断（前期释放）


def synth(rng):
    """合成累积释放率（%）：脂质体组缓慢（一阶 k 小），游离药组快速。"""
    out = {}
    for name, k, plateau, cv in (("liposomal", 0.035, 92.0, 0.020),
                                 ("free", 0.42, 99.0, 0.025)):
        y = plateau * (1.0 - np.exp(-k * TIMES_H))
        y = np.clip(y * np.exp(rng.normal(0.0, cv, size=y.shape)), 0.0, 100.0)
        y[0] = 0.0
        out[name] = y
    return out


def fit_first_order(t, y):
    """一阶模型 y = plateau*(1 - exp(-k t)) 的网格+细化最小二乘（纯 numpy）。"""
    ks = np.linspace(1e-4, 2.0, 4000)
    sse = ((100.0 * (1.0 - np.exp(-np.outer(ks, t))) - y) ** 2).sum(axis=1)
    k0 = float(ks[int(np.argmin(sse))])
    ks2 = np.linspace(max(k0 - 2e-3, 1e-6), k0 + 2e-3, 4000)
    sse2 = ((100.0 * (1.0 - np.exp(-np.outer(ks2, t))) - y) ** 2).sum(axis=1)
    k = float(ks2[int(np.argmin(sse2))])
    pred = 100.0 * (1.0 - np.exp(-k * t))
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return k, pred, r2


def fit_higuchi(t, y, cut):
    """Higuchi 模型 y = k_H * sqrt(t) 的线性拟合（仅用 t <= cut 段）。"""
    mask = t <= cut
    coef = np.polyfit(np.sqrt(t[mask]), y[mask], 1)
    pred = np.polyval(coef, np.sqrt(t))
    ss_res = float(((y[mask] - np.polyval(coef, np.sqrt(t[mask]))) ** 2).sum())
    ss_tot = float(((y[mask] - y[mask].mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(coef[0]), pred, r2


def main():
    apply_style()
    rng = np.random.default_rng(SEED)
    data = synth(rng)
    t_dense = np.linspace(0.0, TIMES_H[-1], 300)

    fig, ax = plt.subplots()
    summary = {}
    for gi, name in enumerate(("liposomal", "free")):
        y = data[name]
        color = GROUP_COLORS[name]
        label = "Liposomal" if name == "liposomal" else "Free drug"
        k, _, r2_1 = fit_first_order(TIMES_H, y)
        pred1 = 100.0 * (1.0 - np.exp(-k * t_dense))
        kh, _, r2_h = fit_higuchi(TIMES_H, y, HIGUCHI_CUT_H)
        t50 = float(np.log(2.0) / k)
        summary[name] = dict(k=k, r2_1=r2_1, kh=kh, r2_h=r2_h, t50=t50)

        ax.plot(TIMES_H, y, ls="none", marker="o" if gi == 0 else "s", ms=5.0,
                mfc="white", mew=1.2, color=color, label=f"{label} (measured)")
        ax.plot(t_dense, pred1, color=color, ls="-", lw=1.4,
                label=f"{label}: first-order, k={k:.4f} h$^{{-1}}$, $R^2$={r2_1:.3f}")
        ax.plot(t_dense, kh * np.sqrt(t_dense), color=color, ls=LINESTYLES[2], lw=1.1,
                label=f"{label}: Higuchi, $k_H$={kh:.2f} %/$\\sqrt{{h}}$, $R^2$={r2_h:.3f}")
    ax.axhline(50.0, color="#999999", lw=0.7, ls=":")
    ax.text(TIMES_H[-1] * 0.99, 51.5, "50% release", ha="right", va="bottom", fontsize=8, color="#666666")
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Cumulative release (%)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 105)
    legend(ax, loc="lower right", fontsize=7.6)
    fig.tight_layout()
    save_fig(fig, "fig5_release")

    # ---- 关键数值（尾部打印）----
    for name, s in summary.items():
        print(f"[fig5] {name:>9}: first-order k = {s['k']:.4f} /h, R2 = {s['r2_1']:.4f}, "
              f"t50 = {s['t50']:.1f} h | Higuchi kH = {s['kh']:.2f} %/sqrt(h), R2 = {s['r2_h']:.4f} "
              f"(cut = {HIGUCHI_CUT_H:g} h)")
    print(f"[fig5] observed 24 h release: liposomal = {data['liposomal'][8]:.1f}% | "
          f"free = {data['free'][8]:.1f}%")
    print(f"[fig5] seed = {SEED}; n = 3/group (mean plots; fits by least squares, numpy only)")


if __name__ == "__main__":
    main()
