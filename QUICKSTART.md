# QUICKSTART — 5 分钟上手（Vesi-Labflow）

> 前提：Python 3.11+。全程无需 API key、无需联网、无需任何特定 agent。

## 0. 拿包

```bash
git clone https://github.com/WannaC77/Vesi-Labflow Vesi-Labflow
cd Vesi-Labflow
```

## 1. 装依赖（可选但推荐）

```bash
python -m venv .venv
# 下面用 <venv> 指代你刚建的虚拟环境目录（本仓示例目录名 .venv）
<venv>/Scripts/python -m pip install -r requirements.txt   # Windows
<venv>/bin/python     -m pip install -r requirements.txt   # Linux/macOS
```

> 不装 venv 也能跑：`tools/` 会在系统 Python 下回退，缺包时输出 `SKIP` 并说明原因（**不会**假装通过）。

## 2. 自检环境

```bash
python tools/env_check.py --selftest
```

输出各项 `[PASS]/[FAIL]/[SKIP]` 与档位。**FAIL 必须处理**，SKIP 请记下原因。

## 3. 跑冒烟链（合成数据 · 已知答案）

```bash
python tools/smoke_chain.py --selftest        # 端到端：数据 → 统计 → 图件 → 论文骨架（含数值断言）
python tools/nca.py --selftest                # 非房室分析（含个体维）
python tools/stats_pipeline.py --selftest     # 统计管线（含配对用例）
```

## 4. 装载（人 / code agent 通用）

```
1. 读 BOOT.md → VESI-CORE.md → VESI-ENGINE.md
2. 按任务选 runbook：workflows/01-项目管理.md … 13-导师与团队.md（+ workflows/_SHARED.md）
3. 产物落盘 → 过门禁（脚本 exit code）→ 记交接卡
```

code agent 请先读 `AGENTS.md`。

## 5. 第一条完整链（以「体外释放实验」为例）

1. `workflows/02-文献调研.md` → 检索式 → 证据表（三态标注）
2. `workflows/03-制剂制备与表征.md` + `templates/` 设计卡 → 变量 / 对照 / n / 预注册
3. `workflows/04-体外释放.md` → 取样方案 → `tools/release_fit.py` 拟合（含模型选择与优度）
4. `workflows/08-数据处理与可视化.md` → `tools/stats_pipeline.py`（正态 / 效应量+CI / 多重比较三证齐）
5. `workflows/09-论文写作.md` → 论文装配（Claim-Evidence 映射）
6. `scripts/` 交付门禁 → 卫生断言 / 一致性检查

## 6. 私有校准（L2 · 可选）

```bash
mkdir -p kb                                   # 你的知识库（文献笔记、检索式、证据表）
cp templates/校准台账模板.md <校准台账>.md
cp templates/锚注册卡模板.md <锚注册卡>.md
```

机制说明见 `references/outcome-anchor-protocol.md`（含空锚表与**填锚规程**）。

## 7. 出问题

- 环境 / 依赖 → `references/故障速查卡.md`
- 统计口径 → `references/` 统计相关件 + `tools/stats_pipeline.py --help`
- 许可与来源 → `THIRD-PARTY.md`
