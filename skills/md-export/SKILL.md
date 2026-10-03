---
name: md-export
description: "把一般 Markdown 文档转成可打印的 PDF（Pandoc + Chrome），处理纸张方向、表格、代码块换行和中英文字体。需要课程报告封面、目录、章节分页和国标参考文献时用 course-report。"
---

# Markdown 转 PDF

Pandoc 把 Markdown 转成 HTML，套上 `assets/print.css`，再由 Chrome headless 打印成 PDF。不需要 TeX 环境；中文、宽表和长代码行靠 CSS 处理。下文 `$SKILL_DIR` 指当前加载的这份 SKILL.md 所在目录。

## 转换

```bash
uv run "$SKILL_DIR/scripts/md_to_pdf.py" input.md --output output.pdf --paper-size A4 --orientation portrait
```

- 公式默认用 MathML 离线渲染。`--math none` 只在原文已是可直接显示的公式，或用户接受显示公式原文时用。
- 默认保留源文件里的单个换行，中文“1）”这类逐行编号不会被合并成一段；要标准 Markdown 软换行时加 `--no-hard-line-breaks`。
- 正文已有一级标题时，脚本不再渲染 YAML `title` 的标题块，不用改原稿。
- 找不到 Chrome 时用 `--chrome <路径>`；`--html <路径>` 保留中间 HTML 供排查。
- 脚本先打印到临时目录，检查通过才替换输出文件，失败时原有 PDF 不动。脚本不删除其他文件；清理旧文件要有用户确认的清单。

## 检查

脚本成功时打印 JSON：输出路径、页数、页面尺寸和 Pandoc 警告（如图片找不到）；PDF 打不开、没有页面或尺寸与请求不符时失败退出。这些只是静态检查。图片是否显示正确、公式是否渲染、宽表和长代码是否溢出，要把相关页面渲染成 PNG 看一遍（Claude 用 Read，Codex 用 view_image），至少看首页和含图片、公式、宽表的页。有警告或没看过的部分，交付时说明，不声称已经保真。

排查具体问题时读 [qa.md](references/qa.md)。
