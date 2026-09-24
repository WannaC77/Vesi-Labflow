# Changelog · Vesi-Labflow

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## v1.0.0 — 首次公开发行

**定位**：面向**药学与生命科学**的科研工作流引擎——文献 → 实验设计 → 数据记录 → 统计分析 → 论文装配。

**包含**
- 模块体系：11 个模块（文献 / 设计工坊 / 记录线 / 统计台 / 领域台 / 图件车间 / 论文装配 / 多赛道改写 / 申报与答辩 / 校准钩子 / 编排器）+ 底座
- 运行手册：`workflows/01–13` + `_SHARED.md`（共享纪律）+ `D-ABSORB.md`（吸收门）
- 数据与统计工具：`tools/`（NCA · 房室拟合 · 释放拟合 · 统计管线 · 冒烟链 · 环境自检），全部带 `--selftest` 与**已知答案数值断言**
- 交付门禁脚本：`scripts/`（交付卫生 / 剂量换算 / 记录转写 / 元数据清理 / 跨文档一致性 / 自然度与重复预检 / 引用编号 / 包结构校验 / 元自检）
- 模板：设计卡（体外释放 / 体内 PK / 组织分布 / 排泄）、记录模板、图注模板、校准台账模板、锚注册卡模板
- 装载件：`BOOT.md` / `AGENTS.md` / `README.md` / `README.en.md` / `QUICKSTART.md`
- 合规件：`LICENSE`（MIT）/ `LICENSE-DOCS`（CC BY 4.0）/ `THIRD-PARTY.md`
- 社区件：`CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `.github/ISSUE_TEMPLATE/`

**设计要点**
- 诚实性优先：模块表含**降级列**，缺件一律 `[降级]`/`SKIP` 并留证
- 证据链：Claim-Evidence 映射 + 三态标注 + 动机审计
- 统计纪律：三证齐（正态 / 效应量+CI / 多重比较）；n=3 是下限不是目标
- 个体维正确性：NCA 支持 `--subject` 个体分析后汇总（禁止多样本静默缝成单曲线）
- 末段护栏：NCA 末段 λz ≤ 0（末段不下降）**直接报错退出**，不产出负 AUC0-inf / 负 t1/2 / 负 CL；
  外推占比 > 20% 时报告带警示（避免把「有数字」误读成「可信数字」）
- 零私有依赖：不依赖任何特定 agent / CLI / 调度器 / API key

**已知边界**
- 缺 OCR / Word COM / LaTeX 时对应环节降级（`[降级]` 标注，不生成伪产物）
- 本仓库不随附任何真实实验数据、他人材料或课题专用模板

## 版本与 tag 约定

- 版本号遵循 **SemVer**（`vMAJOR.MINOR.PATCH`）；首次公开发行为 `v1.0.0`，tag 与提交同批打（`git tag -a v1.0.0`）。
- **PATCH**：文案/口径纠错、断言补注（不改契约）；**MINOR**：新增模块/模板/判据（向后兼容）；
  **MAJOR**：判据或契约**不兼容**变更（如退出码语义、必需件集合、目录结构）。
- 每个 tag 的说明直接用本文件对应小节的条目；`CHANGELOG.md` 与 tag 一一对应，改名/移动件须在同一小节登记。
