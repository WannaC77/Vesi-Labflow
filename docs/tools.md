# 工具索引

## 命令（pip 安装后直接可用）

| 命令 | 用途 |
|---|---|
| `vesi-env-check` | 环境自检与档位（缺件清单 + 降级路径）；`--selftest` |
| `vesi-smoke-chain` | 端到端冒烟：PK → 统计 → 拟合 → 图件 → 论文装配（含黄金数值断言）；`--selftest` |
| `vesi-nca` | NCA（非房室分析）：AUC / λz / t½ / CL 等独立复算；`--selftest` · `--demo` |
| `vesi-stats-pipeline` | 统计管线：正态 / 效应量+CI / 多重比较三证齐；`--selftest` |
| `vesi-compartment-fit` | 房室模型拟合；`--selftest` |
| `vesi-release-fit` | 释放曲线拟合；`--selftest` · `--demo` |
| `vesi-verify-bundle` | 包结构自校验（`--root <树根>`） |
| `vesi-verify-manifest` | 文档-磁盘一致性自证（`--root <树根>`） |

源码模式下对应 `python tools/<名>.py` 与 `python scripts/<名>.py`。

## 图件样张（tools/fig_samples/）

PK 曲线 / 组织分布热图 / 释放曲线等 6 组样张（png / pdf / svg 三件），随包分发在 `docs/images/`。

## 退出码约定

全仓统一：`0` 通过 · `1` 失败 · `2` 用法错误 · `3` 依赖缺失未执行（未执行 ≠ 通过）。
