# fig_samples —— 出版级图件样例集（vesi / V-M6 图件车间）

> **用途**：给「统计台 → 图件 → 论文」这条链提供**可直接改成真实数据**的 6 类样板图。
> 每个脚本都是独立可跑的单图：自带合成数据（固定 seed）、统一风格、三格式落盘、关键数值打印。
> **定位**：样例 = **形状与流程**的参照，**不是**本课题的结论图；换成真实数据前不得进论文。

---

## 1 · 文件清单

| 文件 | 作用 |
|---|---|
| `style_vesi.py` | 统一风格模块：rcParams（dpi=300 / 字号 / 线宽 / 配色 / 去顶右边框）、三格式落盘、中文字体探测与缺字形防线、`sig_bar` / `trapz` 等小工具 |
| `fig1_pk_curve.py` | 血药浓度-时间半对数曲线（均值 ± SD + 个体散点，两组） |
| `fig2_tissue_heatmap.py` | 组织分布热图（组织 × 时间点，两组并排共享色标） |
| `fig3_pk_bar.py` | PK 参数柱状图（1×3 面板，含误差棒与显著性标注） |
| `fig4_excretion.py` | 累积排泄率曲线（胆汁/尿/粪/总量 × 两组） |
| `fig5_release.py` | 体外释放曲线（实测点 + 一阶 & Higuchi 模型拟合线） |
| `fig6_char.py` | 制剂表征（粒径分布 / Zeta 电位分布 / 包封率-载药量柱状图） |
| `_out/` | **运行产物目录**（自动创建）：`<stem>.png` + `<stem>.pdf` + `<stem>.svg` |

## 2 · 运行方式

```bash
# 系统 Python（3.13，已装 matplotlib / numpy）直跑；每个脚本 rc=0 且 _out/ 出现三格式文件
python tools/fig_samples/fig1_pk_curve.py
python tools/fig_samples/fig2_tissue_heatmap.py
python tools/fig_samples/fig3_pk_bar.py
python tools/fig_samples/fig4_excretion.py
python tools/fig_samples/fig5_release.py
python tools/fig_samples/fig6_char.py
```

- 脚本**不依赖当前工作目录**：落盘目录按 `style_vesi.py` 自身位置解析为 `<fig_samples>/_out/`。
- 从其他目录导入时把 `fig_samples` 目录加进 `sys.path`，或直接 `python <脚本绝对路径>`（脚本目录自动入 `sys.path`）。

## 3 · 字体与标签纪律（硬要求）

1. **轴标签、刻度、图内文字、图例一律英文**（ASCII 源）——中文 Windows 与非中文环境都可能缺字形，
   一旦缺字形就是方框（tofu），paper-ready 图不接受。
2. `style_vesi` 在导入时**自动探测**常见中文字体（Microsoft YaHei / SimHei / SimSun / DengXian / Noto CJK…）：
   - 探测到 → 中文字形可用（但样例仍用英文，保持跨机一致）；
   - 探测不到 → 打印提示并**强制英文**；`save_fig` 会扫描图内非 ASCII 文本，**发现中文即报错、不落盘坏图**。
3. 需要「µ」这类符号时用 mathtext（`$\\mu$g/mL`），不要直接打 Unicode 字符。
4. 常用对照见 `style_vesi.ENGLISH_LABELS`。

## 4 · 图型 ↔ workflows/08 对照表

| 样例脚本 | `workflows/08-数据处理与可视化.md` 对应图型 | 该工作流要点（照办） |
|---|---|---|
| `fig1_pk_curve.py` | §本项目专用图表类型 **1. 血药浓度-时间曲线** | 对数刻度；两组；误差棒用 SD **并叠加个体散点** |
| `fig2_tissue_heatmap.py` | §本项目专用图表类型 **2. 组织分布热图** | 行=组织、列=时间点；两组并排；色标注明单位 |
| `fig3_pk_bar.py` | §本项目专用图表类型 **3. PK参数柱状图** | 两组并排；显著性 `*p<0.05, **p<0.01`；报**精确 p 值** |
| `fig4_excretion.py` | §本项目专用图表类型 **4. 累积排泄率曲线** | 多途径曲线；两组对比；累积口径（%dose）声明 |
| `fig5_release.py` | §本项目专用图表类型 **5. 体外释放曲线** | 拟合曲线 + 实测点；标注释放动力学模型 |
| `fig6_char.py` | §本项目专用图表类型 **6. 制剂表征图** | 粒径分布（单峰、PDI 记录）、TEM、Zeta 分布 |

> 上述图型在 `fig_samples` 里是**形状样例**；正式出图还须过 V-M6 三闸（audit / figcheck / vision，无 vision 则双闸 + 人检），
> 并按 `workflows/08` §图表制作标准（单位、n、误差棒含义、图注自含、≥300 DPI）逐条核。

## 5 · 如何换成真实数据

1. **只改 `synth()`**：每个脚本的数据生成集中在 `synth(rng)`（`fig1` 为 `synth` 内两段基线函数），
   把它替换成「读真实数据 → 返回同结构 dict/ndarray」即可，绘图段与落盘段不用动。
2. **数据口径先对齐 `references/数据条目字典.md`**：
   - 组别用 `group_id` / `group_label`（脂质体组 / 游离药组），分析物用 `analyte`（<原型药> / <活性代谢物> / <结合代谢物> / total）；
   - 单位显式：血浆 `µg/mL`、组织 `µg/g`、剂量 `mg/kg`、时间 `h`、排泄 `%dose`、释放 `%`；
   - 累积口径（%ID / %dose）**图注与正文必须一致**，不得一处一套。
3. **n 与误差棒**：保留 `n=` 标注；误差棒统一 SD（用 SEM 必须在图注声明理由）；
   n<3 或只有技术重复时**不要**画显著性标注（`workflows/08` §统计微陷阱）。
4. **不要把 `print` 的数字当报告数字**：脚本尾部打印只用于核对；报告数字须回到正本数据表按 `source_file + source_locator` 取证。
5. **删掉「synthetic demo data」字样**：suptitle / 图注里的示例声明必须替换为真实图注（图注自含）。
6. **落盘与命名**：`save_fig(fig, "<图号>_<主题>")`，三格式齐备；PNG 进 docx/PPT、PDF 进 LaTeX、SVG 进需可编辑矢量的场景。

## 6 · 依赖与边界

- 依赖：`matplotlib` + `numpy`（`fig5` 的模型拟合为**纯 numpy** 实现，不需要 scipy）。
- `trapz()` 已适配 NumPy 2.x（`np.trapz` → `np.trapezoid`）。
- 本目录**不含**真实实验数据；所有数值均为合成示意值，不得引用为课题结果。
