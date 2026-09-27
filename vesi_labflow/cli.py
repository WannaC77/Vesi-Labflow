# -*- coding: utf-8 -*-
"""命令入口 —— 薄层：定位安装树 → 子进程运行工具，透传退出码。"""
import os
import subprocess
import sys
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
TREE = PKG_DIR / "_tree"


def _run(rel: str):
    script = TREE / rel
    if not script.exists():
        sys.stderr.write("[entry] 未找到工具: %s\n" % script)
        raise SystemExit(2)
    env = dict(os.environ)
    env.setdefault("LABFLOW_ROOT", str(TREE))
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(subprocess.call([sys.executable, str(script), *sys.argv[1:]], env=env))


def env_check(): _run("tools/env_check.py")
def smoke_chain(): _run("tools/smoke_chain.py")
def nca(): _run("tools/nca.py")
def stats_pipeline(): _run("tools/stats_pipeline.py")
def compartment_fit(): _run("tools/compartment_fit.py")
def release_fit(): _run("tools/release_fit.py")
def verify_bundle(): _run("scripts/verify_bundle.py")
def verify_manifest(): _run("scripts/verify_manifest.py")
