# -*- coding: utf-8 -*-
"""fig1_pk_curve.py —— 血药浓度-时间半对数曲线（样例）

用途 / Purpose
    体内 PK 主图样例：脂质体组 vs 游离药组，半对数 y 轴 + 均值±SD 误差棒 + 个体散点。
输入 / Input
    无外部输入——合成数据（numpy 固定 seed），保证可复跑、可回归对比。
输出 / Output
    _out/fig1_pk_curve.png / .pdf / .svg（三格式；由 style_vesi.save_fig 落盘）
    stdout：Cmax / AUC(0-72h) / AUC 比值 等关键数值
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from style_vesi import apply_style, save_fig, trapz, GROUP_COLORS, legend

SEED = 20260921
N_REP = 5
TIME_H = np.array([0.083, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 24.0, 48.0, 72.0])


def _biphasic(t, a, alpha, b, beta):
    """双指数（快分布相 + 慢消除相）——脂质体组典型形态。"""
    return a * np.exp(-alpha * t) + b * np.exp(-beta * t)


def synth(rng):
    """合成两组血药浓度：返回 (mean, sd, individual) 字典。"""
    # 游离药组：双相（起始峰高、末端消除较快）——量级跨度控制在 ~4 个数量级内
    base_free = _biphasic(TIME_H, 45.0, 0.90, 20.0, 0.090)
    # 脂质体组：双相（起始峰较低、末端消除慢 → 长循环）
    base_lipo = _biphasic(TIME_H, 25.0, 0.90, 30.0, 0.028)
    out = {}
    for name, base in (("free", base_free), ("liposomal", base_lipo)):
        cv = 0.16 if name == "liposomal" else 0.22
        indiv = base[None, :] * np.exp(rng.normal(0.0, cv, size=(N_REP, 1)))
        out[name] = {
            "base": base,
            "indiv": indiv,
            "mean": indiv.mean(axis=0),
            "sd": indiv.std(axis=0, ddof=1),
        }
    return out


def main():
    apply_style()
    rng = np.random.default_rng(SEED)
    d = synth(rng)

    fig, ax = plt.subplots()
    for name, label, marker in (("liposomal", "Liposomal", "o"), ("free", "Free drug", "s")):
        g = d[name]
        color = GROUP_COLORS[name]
        ax.errorbar(TIME_H, g["mean"], yerr=g["sd"], color=color, marker=marker,
                    ls="-", lw=1.5, ms=4.5, capsize=2.6,
                    label=f"{label} (mean $\\pm$ SD, n={N_REP})", zorder=3)
        ax.scatter(np.repeat(TIME_H, N_REP), g["indiv"].ravel(), s=7, facecolors="none",
                   edgecolors=color, alpha=0.55, lw=0.6, zorder=2,
                   label=f"{label} individual")
    ax.set_yscale("log")
    ax.set_xlabel("Time after administration (h)")
    ax.set_ylabel("Plasma concentration ($\\mu$g/mL)")
    ax.set_xlim(left=0)
    legend(ax, ncol=1)
    fig.tight_layout()
    save_fig(fig, "fig1_pk_curve")

    # ---- 关键数值（尾部打印）----
    lipo, free = d["liposomal"], d["free"]
    auc_lipo = trapz(lipo["mean"], TIME_H)
    auc_free = trapz(free["mean"], TIME_H)
    print(f"[fig1] Cmax  liposomal = {lipo['mean'].max():.2f} ug/mL | free = {free['mean'].max():.2f} ug/mL")
    print(f"[fig1] AUC(0-72h) liposomal = {auc_lipo:.1f} | free = {auc_free:.1f} h*ug/mL"
          f" | ratio = {auc_lipo / auc_free:.2f}")
    print(f"[fig1] C72h liposomal = {lipo['mean'][-1]:.3f} ug/mL | free = {free['mean'][-1]:.3f} ug/mL")
    print(f"[fig1] n = {N_REP}/group; error bars = SD; seed = {SEED}")


if __name__ == "__main__":
    main()
