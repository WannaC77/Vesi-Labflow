# 示例（examples/）

三个最小示例，**全部合成数据**、真跑判据、可直接进 CI：

| 示例 | 演示 | 命令 |
|---|---|---|
| `nca_demo.py` | NCA（非房室分析）跑一遍合成浓度-时间曲线 | `python examples/nca_demo.py` |
| `stats_demo.py` | 统计管线：两组比较 + 报告 | `python examples/stats_demo.py` |
| `release_fit_demo.py` | 释放曲线拟合（合成数据） | `python examples/release_fit_demo.py` |

## 运行前的依赖

- pip 安装：`pip install vesi-labflow[all]`
- 源码：`pip install -r requirements.txt`

缺依赖时示例按仓库契约以 `rc=3` 退出并给出补装提示（诚实降级，不假装通过）。

## 安装态如何跑

同一份示例随包分发在 `vesi_labflow/_tree/examples/`，直接对该目录里的同名脚本运行即可：

```bash
python <site-packages>/vesi_labflow/_tree/examples/nca_demo.py
```
