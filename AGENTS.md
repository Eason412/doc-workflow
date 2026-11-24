# Doc Workflow 项目规则

先读上级 [opensource 工作区规则](../AGENTS.md)。本仓库维护三个相互独立的写作与文档类 Agent Skill：README 与项目文档同步、中英互译、非论文中文写作与措辞精简。**论文写作归 `thesis-skills`，其他写作归 `doc-workflow`。**

## 工作范围

| 任务 | 入口 |
| --- | --- |
| README 与项目文档 | [project-docs](skills/project-docs/SKILL.md) |
| 中英翻译 | [translate](skills/translate/SKILL.md) |
| 非论文写作与措辞精简 | [writing-zh](skills/writing-zh/SKILL.md) |
| 安装、导航与 CI | 根 README、[SETUP.md](SETUP.md)、贡献指南和 `.github/workflows/` |

每个 Skill 保持完整安装单元，入口为 `SKILL.md`、Codex 显示信息放在 `agents/openai.yaml`。本机安装、分发与推送规矩见上级规则；独立环境可用 `scripts/link-skills.sh`。

## 修改与验证

- 行为修复补充回归测试。用户可见命令、状态或依赖变化同步使用说明；根目录 `README.md` 与 `README.en.md` 保持一致。
- 测试在对应目录、独立进程中执行：

| 范围 | 命令 |
| --- | --- |
| 仓库与文本技能检查 | 在根目录运行 `PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m unittest discover -s tests -v` |
| project-docs | 在 `skills/project-docs` 目录运行 `PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with markdown-it-py python -m unittest discover -s tests -v` |

- `translate`、`writing-zh` 为纯文本规范，重要修改的新旧对照盲测按技能 `rules-maintenance`「写作技能纠偏与盲测」执行。
- 修改 Skill 规范后检查 frontmatter 与相对链接；README 与 `SETUP.md` 改动用 `project-docs` 的 `check_readme.py` 检查链接与双语对齐。

## 数据与发布

测试使用临时输入和隔离输出。未公开稿件、私人文档和本机绝对路径不进入源码或提示词。使用 GitHub noreply 邮箱提交；远端更名、公开和删除按用户授权范围执行。
