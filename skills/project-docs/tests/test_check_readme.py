import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
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

    def test_anchors_are_not_checked_but_declared(self):
        report = self.report("[跳转](#nowhere)")
        self.assertTrue(report["ok"])
        self.assertEqual(report["links_checked"], 0)
        self.assertIn("页内锚点", report["not_checked"])

    def test_path_with_fragment_checks_the_path_only(self):
        self.touch("guide.md")
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


if __name__ == "__main__":
    unittest.main()
