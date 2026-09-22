# MODULE · V-M7 论文装配（PAPER）

> 所属：`modules/V-M7-论文装配/`｜层：L0｜版本：v1.0（2026-09-21）｜引擎：`VESI-ENGINE.md` §1

## 目的 / Purpose
IMRaD → docx：逐节装配 + 自查 + Claim-Evidence + 交付卫生断言。

## 输入 → 输出 / IO
- 输入：分析报告/图件/结论（V-M4–M6）
- 输出：论文/章节 + 自查说明 + 引用表

## 接口字段 / Interface
逐节 checklist；Claim-Evidence 映射（`templates/Claim-Evidence映射表.md`）；引用格式卡（`references/引用格式卡.md`）；装配 SOP（`references/论文装配SOP.md`）。

## 装载 / Loading（指针，细节在正本）
`workflows/09-论文写作.md`（正本）；`references/论文装配SOP.md`；`scripts/assert_delivery_hygiene.py`

## 门禁 / Gates
逐节 checklist 过；Claim-Evidence 一一对应；`assert_delivery_hygiene` FAIL=0；**docx 交付件禁止再经 Word 另存**（styleId 回退坑）

## 降级 / Fallback
纯文本/md 装配 + 门禁清单人工核；docx 管线降级时保留中间态 md

## 样例 / Example（合成或去敏）
卫生断言对合成 docx 的只读跑（不依赖个人材料）
