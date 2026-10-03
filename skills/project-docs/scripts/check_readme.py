#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py>=3"]
# ///
"""检查 README 的本地链接与 Git 可交付性，不执行安装或业务命令。

用法：uv run check_readme.py --repo <仓库> [--file README.md] [--require-tracked] [--json]
"""
import argparse
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

NOT_CHECKED = [
    "外部链接可用性",
    "页内锚点",
    "命令运行结果",
    "业务正确性",
    "中文表达质量",
]


class References(dict):
    """记录哪些引用式定义被链接实际用到，用来避免同一目标重复报告。"""

    def __init__(self):
        super().__init__()
        self.used = set()

    def get(self, key, default=None):
        value = super().get(key, default)
        if value is not None:
            self.used.add(key)
        return value

    def __getitem__(self, key):
        self.used.add(key)
        return super().__getitem__(key)


class HtmlTargets(HTMLParser):
    """收集 HTML 片段里的 <a href> 和 <img src>，并记录相对行号。"""

    def __init__(self):
        super().__init__()
        self.found = []  # (相对起始行的行偏移, 目标)

    def handle_starttag(self, tag, attrs):
        wanted = {"a": "href", "img": "src"}.get(tag)
        for name, value in attrs:
            if name == wanted and value:
                self.found.append((self.getpos()[0] - 1, value))


def html_targets(content):
    parser = HtmlTargets()
    parser.feed(content)
    parser.close()
    return parser.found


def make_parser():
    parser = MarkdownIt("commonmark").enable(["table", "strikethrough"])
    # 默认会拒绝 file:/data: 等协议，导致链接不被识别，这里交给后面的规则判断。
    parser.validateLink = lambda url: True
    return parser


def inline_targets(children, first_line):
    """遍历行内 token，产出 (行号, 目标)。代码 span 不含链接，天然被忽略。"""
    line = first_line
    for token in children:
        if token.type == "link_open":
            yield line, token.attrGet("href")
        elif token.type == "image":
            yield line, token.attrGet("src")
            yield from inline_targets(token.children or [], line)
        elif token.type == "html_inline":
            for offset, target in html_targets(token.content):
                yield line + offset, target
            line += token.content.count("\n")
        elif token.type in ("softbreak", "hardbreak"):
            line += 1


def links(text):
    """返回 [(行号, 目标)]，包含链接、图片、HTML 标签和引用式定义。"""
    parser = make_parser()
    references = References()
    env = {"references": references}
    tokens = parser.parse(text, env)

    found = []
    line = 1
    for token in tokens:
        if token.map:
            line = token.map[0] + 1
        if token.type == "inline":
            found.extend(inline_targets(token.children or [], line))
        elif token.type == "html_block":
            for offset, target in html_targets(token.content):
                found.append((line + offset, target))

    # 被用到的定义已按使用处报告；没被用到的定义也要检查。
    for label, reference in references.items():
        if label not in references.used and reference.get("href"):
            start = reference["map"][0] + 1 if reference.get("map") else 1
            found.append((start, reference["href"]))
    return sorted(found, key=lambda item: item[0])


def local_path(href):
    """返回链接指向的本地路径；外部链接、页内锚点和空链接返回 None。"""
    parts = urlsplit(href)
    if parts.scheme not in ("", "file"):
        return None
    if parts.scheme == "" and parts.netloc:
        return None  # //host/path 形式的外部链接
    if not parts.path:
        return None  # 纯 #fragment 或 ?query
    if parts.netloc not in ("", "localhost"):
        return ""  # file://其他主机/...，按仓外处理
    return unquote(parts.path)


def is_tracked(repo, relative):
    result = subprocess.run(
        ["git", "--literal-pathspecs", "ls-files", "--", relative],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def find_issue(repo, base, path, require_tracked):
    if path == "":
        return "仓外本地链接"
    target = (base / path).resolve()
    if not target.is_relative_to(repo):
        return "仓外本地链接"
    relative = target.relative_to(repo)
    if ".work" in relative.parts:
        return "README引用本机工作记录"
    if not target.exists():
        return "目标不存在"
    if require_tracked and not is_tracked(repo, str(relative)):
        return "目标未进入Git索引"
    return None


def check(repo, filename="README.md", require_tracked=False):
    repo = Path(repo).resolve()
    path = (repo / filename).resolve()
    if not path.is_relative_to(repo) or not path.is_file():
        raise ValueError("README必须为目标仓内的现有文件")

    problems = []
    checked = 0
    for number, href in links(path.read_text(encoding="utf-8")):
        local = local_path(href)
        if local is None:
            continue
        checked += 1
        target = unquote(href)
        issue = find_issue(repo, path.parent, local, require_tracked)
        if issue:
            problems.append({"line": number, "reason": issue, "target": target})
    return {
        "file": str(path.relative_to(repo)),
        "ok": not problems,
        "links_checked": checked,
        "issues": problems,
        "not_checked": NOT_CHECKED,
    }


def main():
    parser = argparse.ArgumentParser(description="README静态链接检查")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--file", default="README.md")
    parser.add_argument("--require-tracked", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = check(args.repo, args.file, args.require_tracked)
    except (OSError, UnicodeError, ValueError) as error:
        report = {"ok": False, "error": str(error)}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(("PASS" if report["ok"] else "FAIL") + " " + str(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
