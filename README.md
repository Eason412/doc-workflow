# Doc Workflow

中文 | [English](README.en.md)

**让项目文档、双语文本与交付稿保持准确、清晰。** 本仓库收录四个写作与文档类 Skill，覆盖文档同步、中英互译、防御性措辞删减和 Markdown 导出 Word／PDF。每个 Skill 都是以 `SKILL.md` 为入口的 Agent 任务规范，可独立安装和使用。

当前版本：[V0.1.0](https://github.com/Eason412/doc-workflow/releases/tag/V0.1.0)（[全部版本与更新说明](https://github.com/Eason412/doc-workflow/releases)）。

> ⚠️ 使用前提：Agent 需要能够读取 `SKILL.md` 及其引用文件；导出 Word 需要 Pandoc 3.9+，导出 PDF 还需要 LibreOffice 和中英文字体。

## ✨ 特点

- 🔎 **代码与文档一致性**：文档内容以源码、配置和测试为依据；project-docs 默认撰写或更新逐节对应的中英文 README，并附本地链接、锚点与双语结构检查脚本。
- 🌐 **双语结构与术语一致性**：翻译保留标题、表格、公式和代码结构，共用中英术语表，重点核对否定、数字、条件和情态。
- ✂️ **决策文字精简**：删去自证勤勉的免责声明和层层保留，保留影响判断的限制与原有证据强度。
- 🖨️ **按范式导出 Word 与 PDF**：同一份 Markdown 按通用、学术、公文三套范式生成可编辑的 Word，再由同一份 Word 转出 PDF；字体、字号、行距和编号逐项核对，检查通过才替换输出。

## 🧩 Skill 组成

| Skill | 用途 | 配套资料 |
| --- | --- | --- |
| [project-docs](skills/project-docs/SKILL.md) | README、项目文档与交接说明的撰写、审阅及更新 | [README 规范](skills/project-docs/references/readme.md)、[检查脚本](skills/project-docs/scripts/check_readme.py) |
| [translate](skills/translate/SKILL.md) | 论文、技术文档与笔记的中英互译 | [术语表](skills/translate/references/glossary.md) |
| [trim-hedging](skills/trim-hedging/SKILL.md) | 方案、计划与研究总结的防御性措辞删减或审查 | [边界示例](skills/trim-hedging/references/examples.md) |
| [md-export](skills/md-export/SKILL.md) | Markdown 稿按排版范式导出 Word 或 PDF | [范式说明](skills/md-export/references/presets.md)、[常见问题](skills/md-export/references/qa.md) |

四个 Skill 均为完整安装单元，不依赖其他 Skill 或仓库根目录运行。学术类 Skill 在姊妹仓库 [paper-workflow](https://github.com/Eason412/paper-workflow) 维护。

## 🛠️ 运行条件

- **宿主**：Codex、Claude Code 等能够加载 `SKILL.md` 的 Agent 可使用这些规范；宿主的文件读取、脚本执行和 PDF 阅读能力决定可执行的任务范围。
- **语言**：规范正文以中文为主。

| 功能 | 依赖 | 依据 |
| --- | --- | --- |
| 文档写作、翻译与措辞删减 | Agent；文本规范本身无额外软件包 | 各 Skill 的 `SKILL.md` |
| README 链接与双语检查 | uv、Python ≥ 3.10、`markdown-it-py>=3` | [检查脚本](skills/project-docs/scripts/check_readme.py) |
| Word 导出 | uv、Python ≥ 3.10、`python-docx`、`pdfplumber`、Pandoc 3.9+ | [导出脚本](skills/md-export/scripts/md_export.py) |
| PDF 导出 | Word 导出的依赖，加 LibreOffice 和中英文字体 | [常见问题](skills/md-export/references/qa.md) |

- **Python 依赖**：脚本通过 uv 按内联依赖声明运行，无需预先安装软件包。
- **可选工具**：Git 跟踪检查需要 Git；Poppler 的 `pdftoppm` 用于把 PDF 页面渲染成图片目测。
- **准备与验收**：具体步骤见 [SETUP.md（英文）](SETUP.md)。

## 🚀 设置方法

- **设置**：由 Agent 读取 [SETUP.md（英文）](SETUP.md) 并完成设置；仓库位置由使用者选定。
- **完成后**：开启新的 Agent 会话，确认 Skill 已被发现并能读取其入口；宿主要求重新加载时按宿主机制处理。
- **需用户亲自完成**：无；设置过程无需新增账号登录。

| 设置项 | 位置 | 说明 |
| --- | --- | --- |
| LibreOffice 路径 | 环境变量 `MD_EXPORT_SOFFICE` | `soffice` 不在 PATH 时指定 |
| 自定义排版范式 | `--preset <文件>.json` | 覆盖键见 [范式说明](skills/md-export/references/presets.md) |

## 📁 维护与文档导航

修改与验证规则见 [AGENTS.md](AGENTS.md)。

| 路径 | 用途 |
| --- | --- |
| [SETUP.md（英文）](SETUP.md) | 面向 Agent 的安装、依赖准备和验收步骤 |
| [skills/](skills/) | 独立 Skill、参考资料及配套脚本 |
| [scripts/link-skills.sh](scripts/link-skills.sh) | 本仓库 Skill 的本机链接管理 |
| [AGENTS.md](AGENTS.md) | 项目工作范围与验证命令 |
| [.github/workflows/skills.yml](.github/workflows/skills.yml) | project-docs 与 md-export 的回归任务 |

## 🤝 贡献须知

欢迎提交兼容修复、功能改进与规范修订。提交 PR 前请注意：

- **范围**：每个 PR 聚焦一个问题，附最小复现、修改原因和实际验证结果。
- **规范修改**：附修改前后的对照示例。
- **行为修改**：补充回归测试，相关说明与中英文 README 同步更新。
- **隐私**：凭据与私人文档保留在仓库外。

完整要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

本仓库采用 [MIT License（英文）](LICENSE)，版权署名为 `Copyright (c) 2026 Eason412`。复制或分发软件及文档时保留许可证要求的版权与许可声明。
