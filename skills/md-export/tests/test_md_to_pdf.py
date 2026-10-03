"""Tests for md_to_pdf.py. Run: uv run --with pymupdf python -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPTS / "md_to_pdf.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
import md_to_pdf  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=240,
    )


def installed_chrome() -> str | None:
    try:
        return md_to_pdf.find_chrome()
    except md_to_pdf.ConversionError:
        return None


@unittest.skipUnless(shutil.which("pandoc"), "pandoc not installed")
@unittest.skipIf(sys.platform == "win32", "fake chrome is a shell script")
class SilentChromeTest(unittest.TestCase):
    def test_chrome_exit_0_without_pdf_fails_and_keeps_old_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_s:
            tmp = Path(tmp_s)
            fake = tmp / "fake-chrome"
            fake.write_text("#!/bin/sh\nexit 0\n")
            fake.chmod(0o755)
            md = tmp / "doc.md"
            md.write_text("# Hello\n")
            old = tmp / "doc.pdf"
            old.write_bytes(b"%PDF-old-content")

            proc = run_script(str(md), "--chrome", str(fake), "--timeout", "30")

            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertEqual(old.read_bytes(), b"%PDF-old-content")
            self.assertEqual(sorted(p.name for p in tmp.iterdir()), ["doc.md", "doc.pdf", "fake-chrome"])


@unittest.skipUnless(shutil.which("pandoc") and installed_chrome(), "pandoc or Chrome not installed")
class RealConversionTest(unittest.TestCase):
    def test_landscape_a4_conversion(self):
        with tempfile.TemporaryDirectory() as tmp_s:
            tmp = Path(tmp_s)
            (tmp / "img").mkdir()
            pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 80), False)
            pix.clear_with(90)
            pix.save(tmp / "img" / "fig.png")
            (tmp / "report.md").write_text(
                """---
title: 唯一标题 Quarterly Report
---

# 唯一标题 Quarterly Report

中文段落与 English 混排。
1）第一条
2）第二条

![示意图](img/fig.png)

![不存在](img/missing.png)

行内公式 $\\frac{a}{b}$ 结束。

| 字段 | 说明 |
|---|---|
| alpha | 表格单元格文字 |

```tex
\\frac{a}{b}
```
""",
                encoding="utf-8",
            )

            proc = run_script(str(tmp / "report.md"), "--orientation", "landscape", "--timeout", "120")

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(Path(result["output"]), (tmp / "report.pdf").resolve())
            self.assertTrue(any("missing.png" in w for w in result["warnings"]), result["warnings"])
            self.assertEqual(sorted(p.name for p in tmp.iterdir()), ["img", "report.md", "report.pdf"])

            with pymupdf.open(tmp / "report.pdf") as doc:
                self.assertAlmostEqual(doc[0].rect.width, 841.92, delta=2)
                self.assertAlmostEqual(doc[0].rect.height, 594.96, delta=2)
                text = "\n".join(page.get_text() for page in doc)
                self.assertGreaterEqual(len(doc[0].get_images()), 1)
            self.assertEqual(text.count("唯一标题"), 1)
            self.assertEqual(text.count("\\frac{a}{b}"), 1)  # only the fenced code block
            self.assertNotIn("$", text)  # inline math was typeset, not left as TeX
            self.assertIn("表格单元格文字", text)
            self.assertIn("1）第一条", text)


if __name__ == "__main__":
    unittest.main()
