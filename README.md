# Vesi-Labflow · 药学与生命科学科研工作流（中文版）

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![docs](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)

> **英文版 / English version**：`README.en.md`（本文件为中文版正本；英文版由英文侧维护，两份同构）
> **冷启动**：只有 5 分钟？先读 `BOOT.md`，再读 `QUICKSTART.md`。
> **CI 徽章**：待仓库 URL 确定后补（与 `LICENSE` / `CITATION.cff` 同批替换占位）。

---

## 一句话定位

**Vesi-Labflow 是一套「手册 + 工具链」形态的科研工作流引擎**：把「**文献 → 实验设计 → 数据记录 → 统计分析 → 论文装配**」拆成 **11 个模块 + 1 个底座**，每个模块都带**可执行门禁**与**显式降级路径**——方法写在 `workflows/` 与 `references/`，计算与自检交给 `tools/` 与 `scripts/`。任何能读文件、能跑 Python 的人或 code agent，按三步装载即可开工。

它不替你思考，也不替你下结论；它保证的是：**你做的每一步都留下可核查的证据链**。

## 目标用户

- **药学方向**（药剂 / 药代 / 生物分析 / 制剂表征）的本科生与研究生；
- **生命科学方向**（细胞 / 分子 / 动物实验）的本科生与研究生；
- **学科竞赛与创新创业训练计划队伍**——需要把「做了什么、凭什么这么做」讲清楚的团队；
- **需要可核查流程的 AI 辅助科研者**——想用 AI 提效，但不想让流程变成黑箱的人。

## 不服务（明确拒绝）

- **一键生成论文**：本包给结构、清单、代码骨架与初稿位，不给「交稿即用」的成品；核心论述必须由你本人写。
- **规避学术诚信审查**：不提供降重、洗稿、规避检测之类的手段。
- **伪造数据**：不生成、不补全、不修饰实验数据与统计结果；缺数据就写缺数据，缺证据就标 `[待核]`。

---

## 三步装载

| 步 | 读什么 | 拿到什么 |
|---|---|---|
| 1 | `BOOT.md` | 冷启动索引：身份一句话 · 铁律摘要 · 装载路径（≤2 KB，先读这个） |
| 2 | `VESI-CORE.md` | 人格与铁律：三模式、交付分级、思维铁律、溯源追踪、自改进循环 |
| 3 | `VESI-ENGINE.md` | 生成引擎：模块注册表（§1）、门禁矩阵（§3）、runbooks（§4）、交接卡（§7） |

之后按所选 runbook 的装载清单**按需加载** `workflows/` 与 `modules/`：细节正本在工作流，引擎只索引、不复制正文。**别把整仓读进上下文**——按任务加载是这套体系能长期用下去的前提。

## 能力清单（11 模块 + 底座）

| 模块 | 一句话 |
|---|---|
| **V-M1 文献 LIT** | 检索 → 精读 → 证据表：把文献转成可溯源、带三态标注的证据资产 |
| **V-M2 设计工坊 DESIGN** | 研究问题 → 设计卡：变量 / 对照 / n 与依据 / 统计预注册 / 剂量链 / 伦理，实验前定稿 |
| **V-M3 记录线 RECORD** | 照片 / 口述 / 原始文件 → 结构化实验记录，原始数据只读归档 |
| **V-M4 统计台 STAT** | 数据 → 可复核分析：描述统计 → 正态证据 → 检验树 → 效应量 + 置信区间 → 报告 |
| **V-M5 领域台 PK** | 血药 / 组织 / 排泄 / 释放数据 → 非房室分析 · 房室拟合 · 释放模型拟合 · 排泄累积 |
| **V-M6 图件车间 FIG** | 数据 → 出版级图（PNG + PDF + SVG）+ 图注，过三闸（越界 / 文件层 / 视觉） |
| **V-M7 论文装配 PAPER** | IMRaD → docx / md：逐节装配 + 自查 + Claim-Evidence 映射 + 交付卫生断言 |
| **V-M8 多赛道改写 TRACK** | 母版 → 目标赛道材料：匿名与口径按目标赛道重做（指针，不复制正文） |
| **V-M9 申报与答辩 APPLY** | 申报书 / PPT / QA 题库：结构装配与格式对标（不代做你的判断） |
| **V-M10 校准钩子 CAL** | 只读挂接你的私有校准（L2）：只声明边界，不把个人校准写成模块门禁 |
| **V-M11 编排器 ORCH** | runbook 选线 + 交接卡：输入 / 产物 / 门禁 / 降级 / 下一步 |
| **V-R 底座 BASE** | 环境档位 / 全链冒烟 / 故障速查 / 路径与资产卡 |

## 目录结构

```text
Vesi-Labflow/
├── BOOT.md                     冷启动索引（任何 agent / 人的第一读）
├── README.md / README.en.md    中文 / 英文总入口
├── AGENTS.md                   任意 code agent 的装载协议、CLI 约定、门禁 exit code、降级约定
├── QUICKSTART.md               5 分钟上手
├── VESI-CORE.md                人格与铁律（三模式 / 交付分级 / 思维铁律 / 溯源）
├── VESI-ENGINE.md              模块注册 / 数据流 / 门禁矩阵 / runbooks / 资产清单 / 交接卡
├── learnings.md                空白错题本模板 + 提炼机制
├── modules/                    12 个模块规格件（V-M1…V-M11 + V-R 底座）
├── workflows/                  运行手册 01–13 + _SHARED.md（共享纪律）+ D-ABSORB.md（吸收层）
├── templates/                  交付卡模板（精读笔记 / 证据表 / 设计卡 ×4 / 实验记录 / 图注 / CE 映射 …）
│   └── 申报书线/               申报书写作工作流 + 模板 + 生成脚本
├── references/                 方法卡与协议（检索式库 / 冷水证据 / 锚校准协议 / 装配 SOP / 故障速查 …）
├── tools/                      自检与计算（env_check · smoke_chain · stats_pipeline · nca · 拟合 · fig_samples/）
│   └── fig_samples/_out/       图件 demo 的**生成物样例**（可删可再生：跑对应 demo 脚本即重建）
├── scripts/                    交付门禁脚本（卫生断言 / 剂量换算 / 记录转写 / 一致性检查 …）
├── kb/                         自建知识库（空目录 + 自建说明）
├── requirements.txt            依赖清单
├── LICENSE / LICENSE-DOCS / THIRD-PARTY.md
├── CONTRIBUTING.md / CODE_OF_CONDUCT.md / SECURITY.md   贡献 / 行为准则 / 安全策略
├── .github/ISSUE_TEMPLATE/     缺陷与功能请求模板
└── .github/workflows/ci.yml    自检 + 冒烟
```

## 运行前提

- **Python 3.11+**（工具的运行基线；不用 3.12 独占语法）。
- **依赖**：`requirements.txt`（**分层**：必需 = numpy / scipy / pandas；交付门禁线 = PyYAML / pypdf；可选 = matplotlib / python-docx / Pillow；缺件按模块「降级」列处理）。
- 建议自建虚拟环境（`<venv>/`）并在其中安装依赖，避免污染系统解释器。
- **可选件**：OCR / 视觉能力、Word 自动化（Windows 专有）、LaTeX、中文字体。**缺件不阻塞**——模块表有「降级」列，缺件按降级路径执行并标 `[降级]`，工具输出 `SKIP` 并说明原因。
- **无服务、无数据库、无 API key、无强制联网**（联网仅用于文献检索，且有离线降级路径）。

## 冒烟自检（跑通即装好）

```bash
python tools/env_check.py --selftest            # 环境档位（T0 / T1 / T2）
python tools/smoke_chain.py --selftest          # 全链冒烟：数据 → 统计 → 图件 → 论文骨架（含黄金数值断言）
python tools/nca.py --selftest                  # 非房室分析（含个体维；末段 λz≤0 反例必被拦截）
python tools/compartment_fit.py --selftest      # 房室模型拟合
python tools/release_fit.py --selftest          # 释放模型拟合
python tools/stats_pipeline.py --selftest       # 统计管线（含配对用例）
python scripts/selftest_scripts.py              # 交付门禁脚本元自检
```

约定：全 PASS / SKIP 即 rc=0；**SKIP 不算 FAIL**（但须写明缺件原因）；FAIL 非零退出，必须处理。退出码语义统一为 `0` 通过 · `1` 失败 · `2` 用法错误 · `3` 依赖缺失未执行（全链 `SKIP`，非通过）。

## L2 自建（不随包分发）

| 自建项 | 作用 | 起步方式 |
|---|---|---|
| `kb/` | 你的知识库：文献笔记、检索记录、证据表、方法索引 | 按 `workflows/11-知识管理.md` 的 schema 起步 |
| `<共享层>/` | 可选的多 agent / 多人协作层（共享 SOP 与材料） | 单人使用可完全跳过；吸收机制见 `workflows/D-ABSORB.md` |
| `<校准台账>` | 私有校准数据（判据线 / 复盘记录 / 整改记录） | `templates/校准台账模板.md`（空白） |
| `<锚注册卡>/` | 私有锚注册（已知答案锚 / 已知档位锚样本） | `templates/锚注册卡模板.md`（空白）+ 填锚规程见 `references/outcome-anchor-protocol.md` |

> L2 是**可选增强**：只用包内 L0 也能跑完整条链；没有 L2 时相关模块走「降级」列。

## 学术诚信与 AI 使用声明

- **绝不编造**数据、结果与文献引用；不确定性如实汇报（体系局限、数据缺口、参数敏感性）。
- **核心实验、判断与论述由你本人负责**：本包提供方法、清单、代码骨架与结构，最终结论与文本由人落笔确认。
- **AI 使用透明**：按你所在机构 / 赛事 / 期刊的规定，声明所用 AI 工具的**名称、版本与使用范围**，并保留过程材料备查；未按要求声明的后果由使用者承担。
- **原始数据不改**：记录只追加不修改，原始文件只读归档；统计方法**实验前定稿**，为显著性而改分析方案属学术不端前兆。
- **三态标注**（事实 / 推断 / 假设）与**冷水证据**（交付前主动找否证）是常驻自查项，见 `VESI-CORE.md` 与 `references/cold-water-evidence.md`。

## 许可

- **代码**：MIT（见 `LICENSE`）。
- **文档与模板**：CC BY 4.0（见 `LICENSE-DOCS`）。
- **第三方件**：来源、许可与修改说明见 `THIRD-PARTY.md`；再分发前请先读它。

## 兼容性

本产品不依赖任何特定 agent / CLI / 调度器 / API key。

装载协议、门禁与冒烟全部由「可读文件 + 能跑 Python 的环境」组成——用它的是人还是任意 code agent，流程与产物一致；`AGENTS.md` 给 code agent 的装载口径，`BOOT.md` 给所有装载者的一句话入口。
