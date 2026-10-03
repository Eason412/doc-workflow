import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/check_readme.py"
spec = importlib.util.spec_from_file_location("readme_checker", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def write(self, text):
        (self.root / "README.md").write_text(text, encoding="utf-8")

    def touch(self, relative, text="# Doc"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def report(self, text, **kwargs):
        self.write(text)
        return m.check(self.root, **kwargs)

    def issues(self, report):
        return [(i["line"], i["target"], i["reason"]) for i in report["issues"]]

    # 原有行为

    def test_tracked_link(self):
        self.touch("docs/guide.md")
        subprocess.run(["git", "add", "--", "docs/guide.md"], cwd=self.root, check=True)
        report = self.report("[指南](docs/guide.md)", require_tracked=True)
        self.assertTrue(report["ok"])

    def test_untracked_link(self):
        self.touch("guide.md")
        report = self.report("[指南](guide.md)", require_tracked=True)
        self.assertFalse(report["ok"])
        self.assertEqual(report["issues"][0]["reason"], "目标未进入Git索引")

    def test_missing(self):
        report = self.report("[缺失](missing.md)")
        self.assertEqual(self.issues(report), [(1, "missing.md", "目标不存在")])

    def test_local_work(self):
        self.touch(".work/task.md", "private")
        report = self.report("[任务](.work/task.md)")
        self.assertEqual(report["issues"][0]["reason"], "README引用本机工作记录")

    def test_outside_repo(self):
        report = self.report("[本机](/Users/someone/file.md)")
        self.assertEqual(report["issues"][0]["reason"], "仓外本地链接")

    def test_code_examples_not_links(self):
        report = self.report("```md\n[示例](missing.md)\n```\n[网站](https://example.invalid)")
        self.assertTrue(report["ok"])
        self.assertEqual(report["links_checked"], 0)

    def test_reference_and_spaces(self):
        self.touch("two words.md")
        report = self.report("[guide]: <two words.md>")
        self.assertTrue(report["ok"])
        self.assertEqual(report["links_checked"], 1)

    # 解析回归

    def test_link_title_is_not_part_of_path(self):
        self.touch("good.md")
        report = self.report('[valid](good.md "Title")\n[gone](missing.md \'Tip\')')
        self.assertEqual(self.issues(report), [(2, "missing.md", "目标不存在")])
        self.assertEqual(report["links_checked"], 2)

    def test_inline_code_is_not_a_link(self):
        report = self.report("用法见 `[example](missing.md)`，另见 ``[x](gone.md)``。")
        self.assertTrue(report["ok"])
        self.assertEqual(report["links_checked"], 0)

    def test_parentheses_in_path(self):
        self.touch("folder_(x)/guide.md")
        report = self.report("[ok](folder_(x)/guide.md)\n[bad](folder_(y)/guide.md)")
        self.assertEqual(self.issues(report), [(2, "folder_(y)/guide.md", "目标不存在")])

    def test_nested_fence_with_shorter_fence_inside(self):
        text = "````md\n```\n[inside](missing.md)\n```\n[still inside](missing.md)\n````\n[real](gone.md)\n"
        report = self.report(text)
        self.assertEqual(self.issues(report), [(7, "gone.md", "目标不存在")])

    def test_file_scheme_is_checked_as_local_path(self):
        self.touch("guide.md")
        inside = f"file://{self.root}/guide.md"
        missing = f"file://{self.root}/missing.md"
        report = self.report(f"[a]({inside})\n[b]({missing})\n[c](file:///etc/hosts)")
        self.assertEqual(
            self.issues(report),
            [(2, missing, "目标不存在"), (3, "file:///etc/hosts", "仓外本地链接")],
        )
        self.assertEqual(report["links_checked"], 3)

    def test_html_anchor_and_image(self):
        self.touch("exists.md")
        self.touch("pic.png", "x")
        text = (
            '<a href="exists.md">ok</a> <img src="pic.png" alt="">\n'
            '文字 <a href="missing.md">bad</a>\n'
            '\n'
            '<div>\n'
            '  <img src="gone.png">\n'
            '</div>\n'
        )
        report = self.report(text)
        self.assertEqual(
            self.issues(report),
            [(2, "missing.md", "目标不存在"), (5, "gone.png", "目标不存在")],
        )
        self.assertEqual(report["links_checked"], 4)

    def test_html_external_and_comments_ignored(self):
        report = self.report('<a href="https://example.invalid">x</a>\n\n<!-- <a href="missing.md">x</a> -->\n')
        self.assertTrue(report["ok"])
        self.assertEqual(report["links_checked"], 0)

    def test_markdown_image(self):
        report = self.report("![图](assets/missing.png)")
        self.assertEqual(self.issues(report), [(1, "assets/missing.png", "目标不存在")])

    def test_missing_anchor_is_checked(self):
        report = self.report("[跳转](#nowhere)")
        self.assertFalse(report["ok"])
        self.assertEqual(report["links_checked"], 1)
        self.assertNotIn("页内锚点", report["not_checked"])
        self.assertEqual(self.issues(report), [(1, "#nowhere", "锚点不存在")])

    def test_path_with_fragment_checks_path_and_anchor(self):
        self.touch("guide.md", "# Section")
        report = self.report("[a](guide.md#section)\n[b](missing.md#section)")
        self.assertEqual(self.issues(report), [(2, "missing.md#section", "目标不存在")])

    def test_unused_reference_definition_is_checked(self):
        report = self.report("正文\n\n[unused]: missing.md\n")
        self.assertEqual(self.issues(report), [(3, "missing.md", "目标不存在")])

    def test_used_reference_is_reported_at_use_site_only(self):
        report = self.report("[text][ref] 和 [ref]\n\n[ref]: missing.md\n")
        self.assertEqual([i[1] for i in self.issues(report)], ["missing.md", "missing.md"])
        self.assertEqual({i[0] for i in self.issues(report)}, {1})

    def test_table_cell_link_reports_its_line(self):
        report = self.report("| 名称 | 链接 |\n| --- | --- |\n| a | [x](missing.md) |\n")
        self.assertEqual(self.issues(report), [(3, "missing.md", "目标不存在")])

    def test_line_number_after_soft_break(self):
        report = self.report("第一行\n第二行 [x](missing.md)\n")
        self.assertEqual(self.issues(report), [(2, "missing.md", "目标不存在")])

    def test_cli_json_output(self):
        self.write("[缺失](missing.md)")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.root), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        for key in ("file", "ok", "links_checked", "issues", "not_checked"):
            self.assertIn(key, report)
        self.assertFalse(report["ok"])

    def test_cli_missing_file_reports_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.root), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("error", json.loads(result.stdout))


    def pair(self, left="", right="", switches=True):
        prefix_left = "# 项目\n\n[English](README.en.md)\n\n" if switches else "# 项目\n\n"
        prefix_right = "# Project\n\n[中文](README.md)\n\n" if switches else "# Project\n\n"
        self.write(prefix_left + left)
        self.touch("README.en.md", prefix_right + right)
        return m.check_pair(self.root, ["README.md", "README.en.md"])

    def category(self, report, category, severity="error"):
        return [i for i in report["issues"] if i["category"] == category and i["severity"] == severity]

    def test_heading_slugs_rendered_unicode_and_punctuation(self):
        report = self.report(
            '# **Hello**, `World`! [链接](https://example.invalid) <em>中文</em>\n'
            '[ok](#hello-world-链接-中文)\n'
            '# Café 你好_世界 - 123！\n'
            '[ok](#caf%C3%A9-%E4%BD%A0%E5%A5%BD_%E4%B8%96%E7%95%8C---123)\n'
        )
        self.assertTrue(report["ok"], report)

    def test_duplicate_heading_collision(self):
        report = self.report('# a\n# a\n# a-1\n# a\n[x](#a) [x](#a-1) [x](#a-1-1) [x](#a-2)')
        self.assertTrue(report["ok"], report)
        self.assertEqual(m.Document('# a\n# a\n# a-1\n# a').anchors, {"a", "a-1", "a-1-1", "a-2"})

    def test_html_id_name_and_case_sensitive(self):
        report = self.report('<div id="Mixed"></div>\n\n<a name="Name"></a>\n\n'
                             '[a](#Mixed) [b](#Name) [c](#mixed)\n')
        self.assertEqual(self.issues(report), [(5, '#mixed', '锚点不存在')])

    def test_cross_file_anchor_and_missing(self):
        self.touch('docs/guide.md', '# 中文\n<a id="A"></a>')
        report = self.report('[a](docs/guide.md#中文)\n[b](docs/guide.md#A)\n[c](docs/guide.md#missing)')
        self.assertEqual(self.issues(report), [(3, 'docs/guide.md#missing', '锚点不存在')])

    def test_non_markdown_fragment_is_not_checked(self):
        self.touch('asset.svg', '<svg/>')
        self.assertTrue(self.report('[x](asset.svg#missing)')["ok"])

    def test_bilingual_aligned(self):
        self.touch('guide.md')
        self.touch('guide.en.md')
        self.touch('pic.png', 'image')
        left = '## 用法\n| 名称 | 值 |\n| --- | --- |\n| a | b |\n```sh\nrun --help\n```\n`x` `y` `x`\n[文档](guide.md) ![图](pic.png)'
        right = '## Usage\n| Name | Value |\n| --- | --- |\n| a | b |\n```sh\nrun --help\n```\n`y` `x` `x`\n[Guide](guide.en.md) ![Image](pic.png)'
        report = self.pair(left, right)
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['issues'], [])

    def test_pair_heading_levels(self):
        report = self.pair('## 用法', '### Usage')
        issue, = self.category(report, 'headings')
        self.assertEqual(issue['left'][0]['line'], 5)
        self.assertEqual(issue['right'][0]['line'], 5)
        self.assertFalse(report['ok'])

    def test_pair_heading_count(self):
        report = self.pair('## 用法', '')
        issue, = self.category(report, 'headings')
        self.assertEqual(issue['right'], [])

    def test_pair_table_columns(self):
        report = self.pair('| A | B |\n| --- | --- |\n| a | b |', '| A |\n| --- |\n| a |')
        issue, = self.category(report, 'tables')
        self.assertEqual(issue['left'][0]['line'], 5)
        self.assertEqual(issue['right'][0]['content'], {'rows': 2, 'columns': [1, 1]})

    def test_pair_table_rows(self):
        report = self.pair('| A |\n| --- |\n| a |', '| A |\n| --- |')
        self.assertEqual(len(self.category(report, 'tables')), 1)

    def test_pair_fenced_command_change(self):
        report = self.pair('```sh\nrun --help\n```', '```sh\nrun --version\n```')
        issue, = self.category(report, 'fenced_code')
        self.assertEqual(issue['left'][0]['line'], 5)
        self.assertIn('--version', issue['right'][0]['content']['code'])

    def test_pair_fence_language_and_missing(self):
        for right in ('```bash\nrun\n```', ''):
            with self.subTest(right=right):
                report = self.pair('```sh\nrun\n```', right)
                self.assertFalse(report['ok'])
                self.assertEqual(len(self.category(report, 'fenced_code')), 1)

    def test_pair_translatable_fences_warn(self):
        for language in ('text', '', 'json', 'yaml'):
            with self.subTest(language=language):
                report = self.pair(f'```{language}\n中文\n```', f'```{language}\nEnglish\n```')
                self.assertTrue(report['ok'], report)
                issue, = self.category(report, 'fenced_code', 'warning')
                self.assertEqual(issue['left'][0]['line'], 5)

    def test_pair_inline_missing_multiset_and_positions(self):
        report = self.pair('`run`\n`run` `--help`', '`run` `--help`')
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'], [{'file': 'README.md', 'line': 6, 'content': 'run'}])
        self.assertEqual(issue['right'], [])

    def test_pair_normalized_placeholder_command_change_is_error(self):
        report = self.pair('`tool --help <模型>`', '`tool --version <model>`')
        self.assertFalse(report['ok'])
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'][0]['content'], 'tool --help <模型>')
        self.assertEqual(issue['right'][0]['content'], 'tool --version <model>')
        self.assertFalse(self.category(report, 'inline_code', 'warning'))

    def test_pair_normalized_counts_do_not_treat_placeholder_as_chinese(self):
        report = self.pair('`<模型> --help` `甲文档`', '`<model> --wrong` `doc-a`')
        self.assertFalse(report['ok'])
        issue, = self.category(report, 'inline_code')
        self.assertEqual(len(issue['right']), 2)

    def test_pair_bracket_subscript_change_is_error(self):
        for left, right in [('config["timeout"]', 'config["retries"]'),
                            ('config[timeout]', 'config[retries]'),
                            ('config()[timeout]', 'config()[retries]'),
                            ('config[0][timeout]', 'config[0][retries]')]:
            with self.subTest(left=left):
                report = self.pair(f'`{left}`', f'`{right}`')
                self.assertFalse(report['ok'])
                self.assertEqual(len(self.category(report, 'inline_code')), 1)

    def test_pair_bracket_array_change_is_error(self):
        for left, right in [('"writes": ["README.md"]', '"writes": ["secrets.txt"]'),
                            ("['README.md']", "['secrets.txt']"),
                            ('[first, second]', '[first, third]'), ('[10]', '[20]')]:
            with self.subTest(left=left):
                report = self.pair(f'`{left}`', f'`{right}`')
                self.assertFalse(report['ok'])
                self.assertEqual(len(self.category(report, 'inline_code')), 1)

    def test_pair_standalone_bracket_placeholder_matches(self):
        report = self.pair('`[任务名]`', '`[task]`')
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['issues'], [])

    def test_heading_slug_excludes_image_alt(self):
        self.touch('badge.svg', '<svg/>')
        report = self.report('# Awesome Shell ![Awesome](badge.svg)\n'
                             '[correct](#awesome-shell-)\n[wrong](#awesome-shell-awesome)')
        self.assertEqual(self.issues(report), [(3, '#awesome-shell-awesome', '锚点不存在')])

    def test_heading_slug_preserves_combining_marks(self):
        report = self.report('# Cafe\u0301\n[correct](#cafe%CC%81)\n[wrong](#cafe)')
        self.assertEqual(self.issues(report), [(3, '#cafe', '锚点不存在')])

    def test_heading_slug_unicode_categories(self):
        text = '字\u0301\u0903\u20dd ２_3-4!'
        self.assertEqual(m.heading_slug(text, set()), '字\u0301\u0903\u20dd-２_3-4')

    def test_heading_slug_github_connector_punctuation(self):
        self.assertEqual(m.heading_slug('A‿B⁀C⁔D︳E︴F﹍G﹎H﹏I＿J', set()),
                         'a‿b⁀c⁔d︳e︴f﹍g﹎h﹏i＿j')

    def test_heading_slug_github_number_categories(self):
        self.assertEqual(m.heading_slug('A² ¼ ① ١ Ⅳ B', set()), 'a---١-ⅳ-b')

    def test_heading_slug_github_alphabetic_symbols(self):
        self.assertEqual(m.heading_slug('AⒶⓩ🄰🅐🅰♥ B', set()), 'aⓐⓩ🄰🅐🅰-b')

    def test_heading_slug_github_unicode_version(self):
        # Unicode 13 的 CJK 扩展 G 保留，Unicode 15 的扩展 H 不进入 slug。
        self.assertEqual(m.heading_slug('A𰛸𰼤𱝏𱽻B', set()), 'a𰛸𰼤b')

    def test_pair_inline_position_after_multiline_link(self):
        body = '[web](https://example.invalid\n "title")\n'
        report = self.pair(body + '`--help`', body + '`--wrong`')
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'][0]['line'], 7)
        self.assertEqual(issue['right'][0]['line'], 7)

    def test_link_position_after_multiline_link(self):
        report = self.report('[web](https://example.invalid\n "title")\n[missing](missing.md)')
        self.assertEqual(self.issues(report), [(3, 'missing.md', '目标不存在')])

    def test_multiline_label_and_title_positions(self):
        report = self.report('[multi\nline](https://example.invalid\n "multi\nline title")\n'
                             '[missing](missing.md)')
        self.assertEqual(self.issues(report), [(5, 'missing.md', '目标不存在')])

    def test_pair_code_in_multiline_label_position(self):
        report = self.pair('[text\n`--help`](https://example.invalid\n "title")',
                           '[text\n`--wrong`](https://example.invalid\n "title")')
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'][0]['line'], 6)
        self.assertEqual(issue['right'][0]['line'], 6)

    def test_link_position_after_multiline_image(self):
        self.touch('badge.svg', '<svg/>')
        report = self.report('![image](badge.svg\n "title")\n[missing](missing.md)')
        self.assertEqual(self.issues(report), [(3, 'missing.md', '目标不存在')])

    def test_scripts_size_limits(self):
        for path in SCRIPT.parent.glob('*.py'):
            source = path.read_text(encoding='utf-8')
            with self.subTest(file=path.name):
                self.assertLessEqual(len(source.splitlines()), 500)
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    with self.subTest(file=path.name, function=node.name):
                        self.assertLessEqual(node.end_lineno - node.lineno + 1, 80)

    def test_uv_script_entrypoint_after_split(self):
        self.pair('## 用法', '## Usage')
        result = subprocess.run(['uv', 'run', 'scripts/check_readme.py', '--repo', str(self.root),
                                 '--pair', 'README.md', 'README.en.md', '--json'],
                                cwd=SCRIPT.parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])


    def test_pair_inline_changed_ascii_error(self):
        report = self.pair('`--help`', '`--version`')
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'][0]['line'], 5)
        self.assertEqual(issue['right'][0]['content'], '--version')

    def test_pair_placeholder_normalization(self):
        report = self.pair('`run <模型> [任务名] {{task:名字}} {{phase:阶段}}`', '`run <model> [task] {{task:name}} {{phase:phase}}`')
        self.assertTrue(report['ok'], report)
        self.assertFalse(self.category(report, 'inline_code', 'warning'))

    def test_pair_quoted_json_example_name_translation(self):
        report = self.pair('```json\n{"tasks": [{"label": "甲文档"}]}\n```\n「甲文档」',
                           '```json\n{"tasks": [{"label": "doc-a"}]}\n```\n`doc-a`')
        self.assertTrue(report['ok'], report)
        issue, = self.category(report, 'inline_code', 'warning')
        self.assertEqual(issue['left'][0], {'file': 'README.md', 'line': 8, 'content': '甲文档'})
        self.assertEqual(issue['right'][0]['line'], 8)

    def test_pair_example_mapping_cannot_hide_command_change(self):
        report = self.pair('```json\n{"label": "甲文档"}\n```\n「甲文档」 `--help`',
                           '```json\n{"label": "doc-a"}\n```\n`doc-a` `--wrong`')
        self.assertFalse(report['ok'])
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'][0]['content'], '--help')
        self.assertEqual(issue['right'][0]['content'], '--wrong')

    def test_pair_quoted_name_without_json_evidence_is_error(self):
        report = self.pair('「甲文档」', '`doc-a`')
        self.assertFalse(report['ok'])

    def test_pair_json_name_without_prose_evidence_is_error(self):
        report = self.pair('```json\n{"label": "甲文档"}\n```',
                           '```json\n{"label": "doc-a"}\n```\n`doc-a`')
        self.assertFalse(report['ok'])

    def test_pair_inserted_translatable_fence_keeps_command_alignment(self):
        report = self.pair('```sh\nrun\n```', '```text\nExtra caption\n```\n```sh\nrun\n```')
        self.assertTrue(report['ok'], report)
        self.assertEqual(len(self.category(report, 'fenced_code', 'warning')), 1)

    def test_pair_inline_position_after_multiline_code(self):
        report = self.pair('`multi\nline`\n`--help`', '`multi\nline`')
        issue, = self.category(report, 'inline_code')
        self.assertEqual(issue['left'][0]['line'], 7)


    def test_pair_translated_example_names(self):
        report = self.pair('`甲文档` `乙文档`', '`doc-a` `doc-b`')
        self.assertTrue(report['ok'], report)
        issue, = self.category(report, 'inline_code', 'warning')
        self.assertEqual(len(issue['left']), 2)
        self.assertEqual(len(issue['right']), 2)

    def test_pair_translation_count_does_not_hide_ascii_error(self):
        report = self.pair('`甲文档`', '`doc-a` `--wrong`')
        self.assertFalse(report['ok'])
        issue, = self.category(report, 'inline_code')
        self.assertEqual(len(issue['right']), 2)
        self.assertEqual(len(self.category(report, 'inline_code', 'warning')), 1)

    def test_pair_local_targets(self):
        self.touch('a.md')
        self.touch('b.md')
        report = self.pair('[a](a.md)', '[b](b.md)')
        issue, = self.category(report, 'link_targets')
        self.assertEqual(issue['left'][0], {'file': 'README.md', 'line': 5, 'content': 'a.md'})
        self.assertEqual(issue['right'][0]['content'], 'b.md')

    def test_pair_image_targets(self):
        self.touch('a.png')
        self.touch('b.png')
        report = self.pair('![a](a.png)', '<img src="b.png">')
        issue, = self.category(report, 'images')
        self.assertEqual(issue['left'][0]['line'], 5)
        self.assertEqual(issue['right'][0]['content'], 'b.png')

    def test_pair_missing_language_switch(self):
        report = self.pair('## 用法', '## Usage')
        self.touch('README.en.md', '# Project\n\n## Usage')
        report = m.check_pair(self.root, ['README.md', 'README.en.md'])
        issue, = self.category(report, 'language_switch')
        self.assertEqual(issue['left'], [])
        self.assertEqual(issue['right'][0]['line'], 1)

    def test_pair_switch_must_be_at_top(self):
        report = self.pair('## 用法\n[English](README.en.md)', '## Usage\n[中文](README.md)', switches=False)
        self.assertEqual(len(self.category(report, 'language_switch')), 2)

    def test_pair_unused_reference_is_not_language_switch(self):
        self.write('# 项目\n\n[English]: README.en.md\n\n## 用法')
        self.touch('README.en.md', '# Project\n\n[中文]: README.md\n\n## Usage')
        report = m.check_pair(self.root, ['README.md', 'README.en.md'])
        self.assertEqual(len(self.category(report, 'language_switch')), 2)

    def test_pair_image_fragments_are_distinct(self):
        self.touch('pic.svg', '<svg/>')
        report = self.pair('![a](pic.svg#one)', '![a](pic.svg#two)')
        self.assertFalse(report['ok'])
        self.assertEqual(len(self.category(report, 'images')), 1)

    def test_same_page_anchor_checks_tracking(self):
        report = self.report('# Doc\n[x](#doc)', require_tracked=True)
        self.assertEqual(report['issues'][0]['reason'], '目标未进入Git索引')

    def test_pair_checker_is_read_only(self):
        self.pair('## 用法', '## Usage')
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.root),
                                 '--pair', 'README.md', 'README.en.md', '--json'],
                                capture_output=True, text=True)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, after)


    def test_pair_checks_links_and_tracked(self):
        self.pair('[a](missing.md)', '[a](missing.md)')
        report = m.check_pair(self.root, ['README.md', 'README.en.md'], require_tracked=True)
        self.assertFalse(report['ok'])
        self.assertTrue(any(i['reason'] == '目标未进入Git索引' for i in report['issues']))
        self.assertTrue(any(i['reason'] == '目标不存在' for i in report['issues']))

    def test_pair_reuses_one_parse_per_document(self):
        self.pair('[x](README.en.md#project)', '[x](README.md#项目)')
        with patch.object(m, 'make_parser', wraps=m.make_parser) as parser:
            report = m.check_pair(self.root, ['README.md', 'README.en.md'])
        self.assertTrue(report['ok'], report)
        self.assertEqual(parser.call_count, 2)

    def test_pair_cli_warning_exit_zero_error_nonzero(self):
        for left, right, expected in [('`甲文档`', '`doc-a`', 0), ('`--help`', '`--wrong`', 1)]:
            with self.subTest(expected=expected):
                self.pair(left, right)
                result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.root),
                                         '--pair', 'README.md', 'README.en.md', '--json'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report['ok'], expected == 0)
                self.assertTrue(all('severity' in i for i in report['issues']))


if __name__ == "__main__":
    unittest.main()
