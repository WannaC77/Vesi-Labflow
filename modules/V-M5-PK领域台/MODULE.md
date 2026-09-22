# MODULE · V-M5 PK/领域台（PK）

> 所属：`modules/V-M5-PK领域台/`｜层：L0｜版本：v1.0（2026-09-21）｜引擎：`VESI-ENGINE.md` §1

## 目的 / Purpose
血药/组织/排泄数据 → NCA / 房室 / 释放拟合 / 排泄累积（★护城河）。

## 输入 → 输出 / IO
- 输入：浓度-时间表 / 累积释放% / 排泄分段数据
- 输出：PK 报告字段（参数表+口径声明+拟合优度证据）

## 接口字段 / Interface
NCA：Cmax/Tmax/AUC0-t/AUC0-inf/t1/2/MRT/CL/Vz（`nca.py`）；房室：参数±SE、R²、AIC/BIC（`compartment_fit.py`）；释放：零级/一级/Higuchi/K-P(n)/Hixon-Crowell/Weibull 排名（`release_fit.py`）。**口径：DAS 软件输出为准，本工具=独立复算核对器。**

## 装载 / Loading（指针，细节在正本）
`workflows/05–07`（正本）；`tools/{nca,compartment_fit,release_fit}.py`

## 门禁 / Gates
参数完整 + 口径声明；拟合优度证据（R²/AIC/残差）；包裹/游离质控要点（体系相关时）；小样本结论克制（报告效应量与 CI）

## 降级 / Fallback
外部软件（DAS/Phoenix 等）手工表 + 本工具逐项核对；缺件标 `[降级]`

## 样例 / Example（合成或去敏）
三工具 `--selftest`：一室/二室合成回收、Higuchi 回收（k=20±1%）全部可跑
