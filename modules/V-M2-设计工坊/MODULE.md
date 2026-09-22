# MODULE · V-M2 设计工坊（DESIGN）

> 所属：`modules/V-M2-设计工坊/`｜层：L0｜版本：v1.0（2026-09-21）｜引擎：`VESI-ENGINE.md` §1

## 目的 / Purpose
研究问题 → 设计卡：变量/对照/n 与依据/统计预注册/剂量链/伦理，全部实验前定稿。

## 输入 → 输出 / IO
- 输入：研究问题 + 文献证据表（V-M1）
- 输出：设计卡（体外释放/体内PK/组织分布/排泄 四型）

## 接口字段 / Interface
设计卡字段：研究问题｜变量（自/因/控制）｜对照设置｜样本量 n 与依据（power）｜统计预注册（实验前）｜剂量/浓度链（可复算算式）｜时间点表｜伦理声明｜预注册变更记录节。模板：`templates/设计卡-*.md`×4。

## 装载 / Loading（指针，细节在正本）
`workflows/03–07`（正本）；`templates/设计卡-{体外释放,体内PK,组织分布,排泄}.md`；`scripts/check_dose.py`（剂量换算核对器）

## 门禁 / Gates
对照齐；n 与 power 记录；统计方法实验前定稿（对齐 workflows/08 铁律）；剂量换算可复算（check_dose 核对）；变更走预注册变更记录节

## 降级 / Fallback
按 workflows/03–07 参数表逐项手工填卡；换算用纸面/计算器并留算式

## 样例 / Example（合成或去敏）
`check_dose.py --selftest`（rat 5 mg/kg → HED 0.8108 mg/kg）为合成回归；设计卡样例用 <…> 占位
