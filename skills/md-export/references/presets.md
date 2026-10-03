# 范式数据与覆盖

三份完整 JSON 位于 `presets/`，可复制其中一份修改后用 `--preset 文件路径`。每份独立包含所有样式确定值，不依赖另一个范式。

- `page`：`paper_size`（A4/A3/A5/LETTER）、`orientation`、`margins_cm`（上、下、左、右）、`grid_line_pitch`（twip）。
- `styles`：以 Word 样式名为键，包括 Table Text、Display Math 和 Page Number。
- `table.kind`：`grid` 或 `three_line`。
- `numbering`：`kind`（none/academic/gongwen）、`levels`（0/3/4），与预设编号定义对应。
- `page_numbers`：kind、format、distance_from_body_cm；当前 format 应与 kind 匹配（center 为 PAGE，odd_even 为 — PAGE —）。
- `font_fallbacks`：要求字体 → 按优先级排列的族名数组；保持英文族名。

样式每项必须明确指定 ascii、eastAsia、size、bold、alignment、line_spacing、space_before、space_after、first_line_chars、left_chars、color、italic、keep_next、underline、shading、snap_to_grid。首行与左缩进单位是字符；段前段后和字号单位 pt；行距为 `fixed:20` 或 `multiple:1.5`。颜色固定 000000，样式 italic 固定 false。底纹可用六位十六进制值或 null。字号支持二号、小二、三号、小三、四号、小四、五号、小五和半 pt 精度数值。

`--set` 可重复。样式别名：body、title、heading1–heading9、code、inline_code、table_text、caption、footnote；可覆盖上列样式字段。body 同时更新 Body Text、First Paragraph、Abstract；覆盖 body.size 同时更新行内代码字号。表题/图题的独立样式用自定义 JSON 修改。

页面可覆盖 `page.paper_size`、`page.orientation`、`page.margins_cm`，表格可覆盖 `table.kind`。例如：

```bash
uv run "$SKILL_DIR/scripts/md_export.py" input.md --set 'page.margins_cm=[2.5,2.5,3,2.5]' --set table.kind=three_line
```

更高优先级的 `--paper-size`、`--orientation` 在 `--set` 之后应用。非法值与未知键退出码 2，并列可用键。
