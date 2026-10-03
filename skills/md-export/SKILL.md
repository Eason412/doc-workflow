---
name: md-export
description: "把已有的 Markdown 稿按排版范式导出为 Word（.docx）或 PDF。不用于从零写 Word、修改已有 .docx；带封面、摘要、目录的课程报告用 course-report。"
---

# Markdown 导出

Word 是母版：JSON 范式生成 Pandoc reference.docx，Pandoc 导出 DOCX，XML 后处理补齐编号、表格和公式样式；PDF 用 LibreOffice 从同一份 DOCX 转出。需要 Pandoc 3.9+；只导出 Word 不需要 LibreOffice。Python 用 `uv run`，脚本只声明 python-docx 和 pdfplumber。下文 `$SKILL_DIR` 是这份 SKILL.md 所在目录。

## 范式与标题

用户未指定时选 `general`。

| 范式 | 用途与主要设置 |
| --- | --- |
| `general` | 通用文档；宋体 12pt，1.5 倍行距，无标题编号，全框线表格 |
| `academic` | 学术稿；宋体 12pt，固定 20pt 行距，标题 `1 / 1.1 / 1.1.1`，三线表 |
| `gongwen` | 公文（参考 GB/T 9704-2012）；仿宋 16pt，固定 28pt 行距，中文层级编号，奇偶页码；缺专用字体时明确报告降级 |

保留原文标题层级，不自动升降级。把用户未说明层级的标题整理进 Markdown 时用一级 `#`，只有用户明确二级、三级才用 `##`、`###`。文档标题放 YAML `title`，始终用 Title 样式；只有正文第一个一级标题与 title 文字相同时删除该一级标题，并记录在报告里。手写编号或 `{.unnumbered}` 只关闭该标题的自动编号。

## 命令

```bash
uv run "$SKILL_DIR/scripts/md_export.py" input.md
uv run "$SKILL_DIR/scripts/md_export.py" input.md --to both --preset academic --output out.docx
uv run "$SKILL_DIR/scripts/md_export.py" input.md --output out.pdf --preset gongwen
uv run "$SKILL_DIR/scripts/md_export.py" input.md --set body.size=小四 --set body.line_spacing=fixed:22
uv run "$SKILL_DIR/scripts/md_export.py" input.md --preset path/to/custom.json --orientation landscape
```

默认生成输入旁边同名 `.docx`。`--to` 缺省时按 `--output` 扩展名决定；明确指定但冲突时报错。`--to both` 使用输出去掉扩展名后的 `.docx` 与 `.pdf`。默认 `markdown+hard_line_breaks`，标准软换行用 `--no-hard-line-breaks`。图片路径相对源文件目录。

字号接受中文字号或 pt，例如 `小四`、`12pt`。覆盖键及 JSON 结构见 [presets.md](references/presets.md)，未知键和非法值退出码 2 并列出可用键。`--paper-size`、`--orientation` 覆盖页面设置。

LibreOffice 依次取 `--soffice PATH`、`MD_EXPORT_SOFFICE`、PATH 的 `soffice`；报告记录实际路径。macOS 上无界面 LibreOffice 用自带的 fontconfig，找不到系统字体会让 PDF 丢中文；未设 `FONTCONFIG_FILE` 时，脚本为本次转换和字体检测使用 Homebrew 的 `fonts.conf`，报告的 `fontconfig_file` 记录实际值。`--strict-fonts` 缺字体、无法检测字体或 PDF 替换字体均失败。每次转换使用独立用户配置和输出目录，`--timeout` 默认每个外部命令 120 秒。

## 检查与交付

结束输出 JSON。`conversion`、`docx_check`、`pdf_check` 分开报告 `pass / fail / unknown`，`visual` 固定为 `not_done`。仅 Word 导出时 `pdf_check=unknown`，不表示 PDF 已验证。`checks` 每项列位置/样式、要求、DOCX 有效值和来源、PDF 实际字体/字号/颜色及 `pass / fail / unknown / not_used`；未使用的样式标 `not_used`，无法支持的 raw OOXML 或自定义样式标 `unknown`，关键 unknown 阻止发布。

字体决策列“要求 → 实际”；字体回退与符合范式分别说明。DOCX 可编辑文字全部黑色；PDF 再核对字体、中文缺字风险、文字保留、颜色、字号和页面坐标。图片内文字颜色不在检查范围内。

全部必需检查通过才发布。发布失败尝试恢复旧输出；恢复失败时保留备份并在 `publication.recovery` 记录路径、状态和错误。诊断文件写入系统临时目录，或 `--diagnostics DIR` 下新建的子目录，报告给出路径。`both` 的第二次替换失败会尝试恢复第一次替换。含 OMML 的固定行距段落改用同值最小行距，独立图片段落使用自动行距；`line_spacing_exceptions` 列出这些段落。

交付前把首页及含表格、代码、图片的页渲染成 PNG 看一遍：有 Poppler 时可用 `pdftoppm -png -scale-to 1400 out.pdf /tmp/md-export-page`。Claude 用 Read，Codex 用 `view_image`；确认中文正常、标题和代码符合所选范式、无彩色文字及明显裁切。自动报告的 `visual` 不改，交付中另列实际看过的页和限制。公式、图片、宽表的视觉保真不能只凭自动检查声称通过。

排查字体、编号、行距和表格时读 [qa.md](references/qa.md)。第一版不提供目录 `--toc`。
