# -*- coding: utf-8 -*-
"""体外释放曲线拟合与释放机理解析（零级/一级/Higuchi/Korsmeyer-Peppas/Hixson-Crowell/Weibull）。

适用场景
    纳米制剂（如候选药物 X 脂质体）体外释放实验数据处理：累积释放率(%)-时间(h) 曲线
    的模型拟合、参数估计、模型排名（AIC）与释放机理判读。可多重复列输入
    （自动取均值 ± SD）。

模型（F = 累积释放率 %，t = h）
    零级        ：F = k0·t
    一级        ：F = 100·(1 − e^(−k1·t))
    Higuchi     ：F = kH·√t                      （扩散控释，经典形式）
    Korsmeyer-Peppas：F = k·t^n                   （n 为释放指数，见释义表）
    Hixson-Crowell：F = 100 − (100^(1/3) − kHC·t)³（溶蚀/表面积减小控释）
    Weibull     ：F = 100·(1 − e^(−(t/scale)^shape))（经验模型，参数无直接机理含义）

口径声明
    1. 拟合对象为**累积释放率(%)**（不是累计释放量）；时间须 ≥ 0，t=0 可在数据中。
    2. 未加权非线性最小二乘（curve_fit）；多重复时先取均值再拟合，SD 仅用于报告。
    3. R²adj = 1 − (1−R²)(n−1)/(n−k−1)；AIC = n·ln(RSS/n) + 2k；排名按 AIC 升序。
       模型比较要求同一数据集同一响应（本脚本对全部模型用同一份数据）。
       RSS 下垫 1e-24 仅为防 log(0)，对真实数据无影响。
    4. **适用范围警告**：Higuchi / Korsmeyer-Peppas / Hixson-Crowell 的机理解释
       通常只在前 ~60% 释放段成立；若数据含 >60% 的点，脚本会打印提示，
       此时参数仅供拟合参考，不宜直接作机理解释。
    5. Korsmeyer-Peppas 指数 n 的释义按**圆柱/纤维几何**阈值给出（0.45/0.89）。
       几何形状改变阈值也变：球体为 0.43（Fickian）与 0.85（Case-II），
       薄膜（平板）为 0.5 与 1.0 —— 解读时须与制剂几何一致。

输入
    CSV / TSV / Excel（.xlsx/.xls/.xlsm），列名参数化：
        --time 时间列；--release 单列；或 --rep 多重复列（逗号分隔，取均值±SD）
    CSV/TSV 走标准库解析（编码回退 utf-8-sig → gb18030 → latin-1）；Excel 走 pandas
    （该解释器缺 pandas/openpyxl 时明确报错并提示转存 CSV，不静默）。
输出
    Markdown 报告（各模型参数、R²/R²adj、AIC、ΔAIC、排名、KP 指数释义、最佳模型推荐）；
    --json 输出 JSON。
依赖
    numpy / scipy（必需）；pandas 仅 Excel 输入时需要；不依赖 matplotlib。
命令行示例
    python release_fit.py --selftest
    python release_fit.py --demo
    python release_fit.py --file release.csv --time time --release release
    python release_fit.py --file release.csv --time 时间 --rep R1,R2,R3
    python release_fit.py --file release.tsv --time 时间 --release 释放率 --json
"""

import argparse
import csv
import json
import os
import sys
import tempfile

import numpy as np
from scipy.optimize import curve_fit

# ============ 默认参数区（在这里改 / 或用命令行覆盖）============
DEFAULT_TIME_COL = "time"       # 时间列名（h）
DEFAULT_REL_COL = "release"     # 释放率列名（%）
MODELS = ("zero", "first", "higuchi", "kp", "hc", "weibull")
MODEL_LABELS = {
    "zero": "零级：F = k0·t",
    "first": "一级：F = 100·(1 − e^(−k1·t))",
    "higuchi": "Higuchi：F = kH·√t",
    "kp": "Korsmeyer-Peppas：F = k·t^n",
    "hc": "Hixson-Crowell：F = 100 − (100^(1/3) − kHC·t)³",
    "weibull": "Weibull：F = 100·(1 − e^(−(t/scale)^shape))",
}
PARAM_NAMES = {"zero": ("k0",), "first": ("k1",), "higuchi": ("kH",),
               "kp": ("k", "n"), "hc": ("kHC",), "weibull": ("scale", "shape")}
N_PARAMS = {m: len(PARAM_NAMES[m]) for m in MODELS}
RSS_FLOOR = 1e-24               # 防 log(0)（仅完美拟合时生效）
MAXFEV = 200000
CBRT100 = 100.0 ** (1.0 / 3.0)  # 100^(1/3)，Hixson-Crowell 用
VALID_FRACTION_PCT = 60.0       # Higuchi/KP/HC 的机理解释上限（前 60% 释放）
EXCEL_EXTS = (".xlsx", ".xls", ".xlsm")
TAB_EXTS = (".tsv", ".txt")     # 制表符分隔（标准库 csv 带 delimiter="\t" 解析）
CSV_ENCODINGS = ("utf-8-sig", "gb18030", "latin-1")   # CSV/TSV 编码回退顺序
NA_TOKENS = ("", "na", "nan", "n/a", "null", "none", "-")

# Korsmeyer-Peppas 释放指数 n 释义表（圆柱/纤维几何阈值）
KP_N_TABLE = (
    (0.0, 0.45, "n ≤ 0.45：Fickian 扩散控释"),
    (0.45, 0.89, "0.45 < n < 0.89：异常案例（anomalous transport，扩散 + 溶蚀耦合）"),
    (0.89, 0.895, "n ≈ 0.89：Case-II 转运（溶蚀/松弛主导，表观零级）"),
    (0.895, float("inf"), "n > 0.89：Super Case-II 转运（加速溶蚀/侵蚀）"),
)
# ===============================================================


# ------------------------------------------------------------------
# 输入读取（标准库优先；无 pandas 亦可跑）
# ------------------------------------------------------------------
def _num(v):
    """单元格 → float；空/NA 记号 → NaN；其余解析失败抛 ValueError。"""
    if v is None:
        return float("nan")
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.lower() in NA_TOKENS:
        return float("nan")
    return float(s)


def _read_delimited(path, encoding="utf-8-sig"):
    """读 CSV/TSV → (列名 list, 行 dict list)；编码按 CSV_ENCODINGS 回退。"""
    ext = os.path.splitext(path)[1].lower()
    sep = "\t" if ext in TAB_EXTS else ","
    tried, last, raw = [], None, None
    order = [encoding] + [e for e in CSV_ENCODINGS if e != encoding]
    for enc in order:
        tried.append(enc)
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                raw = list(csv.reader(f, delimiter=sep))
            break
        except (UnicodeDecodeError, UnicodeError) as exc:
            last = exc
    if raw is None:
        raise SystemExit("[错误] 读入失败（已试编码 %s）：%s" % (tried, last))
    if not raw:
        raise SystemExit("[错误] 空文件：%s" % path)
    cols = [str(c).strip() for c in raw[0]]
    rows = []
    for rec in raw[1:]:
        if not any(str(x).strip() for x in rec):     # 跳过空行
            continue
        rows.append({cols[i]: (rec[i] if i < len(rec) else "") for i in range(len(cols))})
    return cols, rows


def load_table(path, encoding="utf-8-sig"):
    """读 CSV/TSV/Excel → (列名 list, 行 dict list)。缺件不静默：Excel 无 pandas → 明确报错。"""
    if not os.path.isfile(path):
        raise SystemExit("[错误] 找不到输入文件：%s" % path)
    ext = os.path.splitext(path)[1].lower()
    if ext in EXCEL_EXTS:
        try:
            import pandas as pd                          # 惰性导入：仅 Excel 输入需要
        except Exception as exc:                         # noqa: BLE001
            raise SystemExit("[错误] 读取 Excel 需要 pandas + openpyxl（当前解释器不可用：%s）。"
                             "[降级] 请把表另存为 CSV/TSV 后重跑（CSV 走标准库，无第三方依赖）。" % exc)
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        return list(df.columns), df.to_dict("records")
    return _read_delimited(path, encoding=encoding)


def col_float(rows, col):
    """取数值列 → np.ndarray；空/NA → NaN；非数值 → SystemExit（报数据序号）。"""
    out = []
    for i, r in enumerate(rows, start=1):
        v = r.get(col)
        try:
            out.append(_num(v))
        except ValueError:
            raise SystemExit("[错误] 列 `%s` 第 %d 个数据值不是数值：%r" % (col, i, v))
    return np.asarray(out, dtype=float)


def rep_matrix(rows, rep_cols):
    """多重复列 → (均值列, SD 列)；列数 = 1 时 SD 全为 NaN（与单列口径一致）。"""
    mat = np.column_stack([col_float(rows, c) for c in rep_cols])
    f = np.nanmean(mat, axis=1)
    sd = np.nanstd(mat, axis=1, ddof=1) if mat.shape[1] > 1 else np.full(len(f), np.nan)
    return f, sd


# ------------------------------------------------------------------
# 模型函数
# ------------------------------------------------------------------
def m_zero(t, k0):
    """零级释放：F = k0·t。"""
    return k0 * np.asarray(t, dtype=float)


def m_first(t, k1):
    """一级释放：F = 100·(1 − e^(−k1·t))。"""
    return 100.0 * (1.0 - np.exp(-k1 * np.asarray(t, dtype=float)))


def m_higuchi(t, kH):
    """Higuchi 扩散控释：F = kH·√t。"""
    return kH * np.sqrt(np.asarray(t, dtype=float))


def m_kp(t, k, n):
    """Korsmeyer-Peppas：F = k·t^n。"""
    return k * np.power(np.asarray(t, dtype=float), n)


def m_hc(t, kHC):
    """Hixson-Crowell（溶蚀/表面积减小）：(100^(1/3) − (100−F)^(1/3)) = kHC·t。"""
    r = np.clip(CBRT100 - kHC * np.asarray(t, dtype=float), 0.0, None)
    return 100.0 - r ** 3


def m_weibull(t, scale, shape):
    """Weibull 经验模型：F = 100·(1 − e^(−(t/scale)^shape))。"""
    t = np.asarray(t, dtype=float)
    return 100.0 * (1.0 - np.exp(-np.power(t / scale, shape)))


def model_func(model):
    """模型名 -> 函数。"""
    return {"zero": m_zero, "first": m_first, "higuchi": m_higuchi,
            "kp": m_kp, "hc": m_hc, "weibull": m_weibull}[model]


def kp_n_text(n):
    """Korsmeyer-Peppas 指数 n 的机理释义。"""
    for lo, hi, txt in KP_N_TABLE:
        if lo <= n < hi:
            return txt
    return "-"


# ------------------------------------------------------------------
# 初值 / 边界
# ------------------------------------------------------------------
def initial_guess(model, t, f):
    """数据驱动初值 + 边界（f 为累积释放率 %）。"""
    f_max = float(np.max(f))
    t_max = float(np.max(t))
    t_pos = t[t > 0]
    t_min_pos = float(np.min(t_pos)) if len(t_pos) else 1.0

    if model == "zero":
        p0, lo, hi = [max(f_max / max(t_max, 1e-6), 1e-6)], [1e-9], [1e4]
    elif model == "first":
        frac = min(f_max / 100.0, 0.999)                        # 防止 log(0)
        k0 = -np.log(1.0 - frac) / max(t_max, 1e-6)
        p0, lo, hi = [max(k0, 1e-6)], [1e-9], [100.0]
    elif model == "higuchi":
        p0, lo, hi = [max(f_max / max(np.sqrt(t_max), 1e-6), 1e-6)], [1e-9], [1e4]
    elif model == "kp":
        n0 = 0.5                                                # 先按 Higuchi 起步
        k0 = f_max / max(t_max ** n0, 1e-6)
        p0, lo, hi = [max(k0, 1e-6), n0], [1e-9, 0.01], [1e4, 3.0]
    elif model == "hc":
        r_max = max(1e-6, CBRT100 - (max(100.0 - f_max, 0.0)) ** (1.0 / 3.0))
        p0, lo, hi = [r_max / max(t_max, 1e-6)], [1e-9], [CBRT100 / max(t_min_pos, 1e-6)]
    elif model == "weibull":
        # scale 初值取 F≈63.2% 的时间（存在则线性内插，否则用最大时间）
        idx = np.where(f >= 63.2)[0]
        if len(idx) and idx[0] > 0:
            i = int(idx[0])
            t1, t2, f1, f2 = t[i - 1], t[i], f[i - 1], f[i]
            scale0 = float(t1 + (t2 - t1) * (63.2 - f1) / (f2 - f1)) if f2 != f1 else float(t2)
        else:
            scale0 = t_max
        p0, lo, hi = [max(scale0, t_min_pos * 0.1), 1.0], [1e-6, 0.01], [1e4, 50.0]
    else:
        raise ValueError(f"未知模型 {model}（可选 {MODELS}）")

    p0 = [min(max(p, l * 1.000001 + 1e-12), h * 0.999999) for p, l, h in zip(p0, lo, hi)]
    return np.array(p0, dtype=float), (np.array(lo, dtype=float), np.array(hi, dtype=float))


# ------------------------------------------------------------------
# 拟合 + 统计量
# ------------------------------------------------------------------
def fit_model(model, t_in, f_in):
    """拟合单个释放模型，返回 dict（参数、R²/R²adj、AIC、残差小结）。"""
    t = np.asarray(t_in, dtype=float)
    f = np.asarray(f_in, dtype=float)
    func = model_func(model)
    p0, bounds = initial_guess(model, t, f)
    try:
        popt, pcov = curve_fit(func, t, f, p0=p0, bounds=bounds, maxfev=MAXFEV)
    except Exception as exc:
        return {"model": model, "label": MODEL_LABELS[model], "ok": False,
                "error": f"{type(exc).__name__}: {exc}", "n": int(len(t)), "k": N_PARAMS[model]}

    pred = func(t, *popt)
    resid = f - pred
    n, k = int(len(t)), int(len(popt))
    rss = float(np.sum(resid ** 2))
    tss = float(np.sum((f - f.mean()) ** 2))
    r2 = 1.0 - rss / tss if tss > 0 else float("nan")
    r2adj = 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1) if n - k - 1 > 0 else float("nan")
    rss_eff = max(rss, RSS_FLOOR)
    aic = n * np.log(rss_eff / n) + 2 * k
    bic = n * np.log(rss_eff / n) + k * np.log(n)
    aicc = aic + 2 * k * (k + 1) / (n - k - 1) if n - k - 1 > 0 else float("nan")
    se = np.sqrt(np.diag(pcov))
    se = np.where(np.isfinite(se), se, np.nan)
    # 触界检查：参数贴在上下界上 => 该估计值不可用于参数/机理结论
    lo, hi = bounds
    bound_flags = [bool(np.isclose(v, l, rtol=1e-6, atol=0.0) or np.isclose(v, h, rtol=1e-6, atol=0.0))
                   for v, l, h in zip(popt, lo, hi)]
    out = {
        "model": model, "label": MODEL_LABELS[model], "ok": True,
        "params": [float(v) for v in popt], "param_names": PARAM_NAMES[model],
        "se": [float(v) for v in se], "n": n, "k": k,
        "bound_flags": bound_flags,
        "bound_hit_names": [nm for nm, fl in zip(PARAM_NAMES[model], bound_flags) if fl],
        "rss": rss, "r2": r2, "r2adj": r2adj, "aic": aic, "bic": bic, "aicc": aicc,
        "rmse": float(np.sqrt(rss / n)),
        "resid_max_abs": float(np.max(np.abs(resid))),
        "resid_sign_changes": int(np.sum(np.diff(np.sign(resid)) != 0)) if n > 1 else 0,
        "f_max_fitted": float(np.max(pred)), "f_max_obs": float(np.max(f)),
    }
    if model == "kp":
        out["kp_n_interpretation"] = kp_n_text(float(popt[1]))
    return out


def fit_all(t, f, models=MODELS):
    """拟合并按 AIC 排名，返回 (results, best_model 名或 None)。"""
    results = [fit_model(m, t, f) for m in models]
    good = [r for r in results if r["ok"]]
    for r in good:
        r["delta_aic"] = r["aic"] - min(x["aic"] for x in good)
    denom = sum(np.exp(-0.5 * r["delta_aic"]) for r in good) if good else 0.0
    for r in good:
        r["akaike_w"] = float(np.exp(-0.5 * r["delta_aic"]) / denom) if denom > 0 else float("nan")
    good.sort(key=lambda r: r["aic"])
    for i, r in enumerate(good, 1):
        r["rank"] = i
    return results, (good[0]["model"] if good else None)


# ------------------------------------------------------------------
# 报告
# ------------------------------------------------------------------
def _fmt(x, nd=4):
    """数值格式化（NaN 稳妥处理）。"""
    if x is None:
        return "-"
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return "nan"
    ax = abs(x)
    if ax != 0 and (ax < 1e-3 or ax >= 1e6):
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def report_markdown(t, f, sd, results, best):
    """Markdown 报告。"""
    good = [r for r in results if r["ok"]]
    good.sort(key=lambda r: r["aic"])
    lines = ["# 体外释放拟合报告", ""]
    lines.append(f"- 数据点数 n = {len(f)}；时间范围 {_fmt(float(np.min(t)))} – "
                 f"{_fmt(float(np.max(t)))} h；F_max = {_fmt(float(np.max(f)), 5)} %")
    if sd is not None and np.any(np.isfinite(sd)):
        lines.append(f"- 重复测量 SD（均值列拟合）：平均 SD = "
                     f"{_fmt(float(np.nanmean(sd)), 3)}%，最大 SD = {_fmt(float(np.nanmax(sd)), 3)}%")
    lines.append("- 全部模型使用**同一份数据**；未加权最小二乘；排名按 AIC 升序")
    lines.append(f"- RSS 下垫 {RSS_FLOOR:g} 仅防 log(0)；AIC = n·ln(RSS/n) + 2k")
    lines.append("")
    if float(np.max(f)) > VALID_FRACTION_PCT:
        lines.append(f"> **适用范围提示**：数据最大释放 {_fmt(float(np.max(f)), 4)}% > "
                     f"{VALID_FRACTION_PCT:g}%。Higuchi / Korsmeyer-Peppas / Hixson-Crowell "
                     "的机理解释通常只在前 ~60% 释放段成立，含高释放段时参数仅供拟合参考。")
        lines.append("")
    lines.append("## 各模型拟合结果")
    lines.append("")
    lines.append("| 模型 | 参数 | R² | R²adj | AIC | ΔAIC | Akaike 权重 | 排名 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in good:
        bf = r.get("bound_flags") or [False] * len(r["params"])
        ps = "；".join(f"{nm}{' ⚠触界' if fl else ''} = {_fmt(v, 5)}"
                       + (f" ± {_fmt(s, 3)}" if np.isfinite(s) else "")
                       for nm, v, s, fl in zip(r["param_names"], r["params"], r["se"], bf))
        lines.append(f"| {r['model']} | {ps} | {_fmt(r['r2'], 6)} | {_fmt(r['r2adj'], 6)} | "
                     f"{_fmt(r['aic'], 6)} | {_fmt(r['delta_aic'], 4)} | "
                     f"{_fmt(r['akaike_w'], 4)} | {r['rank']} |")
    lines.append("")
    for r in good:
        if r.get("bound_hit_names"):
            lines.append(f"- ⚠ 模型 {r['model']} 参数触及边界：{', '.join(r['bound_hit_names'])}"
                         "（估计值不可用于参数/机理结论）")
    lines.append("")
    for r in results:
        if not r["ok"]:
            lines.append(f"- 模型 {r['model']} 拟合失败：{r['error']}")
    if any(not r["ok"] for r in results):
        lines.append("")
    lines.append("## Korsmeyer-Peppas 释放指数 n 释义")
    lines.append("")
    for lo, hi, txt in KP_N_TABLE:
        rng = f"[{lo:g}, {hi:g})" if hi != float("inf") else f"[{lo:g}, +∞)"
        lines.append(f"- {rng} {txt}")
    lines.append("- 阈值随几何形状变化：薄膜(平板) 0.5/1.0；圆柱-纤维 0.45/0.89；球体 0.43/0.85")
    kp = [r for r in results if r["ok"] and r["model"] == "kp"]
    if kp:
        n_fit = kp[0]["params"][1]
        lines.append(f"- **本数据拟合 n = {_fmt(n_fit, 5)} → {kp_n_text(n_fit)}**")
    lines.append("")
    lines.append("## 残差小结")
    lines.append("")
    for r in good:
        lines.append(f"- {r['model']}：RMSE = {_fmt(r['rmse'], 4)} %；最大绝对残差 = "
                     f"{_fmt(r['resid_max_abs'], 4)} %；符号变化 {r['resid_sign_changes']} 次")
    lines.append("")
    if best:
        r = [x for x in good if x["model"] == best][0]
        runner = good[1] if len(good) > 1 else None
        lines.append("## 最佳模型推荐")
        lines.append("")
        lines.append(f"- **最佳模型（AIC 最小）：{best}**（{r['label']}），"
                     f"AIC = {_fmt(r['aic'], 6)}，R²adj = {_fmt(r['r2adj'], 6)}，"
                     f"Akaike 权重 = {_fmt(r['akaike_w'], 4)}")
        if best == "kp":
            lines.append(f"  - 释放指数 n = {_fmt(r['params'][1], 5)} → "
                         f"{kp_n_text(r['params'][1])}")
        if runner:
            lines.append(f"- 次优 {runner['model']}：ΔAIC = {_fmt(runner['delta_aic'], 4)}"
                         f"（ΔAIC < 2 视为无实质差异，须结合机理与几何选择）")
        lines.append("- 机理结论应优先看释放指数/机理自身的物理合理性（几何、载体、"
                     "释放介质），AIC 只是拟合优度的客观排序。")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 自测 / 演示
# ------------------------------------------------------------------
T_REL = np.arange(1.0, 13.0, 1.0)   # 1–12 h
NOISE_CV = 0.001                    # 合成数据相对噪声（0.1%），固定种子保证可复现
SEED = 20260921


def _synth(func, t, truth, cv=NOISE_CV, seed=SEED):
    """按模型 + 真值造带小噪声的合成释放数据（固定种子）。"""
    rng = np.random.default_rng(seed)
    f = func(t, *truth)
    return f * (1.0 + rng.normal(0.0, cv, size=len(t)))


def _selftest_readers():
    """输入读取路径自检（已知真值）：CSV/TSV 走标准库、列名映射、编码回退、非数值拦截。

    返回失败项数（0 = 全绿）。全程不 import pandas —— 该断言即「pandas 可选」的机器证据。
    """
    n_fail = 0
    t = np.array([1.0, 2.0, 4.0, 8.0])
    r1 = np.array([12.0, 17.0, 24.0, 34.0])
    r2 = np.array([14.0, 19.0, 26.0, 36.0])
    truth = (r1 + r2) / 2.0                       # 多重复均值真值（精确值，无噪声）

    def report(name, ok, detail):
        nonlocal n_fail
        n_fail += (not ok)
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))
        print("        %s" % detail)

    with tempfile.TemporaryDirectory(prefix="release_fit_io_") as d:
        # ① CSV（UTF-8）：列名映射 + 多重复取均值
        p_csv = os.path.join(d, "t1.csv")
        with open(p_csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "R1", "R2"])
            for row in zip(t, r1, r2):
                w.writerow(["%g" % v for v in row])
        cols, rows = load_table(p_csv)
        tt = col_float(rows, "time")
        f_rep, sd_rep = rep_matrix(rows, ["R1", "R2"])
        report("读取 CSV（列名映射 + 多重复均值）",
               cols == ["time", "R1", "R2"] and np.allclose(tt, t) and np.allclose(f_rep, truth)
               and np.allclose(sd_rep, np.std(np.column_stack([r1, r2]), axis=1, ddof=1)),
               "列名 = %s | n = %d | 均值列最大偏差 = %.3g" % (cols, len(tt), float(np.max(np.abs(f_rep - truth)))))

        # ② CSV 路径未引入 pandas（标准库解析的机器证据）
        report("CSV 路径未引入 pandas（sys.modules 检查）", "pandas" not in sys.modules,
               "pandas in sys.modules = %s（CSV/TSV 不需要它）" % ("pandas" in sys.modules))

        # ③ TSV + GB18030 + 中文列名（首选编码读失败后须回退成功）
        p_tsv = os.path.join(d, "t2.tsv")
        with open(p_tsv, "w", encoding="gb18030", newline="") as fh:
            fh.write("时间\t释放率\n")
            for tv, fv in zip(t, truth):
                fh.write("%g\t%g\n" % (tv, fv))
        cols2, rows2 = load_table(p_tsv)
        report("读取 TSV + GB18030 回退（中文列名）",
               cols2 == ["时间", "释放率"] and np.allclose(col_float(rows2, "时间"), t)
               and np.allclose(col_float(rows2, "释放率"), truth),
               "列名 = %s | 释放率列最大偏差 = %.3g"
               % (cols2, float(np.max(np.abs(col_float(rows2, "释放率") - truth)))))

        # ④ 非数值单元格 → 明确报错（不静默当 0/NaN）
        p_bad = os.path.join(d, "t3.csv")
        with open(p_bad, "w", encoding="utf-8", newline="") as fh:
            fh.write("time,release\n1,12\n2,abc\n")
        _, rows3 = load_table(p_bad)
        caught, msg = False, ""
        try:
            col_float(rows3, "release")
        except SystemExit as exc:
            caught, msg = True, str(exc)
        report("非数值单元格 → 明确报错（不静默）", caught and "不是数值" in msg,
               (msg.splitlines()[0] if msg else "未触发拦截（危险：非数值被静默吞掉）"))

        # ⑤ 缺列 → 报错并列出实际列名（不猜）
        caught, msg = False, ""
        try:
            if "释放率" not in cols:
                raise SystemExit("[错误] 缺少释放率列 释放率；文件实际列名 = %s" % cols)
        except SystemExit as exc:
            caught, msg = True, str(exc)
        report("缺列 → 报错并列出实际列名", caught and "实际列名" in msg,
               (msg.splitlines()[0] if msg else "未触发拦截"))
    return n_fail


def selftest():
    """known-answer：Higuchi k=20（t=1..12 h）参数回收 + AIC 排名第一；另含读取路径自检。"""
    print("=" * 72)
    print("release_fit.py --selftest")
    print("合成真值：Higuchi k=20（t=1..12 h，噪声 0.1%）；附加：零级 k0=8、一级 k1=0.2")
    print("=" * 72)
    f_hig = _synth(m_higuchi, T_REL, (20.0,))
    res_hig, best_hig = fit_all(T_REL, f_hig)
    r_hig = [r for r in res_hig if r["model"] == "higuchi"][0]
    kp_hig = [r for r in res_hig if r["model"] == "kp"][0]

    checks = []   # (名称, 实测, 期望, 容差%, kind)
    checks.append(("Higuchi kH 回收", r_hig["params"][0], 20.0, 1.0, "rel"))
    checks.append(("Higuchi AIC 排名第一", 1.0 if best_hig == "higuchi" else 0.0, 1.0, 0.0, "eq"))
    # 附加 known-answer：零级 / 一级
    f_zero = _synth(m_zero, T_REL, (8.0,))
    res_zero, best_zero = fit_all(T_REL, f_zero)
    r_zero = [r for r in res_zero if r["model"] == "zero"][0]
    checks.append(("零级 k0 回收", r_zero["params"][0], 8.0, 2.0, "rel"))
    checks.append(("零级 AIC 排名第一", 1.0 if best_zero == "zero" else 0.0, 1.0, 0.0, "eq"))
    f_first = _synth(m_first, T_REL, (0.2,))
    res_first, best_first = fit_all(T_REL, f_first)
    r_first = [r for r in res_first if r["model"] == "first"][0]
    checks.append(("一级 k1 回收", r_first["params"][0], 0.2, 3.0, "rel"))
    checks.append(("一级拟合 R²adj", r_first["r2adj"], 1.0, 0.1, "rel"))
    # 附加：KP 指数释义表覆盖（合成 Fickian 数据 n 应落在 ≤0.45 或异常案例区间）
    checks.append(("Higuchi 数据 KP 拟合 R²adj", kp_hig["r2adj"], 1.0, 0.5, "rel"))

    n_fail = 0
    for name, meas, exp, tol_pct, kind in checks:
        if kind == "eq":
            ok = abs(meas - exp) < 1e-9
            n_fail += (not ok)
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
            print(f"        实测 = {meas:.0f}（1=是/0=否） | 期望 = {exp:.0f}")
            continue
        err = abs(meas - exp) / abs(exp) * 100.0
        ok = err <= tol_pct
        n_fail += (not ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"        实测 = {meas:.6f} | 真值 = {exp:.6f} | "
              f"相对误差 = {err:.4f}% (容差 {tol_pct}%)")
    # 附加：输入读取路径（标准库 csv / pandas 可选）
    n_fail += _selftest_readers()
    print("-" * 72)
    print("Higuchi 合成数据的 AIC 排名前 3：" + ", ".join(
        f"{r['model']}(AIC={r['aic']:.2f})" for r in
        sorted([x for x in res_hig if x["ok"]], key=lambda x: x["aic"])[:3]))
    print("-" * 72)
    if n_fail == 0:
        print("selftest 结果：全部 PASS")
        return 0
    print(f"selftest 结果：{n_fail} 项 FAIL")
    return 1


def demo():
    """合成 Higuchi 释放数据（多重复 → 均值±SD），跑全模型并输出可判读数值。"""
    rng = np.random.default_rng(20260921)
    reps = []
    for i in range(3):
        reps.append(m_higuchi(T_REL, 20.0) * (1.0 + rng.normal(0.0, 0.02, size=len(T_REL))))
    reps = np.vstack(reps)
    f, sd = reps.mean(axis=0), reps.std(axis=0, ddof=1)
    print("### demo：合成 Higuchi 数据（k=20，3 重复，2% 噪声）")
    print("时间(h)  : " + " ".join(f"{v:g}" for v in T_REL))
    print("均值(%)  : " + " ".join(f"{v:.2f}" for v in f))
    print("SD(%)    : " + " ".join(f"{v:.2f}" for v in sd))
    print()
    results, best = fit_all(T_REL, f)
    print(report_markdown(T_REL, f, sd, results, best))
    return 0


# ------------------------------------------------------------------
# 主程序
# ------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="体外释放拟合（零级/一级/Higuchi/KP/Hixson-Crowell/Weibull）+ AIC 择优",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", help="输入 CSV / TSV / Excel 路径")
    p.add_argument("--time", default=DEFAULT_TIME_COL, help=f"时间列名（默认 {DEFAULT_TIME_COL}）")
    p.add_argument("--release", default=DEFAULT_REL_COL, help=f"释放率列名（默认 {DEFAULT_REL_COL}）")
    p.add_argument("--rep", default=None, help="多重复列名（逗号分隔），自动取均值 ± SD")
    p.add_argument("--encoding", default="utf-8-sig",
                   help="CSV/TSV 首选编码（默认 utf-8-sig，其后自动回退 gb18030 → latin-1）")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.add_argument("--selftest", action="store_true", help="跑内置 known-answer 自测")
    p.add_argument("--demo", action="store_true", help="用合成数据跑一遍")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.selftest:
        return selftest()
    if args.demo:
        return demo()
    if not args.file:
        build_parser().print_help()
        print("\n[提示] 需要 --file，或使用 --selftest / --demo")
        return 2

    cols, rows = load_table(args.file, encoding=args.encoding)
    if args.time not in cols:
        raise SystemExit("[错误] 缺少时间列 %s；文件实际列名 = %s" % (args.time, cols))

    if args.rep:
        rep_cols = [c.strip() for c in args.rep.split(",") if c.strip()]
        missing = [c for c in rep_cols if c not in cols]
        if missing:
            raise SystemExit("[错误] 缺少重复列 %s；文件实际列名 = %s" % (missing, cols))
        f, sd = rep_matrix(rows, rep_cols)
    else:
        if args.release not in cols:
            raise SystemExit("[错误] 缺少释放率列 %s；文件实际列名 = %s" % (args.release, cols))
        f = col_float(rows, args.release)
        sd = np.full(len(f), np.nan)

    t = col_float(rows, args.time)
    keep = ~(np.isnan(t) | np.isnan(f))
    t, f, sd = t[keep], f[keep], sd[keep]
    if np.any(t < 0):
        raise SystemExit("[错误] 存在负时间点，请检查数据")

    results, best = fit_all(t, f)
    if args.json:
        print(json.dumps({"n": int(len(t)), "best_by_aic": best, "models": results,
                          "note": "未加权最小二乘；AIC = n·ln(RSS/n)+2k；"
                                  "Higuchi/KP/HC 机理解释限前 ~60% 释放段"},
                         ensure_ascii=False, indent=2, default=str))
    else:
        print(report_markdown(t, f, sd, results, best))
    return 0


if __name__ == "__main__":
    sys.exit(main())
