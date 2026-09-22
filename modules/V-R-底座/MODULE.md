# MODULE · V-R 底座（BASE）

> 所属：`modules/V-R-底座/`｜层：L0｜版本：v1.0（2026-09-21）｜引擎：`VESI-ENGINE.md` §1

## 目的 / Purpose
环境/冒烟/故障/路径卡：让全链可装载、可自检、可排障。

## 输入 → 输出 / IO
- 输入：—（基础设施）
- 输出：环境档位 / 冒烟结果 / 故障卡

## 接口字段 / Interface
`tools/env_check.py`（档位 T0/T1/T2）｜`tools/smoke_chain.py`（合成链冒烟）｜`references/路径与资产清单.md`（SSOT）｜`references/故障速查卡.md`。

## 装载 / Loading（指针，细节在正本）
`references/路径与资产清单.md`；`tools/env_check.py`；`tools/smoke_chain.py`；`references/故障速查卡.md`

## 门禁 / Gates
env_check 可跑（档位明示）；脚本冒烟 rc=0（生科 12 + 目标赛道 6 + tools 全件）；故障卡可检索

## 降级 / Fallback
手工核 ENGINE §6 环境卡；故障按卡中「现象→处置」执行

## 样例 / Example（合成或去敏）
`env_check --selftest`、`smoke_chain`（合成数据，不评分不进锚）
