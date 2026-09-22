# MODULE · V-M6 图件车间（FIG）

> 所属：`modules/V-M6-图件车间/`｜层：L0｜版本：v1.0（2026-09-21）｜引擎：`VESI-ENGINE.md` §1

## 目的 / Purpose
数据 → 出版级图（PNG+PDF+SVG）+ 图注，过三闸。

## 输入 → 输出 / IO
- 输入：分析结果（V-M4/M5）+ 图型规范
- 输出：三格式图件 + 图注

## 接口字段 / Interface
图注四要素：图号+标题｜内容描述（n 与统计）｜方法/条件｜缩写与统计说明。模板：`templates/图注模板.md`。样例代码：`tools/fig_samples/`（style_vesi + 6 图型）。

## 装载 / Loading（指针，细节在正本）
`workflows/08`（图型规范节）；`tools/fig_samples/`；`templates/图注模板.md`

## 门禁 / Gates
三闸：audit_fig（越界检测）/ figcheck（文件层）/ vision 复核（无 vision 则双闸+人检）；轴标签英文或已验证中文字体；误差棒=SD 并声明

## 降级 / Fallback
代码出图 + 人工复核清单；缺中文字体 → 全英文标签（style_vesi 自动探测）

## 样例 / Example（合成或去敏）
`fig_samples/fig1..fig6` 均以固定 seed 合成数据出图（`_out/` 三格式）
