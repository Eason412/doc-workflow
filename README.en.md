# Doc Workflow

[中文](README.md) | English

**Keep project documentation, bilingual text, and printed documents accurate and clear.** This repository contains four writing and documentation Skills for documentation updates, Chinese–English translation, removal of defensive wording, and Markdown-to-PDF conversion. Each Skill is a standalone set of agent task instructions with `SKILL.md` as its entry point.

> ⚠️ Prerequisites: the agent must be able to read `SKILL.md` and its referenced files. PDF conversion also requires Pandoc, a Chrome-family browser, and fonts for Chinese and English text.

## ✨ Features

- 🔎 **Documentation grounded in code**: documentation follows source code, configuration, and tests. project-docs writes or updates Chinese and English READMEs with matching sections by default, and the Skill includes a local link checker.
- 🌐 **Consistent bilingual structure and terminology**: translation preserves headings, tables, formulas, and code structure, uses a shared glossary, and checks negation, numbers, conditions, and modality.
- ✂️ **Concise decision documents**: disclaimers that merely demonstrate diligence and stacked hedges are removed, while decision-relevant limits and the original strength of evidence are preserved.
- 🖨️ **Print layout adaptation**: print styles handle wide tables, long code lines, and Chinese–English font fallback, with paper size and orientation options. Output is replaced only after PDF readability, page count, and dimensions pass validation.

## 🧩 Skills

| Skill | Purpose | Supporting material |
| --- | --- | --- |
| [project-docs](skills/project-docs/SKILL.md) (Chinese) | Writing, reviewing, and updating READMEs, project documentation, and handover notes | [README guidelines](skills/project-docs/references/readme.md) (Chinese), [link checker](skills/project-docs/scripts/check_readme.py) |
| [translate](skills/translate/SKILL.md) (Chinese) | Chinese–English translation of papers, technical documents, and notes | [Glossary](skills/translate/references/glossary.md) (Chinese–English) |
| [trim-hedging](skills/trim-hedging/SKILL.md) (Chinese) | Editing or reviewing defensive wording in proposals, plans, and research summaries | [Boundary examples](skills/trim-hedging/references/examples.md) (Chinese) |
| [md-export](skills/md-export/SKILL.md) (Chinese) | Printable PDF conversion for general Markdown documents | [Troubleshooting](skills/md-export/references/qa.md) (Chinese), [print styles](skills/md-export/assets/print.css) |

Each Skill is a complete installation unit and runs without another Skill or the repository root. Academic Skills are maintained in the sister repository [paper-workflow](https://github.com/Eason412/paper-workflow).

## 🛠️ Requirements

Agents that load `SKILL.md`, including Codex and Claude Code, can use these instructions. Available file access, script execution, and PDF reading capabilities determine the tasks a host can perform. The instructions are primarily in Chinese.

| Function | Dependencies | Source |
| --- | --- | --- |
| Documentation writing, translation, and wording edits | An agent; the text instructions require no extra packages | Each Skill's `SKILL.md` |
| Local README link checks | uv, Python ≥ 3.10, `markdown-it-py>=3` | [Checker](skills/project-docs/scripts/check_readme.py) |
| PDF conversion | uv, Python ≥ 3.10, `pymupdf>=1.24`, Pandoc, Chrome / Chromium / Edge | [Converter](skills/md-export/scripts/md_to_pdf.py) |
| Chinese typesetting | Available Chinese and English fonts, with print-style fallback | [Font stack](skills/md-export/assets/print.css) |

Python scripts run through uv using inline dependency declarations. Git tracking checks require Git; `pdffonts` is only a font troubleshooting tool. PDF conversion uses HTML and browser printing, with no TeX requirement. Preparation and validation are described in [SETUP.md](SETUP.md).

## 🚀 Setup

An agent reads [SETUP.md](SETUP.md) and completes the setup. Afterward, a new agent session confirms Skill discovery and entry-point access; any reload follows the host's own mechanism. The user selects the repository location. Setup requires no additional account login.

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

Each PR focuses on one issue and includes a minimal reproduction, the reason for the change, and actual validation results. Instruction changes include before-and-after examples; behavior changes include regression tests. Related documentation and both READMEs stay in sync. Credentials and private documents remain outside the repository. Full requirements are in [CONTRIBUTING.md](CONTRIBUTING.md) (Chinese).

## 📄 License

This repository uses the [MIT License](LICENSE), with `Copyright (c) 2026 Eason412`. Copies and distributions of the software and documentation retain the copyright and permission notices required by the license.
