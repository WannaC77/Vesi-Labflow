# MODULE · V-M4 统计台（STAT）

> 所属：`modules/V-M4-统计台/`｜层：L0｜版本：v1.0（2026-09-21）｜引擎：`VESI-ENGINE.md` §1

## 目的 / Purpose
数据 → 可复核分析（★高杠杆）：描述 → 正态证据 → 检验树 → 效应量+CI → 报告。

## 输入 → 输出 / IO
- 输入：CSV/Excel 数据（含分组列）
- 输出：分析报告 md（描述统计/正态证据/检验树/效应量+CI/校正记录）

## 接口字段 / Interface
报告节：0 输入与口径｜1 描述统计（mean±SD、median[IQR]、CV）｜2 正态与方差证据｜3 检验树决策与主检验｜4 结论（纪律口径）。工具：`tools/stats_pipeline.py`。

## 装载 / Loading（指针，细节在正本）
`workflows/08-数据处理与可视化.md`（正本：速查/微陷阱/图型）；`tools/stats_pipeline.py`

## 门禁 / Gates
三证齐（正态证据 / 效应量+CI / 多重比较记录）；n≥3 纪律（n=3 非参数报 p 下限 0.10，禁 */**）；方法预注册；异常值只标记不删除

## 降级 / Fallback
按 workflows/08 速查表手工走 GraphPad/手算，报告标注 `[降级]` 与所用方法

## 样例 / Example（合成或去敏）
`stats_pipeline.py --selftest`：合成数据 7 组断言（t/MWU/ANOVA/配对/n=3 下限/Holm）全部可跑
