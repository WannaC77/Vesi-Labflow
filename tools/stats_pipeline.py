#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stats_pipeline —— Vesi 统计管线（L0 核心 · V-M4 统计台）

适用场景 / Purpose
    实验数据的可复核统计分析：CSV/Excel → 数据质量标记 → Shapiro 正态证据
    → 检验树决策 → 主检验 + 事后（Holm）→ 效应量 + 95%CI → Markdown 报告。
    模块 V-M4「统计台」核心工具；产物=分析报告 md（门禁：三证齐）。

输入 / Input
    CSV 或 Excel（--file），需指定 --value 指标列；比较型分析需 --group 分组列。
输出 / Output
    Markdown 报告（stdout 或 --out 落盘）；--json 输出机器可读结果。

依赖 / Deps
    numpy / scipy（必需）；pandas 仅 Excel（.xlsx/.xls/.xlsm）输入需要——CSV/TSV 走标准库，
    缺 pandas 亦可跑；Excel 缺 pandas 时明确报错并提示转存 CSV（不静默）。不依赖 statsmodels/sklearn。

配对设计（科学正确性修复 · 必读）
    --paired 有两种输入形态，**都必须有配对信息，缺则直接报错退出**（旧版对长表静默
    降级成独立样本检验 paired=False，把配对数据当独立数据处理 → 方差被高估、p 被高估、
    结论方向可能反）：
      ① 宽表：两列数值列（一行 = 一对），不给 --group；
      ② 长表：给 --group（正好 2 个水平）**且必须给 --pair-id**（配对标识列），
         每个配对标识须在两个水平各出现 1 次。
    长表给出 --paired 但缺 --pair-id → exit 1（禁止静默降级）。

口径声明 / Convention（对齐 `workflows/08` 统计方法速查 + 微陷阱表）
    1) **方法预注册**：统计方法在实验前确定，非事后选择；本工具输出=复核证据，
       不得用于事后挑选检验以凑显著性。
    2) 检验树：两组正态→独立 t（方差不齐 Welch）｜两组非正态→Mann-Whitney U；
       多组正态→单因素 ANOVA + Tukey-HSD｜多组非正态→Kruskal-Wallis +
       成对 MWU（Holm 校正；等效 Dunn 的替代法，报告中注明）。
    3) 配对设计：配对 t / Wilcoxon 符号秩（按 --pair-id 对齐后逐对求差）。
    4) **n=3 非参数下限**：两组各 n=3 时 Mann-Whitney 双侧精确 p 下限=2/C(6,3)=0.10，
       不可能 p<0.05——报告中强制提示，禁止标注 */**。
    5) n<3：不做推断统计（只描述）。
    6) 异常值：只标记候选（|z|>3），**不自动删除**（直接删=选择性报告）。
    7) PK 参数（AUC/Cmax）比较可用 --log 对数转换后再选检验。
    8) 误差棒用 SD（SEM 仅表均值置信度且须图注声明）——本报告只出数值结论，图走 V-M6。

用法 / Usage
    python stats_pipeline.py data.csv --value 浓度 --group 组别
    python stats_pipeline.py data.csv --value 含量 --group 组别 --log --out 报告.md --json
    python stats_pipeline.py wide.csv --value 值 --paired              # 宽表配对（两列数值）
    python stats_pipeline.py long.csv --value 值 --group 组别 --paired --pair-id 样本
    python stats_pipeline.py --selftest                               # 合成数据回归断言
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np
from scipy import stats

VERSION = 'v1.1 (2026-09-22)'          # v1.1：长表配对强制 --pair-id（禁静默降级）+ 配对 known-answer 自测
ALPHA_DEFAULT = 0.05
N3_NONPARAM_FLOOR = 2.0 / 20.0         # 2/C(6,3) = 0.10
NA_TOKENS = ('', 'na', 'nan', 'n/a', 'null', 'none', '-')
CSV_ENCODINGS = ('utf-8-sig', 'gb18030', 'latin-1')
EXCEL_EXTS = ('.xlsx', '.xls', '.xlsm')


# ---------------------------------------------------------------- 基础工具
def _num(v):
    """单元格 → float；空/NA 记号 → NaN；其余解析失败抛 ValueError。"""
    if v is None:
        return float('nan')
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.lower() in NA_TOKENS:
        return float('nan')
    return float(s)


def _label(v):
    """单元格 → 文本标签；空/NA → ''（用于分组列取水平）。"""
    if v is None:
        return ''
    if isinstance(v, float) and np.isnan(v):
        return ''
    s = str(v).strip()
    return '' if s.lower() in NA_TOKENS else s


class Table:
    """极简列式表（行 = dict）——CSV/TSV 路径不依赖 pandas；Excel 由 pandas 读入后转本表。"""

    def __init__(self, cols, rows):
        self.cols = list(cols)
        self.rows = [dict(r) for r in rows]

    # ---- 构造 ----
    @classmethod
    def from_rows(cls, rows):
        cols, seen = [], set()
        for r in rows:
            for c in r:
                if c not in seen:
                    seen.add(c)
                    cols.append(c)
        return cls(cols, rows)

    @classmethod
    def from_mapping(cls, mapping):
        """{列名: [值, ...]} → Table（自测与程序内构造用）。"""
        names = list(mapping)
        n = max((len(mapping[k]) for k in names), default=0)
        rows = [{k: (mapping[k][i] if i < len(mapping[k]) else '') for k in names} for i in range(n)]
        return cls(names, rows)

    def __len__(self):
        return len(self.rows)

    def has(self, name):
        return name in self.cols

    def require(self, names):
        missing = [c for c in names if c and not self.has(c)]
        if missing:
            raise SystemExit('[错误] 缺少列 %s；文件实际列名 = %s' % (missing, self.cols))

    # ---- 列读取 ----
    def numeric_col(self, name):
        out = []
        for i, r in enumerate(self.rows, start=1):
            try:
                out.append(_num(r.get(name)))
            except ValueError:
                raise SystemExit('[错误] 列 `%s` 第 %d 个数据值不是数值：%r（请先清理该列）'
                                 % (name, i, r.get(name)))
        return np.asarray(out, dtype=float)

    def text_col(self, name):
        return [_label(r.get(name)) for r in self.rows]

    def is_numeric(self, name):
        seen = False
        for r in self.rows:
            try:
                x = _num(r.get(name))
            except ValueError:
                return False
            if not np.isnan(x):
                seen = True
        return seen

    # ---- 行筛选 / 派生 ----
    def count_missing(self, name):
        return sum(1 for r in self.rows
                   if (lambda x: np.isnan(x) if isinstance(x, float) else True)(self._safe_num(r.get(name))) is True)

    def _safe_num(self, v):
        try:
            return _num(v)
        except ValueError:
            return float('nan')

    def duplicated_rows(self):
        seen, dup = set(), 0
        for r in self.rows:
            key = tuple(str(r.get(c)) for c in self.cols)
            if key in seen:
                dup += 1
            else:
                seen.add(key)
        return dup

    def dropna(self, name):
        return Table(self.cols, [r for r in self.rows if not np.isnan(self._safe_num(r.get(name)))])

    def count_le(self, name, thr):
        n = 0
        for r in self.rows:
            x = self._safe_num(r.get(name))
            if np.isnan(x) or x <= thr:
                n += 1
        return n

    def filter_gt(self, name, thr):
        return Table(self.cols, [r for r in self.rows
                                 if not np.isnan(self._safe_num(r.get(name)))
                                 and self._safe_num(r.get(name)) > thr])

    def log_col(self, name):
        rows = []
        for r in self.rows:
            rr = dict(r)
            x = self._safe_num(r.get(name))
            rr[name] = float(np.log(x)) if (not np.isnan(x) and x > 0) else ''
            rows.append(rr)
        return Table(self.cols, rows)


def load_data(path, sheet=None) -> Table:
    """读 CSV/TSV/Excel（按扩展名路由；CSV 编码回退 utf-8-sig → gb18030 → latin-1）。"""
    if not os.path.isfile(path):
        raise SystemExit('[错误] 找不到输入文件：%s' % path)
    low = path.lower()
    if low.endswith(EXCEL_EXTS):
        try:
            import pandas as pd
        except Exception as exc:                       # noqa: BLE001
            raise SystemExit('[错误] 读取 Excel 需要 pandas + openpyxl（当前解释器不可用：%s）。'
                             '[降级] 请把表另存为 CSV/TSV 后重跑（CSV 走标准库，无第三方依赖）。' % exc)
        df = pd.read_excel(path, sheet_name=sheet if sheet is not None else 0)
        df.columns = [str(c).strip() for c in df.columns]
        return Table(list(df.columns), df.to_dict('records'))
    sep = '\t' if low.endswith('.tsv') else ','
    raw, tried, last = None, [], None
    for enc in CSV_ENCODINGS:
        tried.append(enc)
        try:
            with open(path, 'r', encoding=enc, newline='') as f:
                raw = list(csv.reader(f, delimiter=sep))
            break
        except (UnicodeDecodeError, UnicodeError) as exc:
            last = exc
    if raw is None:
        raise SystemExit('[错误] 读入失败（已试编码 %s）：%s' % (tried, last))
    if not raw:
        raise SystemExit('[错误] 空文件：%s' % path)
    cols = [str(c).strip() for c in raw[0]]
    rows = []
    for rec in raw[1:]:
        if not any(str(x).strip() for x in rec):
            continue
        rows.append({cols[i]: (rec[i] if i < len(rec) else '') for i in range(len(cols))})
    return Table(cols, rows)


def clean_flags(tbl: Table, value: str, group: str | None) -> list:
    """数据质量标记（不修改数据）：缺失/非数值/重复行。"""
    flags = []
    n_missing = sum(1 for r in tbl.rows if np.isnan(tbl._safe_num(r.get(value))))
    if n_missing:
        flags.append('缺失值 %d 个（已剔除后再分析）' % n_missing)
    n_dup = tbl.duplicated_rows()
    if n_dup:
        flags.append('完全重复行 %d 行（请确认是否误录，本工具不自动删除）' % n_dup)
    if group is None:
        flags.append('未指定分组列：执行单组描述/正态性分析')
    return flags


# ---------------------------------------------------------------- 描述与证据
def describe(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    return dict(n=int(x.size), mean=float(np.mean(x)), sd=float(np.std(x, ddof=1)) if x.size > 1 else None,
                median=float(np.median(x)),
                q1=float(np.percentile(x, 25)), q3=float(np.percentile(x, 75)),
                min=float(np.min(x)), max=float(np.max(x)),
                cv=float(np.std(x, ddof=1) / np.mean(x)) if x.size > 1 and np.mean(x) != 0 else None)


def shapiro_evidence(x: np.ndarray) -> dict:
    """Shapiro-Wilk 正态证据；n<3 或 n>5000 时给出限制说明。"""
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 3:
        return dict(test='shapiro', n=n, W=None, p=None, ok=None,
                    note='n<3，不足以检验正态性（不做推断统计）')
    if n > 5000:
        return dict(test='shapiro', n=n, W=None, p=None, ok=None,
                    note='n>5000 超出 Shapiro 适用范围（改用图形/其它证据）')
    if np.all(x == x[0]):
        return dict(test='shapiro', n=n, W=None, p=None, ok=None, note='常数向量，无法检验')
    w, p = stats.shapiro(x)
    return dict(test='shapiro', n=n, W=float(w), p=float(p), ok=bool(p >= 0.05),
                note='正态（p>=0.05）' if p >= 0.05 else '偏离正态（p<0.05）')


def variance_evidence(*groups: np.ndarray) -> dict:
    """Levene 方差齐性（>=2 组且每组>=2 时）。"""
    clean = [np.asarray(g, dtype=float) for g in groups if np.asarray(g).size >= 2]
    if len(clean) < 2:
        return dict(test='levene', p=None, note='组数或样本不足，跳过')
    w, p = stats.levene(*clean)
    return dict(test='levene', W=float(w), p=float(p), equal=bool(p >= 0.05),
                note='方差齐（p>=0.05）' if p >= 0.05 else '方差不齐（p<0.05）')


def outlier_candidates(x: np.ndarray, thr=3.0) -> list:
    """|z|>3 候选（仅标记）。"""
    x = np.asarray(x, dtype=float)
    if x.size < 3 or np.std(x, ddof=1) == 0:
        return []
    z = (x - np.mean(x)) / np.std(x, ddof=1)
    return [dict(index=int(i), value=float(x[i]), z=float(z[i])) for i in np.where(np.abs(z) > thr)[0]]


def unique_in_order(values) -> list:
    """保持首次出现顺序去重（分组/水平顺序稳定，便于复跑比对）。"""
    out, seen = [], set()
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


# ---------------------------------------------------------------- 效应量
def cohens_d(a: np.ndarray, b: np.ndarray) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    n1, n2 = a.size, b.size
    sp2 = ((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1)) / (n1 + n2 - 2)
    d = (np.mean(a) - np.mean(b)) / np.sqrt(sp2)
    g = d * (1 - 3.0 / (4 * (n1 + n2) - 9))  # Hedges 小样本校正
    return dict(d=float(d), hedges_g=float(g))


def rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    """秩双列相关 r = 1 - 2U1/(n1*n2)；正值=a 偏大。"""
    U1 = stats.mannwhitneyu(a, b, alternative='two-sided').statistic
    return float(1 - 2 * U1 / (a.size * b.size))


def eta_squared_kw(groups: list) -> float:
    """Kruskal-Wallis 的 epsilon² = (H - k + 1) / (n - k)。"""
    H = stats.kruskal(*groups).statistic
    k = len(groups)
    n = sum(g.size for g in groups)
    return float((H - k + 1) / (n - k)) if n > k else float('nan')


def mean_diff_ci(a: np.ndarray, b: np.ndarray, alpha: float, welch: bool) -> tuple:
    """均值差的 95%CI（Welch 或 pooled）；返回 (diff, lo, hi)。"""
    diff = float(np.mean(a) - np.mean(b))
    n1, n2 = a.size, b.size
    s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
    if welch:
        se = np.sqrt(s1 / n1 + s2 / n2)
        df = (s1 / n1 + s2 / n2) ** 2 / ((s1 / n1) ** 2 / (n1 - 1) + (s2 / n2) ** 2 / (n2 - 1))
    else:
        sp2 = ((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)
        se = np.sqrt(sp2 * (1 / n1 + 1 / n2))
        df = n1 + n2 - 2
    tcrit = stats.t.ppf(1 - alpha / 2, df)
    return diff, float(diff - tcrit * se), float(diff + tcrit * se)


# ---------------------------------------------------------------- 检验树
def choose_two_group_test(x: np.ndarray, y: np.ndarray, paired: bool, alpha: float, forced: str | None) -> dict:
    """两组检验树（对齐 workflows/08）。"""
    if forced and forced != 'auto':
        return dict(chosen=forced, reason='用户指定 --method %s' % forced)
    nx, ox = shapiro_evidence(x), shapiro_evidence(y)
    if paired:
        d = x - y
        nd = shapiro_evidence(d)
        chosen = 'ttest_rel' if (nd['ok'] is not False) else 'wilcoxon'
        return dict(chosen=chosen, reason='配对设计：差值正态证据 → %s' % chosen,
                    normality_x=nx, normality_y=ox, normality_diff=nd)
    if nx['ok'] is False or ox['ok'] is False:
        return dict(chosen='mwu', reason='存在非正态组（Shapiro p<0.05）→ Mann-Whitney U',
                    normality_x=nx, normality_y=ox)
    lev = variance_evidence(x, y)
    if lev.get('equal') is False:
        return dict(chosen='welch', reason='正态且方差不齐（Levene p<0.05）→ Welch t',
                    normality_x=nx, normality_y=ox, levene=lev)
    return dict(chosen='ttest', reason='正态且方差齐 → 独立 t', normality_x=nx, normality_y=ox, levene=lev)


def choose_multi_group_test(groups: list, forced: str | None) -> dict:
    """多组检验树（>=3 组）。"""
    if forced and forced != 'auto':
        return dict(chosen=forced, reason='用户指定 --method %s' % forced)
    norm = [shapiro_evidence(g) for g in groups]
    if any(s['ok'] is False for s in norm):
        return dict(chosen='kruskal', reason='存在非正态组 → Kruskal-Wallis + 成对 MWU(Holm)', normality=norm)
    lev = variance_evidence(*groups)
    if lev.get('equal') is False:
        # ANOVA 对轻度方差偏离稳健；报告记录并继续 ANOVA（备选 Welch-ANOVA 未实现）
        return dict(chosen='anova', reason='正态但方差不齐（Levene p<0.05）→ ANOVA（记录偏离；解释谨慎）',
                    normality=norm, levene=lev)
    return dict(chosen='anova', reason='正态且方差齐 → 单因素 ANOVA + Tukey', normality=norm, levene=lev)


def holm_adjust(pvals: list) -> list:
    """Holm 逐步校正。"""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running = max(running, val)
        adj[idx] = min(1.0, running)
    return [float(v) for v in adj]


# ---------------------------------------------------------------- 配对（长表）
def paired_long_table(res: dict, tbl: Table, value: str, group: str, pair_id: str,
                      alpha: float, method: str) -> dict:
    """长表配对：按 --pair-id 对齐两个水平（每对两水平各 1 次），再走配对检验树。

    任何不合规（水平数≠2、标识不成对、同一对同一水平重复、标识为空）→ SystemExit(1)，
    绝不退化为独立样本检验。
    """
    levels = unique_in_order([lv for lv in tbl.text_col(group) if lv != ''])
    if len(levels) != 2:
        raise SystemExit('[错误] --paired 长表需 --group 正好 2 个水平（当前 %d 个：%s）；'
                         '多水平请改用成对比较或先选两个水平。' % (len(levels), levels))
    bucket, order = {}, []
    for i, r in enumerate(tbl.rows, start=1):
        pid = _label(r.get(pair_id))
        lv = _label(r.get(group))
        if pid == '':
            raise SystemExit('[错误] --pair-id 列 `%s` 第 %d 行为空：配对标识不可缺（exit 1）。' % (pair_id, i))
        if lv not in levels:
            continue                      # 分组列缺失行不计入（已在 flags 记录）
        if pid not in bucket:
            bucket[pid] = {}
            order.append(pid)
        if lv in bucket[pid]:
            raise SystemExit('[错误] 配对标识 `%s` 在水平 `%s` 出现多次（同一对同一水平只能 1 次）；'
                             '请检查 --pair-id 是否唯一标识实验单元。' % (pid, lv))
        bucket[pid][lv] = float(tbl._safe_num(r.get(value)))
    if not order:
        raise SystemExit('[错误] 长表配对：按 --pair-id 未收集到任何配对（请检查列名与取值）。')
    bad = [pid for pid in order if len(bucket[pid]) != 2]
    if bad:
        raise SystemExit('[错误] 以下配对标识不成对（缺一个水平）：%s%s（共 %d 个）——'
                         '请补齐数据或用 --pair-id 指向正确的配对列。'
                         % (', '.join(bad[:6]), ' …' if len(bad) > 6 else '', len(bad)))
    a = np.asarray([bucket[pid][levels[0]] for pid in order], dtype=float)
    b = np.asarray([bucket[pid][levels[1]] for pid in order], dtype=float)

    res['pair_id'] = pair_id
    res['n_pairs'] = len(order)
    res['test_labels'] = levels
    res['groups_n'] = {levels[0]: int(a.size), levels[1]: int(b.size)}
    res['groups'] = {levels[0]: describe(a), levels[1]: describe(b)}
    res['outliers'] = {levels[0]: outlier_candidates(a), levels[1]: outlier_candidates(b)}
    res['flags'].append('长表配对：按 `--pair-id %s` 对齐 %d 对（每对两水平各 1 次）'
                        % (pair_id, len(order)))
    if a.size < 3:
        res['conclusion'] = '配对数 n=%d（<3）：不做推断统计（只描述）' % a.size
        return res
    return _two_group_block(res, a, b, paired=True, alpha=alpha, method=method, labels=levels)


# ---------------------------------------------------------------- 主管线
def run_analysis(tbl: Table, value: str, group: str | None, paired: bool,
                 alpha: float, method: str, log_transform: bool, pair_id: str | None = None) -> dict:
    """主入口：执行完整管线，返回结果字典（报告由 report_md 渲染）。"""
    res: dict = dict(version=VERSION, alpha=alpha, value=value, group=group,
                     paired=bool(paired), pair_id=pair_id,
                     log_transform=bool(log_transform), method_forced=method)
    tbl = tbl.dropna(value)
    res['flags'] = clean_flags(tbl, value, group)
    if group is not None:
        n_gmiss = sum(1 for r in tbl.rows if _label(r.get(group)) == '')
        if n_gmiss:
            res['flags'].append('分组列 `%s` 缺失/空值 %d 行（未计入任何组）' % (group, n_gmiss))
    if log_transform:
        n_le = tbl.count_le(value, 0.0)
        if n_le:
            res['flags'].append('--log：存在 <=0 数据 %d 行，已剔除后对数转换' % n_le)
            tbl = tbl.filter_gt(value, 0.0)
        tbl = tbl.log_col(value)

    if paired and group is None:
        if pair_id:
            raise SystemExit('[错误] --paired 给了 --pair-id 但没有 --group：长表配对需要'
                             ' `--group`（两个水平列）+ `--pair-id`；宽表配对请去掉 --pair-id。')
        # 宽表配对：前两列数值列
        numcols = [c for c in tbl.cols if tbl.is_numeric(c)]
        if len(numcols) < 2:
            raise SystemExit('[错误] 配对模式需两列数值（宽表）或 --group 长表两水平 + --pair-id；'
                             '当前数值列 %s' % numcols)
        a, b = tbl.numeric_col(numcols[0]), tbl.numeric_col(numcols[1])
        keep = ~(np.isnan(a) | np.isnan(b))
        a, b = a[keep], b[keep]
        if a.size != b.size:
            raise SystemExit('[错误] 配对两列长度不一致（剔除缺失后 %d vs %d）' % (a.size, b.size))
        if a.size < 3:
            res['conclusion'] = '配对数 n=%d（<3）：不做推断统计（只描述）' % a.size
            res['groups'] = {numcols[0]: describe(a), numcols[1]: describe(b)}
            return res
        res['groups'] = {numcols[0]: describe(a), numcols[1]: describe(b)}
        res['outliers'] = {numcols[0]: outlier_candidates(a), numcols[1]: outlier_candidates(b)}
        res['n_pairs'] = int(a.size)
        return _two_group_block(res, a, b, paired=True, alpha=alpha, method=method, labels=numcols[:2])

    if paired and group is not None:
        if not pair_id:
            raise SystemExit('[错误] --paired + --group（长表）必须指定 --pair-id 指出配对列；'
                             '本工具拒绝静默降级（旧版此处静默 paired=False，把配对数据当独立样本，'
                             '方差被高估、p 被高估）。\n'
                             '       若不配对：去掉 --paired；若为宽表两列：去掉 --group；'
                             '长表请补 --pair-id <配对列名>。exit 1。')
        if not tbl.has(pair_id):
            raise SystemExit('[错误] --pair-id 列 `%s` 不在文件里；实际列名 = %s' % (pair_id, tbl.cols))
        return paired_long_table(res, tbl, value, group, pair_id, alpha, method)

    if group is None:
        x = tbl.numeric_col(value)
        if x.size == 0:
            raise SystemExit('[错误] 指标列 `%s` 无有效数值（请检查数据与 --value 列名）' % value)
        res['groups'] = {'全体': describe(x)}
        res['normality'] = {'全体': shapiro_evidence(x)}
        res['outliers'] = {'全体': outlier_candidates(x)}
        res['conclusion'] = '单组描述（未指定分组，不做组间推断）'
        return res

    labels = unique_in_order([lv for lv in tbl.text_col(group) if lv != ''])
    groups = {lv: np.asarray([tbl._safe_num(r.get(value)) for r in tbl.rows if _label(r.get(group)) == lv],
                             dtype=float) for lv in labels}
    res['groups_n'] = {k: int(v.size) for k, v in groups.items()}
    res['groups'] = {k: describe(v) for k, v in groups.items()}
    res['outliers'] = {k: outlier_candidates(v) for k, v in groups.items()}

    small = [k for k, v in groups.items() if v.size < 3]
    if small:
        res['conclusion'] = '存在 n<3 组（%s）：不做推断统计（只描述）' % ','.join(small)
        return res

    if len(groups) == 2:
        keys = list(groups.keys())
        a, b = groups[keys[0]], groups[keys[1]]
        return _two_group_block(res, a, b, paired=False, alpha=alpha, method=method, labels=keys)
    return _multi_group_block(res, groups, alpha=alpha, method=method)


def _two_group_block(res: dict, a: np.ndarray, b: np.ndarray, paired: bool,
                     alpha: float, method: str, labels=None) -> dict:
    labels = labels or ['组1', '组2']
    res['test_labels'] = labels
    dec = choose_two_group_test(a, b, paired, alpha, method)
    res['decision'] = dec
    chosen = dec['chosen']
    out: dict = dict(test=chosen)
    if chosen == 'mwu':
        st = stats.mannwhitneyu(a, b, alternative='two-sided')
        out.update(statistic=float(st.statistic), p=float(st.pvalue))
        out['effect'] = dict(rank_biserial_r=rank_biserial(a, b))
        if a.size == 3 and b.size == 3:
            out['p_floor_warning'] = ('n=3 非参数双侧精确 p 下限=2/C(6,3)=0.10；'
                                      '任何数据均不可能 p<0.05——禁止标注 */**，改报效应量+CI 或「呈趋势」')
        # 精确法复核
        try:
            pe = stats.mannwhitneyu(a, b, alternative='two-sided', method='exact').pvalue
            out['p_exact'] = float(pe)
        except Exception:
            pass
    elif chosen in ('ttest', 'welch'):
        st = stats.ttest_ind(a, b, equal_var=(chosen == 'ttest'))
        diff, lo, hi = mean_diff_ci(a, b, alpha, welch=(chosen == 'welch'))
        out.update(statistic=float(st.statistic), p=float(st.pvalue),
                   mean_diff=diff, mean_diff_ci95=[lo, hi])
        out['effect'] = cohens_d(a, b)
    elif chosen == 'ttest_rel':
        st = stats.ttest_rel(a, b)
        d = a - b
        out.update(statistic=float(st.statistic), p=float(st.pvalue),
                   mean_diff=float(np.mean(d)),
                   mean_diff_ci95=_paired_ci(d, alpha))
        out['effect'] = dict(cohens_dz=_paired_dz(a, b))
    elif chosen == 'wilcoxon':
        st = stats.wilcoxon(a, b)
        out.update(statistic=float(st.statistic), p=float(st.pvalue),
                   mean_diff=float(np.mean(a - b)))
        out['effect'] = dict(cohens_dz=_paired_dz(a, b))
    else:
        raise SystemExit('未知方法：%s' % chosen)
    res['result'] = out
    res['conclusion'] = _conclude(out, alpha)
    return res


def _paired_ci(d: np.ndarray, alpha: float) -> list:
    n = d.size
    se = np.std(d, ddof=1) / np.sqrt(n)
    tc = stats.t.ppf(1 - alpha / 2, n - 1)
    return [float(np.mean(d) - tc * se), float(np.mean(d) + tc * se)]


def _paired_dz(a: np.ndarray, b: np.ndarray):
    """配对效应量 Cohen's dz = mean(d)/sd(d)；差值全等（sd=0）→ None（不产生 inf/除零警告）。"""
    d = np.asarray(a, float) - np.asarray(b, float)
    if d.size < 2:
        return None
    sd = float(np.std(d, ddof=1))
    return float(np.mean(d) / sd) if sd > 0 else None


def _multi_group_block(res: dict, groups: dict, alpha: float, method: str) -> dict:
    keys = list(groups.keys())
    arrs = [groups[k] for k in keys]
    dec = choose_multi_group_test(arrs, method)
    res['decision'] = dec
    chosen = dec['chosen']
    out: dict = dict(test=chosen, labels=keys)
    if chosen == 'anova':
        st = stats.f_oneway(*arrs)
        # eta²
        allv = np.concatenate(arrs)
        ss_tot = np.sum((allv - allv.mean()) ** 2)
        ss_b = sum(len(g) * (g.mean() - allv.mean()) ** 2 for g in arrs)
        out.update(statistic=float(st.statistic), p=float(st.pvalue),
                   eta_squared=float(ss_b / ss_tot))
        try:
            tuk = stats.tukey_hsd(*arrs)
            pairs = []
            for i in range(len(arrs)):
                for j in range(i + 1, len(arrs)):
                    pairs.append(dict(pair=(keys[i], keys[j]), p=float(tuk.pvalue[i, j])))
            out['posthoc'] = dict(test='tukey_hsd', pairs=pairs)
        except Exception as e:  # pragma: no cover
            out['posthoc'] = dict(test='tukey_hsd', error=str(e))
    elif chosen == 'kruskal':
        st = stats.kruskal(*arrs)
        out.update(statistic=float(st.statistic), p=float(st.pvalue),
                   epsilon_squared=eta_squared_kw(arrs))
        pairs, pvals = [], []
        for i in range(len(arrs)):
            for j in range(i + 1, len(arrs)):
                p = stats.mannwhitneyu(arrs[i], arrs[j], alternative='two-sided').pvalue
                pairs.append((keys[i], keys[j]))
                pvals.append(float(p))
        adj = holm_adjust(pvals)
        out['posthoc'] = dict(test='pairwise_mwu_holm',
                              note='成对 Mann-Whitney + Holm 校正（scikit-posthocs 不可用时的等效替代口径；Dunn 版可在其可用环境复跑）',
                              pairs=[dict(pair=p, p_raw=pr, p_holm=pa) for p, pr, pa in zip(pairs, pvals, adj)])
    else:
        raise SystemExit('未知方法：%s' % chosen)
    res['result'] = out
    res['conclusion'] = _conclude(out, alpha)
    return res


def _conclude(out: dict, alpha: float) -> str:
    p = out.get('p')
    if p is None:
        return '无 p 值'
    if p < alpha:
        txt = '差异有统计学意义（p=%.4g < %.2g）' % (p, alpha)
        if out.get('p_floor_warning'):
            txt = '【受 n=3 下限约束】' + txt + '——但见 p_floor_warning，禁止标注 */**'
        return txt
    if out.get('test') == 'ttest_rel' and out.get('mean_diff') is not None and out.get('mean_diff') == 0.0:
        return '未达统计显著（p=%.4g >= %.2g）；配对差全为 0（无效应）' % (p, alpha)
    return '未达统计显著（p=%.4g >= %.2g）；报告效应量与 CI，措辞「呈趋势」' % (p, alpha)


# ---------------------------------------------------------------- 报告渲染
def report_md(res: dict) -> str:
    L = []
    A = L.append
    A('# 统计分析报告（stats_pipeline %s）' % res['version'])
    A('')
    A('> 口径：方法预注册（`workflows/08` 铁律）；本报告为**复核证据**，不得用于事后再选择检验。')
    A('')
    A('## 0. 输入与参数')
    A('')
    pair_note = ''
    if res.get('paired'):
        pair_note = '（--pair-id `%s`，配对数 %s）' % (res.get('pair_id') or '—', res.get('n_pairs', '—'))
    A('- 指标列：`%s`｜分组列：`%s`｜配对：%s%s｜对数转换：%s｜alpha=%.3g' %
      (res['value'], res['group'], res['paired'], pair_note, res['log_transform'], res['alpha']))
    if res.get('flags'):
        A('- 数据质量标记：')
        for f in res['flags']:
            A('  - %s' % f)
    A('')
    A('## 1. 描述统计（mean±SD / median[IQR]）')
    A('')
    A('| 组 | n | mean | SD | median | IQR | min | max | CV |')
    A('|---|---|---|---|---|---|---|---|---|')
    for k, d in res.get('groups', {}).items():
        A('| %s | %d | %s | %s | %s | %s | %s | %s | %s |' % (
            k, d['n'],
            _f(d['mean']), _f(d['sd']), _f(d['median']),
            '%s–%s' % (_f(d['q1']), _f(d['q3'])), _f(d['min']), _f(d['max']),
            _f(d['cv'])))
    A('')
    if res.get('outliers'):
        any_o = any(v for v in res['outliers'].values())
        A('- 异常值候选（|z|>3，仅标记不删除）：%s' % ('见下' if any_o else '无'))
        for k, v in res['outliers'].items():
            for o in v:
                A('  - %s[%d] = %s (z=%.2f)——处理需说明理由（Grubbs/ROUT）' % (k, o['index'], _f(o['value']), o['z']))
    A('')
    A('## 2. 正态与方差证据')
    A('')
    dec = res.get('decision', {})
    if 'normality' in dec and isinstance(dec['normality'], list):
        A('| 组 | Shapiro W | p | 判定 |')
        A('|---|---|---|---|')
        for k, s in zip(res['result'].get('labels', []), dec['normality']):
            A('| %s | %s | %s | %s |' % (k, _f(s.get('W')), _f(s.get('p')), s.get('note', '')))
    elif 'normality_x' in dec:
        A('| 组 | Shapiro W | p | 判定 |')
        A('|---|---|---|---|')
        for k, s in zip(res.get('test_labels', ['组1', '组2']), [dec['normality_x'], dec['normality_y']]):
            A('| %s | %s | %s | %s |' % (k, _f(s.get('W')), _f(s.get('p')), s.get('note', '')))
        if dec.get('normality_diff'):
            s = dec['normality_diff']
            A('| 差值(配对) | %s | %s | %s |' % (_f(s.get('W')), _f(s.get('p')), s.get('note', '')))
    if dec.get('levene'):
        A('')
        A('- Levene 方差齐性：p=%s（%s）' % (_f(dec['levene'].get('p')), dec['levene'].get('note', '')))
    A('')
    A('## 3. 检验树决策与主检验')
    A('')
    A('- 决策依据：%s' % dec.get('reason', '（单组/描述）'))
    r = res.get('result', {})
    if r:
        A('- 主检验：**%s**｜统计量 %s｜p=%s' % (r.get('test'), _f(r.get('statistic')), _f(r.get('p'))))
        if 'mean_diff' in r:
            A('- 均值差 = %s（95%%CI %s）%s' % (_f(r.get('mean_diff')), _f(r.get('mean_diff_ci95')),
                                                  '｜配对差 = 逐对相减（水平1 − 水平2）' if res.get('paired') else ''))
        eff = r.get('effect') or {}
        if eff:
            A('- 效应量：' + '；'.join('%s=%s' % (k, _f(v)) for k, v in eff.items()))
        if r.get('eta_squared') is not None:
            A('- η² = %s' % _f(r['eta_squared']))
        if r.get('epsilon_squared') is not None:
            A('- ε²(KW) = %s' % _f(r['epsilon_squared']))
        if r.get('p_floor_warning'):
            A('- ⚠ **p 下限提示**：%s' % r['p_floor_warning'])
        ph = r.get('posthoc')
        if ph:
            A('')
            A('- 事后检验（%s）%s' % (ph.get('test'), ('：' + ph.get('note', '')) if ph.get('note') else ''))
            if ph.get('pairs'):
                A('')
                A('| 对 | p | 校正后 p |')
                A('|---|---|---|')
                for pr in ph['pairs']:
                    if 'p_holm' in pr:
                        A('| %s vs %s | %s | %s |' % (pr['pair'][0], pr['pair'][1], _f(pr['p_raw']), _f(pr['p_holm'])))
                    else:
                        A('| %s vs %s | %s | — |' % (pr['pair'][0], pr['pair'][1], _f(pr['p'])))
    A('')
    A('## 4. 结论（含纪律口径）')
    A('')
    A('- %s' % res.get('conclusion', ''))
    A('- 多重比较已校正（Tukey / Holm）；误差棒用 SD；图件走 V-M6（本报告不含图）。')
    if res.get('paired'):
        A('- 配对口径：按 `--pair-id` 对齐后**逐对相减**做配对检验；配对数据一律不得按独立样本处理。')
    A('')
    A('---')
    A('*由 stats_pipeline 生成（本机工具；复跑到 `tools/stats_pipeline.py`）。*')
    return '\n'.join(L)


def _f(v):
    if v is None:
        return '—'
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(_f(x) for x in v) + ']'
    if isinstance(v, float):
        return '%.4g' % v
    return str(v)


# ---------------------------------------------------------------- 自测
def selftest() -> int:
    ok = True
    rng = np.random.default_rng(20260921)

    def check(name, cond, extra=''):
        nonlocal ok
        print('[%s] %s %s' % ('PASS' if cond else 'FAIL', name, extra))
        ok = ok and bool(cond)

    def base_res(paired=False):
        return dict(version=VERSION, alpha=.05, value='x', group='g', paired=paired,
                    pair_id=None, log_transform=False, method_forced='auto', flags=[])

    # T1 两正态组（δ=1.0σ）→ 独立 t/Welch，p<0.01，g 接近 1
    a = rng.normal(0, 1, 16)
    b = rng.normal(1.0, 1, 16)
    r1 = _two_group_block(base_res(), a, b, False, .05, 'auto')
    check('T1 正态路径选定 t 系', r1['result']['test'] in ('ttest', 'welch'), r1['result']['test'])
    check('T1 p<0.01', r1['result']['p'] < 0.01, 'p=%.3g' % r1['result']['p'])
    check('T1 |g|≈1 (±0.35)', abs(abs(r1['result']['effect']['hedges_g']) - 1.0) < 0.35,
          'g=%.3f' % r1['result']['effect']['hedges_g'])

    # T2 非正态（指数分布）→ MWU
    a2 = rng.exponential(1.0, 18)
    b2 = rng.exponential(1.0, 18) + 1.5
    r2 = _two_group_block(base_res(), a2, b2, False, .05, 'auto')
    check('T2 非正态路径选定 mwu', r2['result']['test'] == 'mwu', r2['result']['test'])
    check('T2 p<0.01', r2['result']['p'] < 0.01, 'p=%.3g' % r2['result']['p'])
    check('T2 |r_rb|>0.5', abs(r2['result']['effect']['rank_biserial_r']) > 0.5,
          'r=%.3f' % r2['result']['effect']['rank_biserial_r'])

    # T3 三组 ANOVA + Tukey
    g1 = rng.normal(0, 1, 12)
    g2 = rng.normal(0.6, 1, 12)
    g3 = rng.normal(1.2, 1, 12)
    r3 = _multi_group_block(base_res(), {'A': g1, 'B': g2, 'C': g3}, .05, 'auto')
    check('T3 选定 anova', r3['result']['test'] == 'anova', r3['result']['test'])
    check('T3 p<0.05', r3['result']['p'] < 0.05, 'p=%.3g' % r3['result']['p'])
    check('T3 η²∈(0.05,0.7)', 0.05 < r3['result']['eta_squared'] < 0.7, 'η²=%.3f' % r3['result']['eta_squared'])
    min_p = min(pr['p'] for pr in r3['result']['posthoc']['pairs'])
    check('T3 Tukey 至少一对 p<0.05', min_p < 0.05, 'min_p=%.3g' % min_p)

    # T4 配对 t（随机：效应量 d≈1.2，种子固定 → 稳健 p<0.01）
    dd = rng.normal(1.2, 1, 22)
    a4, b4 = dd + rng.normal(0, .5, 22), rng.normal(0, .5, 22)
    r4 = _two_group_block(base_res(paired=True), a4, b4, True, .05, 'auto')
    check('T4 配对 t', r4['result']['test'] == 'ttest_rel', r4['result']['test'])
    check('T4 p<0.05', r4['result']['p'] < 0.05, 'p=%.3g' % r4['result']['p'])

    # T5 n=3 非参数下限护栏
    a5, b5 = np.array([1., 2., 3.]), np.array([10., 20., 30.])
    r5 = _two_group_block(base_res(), a5, b5, False, .05, 'mwu')
    check('T5 n=3 触发下限提示', 'p_floor_warning' in r5['result'])
    check('T5 p>=0.099', r5['result']['p'] >= 0.099, 'p=%.3g' % r5['result']['p'])

    # T6 n<3 拒做推断
    tbl6 = Table.from_mapping({'v': [1., 2., 3., 4.], 'g': ['A', 'A', 'B', 'B']})
    r6 = run_analysis(tbl6, 'v', 'g', False, .05, 'auto', False)
    check('T6 n<3 只描述', 'n<3' in r6.get('conclusion', ''), r6.get('conclusion', ''))

    # T7 Holm 校正正确性（已知 p 列表；Holm 需单调化 running max）
    adj = holm_adjust([0.01, 0.04, 0.03])
    check('T7 Holm 校验', abs(adj[0] - 0.03) < 1e-9 and abs(adj[1] - 0.06) < 1e-9 and abs(adj[2] - 0.06) < 1e-9,
          str(adj))

    # T8 配对 t known-answer（闭式：t = mean(d)/(sd(d)/√n)，p = 2·sf(|t|, n−1)；另核 mean_diff / dz）
    d_known = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    a8, b8 = 10.0 + d_known, np.full(5, 10.0)
    r8 = _two_group_block(base_res(paired=True), a8, b8, True, .05, 'ttest_rel')
    md = float(np.mean(d_known))
    sd = float(np.std(d_known, ddof=1))
    t_exp = md / (sd / np.sqrt(d_known.size))
    p_exp = float(2.0 * stats.t.sf(abs(t_exp), d_known.size - 1))
    check('T8 配对 t 统计量 = 闭式 t = mean(d)/(sd/√n)',
          abs(r8['result']['statistic'] - t_exp) <= 1e-9 * abs(t_exp),
          '实测 = %.10f｜闭式 = %.10f' % (r8['result']['statistic'], t_exp))
    check('T8 配对 p = 闭式 2·sf(|t|,4)',
          abs(r8['result']['p'] - p_exp) <= 1e-12,
          '实测 = %.10f｜闭式 = %.10f' % (r8['result']['p'], p_exp))
    check('T8 配对 mean_diff = 3.0', abs(r8['result']['mean_diff'] - 3.0) <= 1e-12,
          '实测 = %.10g' % r8['result']['mean_diff'])
    check('T8 配对 dz = mean(d)/sd(d)', abs(r8['result']['effect']['cohens_dz'] - md / sd) <= 1e-9,
          '实测 = %.10f｜闭式 = %.10f' % (r8['result']['effect']['cohens_dz'], md / sd))

    # T9 长表配对（--pair-id）：必须走配对检验，且差值与逐对差一致
    va = [10.2, 11.4, 9.8, 12.1, 10.9, 11.7]
    vb = [8.9, 9.7, 8.4, 10.2, 9.1, 9.9]
    rows9 = []
    for i, (x, y) in enumerate(zip(va, vb), 1):
        rows9.append({'样本': 'P%02d' % i, '组别': '处理', '值': x})
        rows9.append({'样本': 'P%02d' % i, '组别': '对照', '值': y})
    tbl9 = Table.from_rows(rows9)
    r9 = run_analysis(tbl9, '值', '组别', True, .05, 'auto', False, pair_id='样本')
    check('T9 长表配对选定配对检验（非独立样本）',
          r9['result']['test'] in ('ttest_rel', 'wilcoxon'), r9['result']['test'])
    check('T9 配对数 n = 6', r9.get('n_pairs') == 6, 'n_pairs=%s' % r9.get('n_pairs'))
    check('T9 配对差 = 逐对差闭式均值', abs(r9['result']['mean_diff'] - float(np.mean(np.array(va) - np.array(vb)))) <= 1e-12,
          '实测 = %.10f｜闭式 = %.10f' % (r9['result']['mean_diff'], float(np.mean(np.array(va) - np.array(vb)))))
    check('T9 决策记录为配对设计', '配对' in r9['decision']['reason'], r9['decision']['reason'])

    # T10 反例：长表配对缺 --pair-id 必须报错（旧版静默降级 paired=False）
    caught, msg = False, ''
    try:
        run_analysis(tbl9, '值', '组别', True, .05, 'auto', False, pair_id=None)
    except SystemExit as exc:
        caught, msg = True, str(exc)
    check('T10 长表配对缺 --pair-id → 报错退出（禁静默降级）',
          caught and '--pair-id' in msg, (msg.splitlines()[0] if msg else '未拦截（危险：静默降级）'))

    # T11 反例：配对标识不成对 → 报错退出
    rows11 = list(rows9) + [{'样本': 'P07', '组别': '处理', '值': 11.0}]
    caught2, msg2 = False, ''
    try:
        run_analysis(Table.from_rows(rows11), '值', '组别', True, .05, 'auto', False, pair_id='样本')
    except SystemExit as exc:
        caught2, msg2 = True, str(exc)
    check('T11 配对标识不成对 → 报错退出', caught2 and '不成对' in msg2,
          (msg2.splitlines()[0] if msg2 else '未拦截'))

    # T12 反例：--paired 给了 --pair-id 但没给 --group → 报错退出
    caught3, msg3 = False, ''
    try:
        run_analysis(tbl9, '值', None, True, .05, 'auto', False, pair_id='样本')
    except SystemExit as exc:
        caught3, msg3 = True, str(exc)
    check('T12 --pair-id 但缺 --group → 报错退出', caught3 and '--group' in msg3,
          (msg3.splitlines()[0] if msg3 else '未拦截'))

    # T13 宽表配对（无 --group、无 --pair-id）仍可用（CLI 兼容）
    tbl13 = Table.from_mapping({'前': [1.0, 2.0, 3.0, 4.5], '后': [0.5, 1.2, 2.8, 3.5]})
    r13 = run_analysis(tbl13, '前', None, True, .05, 'auto', False)
    check('T13 宽表配对可用且判为配对检验', r13['result']['test'] in ('ttest_rel', 'wilcoxon'),
          r13['result']['test'])
    check('T13 宽表配对差值均值 = 逐对差闭式',
          abs(r13['result']['mean_diff'] - float(np.mean(np.array([1.0, 2.0, 3.0, 4.5]) - np.array([0.5, 1.2, 2.8, 3.5])))) <= 1e-12,
          '实测 = %.10f' % r13['result']['mean_diff'])

    print('SELFTEST', 'OK — 全部断言通过' if ok else 'FAILED')
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Vesi 统计管线（stats_pipeline）')
    ap.add_argument('file', nargs='?', help='CSV/Excel 数据文件')
    ap.add_argument('--value', help='指标列名')
    ap.add_argument('--group', help='分组列名（可省=单组描述；配对长表需正好 2 个水平）')
    ap.add_argument('--paired', action='store_true',
                    help='配对设计（宽表两列；或长表 + --pair-id）')
    ap.add_argument('--pair-id', dest='pair_id',
                    help='配对标识列名（--paired 长表必给；缺 → 报错退出，不静默降级）')
    ap.add_argument('--log', action='store_true', help='对数转换后分析（PK 参数比较）')
    ap.add_argument('--method', default='auto', help='auto|ttest|welch|mwu|anova|kruskal|ttest_rel|wilcoxon')
    ap.add_argument('--alpha', type=float, default=ALPHA_DEFAULT)
    ap.add_argument('--out', help='报告输出路径（默认 stdout）')
    ap.add_argument('--json', action='store_true', help='同时输出 JSON 摘要到 stdout')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.file or not a.value:
        ap.error('需要 --file 与 --value（或 --selftest）')
    if a.paired and a.pair_id and not a.group:
        raise SystemExit('[错误] --paired --pair-id 还需要 --group（长表两个水平列）：'
                         'exit 1（不静默降级；宽表配对请去掉 --pair-id）。')

    df = load_data(a.file)
    df.require([a.value, a.group, a.pair_id])
    res = run_analysis(df, a.value, a.group, a.paired, a.alpha, a.method, a.log, pair_id=a.pair_id)
    md = report_md(res)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(md)
        print('[saved] %s' % a.out)
    else:
        print(md)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
