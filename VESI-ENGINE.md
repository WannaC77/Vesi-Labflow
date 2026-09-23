# VESI-ENGINE — 生成引擎（模块注册 · 门禁 · runbook · 装载）

> **用途 / Purpose**：以「实验 → 数据 → 证据链」为中心的科研生成引擎（生命科学 / 纳米制剂 / 多赛道并存；人机混编 HITL）。
> **装载 / Mount**：任何可读文件 + 跑 Python 的人或 agent 按 §0 三步装载；不依赖任何 agent 私有机制。
> **正本 / SSOT**：细节正本在 `workflows/` 与各模块规格件；**本文件只索引，不复制正文**。
> **版本 / Version**：v1.2（2026-09-22）· 模块 11 + 底座 · 执行方：任何可读文件 + 跑 Python 者（无私有依赖）
> **分层 / Layers**：L0 领域能力（本文件 · `modules/` · `templates/` · `tools/` · `references/`）｜L1 配置剖面（`VESI-CORE.md` 轨道开关节 + 轨侧 `track-config.md`）｜L2 本机协作（PERSONAS / junction / 个人台账与锚——只读引用，**不进 L0 必载**）
> **开源兼容**：本文件全部路径为系统根相对；L0 不依赖个人校准数值；profile 可拆（轨道/赛事参数在 L1）。

## 0 · 装载协议（三步 · 任意 agent）

1. 读 `VESI-CORE.md`（人格与铁律）→ 读本文件（模块与 runbook）。
2. 按所选 runbook 的装载清单加载 **L0/L1** 件；**L2 可选**。缺件按模块表「降级」列执行并标 `[降级]`。
3. 产物落盘 → 过对应门禁（§3）→ 记交接卡（§7）。

**环境自检**：`tools/env_check.py`（已落盘；`--selftest` 可自证；档位 T0/T1/T2）；链级冒烟 `tools/smoke_chain.py`。

**路径基点（SSOT）**——本文件内路径均以**包根**为基点（包根 = 本文件所在目录；迁移时在新根下重建同名目录即可）：

| 基点 | 覆盖 |
|---|---|
| `./`（包根） | ENGINE · modules · templates · tools · references · workflows · scripts |
| `templates/申报书线/` | 申报书线正本（流程件；内容件不入库） |
| `scripts/` · `track-config.md` | 赛轨侧脚本 · 赛道配置 / 校准台账（自建） |
| `kb/` | 知识库（空目录开局；L2 自建内容不入库） |

## 1 · 模块注册表（L0 · interface: loading → output → gates → fallback）

| # | 模块 | 一句话 | 装载（指针） | 产物 | 门禁要点 | 降级 |
|---|---|---|---|---|---|---|
| V-M1 | 文献 LIT | 检索→精读→证据表 | `workflows/02` | 精读笔记 / 证据表 / 检索记录 | 元数据可核验；三态；检索式可复跑 | 无技能机制 → E-utilities 手工 + `[降级]` |
| V-M2 | 设计工坊 DESIGN | 问题→设计卡 | `workflows/03–07` | 设计卡（变量/对照/n/统计预注册/剂量链/伦理） | 对照齐；n 与 power 记录；统计实验前定稿；换算可复算 | 按 03–07 参数表逐项填卡 |
| V-M3 | 记录线 RECORD | 照片/口述→结构化记录 | `workflows/12`；`scripts/transcribe_record.py` | 结构化实验记录 + 原始文件只读归档 | 字段齐；原始数据不可改；记录↔文件路径对应 | 口述+代录并标注执行者 |
| V-M4 | 统计台 STAT ★ | 数据→可复核分析 | `workflows/08` | 分析报告 md + 图（走 M6） | 三证齐（正态证据 / 效应量+CI / 多重比较记录）；n=3 纪律；图闸 | 按 08 速查手工 + 声明 |
| V-M5 | PK/领域台 ★ | NCA/房室/释放/排泄 | `workflows/05–07` | NCA / 房室 / 释放拟合 / 排泄累积 报告字段 | 参数完整+口径声明；拟合优度证据；包裹/游离质控要点 | 外部软件手工表 + 核对 |
| V-M6 | 图件车间 FIG | 出版级图（三闸） | 图件规范；`tools/fig_samples/`（图件样例）· `templates/图注模板.md`；`workflows/08` 图型 | PNG+PDF+SVG + 图注 | audit / figcheck / vision 三闸（无 vision 则双闸+人检） | 代码出图 + 人工复核 |
| V-M7 | 论文装配 PAPER | IMRaD→docx | `workflows/09`；`scripts/assert_delivery_hygiene.py` | 论文/章节 + 自查 + 引用表 | 逐节 checklist；Claim-Evidence；hygiene FAIL=0；**docx 禁令见故障卡（另存 styleId 回退）** | 纯文本/md 装配 + 门禁清单 |
| V-M8 | 三轨改写 TRACK | 母版→目标轨 | `track-config.md`、`track-config.md` + CORE 轨道节 | 目标轨材料 | 匿名按目标轨重做；口径不串台；一稿多投禁令；数据单一正本 | 手工过改写卡 |
| V-M9 | 申报与答辩 APPLY | 申报书/PPT/QA | `templates/申报书线/申报书写作工作流.md` | 申报书 / PPT / QA | 格式对标；六栏结构；自查表 | 纯 md 版 + 人检 |
| V-M10 | 校准钩子 CAL | 只读挂接 L2 锚协议 | `references/outcome-anchor-protocol.md`（**存在性**） | 无（声明与边界） | 只声明「存在校准协议文件、生成侧只读挂接」；个人校准 ≠ 模块门禁 | 不挂接亦可走全链 |
| V-M11 | 编排器 ORCH | runbook+交接卡 | 本文件 §4/§7 | 交接卡 | 每交付一次交接记录 | 口述交接 + 记录 |
| V-R | 底座 BASE | 环境/冒烟/故障/路径卡 | `references/路径与资产清单.md`；`tools/{env_check,smoke_chain}.py` | 环境档位 / 冒烟结果 / 故障卡 | env_check；脚本冒烟 rc=0 | 手工核 §6 |

## 2 · 数据流契约（L0）

```text
M1 证据表 → M2 设计卡（引用文献）→ M3 记录集（引用设计卡）
M3 → M4 分析报告 → M6 图件 → M7 论文
M4/M5 → M7 → M8 三轨改写（指针，不复制正文）→ M9 申报/答辩
M10 校准 ⇄ 各模块（L2 只读挂接，不进 L0 必载）
```

## 3 · 门禁矩阵

| 阶段 | 机检/清单 | 通过线 | 留证 |
|---|---|---|---|
| 文献入库 | esummary/元数据核对 | 可追溯 | 笔记 |
| 设计定稿 | 换算复算 + power 记录 | 一致 | 设计卡 |
| 记录归档 | 字段比对 | 字段齐 | 记录 |
| 数据分析 | `tools/stats_pipeline.py` | 三证齐 | 报告 md |
| PK | `tools/{nca,compartment_fit,release_fit}.py` 合成断言 + 参数表 | PASS+完整 | 报告 |
| 图件 | 三闸/双闸 | 过闸 | 记录 |
| docx | `assert_delivery_hygiene` | FAIL=0 | 输出 |
| 生科提交 | 匿名三层 + 格式 | 全过 | 扫描记录 |
| 跨轨 | 改写卡勾选 | 全过 | 卡 |
| **未来兼容** | 新建 L0 无用户绝对路径（盘符用户目录 / 本地应用数据目录等环境变量形态路径）；资产清单可解析 | 零命中 | grep 输出 |

## 4 · Runbooks

| # | 线 | 步骤 | 产物 |
|---|---|---|---|
| RB-V1 | 申报书线 | M1 → M2 → M9 → 格式对标 | 申报书 + 自查 |
| RB-V2 | 方案线 | M1 → M2 设计卡 → 审 | 设计卡 |
| RB-V3 | 数据线 | M3 → M4 → M5 → M6 → 归档 | 记录 + 报告 + 图 |
| RB-V4 | 论文线 | M4/M5 → M7 → M6 → Claim → 断言 | 论文 + 自查 |
| RB-V5 | 答辩线 | M7 → M9 QA/PPT | PPT + QA |
| RB-V6 | 跨轨线 | 母版 → M8 → 目标轨门禁 | 目标轨材料 |

## 5 · 资产清单（L0 抬包清单 · 新增件落盘即登记）

| 件名 | 相对路径 | 版本 | 模块 | 层 | 状态 |
|---|---|---|---|---|---|
| 引擎（本文件） | `VESI-ENGINE.md` | v1.0 | V-M11 | L0 | ✅ |
| SSOT 卡 | `references/路径与资产清单.md` | v1.0 | V-R | L0 | ✅ |
| 工作流正本 01–13 | `workflows/01–13` | — | 全域 | L0 既有·**正文冻结** | ✅ |
| 工作流共享层 | `workflows/_SHARED.md` | — | 全域 | L0 既有 | ✅ |
| 材料吸收层 | `workflows/D-ABSORB.md` | — | 全域 | L0 既有 | ✅ |
| 冷水证据 | `references/cold-water-evidence.md` | — | V-M1/M6 | L0 既有 | ✅ |
| 校准协议（只读挂接） | `references/outcome-anchor-protocol.md` | v1.7 | V-M10 | L0(协议) / L2(数据) | ✅ |
| 行为测试最小集 | `references/behavioral-tests-minimal.md` | — | V-R | L0 既有 | ✅ |
| 申报书线 | `templates/申报书线/`（申报书写作工作流 + 模板 + 生成脚本 + 一键生成工作流） | — | V-M9 | L0 既有 | ✅ |
| 轨侧脚本（本仓 `scripts/`） | `scripts/`（交付门禁集：卫生断言 / 剂量换算 / 记录转写 / 元数据清理 / 跨文档一致性 / 自然度 / 重复预检 / 引用编号 / 包结构校验 / 元自检） | L0 既有 | ✅ |
| 轨侧脚本（并轨件） | `scripts/`（15 件 .py：verify_bundle / consistency_check / naturalness_check / precheck_similarity / ref_numberizer / selftest_scripts / assert_delivery_hygiene / check_dose / clean_pdf_meta / crop_zoom / dump_docx_full / transcribe_record / tile_image / batch_ocr / delivery_gate_check） | — | V-M8/R | L0 既有 | ✅ |
| 轨侧配置 | `track-config.md`、`track-config.md` | — | V-M8 | L1 轨侧 | ✅ |
| 模块规格件 ×12 | `modules/V-M*/MODULE.md`（四件：目的/接口/门禁/降级） | v1.0 | 各模块 | L0 | ✅ |
| 模板集 ×13 | `templates/`（精读笔记 / 证据表 / 设计卡×4 / 实验记录 / 图注 / Claim-Evidence / QA题库 / 申报-中期-结题映射 / 报告模板-排泄累积 / 报告模板-组织分布与靶向） | v1.0 | V-M1–M9 | L0 | ✅ |
| 工具集 | `tools/`（env_check / stats_pipeline / smoke_chain / nca / compartment_fit / release_fit / fig_samples×8） | v1.0 | V-M4/M5/M6/R | L0 | ✅ |
| 参考卡 ×6 | `references/`（检索式库 / 数据条目字典 / 论文装配SOP / 跨轨改写卡 / 引用格式卡 / 故障速查卡） | v1.0 | 各模块 | L0 | ✅ |

## 6 · 环境卡（以本机 `env_check` 实测为准）

| 项 | 值 |
|---|---|
| 参考解释器 | Python 3.11+（推荐 3.13；`tools/env_check.py` 自探测依赖最全的解释器，不写死路径） |
| 虚拟环境（可选） | 自建 `<venv>`；缺件时回退系统 Python 并按模块「降级」列声明 |
| 可选件 | OCR 脚本（batch_ocr）/ Word COM（word_update_save_pdf）/ PDF 渲染（render_docx_pdf）——缺件按模块降级列声明 |

> **档位以本机 `env_check.py` 输出为准**：本卡不记录任何特定机器的实测值（T0/T1/T2 为连续达标口径——低档缺件会把整体档位压到该档；报告另给「分档可用性」逐档说明）。

## 7 · 交接卡模板（V-M11 · 模块版）

```markdown
## 交接卡 <日期> · <模块>
- 输入：<上游产物 + 路径>
- 产物：<落盘路径 + 版本>
- 门禁：<过了哪条 + 留证路径>
- 降级/未决：<[降级] 标记项；待裁定项>
- 下一步：<runbook / 节点>
```

## 8 · 维护纪律

- 新增 L0 件：四件齐（目的 / 接口 / 门禁 / 降级）→ 落盘 → 登记 §5 → 过「未来兼容」门（路径 grep）。
- 本文件**禁止抄写 workflows 正文**；模块细节进 `modules/` 规格件，过程细节进 workflows。
- L1/L2 变更（轨道/赛事/个人台账）**不阻塞** L0；L0 门禁不引用个人校准数值与个人分数。
- 每次修改本文件，在文末追加一行变更记录。

## 9 · 附录 A · docx 管线卡（V-M7）

1. **装配**：md/文本正稿 → python-docx 生成（正稿即交付源；避免中间态经 Word 编辑）。
2. **域**：TOC/PAGE 用域；Word 保存会吞 `w:updateFields` → zip 级回补（故障速查卡 §1.2）。
3. **交付件禁止再经 Word 另存**——styleId 回退实测坑（故障速查卡 §1.1）；必须改时先枚举实际 styleId 再改、逐级断言。
4. **断言**：`scripts/assert_delivery_hygiene.py <docx>` FAIL=0（字面标记/占位/域核查）。
5. **匿名轨**：`transcribe_record.py`（内部版→匿名版）+ `clean_pdf_meta.py`（元数据）+ 页脚域核查。
6. **渲染验收**：pymupdf 渲染目视（防空框；故障速查卡 §4.1）。

---

**变更记录**
- v1.0（2026-09-21 · 生成侧强化批 2）：骨架建立（装载协议 / 模块注册 ×12 / 数据流 / 门禁矩阵 / runbooks / 资产清单 / 环境卡 / 交接卡 / 维护纪律）。
- v1.1（2026-09-21 · 生成侧强化批 3 · 总装）：模块规格件 ×12 / 模板集 ×13 / 工具集（env_check · stats_pipeline · smoke_chain · nca · compartment_fit · release_fit · fig_samples）/ 参考卡 ×6 全部落盘并登记；门禁行挂接实路径；新增 §9 附录 A docx 管线卡；轨侧脚本 +check_dose。
- v1.2（2026-09-22 · 开源发布批）：资产清单对齐（轨侧脚本件数与文件名、自检脚本指针改名同步）；吸收层回灌改为工作流内清单（手工过卡，不再指向独立脚本）；跨系统参考件 → 仓内件；§0 路径基点改为包根口径；环境卡改为以本机 env_check 实测为准；退出码补 `3`（依赖缺失未执行）。
