# AGENTS.md — code agent 装载协议（Vesi-Labflow）

> 本文件是**通用入口**：任何 code agent 按本文件即可装载本仓库（已在 OpenCode、Trae 与纯 shell+Python 执行器上实测；Cursor / Codex / Aider / Windsurf 等按 §5 配置）。
> **本产品不依赖**任何特定 agent、私有 skill 注册、junction、cron 或 MCP；装载只依赖「读文件 + 跑 Python」。

## 1. 三步装载（与 BOOT.md 一致）

```
1. 读 BOOT.md → 读 VESI-CORE.md → 读 VESI-ENGINE.md
2. 按用户任务选 runbook，加载对应 workflows/NN-*.md + workflows/_SHARED.md
3. 需要计算/门禁时调用 tools/ 或 scripts/（见 §3）；缺件标 [降级] 并继续
```

**渐进披露预算**：BOOT(≤2 KB) → CORE/ENGINE → workflows/tools。不要把整仓读进上下文。

## 2. 本仓库的结构契约

| 目录 | 作用 | 装载时机 |
|---|---|---|
| `VESI-CORE.md` | 人格、铁律、模块表、装载协议 | 必读 |
| `VESI-ENGINE.md` | 模块能力矩阵、门禁、环境卡 | 必读 |
| `modules/` | 模块说明（每个含门禁要点与**降级列**） | 按需 |
| `workflows/` | 运行手册（`01–13` + `_SHARED.md` + `D-ABSORB.md`） | 按任务 |
| `templates/` | 设计卡 / 记录模板 / 图注模板 / 校准台账 / 锚注册卡 | 按任务 |
| `references/` | 方法论文档（锚校准 / 统计口径 / 图件管线 / 装配 SOP / 故障速查） | 按需 |
| `tools/` | 可执行工具（NCA · 房室拟合 · 释放拟合 · 统计管线 · 冒烟链 · 环境自检） | 计算与自检 |
| `scripts/` | 交付门禁脚本（卫生断言 / 剂量换算 / 记录转写 / 元数据清理 / 一致性检查 …） | 交付前 |
| `kb/` | 用户自建知识库（空目录，见 `kb/README.md`） | 可选 |

## 3. 工具 CLI 契约（统一）

```
python tools/env_check.py [--selftest] [--json]
python tools/smoke_chain.py [--selftest] [--root <路径>]
python tools/<领域工具>.py --selftest        # nca / compartment_fit / release_fit / stats_pipeline
python scripts/<checker>.py <args>           # exit 0=PASS 1=FAIL 2=usage
```

- 所有脚本：**无用户绝对路径**；`--help` 可用；依赖见 `requirements.txt`
- 门禁脚本**必须可失败**（自检里带反例）；`--selftest` 用于验证工具自身
- 退出码语义：`0` 通过 · `1` 失败 · `2` 用法错误

## 4. 降级约定（诚实性要求）

| 缺件 | 处理 |
|---|---|
| OCR / 视觉能力 | 记录转写走人工，标 `[降级]`；不伪造识别结果 |
| Word COM（Windows 专有） | 文档生成改 Markdown / 手工另存；标 `[降级]` |
| LaTeX / CJK 字体 | 论文产出 `.tex` + 编译说明；图注改英文 |
| 依赖（numpy / scipy / matplotlib …） | 回退系统 Python 并声明版本；相关自检记 `SKIP` |

**禁止**：假装成功、伪造数值、把 SKIP 写成 PASS。

## 5. agent 侧配置片段（可选）

- **Cursor / Windsurf**：把本文件加入工作区规则（`.cursorrules` 或规则文件引用 `AGENTS.md`）。
- **CLI agent（Codex / Aider 等）**：把 `AGENTS.md` 放进 system 上下文，或让 agent 先读它。
- **纯 API / 裸 LLM**：system prompt 注入 `BOOT.md` 全文，再按需读取 `VESI-CORE.md`。

## 6. 禁止项

包内不存在、也不应创建：私有 agent 的正本路由文件、必须安装的私有 skill、cron 正本依赖、任何指向仓库外的绝对路径。
