# Doc Workflow 项目规则

本仓库维护三个相互独立的写作与文档类 Agent Skill：README 与项目文档同步、中英互译、非论文中文写作与措辞精简。运行行为以各 Skill 的源码与测试为准，任务按对应 `SKILL.md` 执行。

## 工作范围

| 任务 | 入口 |
| --- | --- |
| README 与项目文档 | [project-docs](skills/project-docs/SKILL.md) |
| 中英翻译 | [translate](skills/translate/SKILL.md) |
| 非论文写作与措辞精简 | [writing-zh](skills/writing-zh/SKILL.md) |
| 安装、导航与 CI | 根 README、[SETUP.md](SETUP.md)、贡献指南和 `.github/workflows/` |

每个 Skill 保持完整安装单元，不依赖另一个 Skill 或总仓库根目录运行。入口为 `SKILL.md`，Codex 的显示信息放在 `agents/openai.yaml`。

使用 Magpie 资源库的环境经 `~/.config/magpie/library/skills/<name>` 软链到本仓库 `skills/<name>` 并统一分发到各客户端（不再运行 `scripts/link-skills.sh`）；独立环境可用 `scripts/link-skills.sh` 软链到 `~/.codex/skills` 与 `~/.claude/skills`。软链下本地优化 Skill 即修改本仓库，验证通过后提交并推送。**论文写作归 paper-workflow，其他写作归 doc-workflow。**

## 修改与验证

- 先检查 Git 状态，保留现有改动；只处理用户要求及其必要关联变更。
- 行为修复补充回归测试。用户可见命令、状态或依赖变化同步使用说明；根目录 README 与 README.en.md 保持一致。
- 测试在对应目录、独立进程中执行：

| 范围 | 命令 |
| --- | --- |
| 仓库与文本技能检查 | 在根目录运行 `PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m unittest discover -s tests -v` |
| project-docs | `PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with markdown-it-py python -m unittest discover -s tests -v` |

- translate、writing-zh 为纯文本规范，改动检查内容、差异与内部链接；写作类规范的重要修改用新旧双盲对照验证：平时写稿的执行者分别按旧版、新版规范运行全套回归题并照常读参考文件，评判方在不知哪份为新版时比较结果。
- 修改 Skill 规范后检查 frontmatter 与相对链接；README 与 SETUP 改动用 project-docs 的 `check_readme.py` 检查链接与双语对齐。

## 数据与发布

测试使用临时输入和隔离输出。凭据、未公开稿件、私人文档和本机绝对路径不进入源码或提示词。

提交前检查差异和相对链接，使用 GitHub noreply 邮箱。远端更名、公开和删除按用户授权范围执行；破坏性操作先说明具体目标及影响并等待确认。交付区分源码修改、安装入口、测试和推送结果。
