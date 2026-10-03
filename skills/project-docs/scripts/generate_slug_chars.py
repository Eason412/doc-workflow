#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9,<3.10"
# dependencies = []
# ///
"""从 CPython 3.9 内置 Unicode 13 数据生成 slug 字符表，结果输出到 stdout。

uv run generate_slug_chars.py > slug_chars.json
原创生成逻辑，不复用 github-slugger 的 ISC 代码。
"""
import json
import unicodedata


def allowed(char):
    category = unicodedata.category(char)
    # Alphabetic 中的带圈/方框拉丁字母；其他 Alphabetic 字符已属于 L/M/Nl。
    alphabetic_symbol = (0x24B6 <= ord(char) <= 0x24E9
                         or 0x1F130 <= ord(char) <= 0x1F149
                         or 0x1F150 <= ord(char) <= 0x1F169
                         or 0x1F170 <= ord(char) <= 0x1F189)
    return (category[0] in "LM" or category in {"Nd", "Nl", "Pc"}
            or alphabetic_symbol or char in " -")


def main():
    if unicodedata.unidata_version != "13.0.0":
        raise SystemExit("需要 Unicode 13.0.0 数据（CPython 3.9）")
    boundaries = []
    previous = False
    for codepoint in range(0x110000):
        current = allowed(chr(codepoint))
        if current != previous:
            boundaries.append(codepoint)
            previous = current
    if previous:
        boundaries.append(0x110000)
    data = {"unicode_version": unicodedata.unidata_version,
            "source": "CPython 3.9 unicodedata; original property selection",
            "properties": ["L", "M", "Nd", "Nl", "Pc", "Alphabetic symbols", "space", "hyphen"],
            "boundaries": boundaries}
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
