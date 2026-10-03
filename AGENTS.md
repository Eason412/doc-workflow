# Doc Workflow 项目规则

本仓库维护四个相互独立的写作与文档类 Agent Skill：README 与项目文档同步、中英互译、删除防御性措辞和 Markdown 转 PDF。运行行为以各 Skill 的源码与测试为准，任务按对应 `SKILL.md` 执行。

## 工作范围

| 任务 | 入口 |
| --- | --- |
| README 与项目文档 | [doc-sync](skills/doc-sync/SKILL.md) |
| 中英翻译 | [translate](skills/translate/SKILL.md) |
| 删除防御性措辞 | [trim-hedging](skills/trim-hedging/SKILL.md) |
| Markdown 转 PDF | [md-to-pdf](skills/md-to-pdf/SKILL.md) |
| 安装、导航与 CI | 根 README、[SETUP.md](SETUP.md)、贡献指南和 `.github/workflows/` |

每个 Skill 保持完整安装单元，不依赖另一个 Skill 或总仓库根目录运行。入口为 `SKILL.md`，Codex 的显示信息放在 `agents/openai.yaml`。

本机的 `~/.codex/skills/<name>`、`~/.claude/skills/<name>` 由 `scripts/link-skills.sh` 软链到本仓库 `skills/<name>`，在本机优化 Skill 即修改本仓库；验证通过后提交并推送。新增 Skill 后重跑该脚本。学术类 Skill 在姊妹仓库 paper-workflow 维护。

## 修改与验证

- 先检查 Git 状态，保留现有改动；只处理用户要求及其必要关联变更。
- 行为修复补充回归测试。用户可见命令、状态或依赖变化同步使用说明；根目录 README 与 README.en.md 保持一致。
- 测试在各自 Skill 目录、独立进程中执行：

| Skill | 命令 |
| --- | --- |
| doc-sync | `PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with markdown-it-py python -m unittest discover -s tests -v` |
| md-to-pdf | `PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with pymupdf python -m unittest discover -s tests -v` |

- translate、trim-hedging 只有规范文本，改动检查内容与差异；写作类规范的重要修改可用盲写对照验证：执行者只读规范从零写，再与认可稿逐处比较。
- 修改 Skill 规范后，用 `quick_validate.py` 等校验工具检查 frontmatter；README 改动用 doc-sync 的 `check_readme.py` 检查链接。

## 数据与发布

测试使用临时输入和隔离输出。凭据、私人文档和本机绝对路径不进入源码或提示词。

提交前检查差异和相对链接，使用 GitHub noreply 邮箱。远端更名、公开和删除按用户授权范围执行；破坏性操作先说明具体目标及影响并等待确认。交付区分源码修改、安装入口、测试和推送结果。
