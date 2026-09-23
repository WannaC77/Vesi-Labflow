# -*- coding: utf-8 -*-
"""房室模型拟合器（1 室 IV / 2 室 IV / 1 室 PO）—— PK 参数估计与模型选择。

适用场景
    已知给药途径的血药浓度-时间数据的房室模型拟合：参数估计（含标准误）、
    拟合优度评价、按 AIC 做模型的客观选择。典型用例：候选药物 X 脂质体 vs 参比制剂
    大鼠 PK（5 mg/kg 尾静脉 = IV；如后续做口服则用 PO 模型）。

模型（C 为浓度，t 为 h）
    1c_iv ：C = A·e^(-αt)                       参数 A, α           （2 参数）
    2c_iv ：C = A·e^(-αt) + B·e^(-βt)           参数 A, α, B, β     （4 参数）
    1c_po ：C = A·(e^(-ke·t) − e^(-ka·t))       参数 A, ke, ka      （3 参数）
    注：1c_po 的 ke/ka 可互换（flip-flop 情形数值上不可区分），报告按拟合值原样给出。

口径声明
    1. 拟合用 scipy.optimize.curve_fit（非线性最小二乘，含边界约束 + 数据驱动初值）。
    2. 参数 SE 取协方差矩阵对角线的平方根（curve_fit 默认按残差方差缩放，即 SE(参数)）。
    3. AIC = n·ln(RSS/n) + 2k；BIC = n·ln(RSS/n) + k·ln(n)；AICc = AIC + 2k(k+1)/(n−k−1)。
       模型比较要求**同一数据集、同一响应**（本脚本对全部模型用同一份数据）。
       RSS 下垫 1e-24 仅为防 log(0)（完美拟合时），对真实数据无影响。
    4. R² 为普通决定系数；R²adj = 1 − (1−R²)(n−1)/(n−k−1)。
    5. 单位随输入（如 μg/mL 与 h）；A、B 与浓度同单位，α、β、ke、ka 为 h⁻¹。

自测 / Known-answer selftest（科学正确性 · G9 清单件）
    `--selftest` 对**合成已知参数**数据做参数回收断言：2 室 IV（A=80, α=1.2, B=20, β=0.08）、
    1 室 IV（A=50, α=0.3）、1 室 PO（A=60, ke=0.2, ka=1.5）各参数在真值 ±容差内，
    且 AIC 必须挑中正确的复杂模型（2c_iv 优于 1c_iv / 1c_po）。容差随断言逐条打印。

输入
    CSV / TSV / Excel（.xlsx/.xls/.xlsm），列名参数化：--time 时间列；--conc 浓度列。
    CSV/TSV 走标准库解析（编码回退 utf-8-sig → gb18030 → latin-1）；Excel 走 pandas
    （缺 pandas/openpyxl → 明确报错并提示转存 CSV，不静默）。
输出
    Markdown 报告（模型参数 ± SE、R²、R²adj、AIC/BIC/AICc、残差小结、AIC 推荐）；
    --json 输出 JSON。
依赖
    numpy / scipy（必需）；pandas 仅 Excel 输入时需要（无 matplotlib）。
命令行示例
    python compartment_fit.py --selftest
    python compartment_fit.py --demo
    python compartment_fit.py --file pk.csv --time time --conc conc          # auto：三种模型全比
    python compartment_fit.py --file pk.csv --time time --conc conc --model 2c_iv
"""

import argparse
import csv
import json
import os
import sys

import numpy as np
from scipy.optimize import curve_fit

# ============ 默认参数区（在这里改 / 或用命令行覆盖）============
DEFAULT_TIME_COL = "time"        # 时间列名（h）
DEFAULT_CONC_COL = "conc"        # 浓度列名
DEFAULT_MODEL = "auto"           # auto = 三种模型全比；或 1c_iv / 2c_iv / 1c_po
MODELS = ("1c_iv", "2c_iv", "1c_po")
MODEL_LABELS = {
    "1c_iv": "一室 IV：C = A·e^(-αt)",
    "2c_iv": "二室 IV：C = A·e^(-αt) + B·e^(-βt)",
    "1c_po": "一室 PO：C = A·(e^(-ke·t) − e^(-ka·t))",
}
N_PARAMS = {"1c_iv": 2, "2c_iv": 4, "1c_po": 3}
PARAM_NAMES = {"1c_iv": ("A", "alpha"), "2c_iv": ("A", "alpha", "B", "beta"),
               "1c_po": ("A", "ke", "ka")}
RSS_FLOOR = 1e-24                # 防 log(0)（仅完美拟合时生效）
MAXFEV = 200000                  # curve_fit 最大迭代
DELTA_AIC_TEXT = ((0, 2, "无实质差异"), (2, 7, "有差异"), (7, 10, "差异明显"),
                  (10, float("inf"), "差异显著"))
EXCEL_EXTS = (".xlsx", ".xls", ".xlsm")
NA_TOKENS = ("", "na", "nan", "n/a", "null", "none", "-")
CSV_ENCODINGS = ("utf-8-sig", "gb18030", "latin-1")
# ===============================================================


# ------------------------------------------------------------------
# 模型函数
# ------------------------------------------------------------------
def f1c_iv(t, A, alpha):
    """一室 IV：C = A·e^(-αt)。"""
    return A * np.exp(-alpha * np.asarray(t, dtype=float))


def f2c_iv(t, A, alpha, B, beta):
    """二室 IV：C = A·e^(-αt) + B·e^(-βt)。"""
    t = np.asarray(t, dtype=float)
    return A * np.exp(-alpha * t) + B * np.exp(-beta * t)


def f1c_po(t, A, ke, ka):
    """一室 PO（吸收相 + 消除相）：C = A·(e^(-ke·t) − e^(-ka·t))。"""
    t = np.asarray(t, dtype=float)
    return A * (np.exp(-ke * t) - np.exp(-ka * t))


def model_func(model):
    """模型名 -> 函数。"""
    return {"1c_iv": f1c_iv, "2c_iv": f2c_iv, "1c_po": f1c_po}[model]


# ------------------------------------------------------------------
# 初值 / 边界（数据驱动，提高收敛率）
# ------------------------------------------------------------------
def _terminal_loglin(t, c, n=3):
    """末 n 个 C>0 点做 ln(C)-t 回归，返回 (slope, intercept)；点数不足返回 (None, None)。"""
    pos = np.where(c > 0)[0]
    if len(pos) < 2:
        return None, None
    sel = pos[-min(n, len(pos)):]
    tt, cc = t[sel], c[sel]
    slope, intercept = np.polyfit(tt, np.log(cc), 1)
    return float(slope), float(intercept)


def initial_guess(model, t, c):
    """按模型给 (p0, lower, upper)：先用末段回归估消除项，再由首段估分布项。"""
    c_max = float(np.max(c))
    slope_t, inter_t = _terminal_loglin(t, c, 3)
    lam_t = -slope_t if slope_t is not None else None      # 末段消除速率估计
    if lam_t is None or not np.isfinite(lam_t) or lam_t <= 0:
        lam_t = 0.1
    lam_t = float(np.clip(lam_t, 1e-4, 20.0))

    if model == "1c_iv":
        A0 = max(c_max, 1e-9)
        p0 = [A0, lam_t]
        lo = [1e-12, 1e-6]
        hi = [1e9, 100.0]

    elif model == "2c_iv":
        B0 = float(np.exp(inter_t)) if inter_t is not None else c_max * 0.2
        B0 = float(np.clip(B0, c_max * 1e-4, c_max))
        beta0 = float(np.clip(lam_t * 0.8, 1e-4, 1.0))
        # α 初值：用前两个点的下降速率（二室分布相通常远快于消除相）
        if len(t) >= 2 and t[1] > t[0] and c[0] > 0 and c[1] > 0:
            a0 = float(np.log(c[0] / c[1]) / (t[1] - t[0]))
        else:
            a0 = 2.0
        a0 = float(np.clip(max(a0, beta0 * 1.05), 1e-3, 50.0))
        A0 = float(max(c[0] - B0, 0.2 * c_max))
        p0 = [A0, a0, B0, beta0]
        lo = [1e-12, 1e-6, 1e-12, 1e-6]
        hi = [1e9, 100.0, 1e9, 100.0]

    elif model == "1c_po":
        ke0 = float(np.clip(lam_t, 1e-4, 20.0))
        idx = int(np.argmax(c))
        tmax = float(t[idx]) if t[idx] > 0 else 0.5
        ka0 = float(np.clip(max(3.0 / max(tmax, 0.1), ke0 * 1.2), 1e-3, 60.0))
        ka0 = max(ka0, ke0 * 1.05)
        A0 = float(max(c_max * 1.1, 1e-9))
        p0 = [A0, ke0, ka0]
        lo = [1e-12, 1e-6, 1e-6]
        hi = [1e9, 100.0, 200.0]

    else:
        raise ValueError("未知模型 %s（可选 %s）" % (model, MODELS))

    # 保证初值严格落在边界内（curve_fit 要求）
    p0 = [min(max(p, l * 1.000001 + 1e-12), h * 0.999999) for p, l, h in zip(p0, lo, hi)]
    return np.array(p0, dtype=float), (np.array(lo), np.array(hi))


# ------------------------------------------------------------------
# 拟合 + 统计量
# ------------------------------------------------------------------
def fit_model(model, t_in, c_in):
    """拟合单个模型，返回 dict（参数 ± SE、拟合优度、残差小结）。"""
    t = np.asarray(t_in, dtype=float)
    c = np.asarray(c_in, dtype=float)
    func = model_func(model)
    p0, bounds = initial_guess(model, t, c)
    try:
        popt, pcov = curve_fit(func, t, c, p0=p0, bounds=bounds, maxfev=MAXFEV)
        ok, err = True, None
    except Exception as exc:                      # 收敛失败不崩溃，标记后继续比其它模型
        return {"model": model, "label": MODEL_LABELS[model], "ok": False,
                "error": "%s: %s" % (type(exc).__name__, exc), "n": int(len(t)), "k": N_PARAMS[model]}

    pred = func(t, *popt)
    resid = c - pred
    n, k = int(len(t)), int(len(popt))
    # 触界检查：参数贴在上下界上 => 结果不可用于参数结论（常见于模型设定错误）
    lo, hi = bounds
    bound_flags = [bool(np.isclose(v, l, rtol=1e-6, atol=0.0) or np.isclose(v, h, rtol=1e-6, atol=0.0))
                   for v, l, h in zip(popt, lo, hi)]
    rss = float(np.sum(resid ** 2))
    tss = float(np.sum((c - c.mean()) ** 2))
    r2 = 1.0 - rss / tss if tss > 0 else float("nan")
    r2adj = 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1) if n - k - 1 > 0 else float("nan")
    rss_eff = max(rss, RSS_FLOOR)
    aic = n * np.log(rss_eff / n) + 2 * k
    bic = n * np.log(rss_eff / n) + k * np.log(n)
    aicc = aic + 2 * k * (k + 1) / (n - k - 1) if n - k - 1 > 0 else float("nan")
    se = np.sqrt(np.diag(pcov))
    se = np.where(np.isfinite(se), se, np.nan)
    # 残差小结（拟合优度证据）
    sign_changes = int(np.sum(np.diff(np.sign(resid)) != 0)) if n > 1 else 0
    corr_t = float(np.corrcoef(t, resid)[0, 1]) if n > 2 and np.std(resid) > 0 else 0.0
    return {
        "model": model, "label": MODEL_LABELS[model], "ok": True,
        "params": [float(v) for v in popt],
        "param_names": PARAM_NAMES[model], "se": [float(v) for v in se],
        "bound_flags": bound_flags,
        "bound_hit_names": [nm for nm, fl in zip(PARAM_NAMES[model], bound_flags) if fl],
        "n": n, "k": k, "rss": rss, "r2": r2, "r2adj": r2adj,
        "aic": aic, "bic": bic, "aicc": aicc,
        "resid_mean": float(np.mean(resid)), "resid_sd": float(np.std(resid, ddof=1)) if n > 1 else float("nan"),
        "resid_max_abs": float(np.max(np.abs(resid))),
        "resid_max_pct_cmax": float(np.max(np.abs(resid)) / np.max(c) * 100.0) if np.max(c) > 0 else float("nan"),
        "resid_sign_changes": sign_changes, "resid_corr_t": corr_t,
    }


def fit_all(t, c, models=MODELS):
    """拟合并按 AIC 排名，返回 (results_列表, 最佳模型名或None)。"""
    results = [fit_model(m, t, c) for m in models]
    good = [r for r in results if r["ok"]]
    for r in good:
        r["delta_aic"] = r["aic"] - min(x["aic"] for x in good)
    # Akaike 权重（由 ΔAIC 计算，仅在同数据集、同响应时可解释）
    denom = sum(np.exp(-0.5 * r["delta_aic"]) for r in good) if good else 0.0
    for r in good:
        r["akaike_w"] = float(np.exp(-0.5 * r["delta_aic"]) / denom) if denom > 0 else float("nan")
    good.sort(key=lambda r: r["aic"])
    for i, r in enumerate(good, 1):
        r["rank"] = i
    return results, (good[0]["model"] if good else None)


def delta_aic_text(d):
    """ΔAIC 的经验解释。"""
    for lo, hi, txt in DELTA_AIC_TEXT:
        if lo <= d < hi:
            return txt
    return "-"


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


def load_table(path, encoding="utf-8-sig"):
    """读 CSV/TSV/Excel → (列名 list, 行 dict list)。Excel 无 pandas → 明确报错，不静默。"""
    if not os.path.isfile(path):
        raise SystemExit("[错误] 找不到输入文件：%s" % path)
    ext = os.path.splitext(path)[1].lower()
    if ext in EXCEL_EXTS:
        try:
            import pandas as pd
        except Exception as exc:                 # noqa: BLE001
            raise SystemExit("[错误] 读取 Excel 需要 pandas + openpyxl（当前解释器不可用：%s）。"
                             "[降级] 请把表另存为 CSV/TSV 后重跑（CSV 走标准库，无第三方依赖）。" % exc)
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        return list(df.columns), df.to_dict("records")
    sep = "\t" if ext in (".tsv", ".txt") else ","
    raw, tried, last = None, [], None
    for enc in [encoding] + [e for e in CSV_ENCODINGS if e != encoding]:
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
        if not any(str(x).strip() for x in rec):
            continue
        rows.append({cols[i]: (rec[i] if i < len(rec) else "") for i in range(len(cols))})
    return cols, rows


def column_float(rows, col):
    """取数值列 → np.ndarray；空/NA → NaN；非数值 → SystemExit（报数据序号）。"""
    out = []
    for i, r in enumerate(rows, start=1):
        try:
            out.append(_num(r.get(col)))
        except ValueError:
            raise SystemExit("[错误] 列 `%s` 第 %d 个数据值不是数值：%r" % (col, i, r.get(col)))
    return np.asarray(out, dtype=float)


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
        return "%.*e" % (nd, x)
    return "%.*g" % (nd, x)


def report_markdown(t, c, results, best):
    """输出 Markdown 报告。"""
    good = [r for r in results if r["ok"]]
    good.sort(key=lambda r: r["aic"])
    lines = ["# 房室模型拟合报告", ""]
    lines.append("- 数据点数 n = %d；时间范围 %s – %s h；Cmax = %s"
                 % (len(c), _fmt(float(np.min(t))), _fmt(float(np.max(t))), _fmt(float(np.max(c)))))
    lines.append("- 全部模型使用**同一份数据**（AIC/BIC 可直接比较）")
    lines.append("- 口径：nonlinear least squares（curve_fit）；"
                 "AIC = n·ln(RSS/n)+2k；BIC = n·ln(RSS/n)+k·ln(n)；"
                 "RSS 下垫 %g 仅防 log(0)" % RSS_FLOOR)
    lines.append("")
    for r in results:
        lines.append("## 模型：%s（%s）" % (r["model"], r["label"]))
        if not r["ok"]:
            lines.append("- **拟合失败**：%s" % r["error"])
            lines.append("")
            continue
        lines.append("")
        lines.append("| 参数 | 估计值 | SE | 相对 SE (%) |")
        lines.append("| --- | --- | --- | --- |")
        for i, (nm, val, se) in enumerate(zip(r["param_names"], r["params"], r["se"])):
            rel = abs(se / val) * 100.0 if val != 0 else float("nan")
            mark = " ⚠触界" if (r.get("bound_flags") or [])[i] else ""
            lines.append("| %s%s | %s | %s | %s |" % (nm, mark, _fmt(val, 6), _fmt(se, 4), _fmt(rel, 4)))
        lines.append("")
        lines.append("| 统计量 | 值 |")
        lines.append("| --- | --- |")
        lines.append("| n / k | %d / %d |" % (r["n"], r["k"]))
        lines.append("| RSS | %s |" % _fmt(r["rss"], 6))
        lines.append("| R² | %s |" % _fmt(r["r2"], 8))
        lines.append("| R²adj | %s |" % _fmt(r["r2adj"], 8))
        lines.append("| AIC | %s |" % _fmt(r["aic"], 6))
        lines.append("| AICc | %s |" % _fmt(r["aicc"], 6))
        lines.append("| BIC | %s |" % _fmt(r["bic"], 6))
        lines.append("| ΔAIC (vs 最优) | %s |" % _fmt(r.get("delta_aic", float("nan")), 4))
        lines.append("| Akaike 权重 | %s |" % _fmt(r.get("akaike_w", float("nan")), 4))
        lines.append("| AIC 排名 | %s |" % r.get("rank", "-"))
        lines.append("")
        if r.get("bound_hit_names"):
            lines.append("- ⚠ **参数触及边界：%s** —— "
                         "该估计值不可用于参数/机理结论（常见于模型设定与数据不符，"
                         "先怀疑模型是否选错）" % ", ".join(r["bound_hit_names"]))
        lines.append("**残差小结（拟合优度证据）**")
        lines.append("")
        lines.append("- 残差均值 = %s；残差 SD = %s" % (_fmt(r["resid_mean"], 4), _fmt(r["resid_sd"], 4)))
        lines.append("- 最大绝对残差 = %s（占 Cmax 的 %s%%）"
                     % (_fmt(r["resid_max_abs"], 4), _fmt(r["resid_max_pct_cmax"], 3)))
        lines.append("- 残差符号变化次数 = %d；残差-时间相关 r = %s%s"
                     % (r["resid_sign_changes"], _fmt(r["resid_corr_t"], 4),
                        "（|r|>0.5，提示存在系统偏差，模型可能不足）" if abs(r["resid_corr_t"]) > 0.5
                        else "（未见明显时间趋势）"))
        lines.append("")
    if best:
        r = [x for x in good if x["model"] == best][0]
        runner = good[1] if len(good) > 1 else None
        lines.append("## 模型推荐（按 AIC）")
        lines.append("")
        lines.append("- **推荐模型：%s（%s）**，AIC = %s，Akaike 权重 = %s"
                     % (best, r["label"], _fmt(r["aic"], 6), _fmt(r.get("akaike_w", float("nan")), 4)))
        if runner:
            lines.append("- 次优 %s：ΔAIC = %s（%s）"
                         % (runner["model"], _fmt(runner["delta_aic"], 4), delta_aic_text(runner["delta_aic"])))
        lines.append("- AIC 只衡量拟合优度与复杂度的折中，不判断机制合理性；"
                     "机制结论须结合给药途径与实验设计（如 IV 不应报 PO 模型）。")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 自测 / 演示
# ------------------------------------------------------------------
T_2C = np.array([0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0,
                 6.0, 8.0, 12.0, 16.0, 20.0, 24.0], dtype=float)   # 早期密集，抓分布相
T_1C = np.array([0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0], dtype=float)
T_PO = np.array([0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 24.0], dtype=float)
NOISE_CV = 0.005                 # 合成数据相对噪声（0.5%），固定种子保证可复现
SEED = 20260921
TRUTH_2C = (80.0, 1.2, 20.0, 0.08)      # A, α, B, β（二室 IV 真值）
TOL_2C = {"A": 5.0, "alpha": 10.0, "B": 5.0, "beta": 10.0}       # 相对容差（%）
TRUTH_1C = (50.0, 0.3)                  # A, α
TOL_1C = {"A": 5.0, "alpha": 5.0}
TRUTH_PO = (60.0, 0.2, 1.5)             # A, ke, ka
TOL_PO = {"A": 10.0, "ke": 15.0, "ka": 15.0}


def _synth(func, t, truth, cv=NOISE_CV, seed=SEED):
    """按给定模型 + 真值造带小噪声的合成数据（固定种子）。"""
    rng = np.random.default_rng(seed)
    c = func(t, *truth)
    return np.maximum(c * (1.0 + rng.normal(0.0, cv, size=len(t))), 1e-12)


def selftest():
    """known-answer：2 室 IV（A=80, α=1.2, B=20, β=0.08）参数回收 + AIC 择优 + 1 室回收。"""
    print("=" * 72)
    print("compartment_fit.py --selftest")
    print("合成真值：2 室 IV  A=80, α=1.2, B=20, β=0.08（0–24 h，早期密集采样，噪声 0.5%）")
    print("          1 室 IV  A=50, α=0.3｜1 室 PO  A=60, ke=0.2, ka=1.5")
    print("断言口径：参数回收相对误差 ≤ 容差（逐条打印）；AIC 必须挑中正确模型")
    print("=" * 72)
    c = _synth(f2c_iv, T_2C, TRUTH_2C)
    r2c = fit_model("2c_iv", T_2C, c)
    r1c = fit_model("1c_iv", T_2C, c)
    rpo2 = fit_model("1c_po", T_2C, c)

    n_fail = 0
    checks = []          # (名称, 实测, 期望, 相对容差%；None = 不等式型断言)

    def add_params(tag, fit, truth, tol):
        if not fit.get("ok"):
            checks.append(("%s 拟合失败：%s" % (tag, fit.get("error")), float("nan"), 0.0, 0.0))
            return
        for nm, val in zip(fit["param_names"], fit["params"]):
            checks.append(("%s 参数回收 %s" % (tag, nm), val, truth[fit["param_names"].index(nm)],
                           tol[nm]))

    add_params("2c_iv", r2c, TRUTH_2C, TOL_2C)
    add_params("1c_iv", fit_model("1c_iv", T_1C, _synth(f1c_iv, T_1C, TRUTH_1C)), TRUTH_1C, TOL_1C)
    add_params("1c_po", fit_model("1c_po", T_PO, _synth(f1c_po, T_PO, TRUTH_PO, cv=0.002)),
               TRUTH_PO, TOL_PO)
    if r2c.get("ok") and r1c.get("ok"):
        checks.append(("AIC(2c_iv) < AIC(1c_iv)", r2c["aic"], r1c["aic"], None))
    if r2c.get("ok") and rpo2.get("ok"):
        checks.append(("AIC(2c_iv) < AIC(1c_po)", r2c["aic"], rpo2["aic"], None))
    if r2c.get("ok") and r1c.get("ok") and rpo2.get("ok"):
        # 模型选择：全模型比较时须挑中 2c_iv
        results, best = fit_all(T_2C, c)
        checks.append(("全模型 AIC 择优 = 2c_iv（实测 %s）" % best, 1.0 if best == "2c_iv" else 0.0, 1.0, None))
        # 拟合优度：2 室数据用 2 室模型拟合 R² 应接近 1
        checks.append(("2c_iv 拟合 R² ≥ 0.999", r2c["r2"], 0.999, None))
        # SE 可用性（协方差矩阵未退化）：相对 SE 全部有限
        checks.append(("2c_iv 参数 SE 有限（协方差可用）",
                       1.0 if all(np.isfinite(s) for s in r2c["se"]) else 0.0, 1.0, None))

    for name, meas, exp, tol_pct in checks:
        if tol_pct is None:                       # 不等式 / 布尔型断言（1.0 = 成立）
            if name.startswith("AIC(2c_iv) < AIC("):
                ok = meas < exp
                detail = "实测 %.6f｜参照 %.6f｜要求 小于" % (meas, exp)
            elif name.startswith("2c_iv 拟合 R²"):
                ok = meas >= exp
                detail = "实测 %.8f｜要求 ≥ %.3f" % (meas, exp)
            else:
                ok = abs(meas - exp) <= 1e-12
                detail = "实测 %.6f｜要求 = %.6f" % (meas, exp)
            n_fail += (not ok)
            print("[%s] %s" % ("PASS" if ok else "FAIL", name))
            print("        %s" % detail)
            continue
        err = abs(meas - exp) / abs(exp) * 100.0
        ok = err <= tol_pct
        n_fail += (not ok)
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))
        print("        实测 = %.6f | 真值 = %.6f | 相对误差 = %.4f%% (容差 %s%%)"
              % (meas, exp, err, tol_pct))

    print("-" * 72)
    if n_fail == 0:
        print("selftest 结果：全部 PASS（%d 项断言）" % len(checks))
        return 0
    print("selftest 结果：%d 项 FAIL（共 %d 项断言）" % (n_fail, len(checks)))
    return 1


def demo():
    """合成 2 室 IV 数据集，跑 auto 全模型比较并输出可判读数值。"""
    c = _synth(f2c_iv, T_2C, TRUTH_2C, cv=0.05)
    print("### demo：合成 2 室 IV 数据（真值 A=80, α=1.2, B=20, β=0.08；噪声 5%）")
    print("时间(h) : " + " ".join("%g" % v for v in T_2C))
    print("浓度    : " + " ".join("%.3g" % v for v in c))
    print()
    results, best = fit_all(T_2C, c)
    print(report_markdown(T_2C, c, results, best))
    return 0


# ------------------------------------------------------------------
# 主程序
# ------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="房室模型拟合（1 室 IV / 2 室 IV / 1 室 PO）+ AIC 模型选择",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", help="输入 CSV / TSV / Excel 路径")
    p.add_argument("--time", default=DEFAULT_TIME_COL, help="时间列名（默认 %s）" % DEFAULT_TIME_COL)
    p.add_argument("--conc", default=DEFAULT_CONC_COL, help="浓度列名（默认 %s）" % DEFAULT_CONC_COL)
    p.add_argument("--model", default=DEFAULT_MODEL, choices=("auto",) + MODELS,
                   help="模型选择（默认 auto：三种全比）")
    p.add_argument("--encoding", default="utf-8-sig", help="CSV 首选编码（默认 utf-8-sig，其后自动回退）")
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
    missing = [c for c in (args.time, args.conc) if c not in cols]
    if missing:
        raise SystemExit("[错误] 缺少列 %s；文件实际列名 = %s" % (missing, cols))
    t = column_float(rows, args.time)
    c = column_float(rows, args.conc)
    keep = ~(np.isnan(t) | np.isnan(c))
    t, c = t[keep], c[keep]
    if len(t) < 3:
        raise SystemExit("[错误] 有效数据点仅 %d 个（至少 3 个）" % len(t))
    models = MODELS if args.model == "auto" else (args.model,)
    results, best = fit_all(t, c, models)
    if args.json:
        print(json.dumps({"n": int(len(t)), "models": results, "best_by_aic": best,
                          "note": "AIC 比较要求同数据集同响应"}, ensure_ascii=False,
                         indent=2, default=str))
    else:
        print(report_markdown(t, c, results, best))
    return 0


if __name__ == "__main__":
    sys.exit(main())
