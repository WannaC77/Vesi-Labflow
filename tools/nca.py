# -*- coding: utf-8 -*-
"""NCA（非房室分析）独立复算 / 核对器 —— 用于与 DAS 软件输出交叉核对。

适用场景
    血药浓度-时间数据的 NCA 参数复算。典型用例：候选药物 X脂质体 vs 参比制剂
    5 mg/kg 尾静脉给药大鼠 PK（n=3，0-24 h 采血）的独立核算。

个体维（科学正确性修复 · 必读）
    多样本数据必须用 `--subject` 指定**个体列**：脚本按 组别×个体 拆成多条曲线，
    逐条做 NCA，再跨个体汇总（mean±SD），报告同时给出逐个体明细。
    **未给 `--subject` 时，若同一曲线内出现重复时间点（含浮点近重复），脚本直接报错
    退出（exit 1），绝不做静默拼接。** 旧版行为：多样本按时间排序后被缝成一条曲线，
    重复时间点段的 np.diff(t)=0 被记成 0 贡献 → AUC 系统性偏低（约为真值的 1/n），
    外部用户据此采信会得到错误的 PK 结论，故本版禁止静默。

口径声明（先读这一段）
    实验室口径以 **DAS 软件输出为准**；本脚本不是 DAS 的替代品，只做独立复算：
    用第二套代码路径 + 显式公式重算 AUC/λz/MRT/CL 等，用于发现录入错误、单位错误、
    末段选点异常。两套结果不一致时，以 DAS 为准并逐项排查差异来源。
    默认算法刻意与 DAS 保持一致：AUC0-t 线性梯形法；λz 用末段 ln(C)-t 线性回归；
    AUMC0-t 线性梯形法（DAS 惯例，不随 --method 切换）。
    已知差异点：DAS 的 AUC0-inf 外推项用**观测末点** C_last；本脚本主口径用 λz 回归
    的**拟合末点** Clast,fit，报告同时给出观测末点口径供比对，两者之差即外推不确定性。
    单位：脚本不做任何单位换算。时间须为 h（λz/t1/2 才是 h^-1 与 h）；浓度单位随输入，
    CL/Vz/Vss 的量纲 = (Dose 单位) / (浓度单位·h) 与 (Dose 单位)/(浓度单位)。

输入
    CSV / TSV / Excel（.xlsx/.xls/.xlsm），列名参数化：
        --time 时间列（h）；--conc 浓度列；--group 可选分组列；--subject 个体列
    CSV/TSV 走标准库解析（编码回退 utf-8-sig → gb18030 → latin-1）；Excel 走 pandas
    （该解释器缺 pandas/openpyxl 时明确报错并提示转存 CSV，不静默）。
输出
    Markdown 报告（stdout）；加 --json 输出 JSON（含逐个体结果与汇总）。
依赖
    numpy（必需）；pandas 仅 Excel 输入时需要；不依赖 scipy / matplotlib。
命令行示例
    python nca.py --selftest
    python nca.py --demo
    python nca.py --file pk.csv --time time --conc conc --group group --subject subject --dose 5
    python nca.py --file pk.xlsx --time 时间 --conc 浓度 --method lul --json
"""

import argparse
import csv
import json
import os
import sys

import numpy as np

# ============ 默认参数区（在这里改 / 或用命令行覆盖）============
DEFAULT_TIME_COL = "time"       # 时间列名（h）
DEFAULT_CONC_COL = "conc"       # 浓度列名（单位随文件，脚本不换算）
DEFAULT_GROUP_COL = None        # 分组列名（None = 不分组）
DEFAULT_SUBJECT_COL = None      # 个体列名（None = 单曲线；多样本必须给）
DEFAULT_METHOD = "linear"       # 梯形法：linear 线性（与 DAS 一致）/ lul 线性上行-对数下行
DEFAULT_N_LAMBDA = 4            # 末端相 λz 回归点数（≥3）
MIN_N_LAMBDA = 3                # 回归点数下限（3 点才有 1 个自由度）
LN2 = np.log(2.0)               # t1/2 = ln2 / λz
SUPPORTED_METHODS = ("linear", "lul")
METHOD_LABELS = {"linear": "线性梯形法（与 DAS 一致）",
                 "lul": "线性上行 / 对数下行（linear-up log-down）"}
EXCEL_EXTS = (".xlsx", ".xls", ".xlsm")
DUP_RTOL = 1e-9                 # 同曲线内时间点之差 ≤ 此值 → 判定为重复（禁止静默拼接）
NA_TOKENS = ("", "na", "nan", "n/a", "null", "none", "-")
CSV_ENCODINGS = ("utf-8-sig", "gb18030", "latin-1")
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
    sep = "\t" if ext in (".tsv", ".txt") else ","
    tried, last = [], None
    order = [encoding] + [e for e in CSV_ENCODINGS if e != encoding]
    raw = None
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
            import pandas as pd
        except Exception as exc:                     # noqa: BLE001
            raise SystemExit("[错误] 读取 Excel 需要 pandas + openpyxl（当前解释器不可用：%s）。"
                             "[降级] 请把表另存为 CSV/TSV 后重跑（CSV 走标准库，无第三方依赖）。" % exc)
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        return list(df.columns), df.to_dict("records")
    return _read_delimited(path, encoding=encoding)


def require_columns(cols, names):
    """缺列 → 直接报错并列出实际列名（不猜、不静默）。"""
    need = [c for c in names if c]
    missing = [c for c in need if c not in cols]
    if missing:
        raise SystemExit("[错误] 缺少列 %s；文件实际列名 = %s" % (missing, cols))


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


def _split_by(rows, col):
    """按列取值分块（保持首次出现顺序）；col=None → 单块 (all, rows)。"""
    if col is None:
        return [("all", rows)]
    order, bucket = [], {}
    for r in rows:
        key = str(r.get(col, "")).strip()
        if key not in bucket:
            bucket[key] = []
            order.append(key)
        bucket[key].append(r)
    return [(k, bucket[k]) for k in order]


def build_curves(rows, group_col=None, subject_col=None):
    """拆曲线：返回 [(组名, 个体名 or None, 行子列表)]（组名/个体名保持出现顺序）。"""
    out = []
    for gname, grows in _split_by(rows, group_col):
        if subject_col is None:
            out.append((gname, None, grows))
            continue
        for sname, srows in _split_by(grows, subject_col):
            out.append((gname, sname, srows))
    return out


# ------------------------------------------------------------------
# NCA 核心计算（单条曲线）
# ------------------------------------------------------------------
def auc_linear(t, y):
    """线性梯形法：Σ (y_i + y_i+1)/2 · Δt（DAS 默认口径）。"""
    return float(np.sum((y[1:] + y[:-1]) / 2.0 * np.diff(t)))


def auc_lul(t, y):
    """线性上行 / 对数下行梯形法：下降段用对数梯形（对指数衰减段精确）。"""
    total = 0.0
    for i in range(len(t) - 1):
        dt = t[i + 1] - t[i]
        a, b = float(y[i]), float(y[i + 1])
        if b < a and a > 0.0 and b > 0.0:
            total += (a - b) / np.log(a / b) * dt   # 对数梯形（下降段）
        else:
            total += (a + b) / 2.0 * dt             # 线性梯形（上行/持平/含 0）
    return float(total)


def lambda_z(t, c, n_lambda):
    """末段 λz：末 n 个 C>0 点做 ln(C) 对 t 的线性回归，返回 (λz, R², Clast拟合, t_last, 点数)。"""
    if n_lambda < MIN_N_LAMBDA:
        raise ValueError("n_lambda 必须 ≥ %d（当前 %d）" % (MIN_N_LAMBDA, n_lambda))
    pos = np.where(c > 0.0)[0]                       # 只对 C>0 点取对数
    if len(pos) < n_lambda:
        raise ValueError("C>0 数据点仅 %d 个，不足以用 %d 点估 λz" % (len(pos), n_lambda))
    sel = pos[-n_lambda:]                            # 末端 n 点
    tt, cc = t[sel], c[sel]
    slope, intercept = np.polyfit(tt, np.log(cc), 1)  # slope = -λz
    lam = float(-slope)
    yhat = slope * tt + intercept
    ss_res = float(np.sum((np.log(cc) - yhat) ** 2))
    ss_tot = float(np.sum((np.log(cc) - np.mean(np.log(cc))) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    t_last = float(tt[-1])
    clast_fit = float(np.exp(intercept + slope * t_last))  # 回归外推的拟合末点浓度
    return lam, r2, clast_fit, t_last, int(len(sel))


def compute_nca(t_in, c_in, method=DEFAULT_METHOD, n_lambda=DEFAULT_N_LAMBDA, dose=None):
    """单条浓度-时间曲线的 NCA 复算，返回 dict（数值 + 中间量）。不做重复时间点判断（由调用方把关）。"""
    if method not in SUPPORTED_METHODS:
        raise ValueError("method 仅支持 %s（当前 %s）" % (SUPPORTED_METHODS, method))
    t = np.asarray(t_in, dtype=float)
    c = np.asarray(c_in, dtype=float)
    order = np.argsort(t, kind="stable")             # 按时间升序（稳定排序保留原始次序）
    t, c = t[order], c[order]
    if len(t) < 2:
        raise ValueError("至少需要 2 个数据点")
    if np.any(np.isnan(t)) or np.any(np.isnan(c)):
        keep = ~(np.isnan(t) | np.isnan(c))          # 丢弃含 NaN 的行（提示在报告里）
        t, c = t[keep], c[keep]
    if np.any(c < 0):
        raise ValueError("存在负浓度，请先检查数据")
    if len(t) < 2:
        raise ValueError("剔除 NaN 后数据点不足 2 个")

    n_pts = int(len(t))
    auc_t = auc_linear(t, c) if method == "linear" else auc_lul(t, c)
    aumc_t = auc_linear(t, t * c)                    # AUMC 一律线性梯形（DAS 惯例）
    lam, r2, clast_fit, t_last, n_used = lambda_z(t, c, n_lambda)
    clast_obs = float(c[-1])
    tau = LN2 / lam
    auc_inf = auc_t + clast_fit / lam                # 主口径：拟合末点外推
    auc_inf_obs = auc_t + clast_obs / lam            # 备口径：观测末点外推（DAS 惯例）
    aumc_inf = aumc_t + clast_fit * t_last / lam + clast_fit / lam ** 2
    mrt = aumc_inf / auc_inf
    mrt_t = aumc_t / auc_t                           # 无外推的 MRT0-t（核对用）
    pct_extrap_auc = (auc_inf - auc_t) / auc_inf * 100.0
    pct_extrap_aumc = (aumc_inf - aumc_t) / aumc_inf * 100.0

    res = {
        "n_points": n_pts,
        "t_first": float(t[0]), "t_last": float(t_last),
        "cmax": float(np.max(c)), "tmax": float(t[int(np.argmax(c))]),
        "clast_obs": clast_obs,
        "auc0_t": auc_t, "aumc0_t": aumc_t,
        "lambda_z": lam, "lambda_z_r2": r2, "lambda_z_n": n_used,
        "clast_fit": clast_fit, "t_half": tau,
        "auc0_inf": auc_inf, "auc0_inf_obs_clast": auc_inf_obs,
        "aumc0_inf": aumc_inf,
        "mrt": mrt, "mrt_0_t": mrt_t,
        "pct_extrap_auc": pct_extrap_auc, "pct_extrap_aumc": pct_extrap_aumc,
        "method": method, "n_lambda": n_lambda,
    }
    if dose is not None:
        cl = float(dose) / auc_inf                   # CL = Dose / AUC0-inf
        res.update({"dose": float(dose), "cl": cl,
                    "vz": cl / lam,                  # Vz = CL / λz
                    "vss": mrt * cl})                # Vss = MRT · CL
    return res


# ------------------------------------------------------------------
# 重复时间点护栏（禁止静默拼接）
# ------------------------------------------------------------------
def duplicate_times(t, rtol=DUP_RTOL):
    """返回同曲线内重复/近重复的时间点列表（排序后相邻差 ≤ rtol 即视为同一时间点）。"""
    ts = np.sort(np.asarray(t, dtype=float))
    ts = ts[~np.isnan(ts)]
    if ts.size < 2:
        return []
    idx = np.where(np.diff(ts) <= rtol)[0]
    hit = set()
    for i in idx:
        hit.add(round(float(ts[i]), 12))
        hit.add(round(float(ts[i + 1]), 12))
    return sorted(hit)


def assert_no_duplicate_times(t, label, subject_col=None):
    """同一曲线内重复时间点 → SystemExit(1)（不静默拼接；提示改用 --subject）。"""
    dup = duplicate_times(t)
    if dup:
        show = ", ".join("%g" % v for v in dup[:6]) + (" …" if len(dup) > 6 else "")
        raise SystemExit(
            "[错误] %s：同一曲线内出现 %d 个重复时间点（%s）。\n"
            "       原因：多样本/重复采样被拼到同一条曲线上——旧版会静默按时间排序后缝成一条曲线，"
            "重复时间点段的区间长度记为 0，AUC 被系统性低估。\n"
            "       处理：① 多样本请用 --subject 指定个体列（按个体分曲线后汇总）；"
            "② 重复采样请先按个体×时间点聚合（均值）或逐个体拆分后再算。\n"
            "       本脚本拒绝静默拼接：exit 1。" % (label, len(dup), show))


# ------------------------------------------------------------------
# 逐曲线计算 + 跨个体汇总
# ------------------------------------------------------------------
def run_curves(rows, time_col, conc_col, group_col=None, subject_col=None,
               method=DEFAULT_METHOD, n_lambda=DEFAULT_N_LAMBDA, dose=None):
    """跑全部曲线（组别×个体）→ [{'group','subject','nca'}]；重复时间点 → SystemExit(1)。"""
    out = []
    for gname, sname, sub in build_curves(rows, group_col, subject_col):
        label = ("%s / 个体 %s" % (gname, sname)) if sname is not None else str(gname)
        t = col_float(sub, time_col)
        c = col_float(sub, conc_col)
        assert_no_duplicate_times(t, label, subject_col)
        try:
            res = compute_nca(t, c, method=method, n_lambda=n_lambda, dose=dose)
        except ValueError as exc:
            raise SystemExit("[错误] %s：%s" % (label, exc))
        out.append({"group": gname, "subject": sname, "nca": res})
    if not out:
        raise SystemExit("[错误] 没有任何可用的曲线（请检查 --group / --subject 列取值）")
    return out


SUMMARY_KEYS = ("n_points", "t_last", "cmax", "tmax", "clast_obs",
                "auc0_t", "aumc0_t", "lambda_z", "lambda_z_r2", "lambda_z_n",
                "clast_fit", "t_half", "auc0_inf", "auc0_inf_obs_clast", "aumc0_inf",
                "mrt", "mrt_0_t", "pct_extrap_auc", "pct_extrap_aumc",
                "cl", "vz", "vss")


def summarize(results, keys=SUMMARY_KEYS):
    """跨个体汇总：{'n_subjects': k, 'params': {key: {'mean','sd','n'}}}；SD = 样本 SD(ddof=1)，k<2 → None。"""
    params = {}
    for key in keys:
        vals = [float(r[key]) for r in results if r.get(key) is not None and np.isfinite(float(r[key]))]
        if not vals:
            continue
        params[key] = {"mean": float(np.mean(vals)),
                       "sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else None,
                       "n": len(vals)}
    return {"n_subjects": len(results), "params": params}


def collect_results(runs):
    """把逐曲线结果按组别归并 → [{'group','n_subjects','aggregate','subjects'}]（组序保持出现顺序）。"""
    order, bucket = [], {}
    for it in runs:
        g = str(it["group"])
        if g not in bucket:
            bucket[g] = []
            order.append(g)
        bucket[g].append(it)
    out = []
    for g in order:
        items = bucket[g]
        agg = summarize([it["nca"] for it in items])
        out.append({"group": g,
                    "n_subjects": agg["n_subjects"],
                    "aggregate": agg["params"],
                    "subjects": [{"subject": ("—" if it["subject"] is None else str(it["subject"])),
                                  "nca": it["nca"]} for it in items]})
    return out


# ------------------------------------------------------------------
# 报告输出
# ------------------------------------------------------------------
def _fmt(x, nd=4):
    """数值格式化（NaN/None 稳妥处理）。"""
    if x is None:
        return "-"
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return "nan"
    return "%.*g" % (nd, x) if abs(x) < 1e5 or x == 0 else "%.*e" % (nd, x)


def report_markdown(results, dose=None):
    """results: collect_results() 的产物 → Markdown 文本（单曲线=长表；多样本=汇总 + 逐个体）。"""
    lines = []
    lines.append("# NCA 独立复算报告")
    lines.append("")
    lines.append("- 脚本：`nca.py`（**独立复算 / 核对用；实验室口径以 DAS 软件输出为准**）")
    first = results[0]["subjects"][0]["nca"]
    lines.append("- 梯形法：%s" % METHOD_LABELS[first["method"]])
    lines.append("- λz：末 %d 个 C>0 点 ln(C)-t 线性回归" % first["n_lambda"])
    multi = any(r["n_subjects"] > 1 for r in results)
    lines.append("- 个体维：%s" % ("按 --subject 拆曲线 → 逐条 NCA → 跨个体 mean±SD"
                                   if multi else "单曲线（未指定 --subject）"))
    lines.append("")
    lines.append("## 口径声明")
    lines.append("1. 本脚本为 DAS 的**交叉核对器**，二者不一致时以 DAS 为准。")
    lines.append("2. AUC0-t / AUMC0-t 线性梯形法；λz 末段 ln(C)-t 回归。")
    lines.append("3. AUC0-inf 主口径 = AUC0-t + Clast,fit/λz（拟合末点）；"
                 "另给 C_last,obs/λz 口径（DAS 惯例）供比对。")
    lines.append("4. AUMC0-inf = AUMC0-t + C_last·t_last/λz + C_last/λz²；"
                 "MRT = AUMC0-inf / AUC0-inf。")
    lines.append("5. 单位不做换算；时间须为 h。CL/Vz/Vss 仅在有 --dose 时给出。")
    lines.append("6. 多样本必须用 --subject 指定个体列；同一曲线内重复时间点 → **直接报错退出"
                 "（exit 1）**，不做静默拼接（静默拼接会把 AUC 系统性压低）。")
    lines.append("7. 多样本汇总口径：跨个体 mean ± SD（样本 SD，ddof=1；个体数 <2 时 SD 记为 -）。")
    lines.append("")
    for item in results:
        agg, nsub = item["aggregate"], item["n_subjects"]
        lines.append("## 组别：%s%s" % (item["group"], ("（个体数 n = %d）" % nsub) if nsub > 1 else ""))
        lines.append("")
        if nsub > 1:
            lines.append("### 汇总（跨个体 mean±SD）")
            lines.append("")
            lines.append("| 项目 | mean | SD | n |")
            lines.append("| --- | --- | --- | --- |")
            for key, label, nd in (("n_points", "数据点数/曲线", 6), ("cmax", "Cmax", 4),
                                   ("tmax", "Tmax (h)", 4), ("lambda_z", "λz (h⁻¹)", 4),
                                   ("lambda_z_r2", "λz 回归 R²", 6), ("t_half", "t1/2 (h)", 4),
                                   ("auc0_t", "AUC0-t", 6), ("auc0_inf", "AUC0-inf（拟合末点）", 6),
                                   ("auc0_inf_obs_clast", "AUC0-inf（观测末点，DAS 口径）", 6),
                                   ("pct_extrap_auc", "AUC 外推占比 (%)", 3), ("aumc0_t", "AUMC0-t", 6),
                                   ("aumc0_inf", "AUMC0-inf", 6), ("pct_extrap_aumc", "AUMC 外推占比 (%)", 3),
                                   ("mrt", "MRT0-inf (h)", 5), ("mrt_0_t", "MRT0-t (h, 无外推)", 5),
                                   ("cl", "CL = Dose/AUC0-inf", 6), ("vz", "Vz = CL/λz", 6),
                                   ("vss", "Vss = MRT·CL", 6)):
                cell = agg.get(key)
                if not cell:
                    continue
                lines.append("| %s | %s | %s | %d |" % (label, _fmt(cell["mean"], nd), _fmt(cell["sd"], nd), cell["n"]))
            if dose is not None:
                lines.append("")
                lines.append("- Dose = %s（单值，组内同剂量）" % _fmt(float(dose)))
            lines.append("")
            lines.append("### 逐个体明细")
            lines.append("")
            lines.append("| 个体 | 点数 | t1/2 (h) | AUC0-t | AUC0-inf | MRT0-inf (h) | λz R² |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for s in item["subjects"]:
                r = s["nca"]
                lines.append("| %s | %d | %s | %s | %s | %s | %s |" % (
                    s["subject"], r["n_points"], _fmt(r["t_half"]), _fmt(r["auc0_t"], 6),
                    _fmt(r["auc0_inf"], 6), _fmt(r["mrt"], 5), _fmt(r["lambda_z_r2"], 6)))
            lines.append("")
            continue
        r = item["subjects"][0]["nca"]
        lines.append("| 项目 | 值 |")
        lines.append("| --- | --- |")
        lines.append("| 数据点数 | %d |" % r["n_points"])
        lines.append("| 时间范围 (h) | %s – %s |" % (_fmt(r["t_first"]), _fmt(r["t_last"])))
        lines.append("| Cmax | %s |" % _fmt(r["cmax"]))
        lines.append("| Tmax (h) | %s |" % _fmt(r["tmax"]))
        lines.append("| C_last 观测 | %s |" % _fmt(r["clast_obs"]))
        lines.append("| C_last 拟合 | %s |" % _fmt(r["clast_fit"]))
        lines.append("| λz (h⁻¹) | %s |" % _fmt(r["lambda_z"]))
        lines.append("| λz 回归 R² | %s |" % _fmt(r["lambda_z_r2"], 8))
        lines.append("| t1/2 (h) | %s |" % _fmt(r["t_half"]))
        lines.append("| AUC0-t | %s |" % _fmt(r["auc0_t"], 6))
        lines.append("| AUC0-inf（拟合末点） | %s |" % _fmt(r["auc0_inf"], 6))
        lines.append("| AUC0-inf（观测末点，DAS 口径） | %s |" % _fmt(r["auc0_inf_obs_clast"], 6))
        lines.append("| AUC 外推占比 (%%) | %s |" % _fmt(r["pct_extrap_auc"], 3))
        lines.append("| AUMC0-t | %s |" % _fmt(r["aumc0_t"], 6))
        lines.append("| AUMC0-inf | %s |" % _fmt(r["aumc0_inf"], 6))
        lines.append("| AUMC 外推占比 (%%) | %s |" % _fmt(r["pct_extrap_aumc"], 3))
        lines.append("| MRT0-inf (h) | %s |" % _fmt(r["mrt"], 5))
        lines.append("| MRT0-t (h, 无外推) | %s |" % _fmt(r["mrt_0_t"], 5))
        if dose is not None:
            lines.append("| Dose | %s |" % _fmt(r["dose"]))
            lines.append("| CL = Dose/AUC0-inf | %s |" % _fmt(r["cl"], 6))
            lines.append("| Vz = CL/λz | %s |" % _fmt(r["vz"], 6))
            lines.append("| Vss = MRT·CL | %s |" % _fmt(r["vss"], 6))
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 自测 / 演示
# ------------------------------------------------------------------
DEMO_T = np.array([0, 0.083, 0.25, 0.5, 1, 2, 4, 6, 8, 12, 16, 24], dtype=float)
SELFTEST_GRID = (0.083, 0.25, 0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0)
SELFTEST_SUBJ = (("S1", 90.0, 0.50), ("S2", 100.0, 0.45), ("S3", 110.0, 0.55))   # (个体, C0, k)


def _synth_iv(t_end=12.0, dt=0.05, c0=100.0, k=0.5):
    """一室 IV 单室模型合成数据：C(t) = C0·e^(-k t)。"""
    t = np.arange(0.0, t_end + dt / 2.0, dt)
    return t, c0 * np.exp(-k * t)


def _synth_rows(subjects=SELFTEST_SUBJ, grid=SELFTEST_GRID, group="G1"):
    """多样本合成行集（无噪声）：每行 = 组别/个体/时间/浓度。
    每个个体的真值：C_i(t) = C0_i·e^(-k_i·t) → AUC0-inf_i = C0_i / k_i，t1/2_i = ln2 / k_i。"""
    rows = []
    for name, c0, k in subjects:
        for ti in grid:
            rows.append({"group": group, "sid": name, "t": float(ti),
                         "c": float(c0 * np.exp(-k * float(ti)))})
    return rows


def selftest():
    """known-answer 合成断言：① 单曲线解析真值（原有）② 3 subject 汇总 vs 逐条 NCA ③ 反例可失败。"""
    print("=" * 72)
    print("nca.py --selftest")
    print("① 单曲线：C0=100, k=0.5 h^-1, 0–12 h, Δt=0.05；解析真值 t1/2=1.3863 h / AUC0-inf=200 / MRT=2.0 h")
    print("② 个体维：3 subject（C0=90/100/110，k=0.45/0.50/0.55）→ 汇总值须与逐条 NCA 一致，且各自回收解析真值")
    print("③ 反例：无 --subject 的多样本（重复时间点）必须被拦截（exit 1）")
    print("=" * 72)
    n_fail = 0

    def check(name, ok, detail=""):
        nonlocal n_fail
        n_fail += (not ok)
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))
        if detail:
            print("        " + detail)

    def relerr(meas, exp):
        return abs(meas - exp) / abs(exp) * 100.0 if exp else abs(meas)

    # ---------- ① 单曲线解析真值 ----------
    t, c = _synth_iv()
    res = compute_nca(t, c, method="linear", n_lambda=4, dose=5.0)
    res_lul = compute_nca(t, c, method="lul", n_lambda=4, dose=5.0)
    t_, _ = _synth_iv()
    n_int, h_ = len(t_) - 1, t_[1] - t_[0]
    r_ = np.exp(-0.5 * h_)
    s_ = r_ * (1.0 - r_ ** (n_int - 1)) / (1.0 - r_)          # Σ_{i=1}^{N-1} r^i
    auc_trap_exact = h_ * 100.0 * (0.5 + s_ + r_ ** n_int / 2.0)

    for name, meas, exp, tol_pct in (
            ("① t1/2 = ln2/λz", res["t_half"], LN2 / 0.5, 1.0),
            ("① AUC0-inf = AUC0-t + Clast,fit/λz", res["auc0_inf"], 200.0, 0.5),
            ("① MRT = AUMC0-inf/AUC0-inf", res["mrt"], 2.0, 1.0),
            ("① λz 回归值", res["lambda_z"], 0.5, 0.1),
            ("① AUC0-t 线性梯形（等比数列解析值）", res["auc0_t"], auc_trap_exact, 1e-6),
            ("① AUC0-inf（lul 法）", res_lul["auc0_inf"], 200.0, 0.05),
            ("① Vz = CL/λz (Dose=5)", res["vz"], 0.05, 1.0),
            ("① Vss = MRT·CL (Dose=5)", res["vss"], 0.05, 1.0)):
        check(name, relerr(meas, exp) <= tol_pct,
              "实测 = %.6f | 期望 = %.6f | 相对误差 = %.4f%% (容差 %g%%)" % (meas, exp, relerr(meas, exp), tol_pct))
    check("① λz 回归 R²", res["lambda_z_r2"] > 0.999999,
          "实测 R² = %.10f | 期望 > 0.999999" % res["lambda_z_r2"])

    # ---------- ② 3 subject 汇总 vs 逐条 NCA（科学正确性核心） ----------
    rows = _synth_rows()
    runs = run_curves(rows, "t", "c", group_col="group", subject_col="sid",
                      method="linear", n_lambda=4, dose=5.0)
    check("② 曲线数 = 个体数（未被缝成 1 条）", len(runs) == len(SELFTEST_SUBJ),
          "曲线数 = %d（期望 %d）" % (len(runs), len(SELFTEST_SUBJ)))
    check("② 每条曲线点数 = 时间网格长度", all(it["nca"]["n_points"] == len(SELFTEST_GRID) for it in runs),
          "点数 = %s（期望 %d）" % ([it["nca"]["n_points"] for it in runs], len(SELFTEST_GRID)))

    agg = summarize([it["nca"] for it in runs])
    per_auc = [it["nca"]["auc0_inf"] for it in runs]
    per_half = [it["nca"]["t_half"] for it in runs]
    mean_auc, sd_auc = float(np.mean(per_auc)), float(np.std(per_auc, ddof=1))
    mean_half, sd_half = float(np.mean(per_half)), float(np.std(per_half, ddof=1))
    check("② 汇总 mean(AUC0-inf) = 逐条 NCA 的均值", relerr(agg["params"]["auc0_inf"]["mean"], mean_auc) <= 1e-9,
          "汇总 = %.10g | 逐条均值 = %.10g | 相对误差 = %.3g%% (容差 1e-9%%)"
          % (agg["params"]["auc0_inf"]["mean"], mean_auc, relerr(agg["params"]["auc0_inf"]["mean"], mean_auc)))
    check("② 汇总 SD(AUC0-inf) = 逐条 NCA 的样本 SD",
          agg["params"]["auc0_inf"]["sd"] is not None and relerr(agg["params"]["auc0_inf"]["sd"], sd_auc) <= 1e-9,
          "汇总 = %.10g | 逐条 SD = %.10g" % (agg["params"]["auc0_inf"]["sd"] or float("nan"), sd_auc))
    check("② 汇总 mean(t1/2) = 逐条 NCA 的均值", relerr(agg["params"]["t_half"]["mean"], mean_half) <= 1e-9,
          "汇总 = %.10g | 逐条均值 = %.10g" % (agg["params"]["t_half"]["mean"], mean_half))
    check("② 汇总 SD(t1/2) = 逐条 NCA 的样本 SD",
          agg["params"]["t_half"]["sd"] is not None and relerr(agg["params"]["t_half"]["sd"], sd_half) <= 1e-9,
          "汇总 = %.10g | 逐条 SD = %.10g" % (agg["params"]["t_half"]["sd"] or float("nan"), sd_half))
    check("② 汇总 n_subjects = 3", agg["n_subjects"] == len(SELFTEST_SUBJ), "n = %d" % agg["n_subjects"])

    # 逐个体回收解析真值（无噪声 → 容差可收紧到 0.5%）
    truth_auc = {name: c0 / k for name, c0, k in SELFTEST_SUBJ}
    truth_half = {name: float(LN2) / k for name, c0, k in SELFTEST_SUBJ}
    worst = max(relerr(it["nca"]["auc0_inf"], truth_auc[it["subject"]]) for it in runs)
    check("② 逐个体 AUC0-inf 回收解析真值 C0/k（无噪声，容差 0.5%）", worst <= 0.5,
          "最大相对误差 = %.4f%%（真值 %s）"
          % (worst, ", ".join("%s=%.4f" % (k, v) for k, v in sorted(truth_auc.items()))))
    worst_h = max(relerr(it["nca"]["t_half"], truth_half[it["subject"]]) for it in runs)
    check("② 逐个体 t1/2 回收解析真值 ln2/k（无噪声，容差 0.5%）", worst_h <= 0.5,
          "最大相对误差 = %.4f%%（真值 %s）"
          % (worst_h, ", ".join("%s=%.6f h" % (k, v) for k, v in sorted(truth_half.items()))))

    # ---------- ③ 反例：无 --subject 的重复时间点必须被拦截 ----------
    dup_rows = _synth_rows(subjects=(("S1", 90.0, 0.45), ("S2", 100.0, 0.50)))
    caught, msg = False, ""
    try:
        run_curves(dup_rows, "t", "c", group_col="group", subject_col=None,
                   method="linear", n_lambda=4, dose=5.0)
    except SystemExit as exc:
        caught, msg = True, str(exc)
    check("③ 无 --subject + 重复时间点 → 已拦截（exit 1，未静默拼接）",
          caught and "--subject" in msg, (msg.splitlines()[0] if msg else "未触发拦截（危险：静默拼接）"))
    check("③ 重复时间点识别数 = 网格长度", len(duplicate_times(np.repeat(np.asarray(SELFTEST_GRID), 2))) == len(SELFTEST_GRID),
          "识别 = %d（期望 %d）" % (len(duplicate_times(np.repeat(np.asarray(SELFTEST_GRID), 2))), len(SELFTEST_GRID)))
    check("③ 正常单曲线无误报", duplicate_times(np.asarray(SELFTEST_GRID)) == [],
          "重复点 = %s" % duplicate_times(np.asarray(SELFTEST_GRID)))

    print("-" * 72)
    if n_fail == 0:
        print("selftest 结果：全部 PASS")
        return 0
    print("selftest 结果：%d 项 FAIL" % n_fail)
    return 1


def demo():
    """合成两组（脂质体 / 参比制剂）× 3 个个体的虚拟 PK 数据，按个体维跑一遍并输出可判读数值。"""
    rng = np.random.default_rng(20260921)
    truth = {"脂质体(合成)": (100.0, 0.05), "参比制剂(合成)": (120.0, 0.45)}
    rows = []
    for gname, (c0, k) in truth.items():
        for i in range(1, 4):
            scale = 1.0 + rng.normal(0.0, 0.15)
            for ti in DEMO_T:
                c = c0 * scale * float(np.exp(-k * float(ti))) * (1.0 + rng.normal(0.0, 0.05))
                rows.append({"组别": gname, "个体": "R%02d" % i, "时间h": float(ti),
                             "浓度": round(max(c, 1e-4), 5)})
    print("### demo：合成数据（固定随机种子 20260921，每组 n=3 个体，个体间变异 15%，测量噪声 5%）")
    print("###     真值：脂质体 k≈0.05 h^-1｜参比制剂 k≈0.45 h^-1（AUC0-inf ≈ C0/k）")
    runs = run_curves(rows, "时间h", "浓度", group_col="组别", subject_col="个体",
                      method="linear", n_lambda=4, dose=5.0)
    results = collect_results(runs)
    for item in results:
        agg = item["aggregate"]
        print("  %s：n=%d 个体｜mean AUC0-inf = %.4g（SD %.4g）｜mean t1/2 = %.4g h（SD %.4g）"
              % (item["group"], item["n_subjects"], agg["auc0_inf"]["mean"],
                 agg["auc0_inf"]["sd"] or float("nan"), agg["t_half"]["mean"], agg["t_half"]["sd"] or float("nan")))
    print()
    print(report_markdown(results, dose=5.0))
    return 0


# ------------------------------------------------------------------
# 主程序
# ------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="NCA 独立复算 / 核对器（口径：DAS 输出为准；多样本请给 --subject）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", help="输入 CSV / TSV / Excel 路径")
    p.add_argument("--time", default=DEFAULT_TIME_COL, help="时间列名（默认 %s）" % DEFAULT_TIME_COL)
    p.add_argument("--conc", default=DEFAULT_CONC_COL, help="浓度列名（默认 %s）" % DEFAULT_CONC_COL)
    p.add_argument("--group", default=DEFAULT_GROUP_COL, help="可选分组列名（按组分别汇总）")
    p.add_argument("--subject", default=DEFAULT_SUBJECT_COL,
                   help="个体列名；给了就按个体分曲线做 NCA 后汇总（mean±SD）。"
                        "多样本不给此列且出现重复时间点时直接报错退出（exit 1）")
    p.add_argument("--method", default=DEFAULT_METHOD, choices=SUPPORTED_METHODS,
                   help="梯形法：linear（默认，DAS 一致）/ lul（线性上行-对数下行）")
    p.add_argument("--n-lambda", type=int, default=DEFAULT_N_LAMBDA, dest="n_lambda",
                   help="λz 末段回归点数（默认 %d，≥%d）" % (DEFAULT_N_LAMBDA, MIN_N_LAMBDA))
    p.add_argument("--dose", type=float, default=None, help="给药剂量（给出则算 CL/Vz/Vss）")
    p.add_argument("--encoding", default="utf-8-sig", help="CSV 首选编码（默认 utf-8-sig，其后自动回退）")
    p.add_argument("--json", action="store_true", help="输出 JSON 而非 Markdown")
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
    require_columns(cols, [args.time, args.conc, args.group, args.subject])
    runs = run_curves(rows, args.time, args.conc, group_col=args.group, subject_col=args.subject,
                      method=args.method, n_lambda=args.n_lambda, dose=args.dose)
    results = collect_results(runs)
    note = "独立复算；实验室口径以 DAS 输出为准"
    if args.subject is None and len(runs) > 1:
        note += "；未见重复时间点（同组内每条 t 唯一）"
    if args.json:
        payload = {"method": args.method, "n_lambda": args.n_lambda, "dose": args.dose,
                   "group_col": args.group, "subject_col": args.subject, "note": note,
                   "results": results}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(report_markdown(results, dose=args.dose))
    return 0


if __name__ == "__main__":
    sys.exit(main())
