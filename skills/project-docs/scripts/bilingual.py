"""双语 README 结构比较；输入由入口脚本解析，不读取或写入文件。"""
from collections import Counter
from itertools import zip_longest
import json
import re
from urllib.parse import unquote, urlsplit

TRANSLATABLE_FENCES = {"", "text", "json", "yaml"}


def normalize_code(content):
    content = re.sub(r"\{\{(task|phase):[^{}]+\}\}", r"{{\1:*}}", content)
    content = re.sub(r"<[^<>\n]+>", "<*>", content)
    # 独立方括号才可能是占位符；下标、带引号/逗号的数组和字面量保留。
    return re.sub(r"(?<![\w)\]}])\[((?:[^\W\d]|_)[\w-]*)\]", "[*]", content)


def has_chinese(content):
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0003134f]", content))


def fence_language(fence):
    return fence[1].split()[0].lower() if fence[1] else ""


def unmatched_codes(docs):
    """保留 (行号, 原文, 归一后内容)，分类只用最后一项。"""
    codes = [[(line, code, normalize_code(code)) for line, code in doc.codes] for doc in docs]
    counts = [Counter(entry[2] for entry in entries) for entries in codes]
    unmatched = []
    for side, entries in enumerate(codes):
        matched = counts[side] & counts[1 - side]
        remaining = []
        for entry in entries:
            if matched[entry[2]]:
                matched[entry[2]] -= 1
            else:
                remaining.append(entry)
        unmatched.append(remaining)
    return unmatched


def collect_example_names(left, right, docs, names):
    """只认成对 JSON 同一位置的 name/title/label，且正文中存在引号译名。"""
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() & right.keys()):
            values = (left[key], right[key])
            if key in {"name", "title", "label"} and all(isinstance(v, str) for v in values):
                for side in (0, 1):
                    source, translation = map(normalize_code, (values[side], values[1 - side]))
                    original = values[1 - side]
                    if source.isascii() and has_chinese(translation) and original in docs[1 - side].quoted_names:
                        names[side][source] = (docs[1 - side].quoted_names[original], original)
            collect_example_names(*values, docs, names)
    elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        for values in zip(left, right):
            collect_example_names(*values, docs, names)


def translated_example_names(docs):
    names = [{}, {}]
    fences = [[f for f in doc.fences if fence_language(f) == "json"] for doc in docs]
    for left, right in zip(*fences):
        try:
            collect_example_names(json.loads(left[2]), json.loads(right[2]), docs, names)
        except (ValueError, TypeError):
            pass  # 无法确证名称映射时，保持一般行内代码比较规则。
    return names


def code_severity(code, side, names, chinese_counts, ascii_counts):
    translated = code.isascii() and chinese_counts[1 - side] >= ascii_counts[side]
    if code in names[side] or has_chinese(code) or translated:
        return "warning"
    return "error"


class Alignment:
    def __init__(self, repo, paths, docs, local_path, is_local):
        self.repo = repo
        self.paths = paths
        self.docs = docs
        self.local_path = local_path
        self.is_local = is_local
        self.issues = []

    def locations(self, side, entries):
        return [{"file": str(self.paths[side].relative_to(self.repo)), "line": line, "content": content}
                for line, content in entries]

    def add(self, category, left, right, severity="error", reason="结构不一致"):
        self.issues.append({"category": category, "severity": severity, "reason": reason,
                            "left": self.locations(0, left), "right": self.locations(1, right)})

    def compare_sequence(self, category, sequences, value, severity="error", display=None):
        for left, right in zip_longest(*sequences):
            if left is not None and right is not None and value(left) == value(right):
                continue
            describe = display or value
            self.add(category, [(left[0], describe(left))] if left else [],
                     [(right[0], describe(right))] if right else [], severity)

    def headings_and_tables(self):
        self.compare_sequence("headings", [d.headings for d in self.docs], lambda x: x[1],
                              display=lambda x: {"level": x[1], "title": x[2]})
        self.compare_sequence("tables", [d.tables for d in self.docs],
                              lambda x: {"rows": len(x[1]), "columns": x[1]})

    def fences(self):
        for translated in (False, True):
            sequences = [[f for f in d.fences if (fence_language(f) in TRANSLATABLE_FENCES) == translated]
                         for d in self.docs]
            self.compare_sequence("fenced_code", sequences,
                                  lambda x: {"language": x[1], "code": x[2]},
                                  severity="warning" if translated else "error")

    def inline_codes(self):
        unmatched = unmatched_codes(self.docs)
        chinese = [sum(has_chinese(code) for _, _, code in entries) for entries in unmatched]
        ascii_counts = [sum(code.isascii() for _, _, code in entries) for entries in unmatched]
        names = translated_example_names(self.docs)
        for severity in ("error", "warning"):
            groups = []
            for side, entries in enumerate(unmatched):
                groups.append([(line, original) for line, original, code in entries
                               if code_severity(code, side, names, chinese, ascii_counts) == severity])
            if severity == "warning":
                for side, entries in enumerate(unmatched):
                    for _, _, code in entries:
                        if code in names[side] and names[side][code] not in groups[1 - side]:
                            groups[1 - side].append(names[side][code])
            if any(groups):
                self.add("inline_code", *groups, severity,
                         reason="行内代码多重集合不一致（已归一占位符）")

    def canonical_target(self, side, href):
        local = self.local_path(href)
        target = (self.paths[side].parent / local).resolve() if local is not None else self.paths[side]
        if target in self.paths:
            target = self.paths[0]
        elif target.name.endswith(".en.md") and target.with_name(target.name[:-6] + ".md").is_file():
            target = target.with_name(target.name[:-6] + ".md")
        return str(target.relative_to(self.repo)) if target.is_relative_to(self.repo) else str(target)

    def target_mapping(self, side, kind):
        mapping = {}
        for line, href, actual_kind in self.docs[side].links:
            wanted = actual_kind in ("link", "definition") if kind == "link" else actual_kind == kind
            if not wanted or (kind == "link" and not self.is_local(href)):
                continue
            parts = urlsplit(href)
            if kind == "link" and self.local_path(href) is None and not parts.fragment:
                continue
            key = self.canonical_target(side, href) if self.is_local(href) else href
            if kind == "image" and self.is_local(href):
                key += ("?" + parts.query if parts.query else "")
                key += ("#" + unquote(parts.fragment) if parts.fragment else "")
            mapping.setdefault(key, []).append((line, href))
        return mapping

    def targets(self):
        for category, kind in (("link_targets", "link"), ("images", "image")):
            mappings = [self.target_mapping(side, kind) for side in (0, 1)]
            differences = [set(mappings[i]) - set(mappings[1 - i]) for i in (0, 1)]
            if any(differences):
                groups = [[entry for key in sorted(differences[side]) for entry in mappings[side][key]]
                          for side in (0, 1)]
                self.add(category, *groups)

    def switches(self):
        for side, doc in enumerate(self.docs):
            # 顶部是第一个二级及以下标题之前的引言区。
            boundary = next((line for line, level, _ in doc.headings if level >= 2), float("inf"))
            switch = any(kind == "link" and line < boundary and self.local_path(href) is not None
                         and (self.paths[side].parent / self.local_path(href)).resolve() == self.paths[1 - side]
                         for line, href, kind in doc.links if self.is_local(href))
            if not switch:
                filename = self.paths[1 - side].relative_to(self.repo)
                missing = [(1, f"缺少顶部语言切换链接：{filename}")]
                self.add("language_switch", missing if side == 0 else [], missing if side == 1 else [])

    def run(self, reports):
        for side, report in enumerate(reports):
            for issue in report["issues"]:
                entries = [(issue["line"], issue["target"])]
                self.add("local_links", entries if side == 0 else [], entries if side == 1 else [],
                         reason=issue["reason"])
        self.headings_and_tables()
        self.fences()
        self.inline_codes()
        self.targets()
        self.switches()
        return self.issues
