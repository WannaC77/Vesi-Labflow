# examples —— 可运行示例（Vesi-Labflow）

本目录是「5 分钟上手」的最小可跑示例，全部使用**合成数据**，不含任何真实实验数据。

| 示例 | 演示 | 依赖 |
|---|---|---|
| `nca_demo.py` | NCA（非房室分析）跑一遍合成 PK 曲线 | `pip install vesi-labflow[all]`（或仓库内 `pip install -r requirements.txt`） |
| `stats_demo.py` | 统计管线：两组比较 + 报告 | 同上 |
| `release_fit_demo.py` | 释放曲线拟合（合成数据） | 同上 |

## 运行

```bash
# ① 仓库内（推荐先在仓库根装好依赖）
python examples/nca_demo.py
python examples/stats_demo.py
python examples/release_fit_demo.py

# ② pip 安装后：同一份示例随包在 vesi_labflow/_tree/examples/，
#    直接对该目录里的同名脚本运行即可（python <path>/nca_demo.py）。
```

## 退出码约定

`0` 通过 · `1` 失败 · `2` 用法错误 · `3` 依赖缺失未执行（未执行 ≠ 通过）。
缺依赖时示例会打印补装提示并按 `3` 退出。
