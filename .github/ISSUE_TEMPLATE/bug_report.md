---
name: 缺陷报告 / Bug report
about: 工具报错、口径不一致、文档与磁盘不符
title: "[bug] "
labels: bug
---

## 影响范围

- 包名 / 版本（`README.md` 或 `CHANGELOG.md` 里的版本号）：
- 受影响文件或工具（如 `tools/env_check.py`）：
- 解释器版本（`python -V`）与操作系统：

## 复现步骤

```bash
# 1. 请粘贴**可直接复跑**的命令（不要用真实实验数据，用合成数据或最小样例）
# 2.
```

## 实际结果

```text
（粘贴真实输出；如报错请含退出码：echo $? / echo %ERRORLEVEL%）
```

## 期望结果

（你期望它输出什么；若涉及口径，请给出依据：文档路径、公式或文献）

## 已做的自检

- [ ] `python tools/env_check.py --selftest`
- [ ] `python tools/smoke_chain.py --selftest`
- [ ] 对应工具的 `--selftest`（如 `python tools/nca.py --selftest`）
- [ ] 其它（请写明）：

```text
（粘贴自检输出的结论行）
```

## 备注

- 是否在**干净副本**里复现（避免 `_smoke_out/` 等产物干扰）：
- 其它上下文：
