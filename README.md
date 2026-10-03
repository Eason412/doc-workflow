# Doc Workflow

中文 | [English](README.en.md)

**让项目文档、双语文本与打印稿保持准确、清晰。** 本仓库收录四个写作与文档类 Skill，覆盖文档同步、中英互译、防御性措辞删减和 Markdown 转 PDF。每个 Skill 都是以 `SKILL.md` 为入口的 Agent 任务规范，可独立安装和使用。

> ⚠️ 使用前提：Agent 需要能够读取 `SKILL.md` 及其引用文件；PDF 转换还需要 Pandoc、Chrome 系浏览器和中英文字体。

## ✨ 特点

- 🔎 **代码与文档一致性**：文档内容以源码、配置和测试为依据；doc-sync 默认撰写或更新逐节对应的中英文 README，并附本地链接检查脚本。
- 🌐 **双语结构与术语一致性**：翻译保留标题、表格、公式和代码结构，共用中英术语表，重点核对否定、数字、条件和情态。
- ✂️ **决策文字精简**：删去自证勤勉的免责声明和层层保留，保留影响判断的限制与原有证据强度。
- 🖨️ **打印版面适配**：通过打印样式处理宽表、长代码行和中英字体回退，支持纸张与方向选择；PDF 打开、页数和尺寸检查通过后才替换输出。

## 🧩 Skill 组成

| Skill | 用途 | 配套资料 |
| --- | --- | --- |
| [doc-sync](skills/doc-sync/SKILL.md) | README、项目文档与交接说明的撰写、审阅及更新 | [README 规范](skills/doc-sync/references/readme.md)、[链接检查脚本](skills/doc-sync/scripts/check_readme.py) |
| [translate](skills/translate/SKILL.md) | 论文、技术文档与笔记的中英互译 | [术语表](skills/translate/references/glossary.md) |
| [trim-hedging](skills/trim-hedging/SKILL.md) | 方案、计划与研究总结的防御性措辞删减或审查 | [边界示例](skills/trim-hedging/references/examples.md) |
| [md-to-pdf](skills/md-to-pdf/SKILL.md) | 一般 Markdown 文档的可打印 PDF 转换 | [常见问题](skills/md-to-pdf/references/qa.md)、[打印样式](skills/md-to-pdf/assets/print.css) |

四个 Skill 均为完整安装单元，不依赖其他 Skill 或仓库根目录运行。学术类 Skill 在姊妹仓库 [paper-workflow](https://github.com/Eason412/paper-workflow) 维护。

## 🛠️ 运行条件

Codex、Claude Code 等能够加载 `SKILL.md` 的 Agent 可使用这些规范；宿主的文件读取、脚本执行和 PDF 阅读能力决定可执行的任务范围。规范正文以中文为主。

| 功能 | 依赖 | 依据 |
| --- | --- | --- |
| 文档写作、翻译与措辞删减 | Agent；文本规范本身无额外软件包 | 各 Skill 的 `SKILL.md` |
| README 本地链接检查 | uv、Python ≥ 3.10、`markdown-it-py>=3` | [检查脚本](skills/doc-sync/scripts/check_readme.py) |
| PDF 转换 | uv、Python ≥ 3.10、`pymupdf>=1.24`、Pandoc、Chrome／Chromium／Edge | [转换脚本](skills/md-to-pdf/scripts/md_to_pdf.py) |
| 中文排版 | 可用的中英文字体，按打印样式回退 | [字体栈](skills/md-to-pdf/assets/print.css) |

Python 脚本通过 uv 按内联依赖声明运行。Git 跟踪检查需要 Git；`pdffonts` 仅用于字体排查。PDF 转换采用 HTML 与浏览器打印，无需 TeX；具体准备与验收见 [SETUP.md（英文）](SETUP.md)。

## 🚀 设置方法

由 Agent 读取 [SETUP.md（英文）](SETUP.md) 并完成设置。完成后开启新的 Agent 会话，确认 Skill 已被发现并能读取其入口；宿主要求重新加载时按宿主机制处理。仓库位置由使用者选定；设置过程无需新增账号登录。

## 📁 维护与文档导航

修改与验证规则见 [AGENTS.md](AGENTS.md)。

| 路径 | 用途 |
| --- | --- |
| [SETUP.md（英文）](SETUP.md) | 面向 Agent 的安装、依赖准备和验收步骤 |
| [skills/](skills/) | 独立 Skill、参考资料及配套脚本 |
| [scripts/link-skills.sh](scripts/link-skills.sh) | 本仓库 Skill 的本机链接管理 |
| [AGENTS.md](AGENTS.md) | 项目工作范围与验证命令 |
| [.github/workflows/skills.yml](.github/workflows/skills.yml) | doc-sync 与 md-to-pdf 的回归任务 |

## 🤝 贡献须知

每个 PR 聚焦一个问题，附最小复现、修改原因和实际验证结果。规范修改附前后对照，行为修改补充回归测试，相关说明与中英文 README 同步更新；凭据与私人文档保留在仓库外。完整要求见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

本仓库采用 [MIT License（英文）](LICENSE)，版权署名为 `Copyright (c) 2026 Eason412`。复制或分发软件及文档时保留许可证要求的版权与许可声明。
