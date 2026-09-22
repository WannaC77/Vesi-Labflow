# -*- coding: utf-8 -*-
"""fig6_char.py —— 制剂表征（样例 · 条形 / 分布示意）

用途 / Purpose
    制剂表征三面板样例：(a) 粒径分布（对数正态示意曲线，两组）｜(b) Zeta 电位分布｜
    (c) 包封率 / 载药量柱状图（含误差棒 + 个体点）。
输入 / Input
    无外部输入——合成数据（numpy 固定 seed）。
输出 / Output
    _out/fig6_char.png / .pdf / .svg
    stdout：Z-average、PDI、zeta 均值、EE%、DL%（两组）
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from style_vesi import apply_style, save_fig, sig_bar, GROUP_COLORS, COLORS, legend

SEED = 20260926
N_REP = 3
SIZE_GRID = np.linspace(10.0, 1000.0, 400)
ZETA_GRID = np.linspace(-60.0, 10.0, 400)

# 制剂：(展示名, 粒径峰位 nm, 几何 SD, zeta 均值 mV, zeta SD, EE% , DL%)
FORMULATIONS = [
    ("Liposomal", 118.0, 0.16, -21.5, 3.2, 88.0, 7.4),
    ("Free drug", 240.0, 0.42, -8.0, 5.5, 0.0, 0.0),
]


def lognorm_pdf(x, peak, sigma):
    """对数正态概率密度（峰值 ≈ exp(mu) = peak；纯 numpy 实现）。"""
    mu = np.log(peak)
    x = np.asarray(x, dtype=float)
    return np.exp(-((np.log(x) - mu) ** 2) / (2.0 * sigma ** 2)) / (x * sigma * np.sqrt(2.0 * np.pi))


def gauss_pdf(x, mu, sigma):
    return np.exp(-((x - mu) ** 2) / (2.0 * sigma ** 2)) / (sigma * np.sqrt(2.0 * np.pi))


def synth(rng):
    """生成粒径/电位分布曲线 + 包封率与载药量的个体值。"""
    out = {}
    for name, peak, sigma, zmu, zsd, ee, dl in FORMULATIONS:
        size = lognorm_pdf(SIZE_GRID, peak, sigma)
        zeta = gauss_pdf(ZETA_GRID, zmu, zsd)
        out[name] = {
            "size": size / size.max(),                      # 归一化（示意）
            "zeta": zeta / zeta.max(),
            "ee_indiv": np.clip(rng.normal(ee, 1.6 if ee else 0.0, size=N_REP), 0.0, 100.0),
            "dl_indiv": np.clip(rng.normal(dl, 0.25 if dl else 0.0, size=N_REP), 0.0, 100.0),
            "peak": peak, "pdi": sigma ** 2, "zeta_mu": zmu,
        }
    return out


def main():
    apply_style()
    rng = np.random.default_rng(SEED)
    d = synth(rng)

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.9))

    # (a) 粒径分布
    ax = axes[0]
    for name in ("Liposomal", "Free drug"):
        ax.plot(SIZE_GRID, d[name]["size"], color=GROUP_COLORS["liposomal" if name == "Liposomal" else "free"],
                lw=1.5, label=f"{name} (peak {d[name]['peak']:.0f} nm)")
    ax.set_xscale("log")
    ax.set_xlabel("Hydrodynamic diameter (nm)")
    ax.set_ylabel("Normalized intensity")
    ax.set_title("(a) Size distribution (DLS)", fontsize=10.5)
    ax.set_ylim(bottom=0)
    legend(ax, fontsize=7.8)

    # (b) Zeta 电位分布
    ax = axes[1]
    for name in ("Liposomal", "Free drug"):
        ax.plot(ZETA_GRID, d[name]["zeta"], color=GROUP_COLORS["liposomal" if name == "Liposomal" else "free"],
                lw=1.5, label=f"{name} ({d[name]['zeta_mu']:.1f} mV)")
    ax.axvline(0.0, color="#999999", lw=0.7, ls=":")
    ax.set_xlabel("Zeta potential (mV)")
    ax.set_ylabel("Normalized count")
    ax.set_title("(b) Zeta potential distribution", fontsize=10.5)
    ax.set_ylim(bottom=0)
    legend(ax, fontsize=7.8)

    # (c) 包封率 / 载药量
    ax = axes[2]
    x = np.arange(2, dtype=float)
    w = 0.34
    for k, (name, color) in enumerate((("Liposomal", GROUP_COLORS["liposomal"]),
                                       ("Free drug", GROUP_COLORS["free"]))):
        ee = d[name]["ee_indiv"].mean()
        ee_sd = d[name]["ee_indiv"].std(ddof=1)
        dl = d[name]["dl_indiv"].mean()
        dl_sd = d[name]["dl_indiv"].std(ddof=1)
        off = (k - 0.5) * w
        ax.bar(x[0] + off, ee, width=w, yerr=ee_sd, capsize=2.6, color=color,
               edgecolor="black", lw=0.5, zorder=3,
               error_kw={"elinewidth": 0.9, "ecolor": "#222222"})
        ax.bar(x[1] + off, dl, width=w, yerr=dl_sd, capsize=2.6, color=color,
               edgecolor="black", lw=0.5, alpha=0.55, zorder=3,
               error_kw={"elinewidth": 0.9, "ecolor": "#222222"})
        ax.scatter(np.full(N_REP, x[0] + off), d[name]["ee_indiv"], s=12, color="#FFFFFF",
                   edgecolor="#222222", lw=0.6, zorder=4)
    ax.set_xticks(x, ["Encapsulation\nefficiency (%)", "Drug loading\n(%)"])
    ax.set_title("(c) EE and DL (mean $\\pm$ SD, n=3)", fontsize=10.5)
    ax.set_ylim(0, 118)
    sig_bar(ax, x[0] - 0.17, x[0] + 0.17, 103.0, "**", h=4.0)
    ax.text(0.02, 0.02, "solid = Liposomal, pale = Free drug", transform=ax.transAxes,
            fontsize=7.2, color=COLORS["slate"])
    fig.suptitle("Formulation characterization (synthetic demo data)", y=1.03, fontsize=11)
    fig.tight_layout()
    save_fig(fig, "fig6_char")

    # ---- 关键数值（尾部打印）----
    for name in ("Liposomal", "Free drug"):
        g = d[name]
        print(f"[fig6] {name:>9}: Z-average = {g['peak']:.0f} nm | PDI (geom.) = {g['pdi']:.3f} | "
              f"zeta = {g['zeta_mu']:.1f} mV")
        print(f"[fig6] {name:>9}: EE = {g['ee_indiv'].mean():.1f} +/- {g['ee_indiv'].std(ddof=1):.2f} % | "
              f"DL = {g['dl_indiv'].mean():.2f} +/- {g['dl_indiv'].std(ddof=1):.2f} %")
    ee = d["Liposomal"]["ee_indiv"]
    print(f"[fig6] liposomal EE individual values: " + ", ".join(f"{v:.1f}" for v in ee) + " (%)")
    print(f"[fig6] seed = {SEED}; n = {N_REP} (independent batches)")


if __name__ == "__main__":
    main()
