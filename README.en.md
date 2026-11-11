# Doc Workflow

[中文](README.md) | English

**Keep project documentation, bilingual text, and non-paper deliverables accurate and clear.** This repository contains three writing and documentation Skills for documentation updates, Chinese–English translation, and non-paper Chinese writing and concise wording. Each Skill is a standalone set of agent task instructions with `SKILL.md` as its entry point.

Latest published release: [V0.1.0](https://github.com/Eason412/doc-workflow/releases/tag/V0.1.0) ([all versions and release notes](https://github.com/Eason412/doc-workflow/releases)); the `main` branch includes subsequent additions and removals. The former document-export Skill `md-export` has been archived; its complete contents remain in [release V0.1.0](https://github.com/Eason412/doc-workflow/tree/V0.1.0/skills/md-export).

> ⚠️ Prerequisites: the agent must be able to read `SKILL.md` and its referenced files; running the README checker also requires uv and Python 3.10+.

## ✨ Features

- 🔎 **Documentation grounded in code**: Documentation follows source code, configuration, and tests. project-docs writes or updates Chinese and English READMEs with matching sections for public projects and a plain Chinese README for internal ones, and includes a checker for local links, anchors, and bilingual structure.
- 🌐 **Consistent bilingual structure and domain glossaries**: Translation preserves headings, tables, formulas, and code structure, uses per-domain glossaries while prioritizing per-project terminology, and checks negation, numbers, conditions, and modality.
- ✂️ **Clear non-paper Chinese writing and concise decision prose**: Cover Chinese technical proposals, reports, thesis proposals, blogs, and post-translation polishing, while removing defensive disclaimers and stacked hedges in Chinese or English drafts without altering decision-relevant limits or evidence strength.

## 🧩 Skills

| Skill | Purpose | Supporting material |
| --- | --- | --- |
| [project-docs](skills/project-docs/SKILL.md) (Chinese) | Writing, reviewing, and updating READMEs, project documentation, and handover notes | [README guidelines](skills/project-docs/references/readme.md) (Chinese), [checker](skills/project-docs/scripts/check_readme.py) |
| [translate](skills/translate/SKILL.md) (Chinese) | Chinese–English translation of papers, technical documents, and notes | [Domain-adaptation glossary](skills/translate/references/domain-adaptation.md) (Chinese–English) |
| [writing-zh](skills/writing-zh/SKILL.md) (Chinese) | Chinese proposals, reports, thesis proposals, blogs, post-translation polishing, and Chinese/English defensive-wording edits or reviews | [Boundary examples](skills/writing-zh/references/examples.md) (Chinese) |

Each Skill is a complete installation unit and runs without another Skill or the repository root. Paper writing and academic Skills are maintained in the sister repository [paper-workflow](https://github.com/Eason412/paper-workflow), while other writing Skills belong in this repository.

project-docs requires explicit invocation: use `/project-docs` in Claude Code or `$project-docs` in Codex. Routine documentation tasks and work-record maintenance do not load it automatically; its guidelines and checking tools remain available when needed.

## 🛠️ Requirements

- **Hosts**: Agents that load `SKILL.md`, including Codex and Claude Code, can use these instructions. Available file access, script execution, and PDF reading capabilities determine the tasks a host can perform.
- **Language**: The instructions are primarily in Chinese.

| Function | Dependencies | Source |
| --- | --- | --- |
| Documentation writing, translation, and non-paper editing | An agent; the text instructions require no extra packages | Each Skill's `SKILL.md` |
| README link and bilingual checks | uv, Python ≥ 3.10, `markdown-it-py>=3` | [Checker](skills/project-docs/scripts/check_readme.py) |

- **Python dependencies**: Scripts run through uv using inline dependency declarations, with no packages to install in advance.
- **Optional tools**: Git tracking checks require Git.
- **Preparation and validation**: The steps are in [SETUP.md](SETUP.md).

## 🚀 Setup

- **Setup**: An agent reads [SETUP.md](SETUP.md) and completes the setup; the user selects the repository location.
- **Afterward**: A new agent session confirms Skill discovery and entry-point access; any reload follows the host's own mechanism.
- **User actions**: None; setup requires no additional account login.

## 📁 Maintenance and Documentation

Editing and validation rules are in [AGENTS.md](AGENTS.md) (Chinese).

| Path | Purpose |
| --- | --- |
| [SETUP.md](SETUP.md) | Agent setup instructions, dependency preparation, and validation |
| [skills/](skills/) | Standalone Skills, references, and supporting scripts |
| [scripts/link-skills.sh](scripts/link-skills.sh) | Local link management for repository Skills |
| [AGENTS.md](AGENTS.md) (Chinese) | Project scope and validation commands |
| [.github/workflows/skills.yml](.github/workflows/skills.yml) | Regression jobs for repository Skills and documentation links |

## 🤝 Contributions

Compatibility fixes, feature improvements, and instruction revisions are welcome. Before opening a PR:

- **Scope**: Each PR focuses on one issue and includes a minimal reproduction, the reason for the change, and actual validation results.
- **Instruction changes**: Include before-and-after examples.
- **Behavior changes**: Add regression tests, and keep related documentation and both READMEs in sync.
- **Privacy**: Credentials and private documents stay outside the repository.

Full requirements are in [CONTRIBUTING.md](CONTRIBUTING.md) (Chinese).

## 📄 License

This repository uses the [MIT License](LICENSE), with `Copyright (c) 2026 Eason412`. Copies and distributions of the software and documentation retain the copyright and permission notices required by the license.
