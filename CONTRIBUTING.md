# 贡献指南 / Contributing · Vesi-Labflow

感谢你考虑为本项目做贡献。本仓库是「工作流 + 可执行工具」的开源包，质量门槛偏**可复核**：
凡结论都要能复跑，凡判据都要**能失败**。

## 可以贡献什么

| 类型 | 例子 | 需要带的证据 |
|---|---|---|
| 缺陷报告 | 工具报错、口径不一致、文档与磁盘不符 | 复现命令 + 实际输出 + 期望输出（见 issue 模板） |
| 领域方法 | 新的 PK / 制剂 / 统计口径、检验选择规则 | 公式或文献出处 + 与该口径一致的测试用例 |
| 工具改进 | 新增 `--selftest` 断言、负例夹具、退出码语义修正 | 自检输出（正例 PASS + 负例 FAIL 各一） |
| 文档 | 术语表、故障速查、示例数据 | 与包内正本（`references/路径与资产清单.md` / `VESI-ENGINE.md`）不冲突 |
| 赛道适配 | 把工作流改写到你的目标赛道 | 只改口径与匿名面，不改机制 |

## 硬性要求（review 会直接打回）

1. **不改私有数据**：不要提交真实实验数据、他人材料、机构名、个人身份信息。
2. **不引入私有依赖**：本包不依赖任何特定 agent / CLI / 调度器 / API key。
3. **工具必须可自检**：新增 `tools/*.py` 必须带 `--selftest`，且自检里含**必须失败的负例**。
4. **退出码语义统一**：`0` 通过 · `1` 失败 · `2` 用法/输入错误 · `3` 依赖缺失未执行（**未执行 ≠ 通过**）。
5. **文本件**：UTF-8 无 BOM、LF 行尾、包内相对路径（正斜杠）、不写绝对路径与本机路径。
6. **不在包内留生成物**：自检 / 冒烟产物落 `tools/_smoke_out/`（已 gitignore），提交前清理。

## 开发与自检（本地）

```bash
python -m venv <venv> && <venv>/bin/pip install -r requirements.txt   # Windows: <venv>\Scripts\pip
python tools/env_check.py --selftest        # 环境档位 T0/T1/T2
python tools/smoke_chain.py --selftest      # 全链冒烟（含黄金数值断言）
python tools/nca.py --selftest              # 领域工具逐个自检
python scripts/selftest_scripts.py          # 交付门禁脚本元自检
python scripts/verify_bundle.py --root .    # 包结构自校验
```

改代码后请同时跑：`tools/*.py --selftest`（全部）+ 上面两条。CI（`.github/workflows/ci.yml`）执行同一组命令，
本地等价脚本见 `QUICKSTART.md`。

## 提交规范

- 一个提交只做一件事；提交信息说清**动机**（中文一句话即可）。
- 涉及口径变更的提交，请同步更新受影响的 `workflows/`、`references/路径与资产清单.md`、`CHANGELOG.md`。
- 提交前自查：`git status` 里不应出现自检产物（`_smoke_out/`）、Python 缓存目录（`__pycache__`）、数据文件、本机路径。

## 评审口径

- 结论要有证据（复跑命令 + 输出）；「我觉得」不是证据。
- 判据要能失败：只证明「能通过」的测试不算测试。
- 允许 `SKIP`（缺件降级），但必须写明缺件原因，且 `SKIP` 不得被读成通过。

## 许可

提交即表示你同意按本仓库许可分发你的贡献：代码 MIT（`LICENSE`）、文档 CC BY 4.0（`LICENSE-DOCS`）。
