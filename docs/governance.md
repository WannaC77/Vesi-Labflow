# 治理与许可

## 许可

本仓以 **MIT License** 发布（见仓库 `LICENSE`）。文档与配方（`LICENSE-DOCS`）同条款。

## 贡献

见仓库 `CONTRIBUTING.md`，硬性要求摘要：

1. 不提交真实实验数据、他人材料、机构名与个人身份信息；
2. 不引入任何特定 agent / CLI / 调度器 / API key 作为依赖；
3. 新增工具必须带 `--selftest`（含**必须失败的负例**）；
4. 退出码语义统一：`0` 通过 · `1` 失败 · `2` 用法 · `3` 依赖缺失未执行；
5. 文本件 UTF-8 无 BOM、LF 行尾、包内相对路径；
6. 不在仓内留生成物（冒烟产物落 `_smoke_out/`，提交前清理）。

## 安全与支持

- 漏洞与敏感问题：见 `SECURITY.md`（请勿公开开 issue）。
- 使用问题与建议：见 `SUPPORT.md`。

## 引用

学术场景引用见仓库 `CITATION.cff`（GitHub 右侧 "Cite this repository" 可直接导出 BibTeX）。

## 双语

仓库提供中文（`README.md`）与英文（`README.en.md`）两版说明；以中文版为权威口径。
