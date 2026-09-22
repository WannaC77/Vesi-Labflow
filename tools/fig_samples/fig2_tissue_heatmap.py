# -*- coding: utf-8 -*-
"""fig2_tissue_heatmap.py —— 组织分布热图（样例）

用途 / Purpose
    组织分布主图样例：行 = 组织，列 = 时间点；两面板并排（脂质体组 vs 游离药组），
    共用色标，便于直接比较蓄积与消退。
输入 / Input
    无外部输入——合成数据（numpy 固定 seed）。
输出 / Output
    _out/fig2_tissue_heatmap.png / .pdf / .svg
    stdout：峰值组织、肝/肾/瘤 代表值、组间蓄积倍数
"""
from __future__ import annotations

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from style_vesi import apply_style, save_fig

SEED = 20260922
TISSUES = ["Heart", "Liver", "Spleen", "Lung", "Kidney", "Brain", "Tumor"]
TIMES_H = np.array([1.0, 4.0, 8.0, 12.0, 24.0, 48.0, 72.0])

# 各组织的相对蓄积倾向（无因次），仅用于合成示意
_TISSUE_WEIGHT = np.array([0.30, 1.00, 0.85, 0.35, 0.55, 0.05, 0.45])


def synth(rng):
    """合成两组「组织浓度 (ug/g)」矩阵：shape = (n_tissues, n_times)。"""
    # 时间廓形：脂质体组衰减慢（末端留驻），游离药组衰减快
    prof_lipo = np.exp(-0.020 * TIMES_H) + 0.10
    prof_free = np.exp(-0.20 * TIMES_H) + 0.02
    scale = 8.0
    out = {}
    for name, prof, cv in (("liposomal", prof_lipo, 0.18), ("free", prof_free, 0.25)):
        m = np.outer(_TISSUE_WEIGHT, prof) * scale
        noise = np.exp(rng.normal(0.0, cv, size=m.shape))
        out[name] = m * noise
    return out


def main():
    apply_style()
    rng = np.random.default_rng(SEED)
    data = synth(rng)
    vmax = max(data["liposomal"].max(), data["free"].max())
    cmap = matplotlib.colormaps["viridis"]

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.0), sharey=True)
    im = None
    for ax, (name, matrix, title) in zip(
            axes, (("liposomal", data["liposomal"], "Liposomal"), ("free", data["free"], "Free drug"))):
        im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0.0, vmax=vmax, origin="upper")
        ax.set_xticks(np.arange(len(TIMES_H)), [f"{t:g}" for t in TIMES_H])
        ax.set_yticks(np.arange(len(TISSUES)), TISSUES)
        ax.set_xlabel("Time after administration (h)")
        ax.set_title(title, fontsize=11)
        ax.grid(False)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                ax.text(j, i, f"{matrix[i, j]:.1f}", ha="center", va="center",
                        fontsize=6.6, color="white" if matrix[i, j] < 0.62 * vmax else "black")
    axes[0].set_ylabel("Tissue")
    cbar = fig.colorbar(im, ax=axes, fraction=0.032, pad=0.02)
    cbar.set_label("Tissue concentration ($\\mu$g/g)")
    fig.suptitle("Tissue distribution: mean concentration (synthetic demo data)", y=1.02, fontsize=11)
    save_fig(fig, "fig2_tissue_heatmap")

    # ---- 关键数值（尾部打印）----
    for name in ("liposomal", "free"):
        m = data[name]
        ti, ti_t = np.unravel_index(int(np.argmax(m)), m.shape)
        print(f"[fig2] {name}: peak = {m[ti, ti_t]:.2f} ug/g at {TISSUES[ti]} @ {TIMES_H[ti_t]:g} h")
        print(f"[fig2] {name}: liver@8h = {m[TISSUES.index('Liver'), 2]:.2f} | "
              f"kidney@8h = {m[TISSUES.index('Kidney'), 2]:.2f} | "
              f"tumor@8h = {m[TISSUES.index('Tumor'), 2]:.2f} ug/g")
    ratio = (data["liposomal"][TISSUES.index("Tumor"), 5] /
             data["free"][TISSUES.index("Tumor"), 5])
    print(f"[fig2] tumor 48 h accumulation ratio (liposomal / free) = {ratio:.2f}")
    print(f"[fig2] seed = {SEED}; shape = {data['liposomal'].shape} (tissues x time points)")


if __name__ == "__main__":
    main()
