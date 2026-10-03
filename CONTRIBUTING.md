# 贡献指南

## 变更范围

每个 PR 聚焦一个问题，通常只涉及一个 Skill。本仓库收录写作与文档类 Skill；学术类 Skill 在 [paper-workflow](https://github.com/Eason412/paper-workflow) 维护。源码、测试及使用说明应同步更新。

## 问题复现

提供受影响的 Skill、系统与相关工具版本、最小输入、执行命令或提示、预期结果、实际结果和脱敏错误。写作类 Skill 提供最小原文与期望输出；转换问题提供最小 Markdown。

不得上传凭据、私人文档、含个人信息的内容或本机绝对路径。

## 解决思路与验证

说明根因、修改范围及现有行为影响，补充对应回归测试；测试命令见 [AGENTS.md](AGENTS.md)。纯规范修改附修改前后的对照示例。根目录的中英文 README 应保持内容一致。

PR 标题建议采用 `fix:`、`feat:`、`docs:` 或 `test:` 加简洁说明。新增提交使用 GitHub noreply 邮箱。
