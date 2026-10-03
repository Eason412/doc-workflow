# Doc Workflow

[中文](README.md) | English

**Keep project documentation, bilingual text, and delivered documents accurate and clear.** This repository contains four writing and documentation Skills for documentation updates, Chinese–English translation, removal of defensive wording, and Markdown export to Word or PDF. Each Skill is a standalone set of agent task instructions with `SKILL.md` as its entry point.

Current version: [V0.1.0](https://github.com/Eason412/doc-workflow/releases/tag/V0.1.0) ([all versions and release notes](https://github.com/Eason412/doc-workflow/releases)).

> ⚠️ Prerequisites: the agent must be able to read `SKILL.md` and its referenced files. Word export requires Pandoc 3.9+; PDF export also requires LibreOffice and fonts for Chinese and English text.

## ✨ Features

- 🔎 **Documentation grounded in code**: Documentation follows source code, configuration, and tests. project-docs writes or updates Chinese and English READMEs with matching sections by default, and includes a checker for local links, anchors, and bilingual structure.
- 🌐 **Consistent bilingual structure and terminology**: Translation preserves headings, tables, formulas, and code structure, uses a shared glossary, and checks negation, numbers, conditions, and modality.
- ✂️ **Concise decision documents**: Disclaimers that merely demonstrate diligence and stacked hedges are removed, while decision-relevant limits and the original strength of evidence are preserved.
- 🖨️ **Word and PDF export by preset**: One Markdown file becomes an editable Word document in the general, academic, or official-document (公文) preset, and the PDF comes from that same Word file. Fonts, sizes, line spacing, and numbering are checked item by item, and output is replaced only after the checks pass.

## 🧩 Skills

| Skill | Purpose | Supporting material |
| --- | --- | --- |
| [project-docs](skills/project-docs/SKILL.md) (Chinese) | Writing, reviewing, and updating READMEs, project documentation, and handover notes | [README guidelines](skills/project-docs/references/readme.md) (Chinese), [checker](skills/project-docs/scripts/check_readme.py) |
| [translate](skills/translate/SKILL.md) (Chinese) | Chinese–English translation of papers, technical documents, and notes | [Glossary](skills/translate/references/glossary.md) (Chinese–English) |
| [trim-hedging](skills/trim-hedging/SKILL.md) (Chinese) | Editing or reviewing defensive wording in proposals, plans, and research summaries | [Boundary examples](skills/trim-hedging/references/examples.md) (Chinese) |
| [md-export](skills/md-export/SKILL.md) (Chinese) | Exporting Markdown documents to Word or PDF by layout preset | [Presets](skills/md-export/references/presets.md) (Chinese), [troubleshooting](skills/md-export/references/qa.md) (Chinese) |

Each Skill is a complete installation unit and runs without another Skill or the repository root. Academic Skills are maintained in the sister repository [paper-workflow](https://github.com/Eason412/paper-workflow).

## 🛠️ Requirements

- **Hosts**: Agents that load `SKILL.md`, including Codex and Claude Code, can use these instructions. Available file access, script execution, and PDF reading capabilities determine the tasks a host can perform.
- **Language**: The instructions are primarily in Chinese.

| Function | Dependencies | Source |
| --- | --- | --- |
| Documentation writing, translation, and wording edits | An agent; the text instructions require no extra packages | Each Skill's `SKILL.md` |
| README link and bilingual checks | uv, Python ≥ 3.10, `markdown-it-py>=3` | [Checker](skills/project-docs/scripts/check_readme.py) |
| Word export | uv, Python ≥ 3.10, `python-docx`, `pdfplumber`, Pandoc 3.9+ | [Exporter](skills/md-export/scripts/md_export.py) |
| PDF export | The Word export dependencies, plus LibreOffice and Chinese and English fonts | [Troubleshooting](skills/md-export/references/qa.md) (Chinese) |

- **Python dependencies**: Scripts run through uv using inline dependency declarations, with no packages to install in advance.
- **Optional tools**: Git tracking checks require Git; Poppler's `pdftoppm` renders PDF pages to images for visual review.
- **Preparation and validation**: The steps are in [SETUP.md](SETUP.md).

## 🚀 Setup

- **Setup**: An agent reads [SETUP.md](SETUP.md) and completes the setup; the user selects the repository location.
- **Afterward**: A new agent session confirms Skill discovery and entry-point access; any reload follows the host's own mechanism.
- **User actions**: None; setup requires no additional account login.

| Setting | Location | Description |
| --- | --- | --- |
| LibreOffice path | Environment variable `MD_EXPORT_SOFFICE` | Set when `soffice` is not on PATH |
| Custom layout preset | `--preset <file>.json` | Override keys are in [Presets](skills/md-export/references/presets.md) (Chinese) |

## 📁 Maintenance and Documentation

Editing and validation rules are in [AGENTS.md](AGENTS.md) (Chinese).

| Path | Purpose |
| --- | --- |
| [SETUP.md](SETUP.md) | Agent setup instructions, dependency preparation, and validation |
| [skills/](skills/) | Standalone Skills, references, and supporting scripts |
| [scripts/link-skills.sh](scripts/link-skills.sh) | Local link management for repository Skills |
| [AGENTS.md](AGENTS.md) (Chinese) | Project scope and validation commands |
| [.github/workflows/skills.yml](.github/workflows/skills.yml) | Regression jobs for project-docs and md-export |

## 🤝 Contributions

Compatibility fixes, feature improvements, and instruction revisions are welcome. Before opening a PR:

- **Scope**: Each PR focuses on one issue and includes a minimal reproduction, the reason for the change, and actual validation results.
- **Instruction changes**: Include before-and-after examples.
- **Behavior changes**: Add regression tests, and keep related documentation and both READMEs in sync.
- **Privacy**: Credentials and private documents stay outside the repository.

Full requirements are in [CONTRIBUTING.md](CONTRIBUTING.md) (Chinese).

## 📄 License

This repository uses the [MIT License](LICENSE), with `Copyright (c) 2026 Eason412`. Copies and distributions of the software and documentation retain the copyright and permission notices required by the license.
