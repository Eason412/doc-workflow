#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown-it-py>=3"]
# ///
"""只读、离线检查本地链接、锚点、Git 跟踪状态和双语 README 结构。

uv run check_readme.py --repo <仓库> [--file README.md | --pair README.md README.en.md]
                      [--require-tracked] [--json]
实现为本项目原创，不复用第三方 slugger 或翻译脚本代码。
"""
import argparse
from bisect import bisect_right
import importlib.util
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True

from markdown_it import MarkdownIt
from markdown_it.rules_inline.backticks import backtick
from markdown_it.rules_inline.image import image
from markdown_it.rules_inline.link import link

NOT_CHECKED = ["外部链接可用性", "命令运行结果", "业务正确性", "中文表达质量"]
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}
# 冻结 Unicode 13 字类，避免 Python 升级改变 GitHub slug 的兼容口径。
SLUG_BOUNDARIES = json.loads(Path(__file__).with_name("slug_chars.json").read_text(encoding="utf-8"))["boundaries"]


class References(dict):
    """记录被实际使用的引用定义，避免在定义处重复报告。"""

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
    def __init__(self):
        super().__init__()
        self.found = []  # (行偏移, 目标, link/image)
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        wanted = {"a": "href", "img": "src"}.get(tag)
        for name, value in attrs:
            if value is not None and (name == "id" or (tag == "a" and name == "name")):
                self.anchors.add(value)
            if name == wanted and value:
                self.found.append((self.getpos()[0] - 1, value, "image" if tag == "img" else "link"))


def parse_html(content):
    parser = HtmlTargets()
    parser.feed(content)
    parser.close()
    return parser


def located_rule(rule, kind):
    """保留解析消耗的源码行号，包括链接目标/title 和代码 span 的换行。"""
    def parse(state, silent):
        start, count = state.pos, len(state.tokens)
        result = rule(state, silent)
        if result and not silent:
            first_line = state.src[:start].count("\n")
            last_line = state.src[:state.pos].count("\n")
            for token in state.tokens[count:]:
                if token.type == kind:
                    token.meta["source_line"] = first_line
                    if kind != "link_open":
                        token.meta["source_end_line"] = last_line
                elif kind == "link_open" and token.type == "link_close":
                    token.meta["source_line"] = last_line
        return result
    return parse


def make_parser():
    parser = MarkdownIt("commonmark").enable(["table", "strikethrough"])
    parser.validateLink = lambda url: True
    parser.inline.ruler.at("backticks", located_rule(backtick, "code_inline"))
    parser.inline.ruler.at("link", located_rule(link, "link_open"))
    parser.inline.ruler.at("image", located_rule(image, "image"))
    return parser


def plain_text(children):
    """标题的渲染文字：格式 token 和 HTML 标记不进入 slug。"""
    result = []
    for token in children:
        if token.type in ("text", "code_inline"):
            result.append(token.content)
        elif token.type in ("softbreak", "hardbreak"):
            result.append(" ")
    return "".join(result)


def heading_slug(text, used):
    base = "".join(c for c in text.lower() if bisect_right(SLUG_BOUNDARIES, ord(c)) % 2).replace(" ", "-")
    slug = base
    suffix = 0
    while slug in used:
        suffix += 1
        slug = f"{base}-{suffix}"
    used.add(slug)
    return slug


class Document:
    """一次解析得到所有检查需要的 token、位置与结构。"""

    def __init__(self, text):
        references = References()
        self.tokens = make_parser().parse(text, {"references": references})
        self.links = []  # (行号, 目标, link/image)
        self.anchors = set()
        self.headings = []
        self.tables = []
        self.fences = []
        self.codes = []
        self.quoted_names = {}  # 普通引号中的示例名称及位置
        generated = set()
        table = None
        for index, token in enumerate(self.tokens):
            line = token.map[0] + 1 if token.map else 1
            if token.type == "heading_open":
                content = plain_text(self.tokens[index + 1].children or [])
                self.headings.append((line, int(token.tag[1:]), content))
                self.anchors.add(heading_slug(content, generated))
            elif token.type == "fence":
                self.fences.append((line, token.info.strip(), token.content))
            elif token.type == "table_open":
                table = [line, []]
                self.tables.append(table)
            elif token.type == "tr_open" and table is not None:
                table[1].append(0)
            elif token.type in ("th_open", "td_open") and table is not None:
                table[1][-1] += 1
            elif token.type == "table_close":
                table = None
            elif token.type == "inline":
                self.read_inline(token.children or [], line)
            elif token.type == "html_block":
                self.read_html(token.content, line)
        for label, reference in references.items():
            if label not in references.used and reference.get("href"):
                line = reference["map"][0] + 1 if reference.get("map") else 1
                self.links.append((line, reference["href"], "definition"))
        self.links.sort(key=lambda item: item[0])

    def read_html(self, content, line):
        html = parse_html(content)
        self.anchors.update(html.anchors)
        self.links.extend((line + offset, href, kind) for offset, href, kind in html.found)

    def read_inline(self, children, first_line):
        line = first_line
        for token in children:
            if "source_line" in token.meta:
                line = first_line + token.meta["source_line"]
            if token.type == "link_open":
                self.links.append((line, token.attrGet("href"), "link"))
            elif token.type == "image":
                self.links.append((line, token.attrGet("src"), "image"))
                # 图片 alt 是文字，不是实际链接或技术代码。
            elif token.type == "html_inline":
                self.read_html(token.content, line)
            elif token.type == "code_inline":
                self.codes.append((line, token.content))
            elif token.type == "text":
                for match in re.finditer(r"「([^」]+)」|“([^”]+)”|‘([^’]+)’", token.content):
                    name = next(group for group in match.groups() if group is not None)
                    self.quoted_names.setdefault(name, line + token.content[:match.start()].count("\n"))
            if "source_end_line" in token.meta:
                line = first_line + token.meta["source_end_line"]
            elif token.type in ("softbreak", "hardbreak"):
                line += 1
            else:
                line += token.content.count("\n")


def links(text):
    return [(line, href) for line, href, _ in Document(text).links]


def local_path(href):
    parts = urlsplit(href)
    if parts.scheme not in ("", "file") or (not parts.scheme and parts.netloc):
        return None
    if parts.netloc not in ("", "localhost"):
        return ""
    return unquote(parts.path) if parts.path else None


def is_local(href):
    parts = urlsplit(href)
    return parts.scheme in ("", "file") and not (not parts.scheme and parts.netloc)


def is_tracked(repo, relative):
    result = subprocess.run(
        ["git", "--literal-pathspecs", "ls-files", "--", relative],
        cwd=repo, capture_output=True, text=True,
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


def load_document(repo, filename, cache):
    path = (repo / filename).resolve()
    if not path.is_relative_to(repo) or not path.is_file():
        raise ValueError("README必须为目标仓内的现有文件")
    if path not in cache:
        cache[path] = Document(path.read_text(encoding="utf-8"))
    return path, cache[path]


def check(repo, filename="README.md", require_tracked=False, *, cache=None):
    repo = Path(repo).resolve()
    cache = {} if cache is None else cache
    path, document = load_document(repo, filename, cache)
    problems = []
    checked = 0
    for number, href, _ in document.links:
        if not is_local(href):
            continue
        parts = urlsplit(href)
        local = local_path(href)
        if local is None and not parts.fragment:
            continue
        checked += 1
        issue = find_issue(repo, path.parent, local if local is not None else path.name, require_tracked)
        target = (path.parent / local).resolve() if local is not None else path
        if not issue and parts.fragment and target.suffix.lower() in MARKDOWN_SUFFIXES and target.is_file():
            _, destination = load_document(repo, target, cache)
            if unquote(parts.fragment) not in destination.anchors:
                issue = "锚点不存在"
        if issue:
            problems.append({"line": number, "reason": issue, "target": unquote(href)})
    return {"file": str(path.relative_to(repo)), "ok": not problems,
            "links_checked": checked, "issues": problems, "not_checked": NOT_CHECKED}


def load_bilingual():
    # 固定从同目录加载，不修改 sys.path；支持 CLI 和 importlib 按文件路径导入。
    path = Path(__file__).with_name("bilingual.py")
    spec = importlib.util.spec_from_file_location("readme_bilingual", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bilingual = load_bilingual()
normalize_code = bilingual.normalize_code


def check_pair(repo, filenames, require_tracked=False):
    if len(filenames) != 2:
        raise ValueError("--pair需要两份不同的文档")
    repo = Path(repo).resolve()
    cache = {}
    loaded = [load_document(repo, name, cache) for name in filenames]
    paths = [path for path, _ in loaded]
    if paths[0] == paths[1]:
        raise ValueError("--pair需要两份不同的文档")
    docs = [doc for _, doc in loaded]
    reports = [check(repo, name, require_tracked, cache=cache) for name in filenames]
    issues = bilingual.Alignment(repo, paths, docs, local_path, is_local).run(reports)
    return {"files": [str(path.relative_to(repo)) for path in paths],
            "ok": not any(issue["severity"] == "error" for issue in issues),
            "links_checked": sum(report["links_checked"] for report in reports),
            "issues": issues, "not_checked": NOT_CHECKED}


def main():
    parser = argparse.ArgumentParser(description="README本地链接、锚点与双语结构对齐检查（只读、离线）")
    parser.add_argument("--repo", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--file", default="README.md")
    mode.add_argument("--pair", nargs=2, metavar=("README", "README_EN"))
    parser.add_argument("--require-tracked", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = (check_pair(args.repo, args.pair, args.require_tracked) if args.pair
                  else check(args.repo, args.file, args.require_tracked))
    except (OSError, UnicodeError, ValueError) as error:
        report = {"ok": False, "error": str(error)}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(("PASS" if report["ok"] else "FAIL") + " " + str(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
