#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke_chain —— 全链技术冒烟（V-U39 · 底座 T1）

适用场景 / Purpose
    用**合成数据**把 M3 记录 → M4 统计 → M5 PK/释放/房室 → M6 图件 的管道整跑一遍，
    同时验证「技术连通性」与「**数值正确性**」。不评分、不进锚、不触碰任何个人材料
    （合成数据全部由脚本自造，真值解析可算）。

黄金断言 / Golden assertions（F13 · 附录 C.3 —— 本文件的核心）
    旧版只做字符串断言（`'AUC' in txt`），任何**数值错误**都能蒙混过关。本版对合成数据
    的已知真值做**数值区间断言**（`abs(实测 − 真值) <= 容差`），容差全部写在断言表里：

    | 编号 | 断言 | 真值来源 | 容差 |
    |---|---|---|---|
    | G1 | 统计管线组间均差 | 组均值之差（解析：50 − 38 = 12） | 绝对 1e-6 |
    | G1 | Hedges g | d·(1 − 3/(4·10−9))，d = 12/√40 | 绝对 0.005 |
    | G1 | 检验 p | 差异显著 | p < 0.05 |
    | G2 | 逐个体 AUC0-inf | C0_i·s_i/k（一室 IV 解析） | 相对 4%（含 2% 测量噪声） |
    | G2 | 全局均 AUC0-inf | 同上，跨 2 组 × 3 个体取均值 | 相对 2% |
    | G2 | 逐个体 t1/2 | ln2/k | 相对 0.8% |
    | G2 | 全局均 MRT | 1/k | 相对 5%（含外推项） |
    | G3 | 无 --subject 多样本 | 必须被拦截（rc≠0，未静默拼接） | 反向断言 |
    | G4 | 房室拟合 A/α/B/β | 合成二室 IV 真值（80, 1.2, 20, 0.08） | 相对 5% |

    任一断言不成立 → 该阶段 FAIL → **整体判定 FAIL 且 exit 1**（不做「看起来跑通了」的判定）。

输入 / Input
    无（脚本自生成合成数据到 `_smoke_out/`）。
输出 / Output
    `_smoke_out/smoke_chain_report.md`（每阶段 PASS/FAIL/SKIP + 黄金断言表：实测/真值/容差）；
    控制台同款状态表；exit 0 = 无 FAIL（SKIP = 未执行项，写明 [降级] 原因，不判 FAIL）。

依赖 / Deps
    numpy（自造合成数据）；被调工具各自管自己的依赖。缺件/缺依赖 → SKIP + [降级] 并写明，
    **不假装成功**：SKIP 的阶段不计入 PASS。

用法 / Usage
    python smoke_chain.py [--keep]     # --keep 保留合成 CSV 供检查
    python smoke_chain.py --selftest   # 别名：完整跑链即自测（无 FAIL 则 rc=0）
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSION = 'v1.1 (2026-09-22)'
RESULTS: list = []      # [(阶段, 状态, 详情)]
GOLDS: list = []        # 黄金断言明细：dict(stage, name, got, truth, tol, ok, unit, note)

# ---------------------------------------------------------------- 合成数据真值参数
PK_K = 0.5                                    # 消除速率常数（h^-1）：t1/2=1.386294 h，MRT=2.0 h
PK_GROUPS = (('脂质体', 100.0), ('参比制剂', 40.0))   # (组别, C0)
PK_SCALES = (1.0, 0.9, 1.1)                   # 个体间变异（解析已知，不用随机数）
PK_NOISE = 0.02                               # 逐点测量噪声（相对 SD，固定种子）
PK_T = (0.083, 0.25, 0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 24.0)
SEED_REC = 20260921
EP_A = (42.0, 46.0, 50.0, 54.0, 58.0)         # 组 A：均值 50，样本 SD = √40（解析）
EP_B = (30.0, 34.0, 38.0, 42.0, 46.0)         # 组 B：均值 38，样本 SD = √40（解析）
EP_DIFF_TRUTH = 12.0                          # 50 − 38（解析，精确）
EP_SD_TRUTH = math.sqrt(40.0)                 # 样本 SD(ddof=1) = √((8²+4²+0+4²+8²)/4)
EP_D_TRUTH = EP_DIFF_TRUTH / EP_SD_TRUTH      # Cohen's d 解析值 = 12/√40
EP_G_TRUTH = EP_D_TRUTH * (1.0 - 3.0 / (4 * 10 - 9))   # Hedges 小样本校正（n1+n2=10）
C2_T = (0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 20.0, 24.0)
C2_TRUTH = (80.0, 1.2, 20.0, 0.08)            # 二室 IV：A, α, B, β
C2_NAMES = ('A', 'alpha', 'B', 'beta')
C2_TOL = 0.05                                 # 参数回收相对容差 5%

# ---------------------------------------------------------------- 基础
def run_tool(args: list, cwd=None) -> tuple:
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=cwd or str(HERE))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def stage(name: str, status: str, detail: str):
    RESULTS.append((name, status, detail))
    print('[%s] %s — %s' % (status, name, detail))


def gold(stage_name: str, name: str, got, truth, tol_rel=None, tol_abs=None,
         unit: str = '', note: str = '') -> bool:
    """数值区间断言：abs(实测 − 真值) <= 容差（相对容差优先，容差随断言登记）。"""
    got, truth = float(got), float(truth)
    if tol_rel is not None:
        tol = tol_rel * abs(truth)
        tol_txt = '相对 %.3g%%' % (tol_rel * 100.0)
    else:
        tol = float(tol_abs if tol_abs is not None else 0.0)
        tol_txt = '绝对 %g' % tol
    ok = bool(abs(got - truth) <= tol)
    GOLDS.append(dict(stage=stage_name, name=name, got=got, truth=truth, tol=tol_txt,
                      ok=ok, unit=unit, note=note))
    return ok


def golds_ok(stage_name: str) -> bool:
    """该阶段的黄金断言是否全绿（无断言则视为 False —— 必须真跑过断言）。"""
    items = [g for g in GOLDS if g['stage'] == stage_name]
    return bool(items) and all(g['ok'] for g in items)


def parse_json_block(text: str):
    """取 stdout 里第一个可解析的 JSON 对象（容忍前置的 [saved] 等日志行）。"""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith('{'):
            try:
                return json.loads('\n'.join(lines[i:]))
            except Exception:
                continue
    return None


def is_dep_missing(text: str) -> bool:
    """子进程是否因缺依赖挂掉（→ [降级] SKIP，不判 FAIL）。"""
    return ('ModuleNotFoundError' in text) or ('ImportError' in text)


# ---------------------------------------------------------------- M3 合成数据
def synth_records(outdir: Path) -> tuple:
    """M3：合成 PK 记录（两组 × 3 个体；含个体列）——一室 IV，真值解析可知。"""
    import numpy as np
    rng = np.random.default_rng(SEED_REC)
    rows = []
    for grp, c0 in PK_GROUPS:
        for j, s in enumerate(PK_SCALES):
            subj = 'R%02d' % (j + 1)
            for ti in PK_T:
                c = c0 * s * math.exp(-PK_K * ti) * float(rng.normal(1.0, PK_NOISE))
                rows.append({'组别': grp, '个体': subj, '时间h': ('%g' % ti),
                             '浓度μg_mL': ('%.8g' % max(c, 0.0))})
    p = outdir / 'synth_records.csv'
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['组别', '个体', '时间h', '浓度μg_mL'])
        w.writeheader()
        w.writerows(rows)
    return p, rows


def synth_endpoint(outdir: Path) -> Path:
    """M4 用：合成终点指标（两组各 n=5，逐点定值 → 均差与样本 SD 解析可算）。"""
    rows = [{'组别': '脂质体', 'AUC': ('%g' % v)} for v in EP_A]
    rows += [{'组别': '参比制剂', 'AUC': ('%g' % v)} for v in EP_B]
    p = outdir / 'synth_endpoint.csv'
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['组别', 'AUC'])
        w.writeheader()
        w.writerows(rows)
    return p


def synth_two_comp(outdir: Path) -> Path:
    """M5d 用：合成二室 IV 数据（无噪声 → 参数回收容差可收紧到 5%）。"""
    A, alpha, B, beta = C2_TRUTH
    rows = [{'时间': ('%g' % t), '浓度': ('%.8g' % (A * math.exp(-alpha * t) + B * math.exp(-beta * t)))}
            for t in C2_T]
    p = outdir / 'synth_two_comp.csv'
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['时间', '浓度'])
        w.writeheader()
        w.writerows(rows)
    return p


# ---------------------------------------------------------------- 各阶段
def stage_m3(outdir: Path):
    rec, rows = synth_records(outdir)
    n_subj = len(PK_GROUPS) * len(PK_SCALES)
    stage('M3 合成记录集', 'PASS', 'synth_records.csv（%d 行｜%d 组 × %d 个体｜真值 k=%.3g h^-1）'
          % (len(rows), len(PK_GROUPS), len(PK_SCALES), PK_K))
    return rec


def stage_m4(outdir: Path):
    """M4 统计管线 + G1 黄金断言（均差/效应量/p 对已知真值）。"""
    tag = 'M4 统计管线（黄金断言）'
    sp = HERE / 'stats_pipeline.py'
    if not sp.exists():
        stage(tag, 'SKIP', 'stats_pipeline.py 不在（未落盘）')
        return
    ep = synth_endpoint(outdir)
    report = outdir / 'synth_report.md'
    rc, txt = run_tool([str(sp), str(ep), '--value', 'AUC', '--group', '组别',
                        '--out', str(report), '--json'])
    data = parse_json_block(txt)
    if rc != 0 or data is None:
        if is_dep_missing(txt):
            stage(tag, 'SKIP', '[降级] 统计管线缺依赖（%s）' % txt.strip().splitlines()[-1][:90])
            return
        stage(tag, 'FAIL', 'rc=%d，未取到 JSON（%s）' % (rc, txt.strip().splitlines()[-1][:90]))
        return
    res = (data.get('result') or {})
    ok_test = res.get('test') in ('ttest', 'welch')
    ok_diff = gold(tag, '组间均差（脂质体 − 参比制剂）', res.get('mean_diff', float('nan')),
                   EP_DIFF_TRUTH, tol_abs=1e-6, note='真值 = 50 − 38（逐点定值，精确可算）')
    ok_g = gold(tag, 'Hedges g', (res.get('effect') or {}).get('hedges_g', float('nan')),
                EP_G_TRUTH, tol_abs=0.005, note='d = 12/√40；g = d·(1 − 3/31)')
    p = res.get('p', float('nan'))
    ok_p = gold(tag, '组间检验 p', 1.0 if p < 0.05 else 0.0, 1.0, tol_abs=0.0,
                note='真值判定：p < 0.05（实测 p=%s）' % ('%.4g' % p))
    report_ok = report.exists() and ('检验树决策' in report.read_text(encoding='utf-8'))
    ok = ok_test and ok_diff and ok_g and ok_p and report_ok
    stage(tag, 'PASS' if ok else 'FAIL',
          'rc=%d｜主检验=%s（t 系=%s）｜均值差=%.6g（真值 %.6g）｜g=%.4g（真值 %.4g）｜p=%s｜报告三证节齐=%s'
          % (rc, res.get('test'), ok_test, res.get('mean_diff', float('nan')), EP_DIFF_TRUTH,
             (res.get('effect') or {}).get('hedges_g', float('nan')), EP_G_TRUTH, '%.4g' % p, report_ok))


def stage_m5(rec: Path):
    """M5 NCA 个体维 + G2 黄金断言（逐个体 AUC0-inf / t1/2 / MRT 对解析真值）。"""
    tag = 'M5 NCA 个体维（黄金断言）'
    nca = HERE / 'nca.py'
    if not nca.exists():
        stage(tag, 'SKIP', 'nca.py 不在（未落盘）')
        return
    rc, txt = run_tool([str(nca), '--file', str(rec), '--time', '时间h', '--conc', '浓度μg_mL',
                        '--group', '组别', '--subject', '个体', '--json'])
    data = parse_json_block(txt)
    if rc != 0 or data is None:
        if is_dep_missing(txt):
            stage(tag, 'SKIP', '[降级] nca 缺依赖（%s）' % txt.strip().splitlines()[-1][:90])
            return
        stage(tag, 'FAIL', 'rc=%d，未取到 JSON（%s）' % (rc, txt.strip().splitlines()[-1][:90]))
        return
    truth_by_subject = dict(PK_GROUPS)          # 组别 → C0
    curves, n_wrong = [], 0
    for grp in data.get('results', []):
        c0 = truth_by_subject.get(grp['group'])
        for s in grp.get('subjects', []):
            idx = int(str(s['subject']).lstrip('R')) - 1 if str(s['subject']).startswith('R') else -1
            s_i = PK_SCALES[idx] if 0 <= idx < len(PK_SCALES) else None
            if c0 is None or s_i is None:
                n_wrong += 1
                continue
            truth_auc = c0 * s_i / PK_K
            truth_half = float(math.log(2.0)) / PK_K
            nca_res = s['nca']
            curves.append((grp['group'], s['subject'], nca_res, truth_auc))
            if not gold(tag, 'AUC0-inf 回收（%s/%s）' % (grp['group'], s['subject']), nca_res['auc0_inf'],
                        truth_auc, tol_rel=0.04, unit='浓度·h',
                        note='真值 = C0·s_i/k；容差含 2% 测量噪声与梯形离散化'):
                n_wrong += 1
            if not gold(tag, 't1/2 回收（%s/%s）' % (grp['group'], s['subject']), nca_res['t_half'],
                        truth_half, tol_rel=0.008, unit='h', note='真值 = ln2/k'):
                n_wrong += 1
    n_curve = len(curves)
    mean_got_v = sum(c[2]['auc0_inf'] for c in curves) / n_curve if n_curve else float('nan')
    mean_truth_v = sum(c[3] for c in curves) / n_curve if n_curve else float('nan')
    mrt_got = sum(c[2]['mrt'] for c in curves) / n_curve if n_curve else float('nan')
    ok_mean = gold(tag, '全局均 AUC0-inf（跨 2 组 × 3 个体）', mean_got_v, mean_truth_v, tol_rel=0.02,
                   unit='浓度·h', note='真值 = mean(C0·s_i/k)')
    ok_mrt = gold(tag, '全局均 MRT0-inf', mrt_got, 1.0 / PK_K, tol_rel=0.05,
                  unit='h', note='真值 = 1/k（含末段外推项）')
    ok = (n_curve == len(PK_GROUPS) * len(PK_SCALES)) and (n_wrong == 0) and ok_mean and ok_mrt
    stage(tag, 'PASS' if ok else 'FAIL',
          'rc=%d｜曲线数=%d（期望 %d）｜AUC0-inf 均值=%.6g（真值 %.6g）｜MRT 均值=%.4g（真值 %.4g）｜超容差断言=%d'
          % (rc, n_curve, len(PK_GROUPS) * len(PK_SCALES), mean_got_v, mean_truth_v,
             mrt_got, 1.0 / PK_K, n_wrong))


def _mean_param(data: dict, key: str) -> float:
    """跨所有曲线取某参数均值（备用；用于对真值做整体回收断言）。"""
    vals = [s['nca'][key] for grp in data.get('results', []) for s in grp.get('subjects', [])
            if s['nca'].get(key) is not None]
    return sum(vals) / len(vals) if vals else float('nan')


def stage_m5_neg(rec: Path):
    """M5b 反例（G3）：多样本不给 --subject 必须被拦截 —— 旧版会静默缝成单曲线。"""
    tag = 'M5b 反例：无 --subject 多样本须被拦截'
    nca = HERE / 'nca.py'
    if not nca.exists():
        stage(tag, 'SKIP', 'nca.py 不在（未落盘）')
        return
    rc, txt = run_tool([str(nca), '--file', str(rec), '--time', '时间h', '--conc', '浓度μg_mL',
                        '--group', '组别'])
    blocked = (rc != 0) and ('--subject' in txt)
    gold(tag, '无 --subject 多样本 → 拦截（1=拦截成功）', 1.0 if blocked else 0.0, 1.0, tol_abs=0.0,
         note='旧版行为：静默按时间排序缝成单曲线（np.diff(t)=0），AUC ≈ 真值/3')
    stage(tag, 'PASS' if blocked else 'FAIL',
          'rc=%d（期望 ≠0）｜错误信息含 --subject=%s｜尾部：%s'
          % (rc, '--subject' in txt, (txt.strip().splitlines() or [''])[0][:90]))


def stage_release():
    """M5c 释放拟合自测（缺件 → SKIP）。"""
    tag = 'M5c 释放拟合自测'
    rf = HERE / 'release_fit.py'
    if not rf.exists():
        stage(tag, 'SKIP', 'release_fit.py 不在（未落盘）')
        return
    rc, txt = run_tool([str(rf), '--selftest'])
    if rc == 0:
        stage(tag, 'PASS', 'rc=0')
    elif is_dep_missing(txt):
        stage(tag, 'SKIP', '[降级] 缺依赖：%s' % txt.strip().splitlines()[-1][:90])
    else:
        stage(tag, 'FAIL', 'rc=%d｜%s' % (rc, txt.strip().splitlines()[-1][:90]))


def stage_compartment(outdir: Path):
    """M5d 房室拟合：① --selftest 接入链（缺件 SKIP）② 合成二室数据参数回收黄金断言（G4）。"""
    tag_self = 'M5d 房室拟合自测（--selftest）'
    tag_gold = 'M5e 房室拟合参数回收（黄金断言）'
    cf = HERE / 'compartment_fit.py'
    if not cf.exists():
        stage(tag_self, 'SKIP', 'compartment_fit.py 不在（未落盘）——F13 清单件，落盘后本阶段自动生效')
        stage(tag_gold, 'SKIP', 'compartment_fit.py 不在（未落盘）')
        return
    rc, txt = run_tool([str(cf), '--selftest'])
    if rc == 0:
        stage(tag_self, 'PASS', 'rc=0（内置 known-answer 全绿）')
    elif is_dep_missing(txt):
        stage(tag_self, 'SKIP', '[降级] 缺依赖：%s' % txt.strip().splitlines()[-1][:90])
    else:
        stage(tag_self, 'FAIL', 'rc=%d｜%s' % (rc, txt.strip().splitlines()[-1][:90]))

    csv2 = synth_two_comp(outdir)
    rc2, txt2 = run_tool([str(cf), '--file', str(csv2), '--time', '时间', '--conc', '浓度',
                          '--model', '2c_iv', '--json'])
    data = parse_json_block(txt2)
    if rc2 != 0 or data is None:
        if is_dep_missing(txt2):
            stage(tag_gold, 'SKIP', '[降级] 缺依赖：%s' % txt2.strip().splitlines()[-1][:90])
            return
        stage(tag_gold, 'FAIL', 'rc=%d，未取到 JSON（%s）' % (rc2, txt2.strip().splitlines()[-1][:90]))
        return
    models = {m.get('model'): m for m in data.get('models', [])}
    fit = models.get('2c_iv') or {}
    if not fit.get('ok'):
        stage(tag_gold, 'FAIL', '2c_iv 拟合未成功：%s' % str(fit.get('error'))[:90])
        return
    params = dict(zip(fit.get('param_names', []), fit.get('params', [])))
    ok = True
    for nm, truth in zip(C2_NAMES, C2_TRUTH):
        ok = gold(tag_gold, '2c_iv 参数回收 %s' % nm, params.get(nm, float('nan')), truth,
                  tol_rel=C2_TOL, note='合成二室 IV 无噪声数据，真值解析已知') and ok
    stage(tag_gold, 'PASS' if ok else 'FAIL',
          'rc=%d｜%s｜R²=%.6g｜AIC 最优=%s'
          % (rc2, '｜'.join('%s=%.6g(真值 %.6g)' % (nm, params.get(nm, float('nan')), tv)
                            for nm, tv in zip(C2_NAMES, C2_TRUTH)), fit.get('r2', float('nan')),
             data.get('best_by_aic')))


def stage_m6():
    """M6 图件样例（缺件/缺 matplotlib → SKIP + [降级]）。"""
    tag = 'M6 图件样例'
    f1 = HERE / 'fig_samples' / 'fig1_pk_curve.py'
    if not f1.exists():
        stage(tag, 'SKIP', 'fig_samples/fig1_pk_curve.py 不在（未落盘）')
        return
    rc, txt = run_tool([str(f1)])
    outs = sorted((HERE / 'fig_samples' / '_out').glob('*'))
    if rc == 0 and len(outs) > 0:
        stage(tag, 'PASS', 'rc=0，_out/ %d 文件' % len(outs))
    elif is_dep_missing(txt):
        stage(tag, 'SKIP', '[降级] 缺 matplotlib 等依赖：%s' % txt.strip().splitlines()[-1][:90])
    else:
        stage(tag, 'FAIL', 'rc=%d，_out/ %d 文件｜%s' % (rc, len(outs), txt.strip().splitlines()[-1][:90]))


# ---------------------------------------------------------------- 报告 / 主程序
def write_report(out: Path) -> str:
    fails = [r for r in RESULTS if r[1] == 'FAIL']
    skips = [r for r in RESULTS if r[1] == 'SKIP']
    verdict = 'PASS' if not fails else 'FAIL'
    lines = ['# smoke_chain 报告（%s）' % VERSION, '',
             '**判定：%s**（PASS=%d｜FAIL=%d｜SKIP=%d｜黄金断言 %d 条，失败 %d 条）'
             % (verdict, len(RESULTS) - len(fails) - len(skips), len(fails), len(skips),
                len(GOLDS), len([g for g in GOLDS if not g['ok']])), '',
             '## 阶段状态', '', '| 阶段 | 状态 | 详情 |', '|---|---|---|']
    lines += ['| %s | %s | %s |' % r for r in RESULTS]
    lines += ['', '## 黄金断言（数值区间：abs(实测 − 真值) <= 容差）', '',
              '| 阶段 | 断言 | 实测 | 真值 | 容差 | 判定 | 说明 |', '|---|---|---|---|---|---|---|']
    for g in GOLDS:
        lines.append('| %s | %s | %.6g%s | %.6g | %s | %s | %s |'
                     % (g['stage'], g['name'], g['got'], (' ' + g['unit']) if g['unit'] else '',
                        g['truth'], g['tol'], 'PASS' if g['ok'] else 'FAIL', g['note']))
    lines += ['', '> 容差口径：相对容差 = |实测−真值|/|真值|；容差按上表逐条写明。',
              '> SKIP = 计划件/依赖未落盘（[降级] 原因见详情列），**不计入 PASS**；任一 FAIL → exit 1。']
    (out / 'smoke_chain_report.md').write_text('\n'.join(lines), encoding='utf-8')
    return verdict


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', action='store_true', help='保留合成 CSV 供检查（默认保留在 _smoke_out/）')
    ap.add_argument('--selftest', action='store_true',
                    help='别名：完整跑链即自测（无 FAIL 则 rc=0）')
    a = ap.parse_args(argv)
    out = HERE / '_smoke_out'
    out.mkdir(exist_ok=True)

    try:
        import numpy  # noqa: F401   （合成数据需要；缺 → 明确 SKIP，而不是假装跑过）
        has_numpy = True
    except Exception:
        has_numpy = False

    if not has_numpy:
        stage('M3 合成记录集', 'SKIP', '[降级] 当前解释器缺 numpy，无法自造合成数据 → 全链未执行（非通过）')
        verdict = write_report(out)
        print('\n判定：SKIP（缺 numpy，未执行）→ %s' % (out / 'smoke_chain_report.md'))
        return 3

    rec = stage_m3(out)
    stage_m4(out)
    stage_m5(rec)
    stage_m5_neg(rec)
    stage_release()
    stage_compartment(out)
    stage_m6()

    if not a.keep:
        removed = 0
        for name in ('synth_records.csv', 'synth_endpoint.csv', 'synth_two_comp.csv'):
            p = out / name
            if p.exists():
                p.unlink()
                removed += 1
        stage('M7 合成数据清理', 'PASS', '已清理 %d 个合成 CSV（--keep 可保留供检查）' % removed)

    verdict = write_report(out)
    n_fail = len([r for r in RESULTS if r[1] == 'FAIL'])
    n_skip = len([r for r in RESULTS if r[1] == 'SKIP'])
    print('\n判定：%s（FAIL=%d SKIP=%d 黄金断言 %d 条）→ %s'
          % (verdict, n_fail, n_skip, len(GOLDS), out / 'smoke_chain_report.md'))
    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
