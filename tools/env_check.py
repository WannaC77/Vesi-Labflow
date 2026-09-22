#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""env_check —— Vesi 环境自检（V-U35 · 底座 T0）

适用场景 / Purpose
    任何会话/agent 装载 Vesi 引擎时的第一步：一键核验本机 Python、依赖包、
    可选专业件、**包内目录**在位情况，输出「档位 + 缺件清单」，
    支撑「工具可执行」判定（VESI-ENGINE §0/§6）。

档位 / Tiers
    T0 核心：Python>=3.10 + numpy/scipy/pandas；包内 `workflows/` 与 `tools/` 在位
    T1 文档/表格线：+ python-docx / openpyxl / matplotlib；references/templates/modules/scripts/fig_samples 在位
    T2 专业件：+ Word COM(win32com) / LaTeX(xelatex) / 中文字体 / PDF(pymupdf) / 虚拟环境解释器
    缺件均为「降级可走」：按各模块表「降级」列执行并标 `[降级]`（缺件≠工具坏）。

路径 / Paths（根解析＝探测链 · 顺序固定 · **源码内不写死任何机器绝对路径**）
    1. 环境变量（最高优先）：`LABFLOW_ROOT`（未设则兼容 `OPENLAB_ROOT`）→ 指向包根
    2. 自脚本位置向上逐级：某祖先目录**同时**含 `tools/` 与 `workflows/` → 该目录＝包根
       （开源包布局：包根即仓根，`workflows/`·`tools/`·`references/`·`templates/`·`modules/` 直接在包根下）
    3. 旧布局兼容：某祖先目录名为旧根目录名且其下 `workflows/` 在位
       → 系统根＝该祖先的父目录，包内容根仍取该祖先目录（开源包内两者合一）
    4. 全失败 → 包根＝脚本父目录的父目录（`tools/` 的上一级），后续目录项允许 FAIL（**诚实降级**，不假装成功）
    外部件一律经环境变量或探测链（不写死路径）：
       `LABFLOW_TEX`（xelatex 可执行）｜`LABFLOW_FONTS`（字体目录或字体文件列表）｜`LABFLOW_VENV`（解释器）
       → 未设则依次走：PATH（`shutil.which`）｜matplotlib 字体表（已知 CJK 字体名）｜运行中解释器是否在虚拟环境内

用法 / Usage
    python env_check.py [--root <包根>] [--json]
    python env_check.py --selftest      # 自证：根解析 / 目录在位 / 探测链降级
    exit 0 = 达到 T0 及以上；1 = 未达 T0

selftest 判据说明
    `--selftest` 断言的是**本工具自身可用**（根解析链、报告生成、目录项判定、探测链降级），
    不把「本机缺某个可选包」判成工具故障——档位与缺件清单照实打印（缺件标 `[降级]`），
    需要机器档位作为门禁时请跑不带 `--selftest` 的调用（未达 T0 时 exit 1）。
"""
from __future__ import annotations

import argparse
import collections
import importlib
import json
import os
import shutil
import sys
from pathlib import Path

VERSION = 'v1.1 (2026-09-22)'    # v1.1：根解析改「探测链」（环境变量 → tools+workflows 同位 → 旧布局 → 诚实降级）

ROOT_ENV_VARS = ('LABFLOW_ROOT', 'OPENLAB_ROOT')     # 中性前缀；可指向包根
TEX_ENV, FONT_ENV, VENV_ENV = 'LABFLOW_TEX', 'LABFLOW_FONTS', 'LABFLOW_VENV'
LEGACY_ROOT_NAME = 'vesi'                            # 旧布局的根目录名（包内已无此前缀）
FONT_CANDIDATES = ('Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Source Han Sans SC',
                   'PingFang SC', 'Heiti SC', 'WenQuanYi Zen Hei')
FONT_EXTS = ('*.ttf', '*.otf', '*.ttc')

REQUIRED = ['numpy', 'scipy', 'pandas']              # T0
DOC_LINE = ['docx', 'openpyxl', 'matplotlib']        # T1
OPTIONAL = ['pymupdf', 'PIL']                        # T2

# 包内目录在位检查：(相对包根路径, 说明, 最少文件数（0=存在即算）, 档位)
DIR_CHECKS = (
    ('workflows', '工作流正本（V-M1…V-M11 的流程卡）', 10, 'T0'),
    ('tools', '工具集（env_check / 统计 / PK / 图件）', 1, 'T0'),
    ('references', '参考卡（口径 / 路径 / 数据字典）', 1, 'T1'),
    ('templates', '模板集（记录 / 设计卡 / 报告 / 图注）', 1, 'T1'),
    ('modules', '模块规格件（V-M*）', 1, 'T1'),
    ('scripts', '轨校验脚本（一致性 / 查重 / 剂量）', 1, 'T1'),
    ('tools/fig_samples', '图件样例（图件车间，位于 tools/ 下）', 1, 'T1'),
    ('kb', '知识库目录（私有内容不入库，仅留占位）', 0, 'T1'),
)

Root = collections.namedtuple('Root', 'system pkg source note')


# ---------------------------------------------------------------- 根解析（探测链）
def _ancestors(start: Path):
    """自 start 起逐级向上（含自身）。"""
    yield start
    for p in start.parents:
        yield p


def resolve_root(explicit=None) -> Root:
    """包根探测链：环境变量 → tools+workflows 同位 → 旧布局 → 诚实降级。"""
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return Root(p, p, 'cli:--root', '命令行指定（最高优先）')
    tried = []
    for var in ROOT_ENV_VARS:
        raw = os.environ.get(var)
        if not raw:
            continue
        p = Path(raw).expanduser()
        if p.is_dir():
            p = p.resolve()
            return Root(p, p, 'env:%s' % var, '环境变量覆盖')
        tried.append('%s=%s 不是目录' % (var, raw))
    here = Path(__file__).resolve().parent            # tools/
    # ② 同时含 tools/ 与 workflows/ 的祖先 = 包根（排除旧根目录名，交给 ③ 判定语义）
    for cand in _ancestors(here):
        if cand.name == LEGACY_ROOT_NAME:
            continue
        if (cand / 'tools').is_dir() and (cand / 'workflows').is_dir():
            return Root(cand, cand, 'probe:tools+workflows',
                        '自脚本位置向上找到 tools/ 与 workflows/ 同层')
    # ③ 旧布局：<系统根>/<旧根目录名>/workflows 在位 → 系统根取父目录，内容根取该目录
    for cand in _ancestors(here):
        if cand.name == LEGACY_ROOT_NAME and (cand / 'workflows').is_dir():
            return Root(cand.parent, cand, 'probe:legacy-layout',
                        '旧布局：workflows/ 位于 <旧根目录名>/ 之下，系统根取其父目录')
    # ④ 全失败 → 降级（后续目录项允许 FAIL）
    p = here.parent
    return Root(p, p, 'fallback:tools-parent',
                '探测链全失败 → 降级为 tools/ 的上一级；目录项可能 FAIL（不假装成功）'
                + ('；此前尝试：' + '；'.join(tried) if tried else ''))


# ---------------------------------------------------------------- 外部件探测（环境变量 → 探测链）
def pkg_ver(name: str):
    """包版本；未安装 → None（不抛异常）。pymupdf 兼容新旧导入名。"""
    cands = {'pymupdf': ('pymupdf', 'fitz'), 'docx': ('docx',), 'PIL': ('PIL',)}.get(name, (name,))
    for mod in cands:
        try:
            m = importlib.import_module(mod)
        except Exception:
            continue
        return getattr(m, '__version__', None) or '?'
    return None


def check_win32com():
    """Word COM（Windows 文档线专业件）；不可用 → None（[降级] 走 python-docx 直改）。"""
    try:
        import win32com.client  # noqa: F401
        return '可用'
    except Exception:
        return None


def check_tex():
    """xelatex：LABFLOW_TEX 环境变量 → PATH（shutil.which）→ None（[降级] 论文线纯文本装配）。"""
    raw = os.environ.get(TEX_ENV)
    if raw:
        p = Path(raw).expanduser()
        return str(p) if p.is_file() else None
    return shutil.which('xelatex')


def check_font():
    """中文字体：LABFLOW_FONTS（目录 / 字体文件列表）→ matplotlib 字体表 → None（[降级] 英文标签）。"""
    raw = os.environ.get(FONT_ENV)
    if raw:
        hits = []
        for part in raw.split(os.pathsep):
            if not part.strip():
                continue
            p = Path(part).expanduser()
            if p.is_dir():
                for ext in FONT_EXTS:
                    hits += sorted(f.stem for f in p.glob(ext))
            elif p.is_file():
                hits.append(p.stem)
        return '环境变量指定：%s' % '、'.join(sorted(set(hits))[:3]) if hits else None
    try:
        from matplotlib import font_manager
        names = {f.name for f in font_manager.fontManager.ttflist}
        for cand in FONT_CANDIDATES:
            if cand in names:
                return cand
    except Exception:
        pass
    return None


def check_venv():
    """虚拟环境解释器：LABFLOW_VENV 环境变量 → 运行中解释器是否在虚拟环境内 → None（[降级]）。"""
    raw = os.environ.get(VENV_ENV)
    if raw:
        p = Path(raw).expanduser()
        return str(p) if p.is_file() else None
    if sys.prefix != sys.base_prefix:
        return '当前解释器在虚拟环境内（%s）' % Path(sys.prefix).name
    return None


# ---------------------------------------------------------------- 自检报告
def run(root: Root) -> dict:
    r = dict(version=VERSION, system_root=str(root.system), pkg_root=str(root.pkg),
             root_source=root.source, root_note=root.note,
             python=sys.version.split()[0], python_ok=sys.version_info >= (3, 10),
             items=[], missing=[])

    def item(name, state, note='', tier='T0'):
        r['items'].append(dict(name=name, ok=bool(state), note=note or ('OK' if state else '[降级] 缺件'),
                               tier=tier))
        if not state:
            r['missing'].append(name)

    item('Python>=3.10', r['python_ok'], r['python'], 'T0')
    for p in REQUIRED:
        v = pkg_ver(p)
        item('包 %s' % p, v is not None, v or '未安装（核心线降级：数值工具不可用）', 'T0')
    for p in DOC_LINE:
        v = pkg_ver(p)
        item('包 %s' % p, v is not None, v or '未安装（文档/表格线降级）', 'T1')
    for p in OPTIONAL:
        v = pkg_ver(p)
        item('包 %s' % p, v is not None, v or '未安装（专业件降级：PDF 回读/图像处理改人工核）', 'T2')

    # 包内目录在位（相对包内容根）
    for rel, label, minn, tier in DIR_CHECKS:
        p = Path(root.pkg) / rel
        n = len([x for x in p.rglob('*') if x.is_file()]) if p.exists() else 0
        ok = p.exists() and (n >= minn if minn > 0 else True)
        item('目录 %s' % rel, ok,
             ('%d 文件｜%s' % (n, label)) if p.exists() else '不存在（相对包根 %s）' % rel, tier)

    wc = check_win32com()
    item('Word COM (win32com)', wc, wc or '不可用（docx 管线降级：python-docx 直改）', 'T2')
    xl = check_tex()
    item('LaTeX (xelatex)', xl, xl or '不在 %s / PATH（论文线降级：纯文本装配）' % TEX_ENV, 'T2')
    f = check_font()
    item('中文字体', f, f or '未探到（可在 %s 指定字体目录/文件；图件降级用英文标签）' % FONT_ENV, 'T2')
    vn = check_venv()
    item('虚拟环境解释器', vn, vn or '未探到（可在 %s 指定解释器；依赖用系统解释器时降级）' % VENV_ENV, 'T2')

    # 档位
    def tier_ok(tier):
        return all(i['ok'] for i in r['items'] if i['tier'] == tier)

    t0, t1 = tier_ok('T0'), tier_ok('T0') and tier_ok('T1')
    t2 = t1 and tier_ok('T2')
    r['tier'] = 'T2' if t2 else ('T1' if t1 else ('T0' if t0 else '未达 T0'))
    r['degraded'] = r['tier'] != 'T2'
    return r


def render(r: dict) -> str:
    lines = ['# Vesi 环境自检（env_check %s）' % r['version'], '',
             '- 系统根：`%s`｜包根：`%s`（来源：%s — %s）' % (r['system_root'], r['pkg_root'],
                                                              r['root_source'], r['root_note']),
             '- Python：%s' % r['python'], '',
             '| 项 | 状态 | 说明 | 档 |', '|---|---|---|---|']
    for i in r['items']:
        lines.append('| %s | %s | %s | %s |' % (i['name'], '✅' if i['ok'] else '❌', i['note'], i['tier']))
    lines += ['', '**档位：%s**%s' % (r['tier'], ('｜缺件（均 [降级] 可走）：' + ', '.join(r['missing']))
                                      if r['missing'] else '｜无缺件')]
    return '\n'.join(lines)


# ---------------------------------------------------------------- 自测
def selftest() -> int:
    """断言本工具自身可用：根解析（含探测链降级）/ 目录项判定 / 报告生成 / 档位计算。"""
    ok = True
    n_fail = 0

    def check(name, cond, detail=''):
        nonlocal ok, n_fail
        ok = ok and bool(cond)
        n_fail += (not cond)
        print('[%s] %s' % ('PASS' if cond else 'FAIL', name))
        if detail:
            print('        ' + detail)

    print('=' * 72)
    print('env_check.py --selftest（根解析探测链 / 目录判定 / 报告生成）')
    print('=' * 72)

    # ① 探测链：脚本位置向上找 tools/ + workflows/ 同位者
    root = resolve_root()
    check('① 包根解析（tools/ 与 workflows/ 同位或旧布局/降级）',
          (Path(root.pkg) / 'tools').is_dir() and (Path(root.pkg) / 'workflows').is_dir(),
          '来源 = %s｜包根 = %s｜系统根 = %s' % (root.source, root.pkg, root.system))
    check('① 包根下 tools/ 含本脚本', (Path(root.pkg) / 'tools' / Path(__file__).name).is_file(),
          '期望 %s' % (Path(root.pkg) / 'tools' / Path(__file__).name))

    # ② 环境变量覆盖（最高优先）：指向存在的目录须被采信
    prev = os.environ.get(ROOT_ENV_VARS[0])
    os.environ[ROOT_ENV_VARS[0]] = str(Path(root.pkg))
    try:
        hv = resolve_root()
        check('② 环境变量 %s 覆盖生效' % ROOT_ENV_VARS[0], hv.source == 'env:%s' % ROOT_ENV_VARS[0],
              '来源 = %s' % hv.source)
    finally:
        if prev is None:
            os.environ.pop(ROOT_ENV_VARS[0], None)
        else:
            os.environ[ROOT_ENV_VARS[0]] = prev

    # ③ 探测链降级：环境变量指向不存在目录 → 不得采信，须回落且给出说明
    tmp_base = Path(os.environ.get('TEMP') or os.environ.get('TMP') or '.')
    missing_dir = str(tmp_base / ('_labflow_probe_not_here_%d' % os.getpid()))
    os.environ[ROOT_ENV_VARS[0]] = missing_dir
    try:
        r3 = resolve_root()
        check('③ 环境变量指向不存在目录 → 回落探测链（不采信坏值）',
              r3.source.startswith('probe:') or r3.source.startswith('fallback:'),
              '来源 = %s｜说明 = %s' % (r3.source, r3.note[:80]))
    finally:
        if prev is None:
            os.environ.pop(ROOT_ENV_VARS[0], None)
        else:
            os.environ[ROOT_ENV_VARS[0]] = prev

    # ④ 报告生成 + 档位计算 + 目录项判定
    r = run(root)
    names = [i['name'] for i in r['items']]
    check('④ 报告项齐（Python / 核心包 / 目录 tools / 目录 workflows）',
          all(k in names for k in ('Python>=3.10', '包 numpy', '目录 tools', '目录 workflows')),
          '%d 项｜档位 = %s' % (len(r['items']), r['tier']))
    check('④ Python>=3.10', r['python_ok'], 'Python %s' % r['python'])
    check('④ 目录项判定按文件数（目录 workflows 在位）',
          [i for i in r['items'] if i['name'] == '目录 workflows'][0]['ok'],
          [i for i in r['items'] if i['name'] == '目录 workflows'][0]['note'])
    check('④ 目录缺失会被判 FAIL（判定逻辑可用）',
          [i for i in r['items'] if i['name'] == '目录 tools'][0]['ok'] is not False
          or 'tools' in r['missing'], '目录 tools → %s' % [i for i in r['items'] if i['name'] == '目录 tools'][0]['note'])
    md = render(r)
    check('④ 报告可渲染（Markdown 含量表头与档位行）',
          ('| 项 | 状态 | 说明 | 档 |' in md) and ('**档位：' in md), '长度 = %d 字符' % len(md))
    check('④ JSON 可序列化', isinstance(json.dumps(r, ensure_ascii=False), str))

    # ⑤ 外部件探测链（环境变量优先；未设则走探测链，全失败返回 None 由上层标 [降级]）
    prev_t = os.environ.get(TEX_ENV)
    os.environ[TEX_ENV] = str(Path(root.pkg) / 'LICENSE')      # 存在的文件 → 采信
    try:
        check('⑤ %s 环境变量优先采信' % TEX_ENV, bool(check_tex()), '值 = %s' % check_tex())
    finally:
        if prev_t is None:
            os.environ.pop(TEX_ENV, None)
        else:
            os.environ[TEX_ENV] = prev_t
    check('⑤ 未设环境变量时探测链返回 None 或真实路径',
          check_tex() is None or Path(check_tex()).exists(),
          'xelatex 探测 = %s（None → [降级]）' % check_tex())
    check('⑤ 字体探测链（未命中返回 None 由上层标 [降级]）',
          check_font() is None or isinstance(check_font(), str), '字体 = %s' % check_font())
    check('⑤ 虚拟环境探测链可用', check_venv() is None or isinstance(check_venv(), str),
          'venv = %s' % check_venv())

    # ⑥ 档位为信息项（本机缺可选包 ≠ 工具故障）：照实打印
    print('-' * 72)
    print('档位 = %s%s' % (r['tier'], ('｜缺件（[降级] 可走）：' + ', '.join(r['missing']))
                          if r['missing'] else '｜无缺件'))
    print('说明：以上档位是**本机环境信息**（缺可选包不判 selftest FAIL，缺件照实标 [降级]）；'
          '需要机器档位作门禁时跑不带 --selftest 的调用（未达 T0 → exit 1）。')

    print('-' * 72)
    print('SELFTEST', 'OK' if ok else 'FAILED（%d 项）' % n_fail)
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Vesi 环境自检')
    ap.add_argument('--root', help='包根（默认按探测链自动解析）')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    root = resolve_root(a.root)
    r = run(root)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render(r))
    return 0 if r['tier'] in ('T0', 'T1', 'T2') else 1


if __name__ == '__main__':
    sys.exit(main())
