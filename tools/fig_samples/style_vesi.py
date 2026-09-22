# -*- coding: utf-8 -*-
"""vesi 图件样例 · 统一风格模块（style_vesi）

用途 / Purpose
    给 fig_samples 下 6 个单图脚本提供**统一风格 + 三格式落盘 + 缺字形防线**三件能力：
    ① rcParams 统一（dpi=300 / 字号 / 线宽 / 配色表 / 去顶右边框）；
    ② save_fig(fig, path) 一次导出 PNG + PDF + SVG 到 _out/ 目录；
    ③ 中文字体自动探测——探测不到即**强制英文标签**可用，绝不出现缺字形方框
       （save_fig 会先扫描图内非 ASCII 文本，中文字形不可用时直接报错，不落盘坏图）。

接口 / Interface
    apply_style(font_size=None, grid=True) -> bool          # 返回中文字形是否可用
    save_fig(fig, path, outdir=None, formats=...)-> list[Path]
    scan_tofu(fig) -> list[str]                             # 非 ASCII 文本清单
    sig_bar(ax, x1, x2, y, text)                            # 显著性横杠标注
    trapz(y, x) -> float                                    # 梯形积分（NumPy 2.x 适配）
    ENGLISH_LABELS / COLORS / COLOR_CYCLE / LINESTYLES / MARKERS

门禁 / Gates
    无缺字形（save_fig 硬断言）；三格式齐备；图内文本一律 ASCII 源（英文标签）。

降级 / Fallback
    无中文字体（非中文系统）→ 打印提示并强制英文标签；本模块不因此报错，
    但任何含中文标签的图会被 save_fig 拒绝落盘。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

# ---------------------------------------------------------------- 路径与常量
MODULE_DIR = Path(__file__).resolve().parent
OUT_DIR = MODULE_DIR / "_out"          # 所有样例图落盘目录（随模块相对定位）

DPI = 300
FONT_SIZE = 10.5
LINEWIDTH = 1.4
MARKERSIZE = 4.5
FIGSIZE = (6.3, 4.2)

# ---------------------------------------------------------------- 配色表
# 学术风：蓝主 / 砖红 / 森绿 / 赭金 / 紫灰 / 冷灰（同族深浅优先，灰度打印可辨）
COLORS = {
    "blue": "#1F4E79",
    "brick": "#C0504D",
    "green": "#2E7D32",
    "gold": "#B8860B",
    "violet": "#6A4C93",
    "slate": "#5B6770",
    "teal": "#3C8DAD",
    "plum": "#9E4A6B",
}
COLOR_CYCLE = [COLORS["blue"], COLORS["brick"], COLORS["green"], COLORS["gold"],
               COLORS["violet"], COLORS["slate"], COLORS["teal"], COLORS["plum"]]
LINESTYLES = ["-", "--", "-.", ":"]
MARKERS = ["o", "s", "^", "D", "v", "P"]

# 组别固定色（跨图一致：脂质体组 = 蓝，游离药组 = 砖红）
GROUP_COLORS = {"liposomal": COLORS["blue"], "free": COLORS["brick"]}

# ---------------------------------------------------------------- 中文字体探测
# 候选族名（先按族名查注册表）
_CJK_CANDIDATE_FAMILIES: Sequence[str] = (
    "Microsoft YaHei", "SimHei", "Microsoft JhengHei", "SimSun", "KaiTi",
    "DengXian", "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
    "Arial Unicode MS",
)
# 系统字体目录下的常见文件（**系统路径**，非用户目录；跨机按存在性自动取舍）
_SYSTEM_FONT_FILES: Sequence[str] = (
    "<系统字体目录>/msyh.ttc",
    "<系统字体目录>/simhei.ttf",
    "<系统字体目录>/simsun.ttc",
    "<系统字体目录>/Deng.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def _register_system_font_files() -> list:
    """把系统目录里存在的中文字体文件显式注册进 matplotlib（addfont 最稳）。"""
    added = []
    for fp in _SYSTEM_FONT_FILES:
        p = Path(fp)
        try:
            if p.exists():
                fm.fontManager.addfont(str(p))
                added.append(p.name)
        except Exception:                                   # noqa: BLE001 - 字体注册失败不应中断绘图
            continue
    return added


def available_families() -> set:
    """当前 matplotlib 已注册的字体族名集合。"""
    return {f.name for f in fm.fontManager.ttflist}


def detect_cjk_font() -> Optional[str]:
    """探测可用的中文字体族名；找不到返回 None（→ 强制英文标签）。"""
    fams = available_families()
    for name in _CJK_CANDIDATE_FAMILIES:
        if name in fams:
            return name
    return None


_REGISTERED_FILES = _register_system_font_files()
CJK_FONT = detect_cjk_font()

# ---------------------------------------------------------------- 英文标签提示
ENGLISH_LABELS = """\
【英文标签纪律】轴标签/图内文字一律用英文（ASCII 源），避免缺字形方框。本项目常用对照：
    时间 Time (h)                 浓度 Concentration (ug/mL) / ($\\mu$g/mL)
    血浆/血药 Plasma              组织浓度 Tissue concentration (ug/g)
    累积释放率 Cumulative release (%)
    累积排泄率 Cumulative excretion (% of dose)
    剂量 Dose (mg/kg)             体重 Body weight (g)
    体积 Volume (mL)              质量 Mass (g) / 回收率 Recovery (%)
    粒径 Particle size (nm)       多分散指数 PDI              Zeta 电位 Zeta potential (mV)
    包封率 Encapsulation efficiency (%)        载药量 Drug loading (%)
    脂质体组 Liposomal / Lipo     游离药组 Free / Free drug
    误差棒 Error bars = SD (n = 5)             显著性 * p < 0.05, ** p < 0.01
"""


# ---------------------------------------------------------------- 风格
def apply_style(font_size: Optional[float] = None, grid: bool = True) -> bool:
    """设置全局 matplotlib 风格（每个脚本开头调用一次）。

    返回 True = 中文字形可用；False = 仅英文标签可用（此时所有标签必须 ASCII）。
    """
    base = FONT_SIZE if font_size is None else float(font_size)
    sans = ([CJK_FONT] if CJK_FONT else []) + ["DejaVu Sans"]
    matplotlib.rcParams.update({
        # 分辨率与落盘
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        # 字体（CJK 族名必须排在 DejaVu 之前，否则中文 tofu）
        "font.family": "sans-serif",
        "font.sans-serif": sans,
        "font.size": base,
        "axes.titlesize": base + 1,
        "axes.labelsize": base,
        "xtick.labelsize": base - 1,
        "ytick.labelsize": base - 1,
        "legend.fontsize": base - 1,
        "mathtext.fontset": "dejavusans",
        "axes.unicode_minus": False,
        # 线宽与坐标框：去顶右边框
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": LINEWIDTH,
        "lines.markersize": MARKERSIZE,
        "errorbar.capsize": 2.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        # 网格（浅）
        "axes.grid": bool(grid),
        "grid.alpha": 0.28,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "axes.axisbelow": True,
        # 配色
        "axes.prop_cycle": plt.cycler(color=COLOR_CYCLE),
        # 画布
        "figure.figsize": FIGSIZE,
        # 可编辑矢量文本（Word/PPT/LaTeX 复用）
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })
    if CJK_FONT is None:
        print("[style_vesi] 未探测到中文字体 → 全部轴标签/图内文字必须用英文标签"
              "（可用 ENGLISH_LABELS 对照表）")
    return CJK_FONT is not None


# ---------------------------------------------------------------- 缺字形防线
def scan_tofu(fig) -> list:
    """扫描图内所有 Text：返回含非 ASCII 字符的文本清单（用于缺字形防线）。

    中文可用时返回的清单属正常（未用则应为空）；中文不可用时非空 = 会出方框。
    """
    from matplotlib.text import Text
    hits = []
    for t in fig.findobj(Text):
        s = (t.get_text() or "").strip()
        if not s:
            continue
        if not s.isascii():
            hits.append(s[:40])
    if hits and CJK_FONT is None:
        print(f"[style_vesi] ✗ 检出非 ASCII 文本 {len(hits)} 处，而中文字形不可用：{hits[:5]}")
    return hits


def save_fig(fig, path, outdir=None, formats=("png", "pdf", "svg"), close: bool = True) -> list:
    """三格式落盘：PNG + PDF + SVG，统一写入 _out/ 目录。

    path    : 基名（'fig1_pk_curve'）或带扩展名（'fig1_pk_curve.png'）皆可；
              **目录部分被忽略**——落盘目录恒为 outdir（默认 fig_samples/_out/）。
    outdir  : 自定义落盘目录（Path）；默认 OUT_DIR。
    formats : 需导出的格式元组，默认 ("png","pdf","svg")。
    返回    : 落盘文件 Path 列表。

    防线：中文字形不可用且图内有非 ASCII 文本 → 抛 RuntimeError，**不落盘坏图**。
    """
    outdir = Path(outdir) if outdir is not None else OUT_DIR
    stem = Path(str(path)).stem
    hits = scan_tofu(fig)
    if hits and CJK_FONT is None:
        raise RuntimeError(
            "图内含非 ASCII 文本但无可用中文字体（会渲染成方框）：%s —— 请改用英文标签。" % hits[:5]
        )
    outdir.mkdir(parents=True, exist_ok=True)
    outs = []
    for fmt in formats:
        p = outdir / f"{stem}.{fmt}"
        fig.savefig(p)
        outs.append(p)
    if close:
        plt.close(fig)
    print("[style_vesi] 已落盘: " + " | ".join(str(p.name) for p in outs))
    return outs


# ---------------------------------------------------------------- 小工具
def sig_bar(ax, x1: float, x2: float, y: float, text: str = "*", h: float = 0.0, **kw):
    """在两组柱之间画显著性横杠（y 为横杠高度，h 为下折线长度）。"""
    ax.plot([x1, x1, x2, x2], [y - h, y, y, y - h],
            color=kw.pop("color", "#333333"), lw=0.9, **kw)
    ax.text((x1 + x2) / 2.0, y, text, ha="center", va="bottom", fontsize=9)


def trapz(y, x) -> float:
    """梯形积分；NumPy 2.x 将 np.trapz 更名 np.trapezoid（本函数自动适配，缺则回退）。"""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    fn = getattr(np, "trapezoid", None)
    if fn is None:                                            # NumPy < 2.0
        fn = getattr(np, "trapz")
    return float(fn(y, x))


def legend(ax, **kw):
    """统一样式图例（无边框、半透明底、位置默认自动）。"""
    kw.setdefault("frameon", False)
    kw.setdefault("loc", "best")
    return ax.legend(**kw)


__all__ = [
    "apply_style", "save_fig", "scan_tofu", "sig_bar", "trapz", "legend",
    "ENGLISH_LABELS", "COLORS", "COLOR_CYCLE", "GROUP_COLORS", "LINESTYLES",
    "MARKERS", "OUT_DIR", "MODULE_DIR", "DPI", "CJK_FONT",
]
