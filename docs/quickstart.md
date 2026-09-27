# 5 分钟上手

## 1. 安装（三种方式任选）

**pip（推荐）**

```bash
pip install vesi-labflow[all]   # [all] = 全套依赖（numpy/scipy/pandas/matplotlib/docx/pypdf/…）
```

**pip（最小）**

```bash
pip install vesi-labflow        # 只装命令入口；计算工具缺依赖时按契约 rc=3 诚实退出
```

**源码**

```bash
git clone https://github.com/WannaC77/Vesi-Labflow
cd Vesi-Labflow
python -m venv .venv
# 下文用 <venv> 指代虚拟环境目录（本仓示例目录名 .venv）
<venv>/Scripts/python -m pip install -r requirements.txt   # Windows
<venv>/bin/python     -m pip install -r requirements.txt   # Linux/macOS
```

## 2. 第一条命令：环境自检

```bash
vesi-env-check
```

列出各级依赖的就绪状态与降级路径（缺什么、哪些功能可走、哪些标注为未执行）。

## 3. 跑一次端到端冒烟

```bash
vesi-smoke-chain --selftest      # 全链冒烟 + 黄金数值断言（PK / 统计 / 拟合 / 图件 / 论文装配）
```

看到 `判定：PASS` 说明这条链在这台机器上全部可用。

## 4. 跑示例

```bash
python examples/nca_demo.py
```

## 退出码约定（全仓统一）

| 码 | 含义 |
|---|---|
| 0 | 通过 |
| 1 | 失败 |
| 2 | 用法 / 输入错误 |
| 3 | **依赖缺失未执行**（未执行 ≠ 通过） |

## 自定义根路径（进阶）

安装态默认使用随包数据；要指向自己的工作树时设 `LABFLOW_ROOT=<树根>`。
