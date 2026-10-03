# 常见问题

## 标题重复

正文已有 `# 标题`，YAML 里又写了 `title`，Pandoc 会多渲染一个标题块。脚本在正文有一级标题时隐藏标题块；仍重复时检查是不是正文里本来就写了两次。

## 页眉页脚出现日期、URL、页码

Chrome 默认打印页眉页脚。脚本固定传 `--no-pdf-header-footer`；正文里本来就有的日期不受影响。

## 宽表或长代码溢出

在 `assets/print.css` 里调：表格用 `table-layout: fixed` 和 `overflow-wrap: anywhere`，必要时缩小表格字号；代码块用 `white-space: pre-wrap`。仍放不下的超宽表改横版（`--orientation landscape`）。

## 逐行编号被合并

`1）……` 这类行在标准 Markdown 里是同一段。脚本默认开启 `hard_line_breaks`；用了 `--no-hard-line-breaks` 时，需要换行的地方行尾加两个空格。

## 缺字或字体不对

`print.css` 的字体栈是西文 Times New Roman，中文按 Songti SC、PingFang SC、Noto Serif CJK SC、Microsoft YaHei 回退，代码用等宽字体。出现方框或字体不对时，先用 `pdffonts` 看实际嵌入的字体，再按本机已装字体调整字体栈。

## 图片不显示

图片路径相对源 Markdown 所在目录解析。脚本把源目录作为 Pandoc 资源路径并嵌入图片；Pandoc 报 `Could not fetch resource` 时，JSON 的 warnings 会列出来，按提示修路径。损坏的图片文件不会触发警告，只能看渲染后的页面。

## 公式没渲染或显示成原文

默认 MathML，离线、不依赖网络。Chrome 对少数 LaTeX 写法支持不全；渲染不对时先简化写法，或在交付时说明哪几处公式有问题。

## 找不到 Chrome 或卡住

找不到 Chrome 时用 `--chrome` 指定路径。打印超时（默认 120 秒）后脚本失败退出，原有 PDF 不动；文档很大时用 `--timeout` 调大。

## 改脚本后的回归

改 `md_to_pdf.py` 或 `print.css` 后，在 skill 目录跑：

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pymupdf python -m unittest discover -s tests -v
```

再用一份含中文、相对路径图片、公式、宽表、代码块的样稿转一次，渲染首页和横版页看一遍。
