# Vesi-Labflow

药学与生命科学**科研工作流引擎**——把从文献调研到论文答辩的科研链路做成**可复现、门禁驱动**的流水线：文献 → 制剂与表征 → 体外释放 → 体内 PK → 组织分布 → 统计与图件 → 论文装配 → 答辩，每一步都有硬判据与诚实降级。

## 这个仓里有什么

| 板块 | 内容 |
|---|---|
| `workflows/` | 13 篇流程正本（项目管理 → 文献 → 制剂 → 释放 → PK → 分布 → 排泄 → 统计 → 论文 → 答辩 → 知识管理） |
| `modules/` | 11 个能力模块 + 底座（文献 / 设计工坊 / 记录线 / 统计台 / PK 领域台 / 图件车间 / 论文装配 / 三轨改写 / 申报答辩 / 校准钩子 / 编排器） |
| `tools/` | 计算与自检工具：`env_check` · `smoke_chain` · `nca`（非房室分析）· `stats_pipeline`（统计管线）· `compartment_fit`（房室拟合）· `release_fit`（释放拟合）· `fig_samples/`（图件样张） |
| `scripts/` | 交付门禁：`verify_bundle`（包结构自校验）· `verify_manifest`（文档-磁盘一致性）等 |
| `examples/` | 3 个 5 分钟上手示例（全合成数据） |

## 快速开始

```bash
pip install vesi-labflow[all]
vesi-env-check
```

[5 分钟上手](quickstart.md) · [运行示例](examples.md) · [工具索引](tools.md)

## 设计原则（摘要）

- **门禁驱动**：计算、统计、交付检查都由**可失败**的脚本判定（退出码契约：`0` 通过 · `1` 失败 · `2` 用法 · `3` 依赖缺失未执行）。
- **诚实降级**：缺依赖标 `SKIP`、未执行返 `3`，绝不假装通过。
- **可复现**：工具随包分发、示例全合成数据、黄金数值断言随测试链真跑。

---
MIT License · 署名 [WannaC77](https://github.com/WannaC77)
