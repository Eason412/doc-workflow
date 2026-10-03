# 导出排查

## 字体与 fontconfig

先看报告 `font_decisions`（要求、实际、回退、降级）与 `soffice` 路径。`fc-list` 检查与 LibreOffice 必须使用同一个 `FONTCONFIG_FILE`。脚本识别包装脚本的 `${FONTCONFIG_FILE:=...}` 设置，也接受环境变量；其他复杂包装脚本请明确导出环境变量。装了字体仍不代表 LibreOffice 会使用，检查 PDF 字符实际字体。

macOS 上未设 `FONTCONFIG_FILE` 时，脚本自动使用 Homebrew 的 `/opt/homebrew/etc/fonts/fonts.conf` 或 `/usr/local/etc/fonts/fonts.conf`。两处都没有（未用 Homebrew 装 fontconfig）时，LibreOffice 自带的 fontconfig 找不到系统字体，中文可能落到 Liberation 等西文字体；这时安装 fontconfig 或自行设置 `FONTCONFIG_FILE`。中文字符的实际字体不在该样式要求或回退链里，或 PDF 丢段落时失败，不发布输出。

缺 FangSong_GB2312 优先 FangSong、STFangsong；楷体优先 KaiTi、Kaiti SC、STKaiti；小标宋缺失降级为 SimSun 加粗。末尾的 Noto CJK 支持 Linux 中文输出。公文预设通过不等于具备原要求的专用字体，报告单列字体降级。严格模式缺任何要求字体直接失败；没有 fc-list 则无法严格核验。PDF 正文和页码都比较实际选定字体：即使替换字体在回退名单内，普通模式仍警告，严格模式失败。

## 标题编号

编号是 numbering.xml 多级列表和 Heading 样式的 numPr，不是写进文本的 `--number-sections`。Pandoc 会重建 numbering.xml，所以导出后重新创建定义并用未占用的 ID 绑定，避免与正文列表冲突。手写编号仅对当前标题直接写 numId=0；`2026 年计划` 不视为编号。删除编号定义或样式绑定会使 DOCX 检查失败。

YAML title 始终保留。正文第一个一级标题与它相同才删除，报告 `title_deduplicated` 记录文字。不同标题同时保留。DOCX 标题数量和层级序列与处理后的输入 AST 核对，缺失或变级均失败。

## 固定行距、图片与公式

学术正文固定 20pt，公文固定 28pt。独立图片使用 Figure / Captioned Figure，独立展示公式使用 Display Math，代码使用 Source Code，移除 Pandoc 给块内 run 套的 Verbatim Char（只用于行内代码）；这些都设 auto 行距、关闭 snapToGrid。只有独立图片段落使用图片样式，正文和标题中的行内图片保留原样式、缩进及标题编号；行内图片在固定行距段落里仍可能压住邻行，需要人工处理或改成独立段落。含 OMML 公式且原样式使用固定行距的段落保留原样式，改用同值的最小行距（学术为 20pt、公文为 28pt），其余段落仍用固定行距。报告 `line_spacing_exceptions` 列出例外段落的位置、文字、原因和行距，检查器核对该例外的实际值。

长代码行在 Word/LibreOffice 自动折行；宽表、大图沿用 Pandoc 缩放，字符坐标检查仅证明文字没有越过纸张边界，不证明没有越过版心或图片完整。交付时看相应页面。公式保留为 OMML，自动文本检查核对公式周围可编辑文字；公式本身的视觉正确性在 not_checked 中。

公文设置 28pt 行网格，每页约 22 行、每行约 27 个三号字；未设置字符网格，因此不是“22 行×28 字”的完整版式认证。

## 表格与 WPS

表格内使用 Table Text，避免 Compact 列表样式冲突。全框线在 tblBorders 显式写六边，0.5pt 黑线。三线表仅顶底 1.5pt，无竖线及内横线；连续表头最后一行每个 tc 写 0.75pt 下线。无表头或仅一行的表格只留顶底线。处理前清掉 tcBorders，保留 tblHeader 以跨页重复。表题 keepNext。

不依赖表格条件格式画边框。Word、LibreOffice 可读，WPS 的实际显示尚需在目标 WPS 版本里打开验收。

## 页码与目录

通用、学术页码居中。公文奇数页靠右、偶数页靠左，各空一字，四号宋体 `— 1 —`；页码距版心下缘约 7mm。若 Pandoc 没有保留偶数页 footer 或 evenAndOddHeaders，则退居中并报告。

不提供 `--toc`：LibreOffice headless 不自动填充 Pandoc 目录字段，PDF 可能为空。需要封面、摘要、目录的课程报告用 course-report。

## 失败产物与报告

发布失败会尝试恢复已替换输出；如果恢复也失败，保留对应的 `.bak` 备份，不继续删除，并在报告 `publication.recovery` 记录输出路径、备份路径、恢复状态和错误。其他输出继续恢复，原发布错误同时保留。诊断目录保存 reference.docx、输出 DOCX、已生成的 PDF、AST 和 report.json，不保留 LibreOffice 临时用户配置。报告打印到标准输出，退出码 1 表示转换/核对/发布失败，2 表示参数或环境前提不满足。核对器范围是本工具生成的结构；raw OOXML、自定义样式或无法解析的继承链标 unknown，不能当通过。

正文与脚注同文时，PDF 核对结合候选位置和左侧脚注标记区分文本流，不以待核对的预期字号选候选；归属不能确定时标 `unknown`，不输出确定的字体或字号结论，阻止发布。
