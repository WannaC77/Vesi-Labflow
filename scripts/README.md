# scripts/ — 交付门禁脚本集

> 这些脚本把「可机械判定的检查」从人脑里拿走：**它能失败，也应当失败**。
> 约定：`exit 0 = PASS · 1 = FAIL · 2 = usage`；无参数时打印用法。
> 全部为 stdlib 优先；需要第三方包时在输出里明确提示。

## 交付卫生 / 一致性

| 脚本 | 作用 | 典型用法 |
|---|---|---|
| `assert_delivery_hygiene.py` | 交付件卫生硬门（禁用词、残留标记、文件名规范） | `python scripts/assert_delivery_hygiene.py <文件…>` |
| `delivery_gate_check.py` | 结构化交付放行机检（规则见 `delivery_gate.check.yaml`） | `python scripts/delivery_gate_check.py --config scripts/delivery_gate.check.yaml <文件…>` |
| `consistency_check.py` | 跨文档口径一致性（同一数字/术语在多件间不打架） | `python scripts/consistency_check.py <文件…>` |
| `naturalness_check.py` | 自然度质检（去 AI 腔、模板腔） | `python scripts/naturalness_check.py <文件…>` |
| `precheck_similarity.py` | 句级重复预检（投稿前自查） | `python scripts/precheck_similarity.py <文件…>` |
| `verify_bundle.py` | 开源包结构自校验（目录/必需件/相对路径） | `python scripts/verify_bundle.py --root .` |
| `selftest_scripts.py` | **元自检**：给上面的门禁脚本喂反例，证明它们真的会失败 | `python scripts/selftest_scripts.py` |

## 数据处理 / 记录链

| 脚本 | 作用 | 典型用法 |
|---|---|---|
| `transcribe_record.py` | 实验记录转写与脱敏（手写/照片 → 结构化文本） | `python scripts/transcribe_record.py --help` |
| `check_dose.py` | 剂量换算核对（mg/kg ↔ mg/m² 等，按体表面积系数） | `python scripts/check_dose.py --help` |
| `ref_numberizer.py` | 参考文献编号与顺序整理 | `python scripts/ref_numberizer.py <文件…>` |
| `clean_pdf_meta.py` | PDF 元数据清理（作者/工具/时间戳） | `python scripts/clean_pdf_meta.py <pdf…>` |
| `dump_docx_full.py` | docx 全量导出（正文/表格/批注，供审计对照） | `python scripts/dump_docx_full.py <docx>` |
| `crop_zoom.py` / `tile_image.py` | 图片裁剪放大 / 分块（核对图表细节） | `python scripts/crop_zoom.py --help` |

## 可选 OCR（离线/自备端点）

| 脚本 | 作用 | 依赖 |
|---|---|---|
| `batch_ocr.py` | 批量图像 OCR（**自备端点**） | 环境变量 `OCR_BASE_URL` / `OCR_MODEL` / `OCR_API_KEY`；未配置时退出并提示（不假装识别） |

> 本仓库**不随附**任何云端端点、密钥或模型名：OCR 能力由你自备（见上表环境变量）。
> 缺 OCR 时，记录转写走人工，并在交付说明中标 `[降级]`。

## 使用顺序建议

```
写完全部材料 → verify_bundle.py（结构） → consistency_check.py（口径）
             → assert_delivery_hygiene.py（卫生） → delivery_gate_check.py（放行）
             → precheck_similarity.py + naturalness_check.py（投稿前）
最后：selftest_scripts.py（确认门禁本身没被改坏）
```
