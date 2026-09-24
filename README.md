# Vesi-Labflow · 药学与生命科学科研工作流（中文版）

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![docs](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)
![smoke](https://img.shields.io/badge/smoke-full%20chain%20PASS-brightgreen)

> **它不替你思考，也不替你下结论；它保证的是：你做的每一步都留下可核查的证据链。**
> **英文版 / English version**：`README.en.md`（本文件为中文正本；同步承诺见 `CONTRIBUTING.md`「双语同步 SLA」）
> **冷启动**：只有 5 分钟？先读 `BOOT.md`，再读 `QUICKSTART.md`。
> **CI**：`.github/workflows/ci.yml` 在每次 push / PR 上跑自检与冒烟（Python 3.11 + 3.13 双版本）；CI 徽章与仓库链接在仓库 URL 确定后同批补上。

---

## 一句话定位

**Vesi-Labflow 是一套「手册 + 工具链」形态的科研工作流引擎**：把「**文献 → 实验设计 → 数据记录 → 统计分析 → 论文装配**」拆成 **11 个模块 + 1 个底座**，每个模块都带**可执行门禁**与**显式降级路径**——方法写在 `workflows/` 与 `references/`，计算与自检交给 `tools/` 与 `scripts/`。任何能读文件、能跑 Python 的人或 code agent，按三步装载即可开工。

## 为什么需要它（Why）

- 实验做完才发现**记录对不上、口径不一致、图注与数据不符**——返工成本远高于当场记录：本包把「记录 → 统计 → 图件 → 论文」做成一条**带门禁的流水线**，每步产物可复核；
- 文献读了记不住、引用查不回：精读笔记 + 证据表 + 三态标注（事实 / 推断 / 假设）把文献变成**可溯源的资产**，而不是一堆 PDF；
- 缺件是常态（没装 LaTeX、没有 Word 自动化、OCR 不可用）：本包把「降级」写成制度——`[降级]` / `SKIP` 一律如实标注并给出替代路径，**绝不假称通过**。

## 目标用户

- **药学方向**（药剂 / 药代 / 生物分析 / 制剂表征）的本科生与研究生；
- **生命科学方向**（细胞 / 分子 / 动物实验）的本科生与研究生；
- **学科竞赛与创新创业训练计划队伍**——需要把「做了什么、凭什么这么做」讲清楚的团队；
- **需要可核查流程的 AI 辅助科研者**——想用 AI 提效，但不想让流程变成黑箱的人。

**门槛**：不需要会 LaTeX、不需要统计软件、不需要写代码——会读文件、能跑 `python` 即可（每个自检与计算脚本都带 `--selftest`，命令照抄 `QUICKSTART.md`）；实验判断与论文论述仍由你本人负责。

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
├── scripts/                    交付门禁脚本（卫生断言 / 剂量换算 / 记录转写 / 一致性检查 / verify_manifest …）
├── kb/                         自建知识库（空目录 + 自建说明）
├── docs/images/                真实运行生成的样张（本文件「5 分钟你会拿到什么」引用）
├── requirements.txt            依赖清单
├── LICENSE / LICENSE-DOCS / THIRD-PARTY.md
├── CONTRIBUTING.md / CODE_OF_CONDUCT.md / SECURITY.md / SUPPORT.md   贡献 / 行为准则 / 安全 / 支持
├── MAINTAINERS.md / .editorconfig / .gitattributes / .pre-commit-config.yaml   维护者 / 开发约定
├── .github/                    CI（workflows/ci.yml）· issue 与 PR 模板 · CODEOWNERS · dependabot
└── CHANGELOG.md / CITATION.cff
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

## 它从哪里长出来（实战演变）

**Origin timeline**：本包骨架脱胎于本人 2026 年 8 月起的科研工作流（初版 2026-08-13 建目录骨架，2026-08-30 完成主题适配与人格重构），此后经一个目标赛道课题与一次目标赛道真实使用迭代至 9 月中；开源剥离工作自 2026-09-22 启动（本包 v1.0.0）。

本包不是纸上设计——方法与门禁来自上述真实运行的科研流程，以下每条都能在交付台账里查到磁盘证据：

**成功案例**
- **目标赛道实验设计三轮过审**：v4 → v5.1 → v7，模拟网评体系（双锚校准）把设计分从 9.0 修到 9.25，且真值锚（已知答案锚）Δ0——分数回升有逐项实据，不是尺子放水。
- **冷水证据库 6 条引文**全部经 NCBI E-utilities 逐条实证后才入卡——"引用须可溯源"不是口号，是被"差点放行无关文献"事件逼出来的机制。
- **竞争型交付**：申报材料按用户反馈 24h 内完成 v1→v2 迭代，每处勘误都有知识库事实依据。

**失败典型（本包最值钱的部分）**
- **编造 PMID 事件**：一次主题重构中，工作流曾用 10 条编造文献替换了 6 条实证文献，还静默删除了两个工作流——抽查 4 条全为无关文献。现在包内所有文献元数据强制过 NCBI 实证，三态标注与冷水证据机制就是这次事故的产物。
- **跨 agent 协作数字不符**：外部 agent 交付清单自报"25/5"，逐条实点却为"4/23/7"——由此固化了"归并只认逐条复点，不采自报汇总"的纪律。

> 更多原始记录见 `learnings.md`（自改进闭环的格式说明——数据本身不随包，机制与格式随包）。

## 学术诚信与 AI 使用声明

- **绝不编造**数据、结果与文献引用；不确定性如实汇报（体系局限、数据缺口、参数敏感性）。
- **核心实验、判断与论述由你本人负责**：本包提供方法、清单、代码骨架与结构，最终结论与文本由人落笔确认。
- **AI 使用透明**：按你所在机构 / 赛事 / 期刊的规定，声明所用 AI 工具的**名称、版本与使用范围**，并保留过程材料备查；未按要求声明的后果由使用者承担。
- **原始数据不改**：记录只追加不修改，原始文件只读归档；统计方法**实验前定稿**，为显著性而改分析方案属学术不端前兆。
- **三态标注**（事实 / 推断 / 假设）与**冷水证据**（交付前主动找否证）是常驻自查项，见 `VESI-CORE.md` 与 `references/cold-water-evidence.md`。

## 5 分钟你会拿到什么

不读参数、不听承诺——直接看真跑出来的样子。以下产物都是**本仓库真实运行生成**（合成数据、固定 seed）：

| 产物 | 它是什么 | 你怎么拿到它 |
|---|---|---|
| ![PK 血药浓度-时间半对数曲线（两组，均值±SD）](docs/images/fig1_pk_curve.png) | `tools/fig_samples/fig1_pk_curve.py` 的血药浓度-时间曲线（两组、均值 ± SD + 个体散点） | `QUICKSTART.md` 第 3 步冒烟链同款管线的样例输出——把 `fig_samples/` 里的脚本换成你自己的数据就能得到同形状 |
| ![体外释放曲线一阶与 Higuchi 拟合](docs/images/fig5_release.png) | 体外释放实测点 + 一阶 & Higuchi 模型拟合线（R² 打印在终端） | `QUICKSTART.md` 第 5 步第 3 条（`workflows/04-体外释放.md` + `tools/release_fit.py`）做到的事，样例脚本见 `fig_samples/fig5_release.py` |
| ![PK 参数柱状图（Cmax/t½/MRT 等，含误差棒与显著性标注）](docs/images/fig3_pk_bar.png) | `tools/fig_samples/fig3_pk_bar.py` 的 1×3 参数面板 | `QUICKSTART.md` 第 3 步之后、第 5 步第 4 条统计/可视化环节的典型产物形态 |

整个样例集的运行方式见 `tools/fig_samples/README.md`；想逐张换真实数据，改对应脚本的数据区即可。

## 维护与发布

- **维护者 / 支持**：`MAINTAINERS.md`（守门范围）· `SUPPORT.md`（提问前先跑自检；首应 ≤ 7 天）
- **版本与回滚**：`CHANGELOG.md`（SemVer tag 约定 + 逐版条目）——按 tag 回退到已知可用版本
- **中英同步**：中文正本 → 英文版 ≤ 7 天（承诺见 `CONTRIBUTING.md`「双语同步 SLA」）
- **提交 PR 前**：`pip install pre-commit && pre-commit run --all-files`（钩子清单见 `.pre-commit-config.yaml`）
- **文档-磁盘一致性**：`python scripts/verify_manifest.py --root .`（缺件 → rc=1；用法错误 → rc=2；判据自带 `--selftest`）

## 许可

- **代码**：MIT（见 `LICENSE`）。
- **文档与模板**：CC BY 4.0（见 `LICENSE-DOCS`）。
- **第三方件**：来源、许可与修改说明见 `THIRD-PARTY.md`；再分发前请先读它。

## 兼容性

本产品不依赖任何特定 agent / CLI / 调度器 / API key。

装载协议、门禁与冒烟全部由「可读文件 + 能跑 Python 的环境」组成——用它的是人还是任意 code agent，流程与产物一致；`AGENTS.md` 给 code agent 的装载口径，`BOOT.md` 给所有装载者的一句话入口。
