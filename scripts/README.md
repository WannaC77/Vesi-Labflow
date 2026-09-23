# scripts/ — 交付门禁脚本集

> 这些脚本把「可机械判定的检查」从人脑里拿走：**它能失败，也应当失败**。
> 约定：`exit 0 = PASS · 1 = FAIL · 2 = 用法/输入错误 · 3 = 依赖或配置缺失（未执行，非通过）`；
> 全部支持 `--help`（rc=0，不抛栈）。需要第三方包时在输出里明确提示缺件与装法。
> 自检入口：`--selftest`（支持者见下表「自检」列；`selftest_scripts.py` 是整组的元自检）。

## 交付卫生 / 一致性

| 脚本 | 作用 | 典型用法 | 自检 |
|---|---|---|---|
| `verify_bundle.py` | 开源包结构自校验（目录/必需件/相对路径） | `python scripts/verify_bundle.py --root .` | n/a |
| `assert_delivery_hygiene.py` | 交付件卫生硬门（Heading 定义 / TOC 域 / updateFields / 表数 / 字面 `**` / 页脚 PAGE 域 + md5 对质） | `python scripts/assert_delivery_hygiene.py <文件.docx…>` | n/a |
| `consistency_check.py` | 跨文档口径一致性（题目/署名/均值±SD 数对全组比对） | `python scripts/consistency_check.py <文件…>` | n/a |
| `delivery_gate_check.py` | 交付放行机检（放行规则见 `delivery_gate.check.yaml`） | `python scripts/delivery_gate_check.py scripts/delivery_gate.check.yaml` | `--selftest` |
| `precheck_similarity.py` | 句级重复预检（整句复制 / 近似重复） | `python scripts/precheck_similarity.py 目标.md --against 对照.md` | n/a |
| `naturalness_check.py` | 自然度质检（套话 / 连接词 / 句首重复 / 段长方差 / 模板段） | `python scripts/naturalness_check.py <文件…>` | n/a |
| `selftest_scripts.py` | **元自检**：给上面的门禁脚本喂反例，证明它们真的会失败 | `python scripts/selftest_scripts.py [SC-5]` | 无参即全跑（`--selftest` 同义） |

## 数据处理 / 记录链

| 脚本 | 作用 | 典型用法 | 自检 |
|---|---|---|---|
| `transcribe_record.py` | 实验记录转写与脱敏（手写/照片 → 结构化文本） | `python scripts/transcribe_record.py --help` | `--selftest` |
| `check_dose.py` | 剂量换算核对（mg/kg ↔ mg/m² 等，按体表面积系数） | `python scripts/check_dose.py --help` | `--selftest` |
| `clean_pdf_meta.py` | PDF 元数据清理（作者/工具/时间戳） | `python scripts/clean_pdf_meta.py <pdf…>` | `--selftest` |
| `ref_numberizer.py` | 占位引用编号器（写作期 `{ref1}`…→ 定稿按首次出现顺序重排为 `[1]`…） | `python scripts/ref_numberizer.py 论文.md [--write]` | n/a |
| `dump_docx_full.py` | docx 全量转储（段落 + 表格）→ txt，供逐字审计 | `python scripts/dump_docx_full.py <docx> <输出.txt>` | n/a |
| `crop_zoom.py` | 按相对坐标裁剪并放大（图中细节核对） | `python scripts/crop_zoom.py <img> 0.1 0.1 0.6 0.4 3 <输出.png>` | n/a |
| `tile_image.py` | 图片切瓦片并放大（分区送 OCR） | `python scripts/tile_image.py <img> [--rows 3 --cols 2]` | n/a |

## 可选 OCR（离线/自备端点）

| 脚本 | 作用 | 依赖 | 自检 |
|---|---|---|---|
| `batch_ocr.py` | 批量图像 OCR（**自备端点**） | 环境变量 `OCR_BASE_URL` / `OCR_MODEL` / `OCR_API_KEY`；未配置时退出（rc=3）并提示（不假装识别） | n/a |

> 本仓库**不随附**任何云端端点、密钥或模型名：OCR 能力由你自备（见上表环境变量）。
> 缺 OCR 时，记录转写走人工，并在交付说明中标 `[降级]`。

## 使用顺序建议

```
写完全部材料 → verify_bundle.py（结构） → consistency_check.py（口径）
             → assert_delivery_hygiene.py（卫生） → delivery_gate_check.py（放行）
             → precheck_similarity.py + naturalness_check.py（投稿前）
最后：selftest_scripts.py（确认门禁本身没被改坏）
```
