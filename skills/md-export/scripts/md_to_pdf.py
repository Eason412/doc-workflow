#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pymupdf>=1.24",
# ]
# ///
"""Convert Markdown to PDF: Pandoc -> self-contained HTML -> Chrome headless print.

Everything intermediate lives in a TemporaryDirectory; the final PDF is replaced
atomically only after it has been opened and inspected.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pymupdf

ASSET_CSS = Path(__file__).resolve().parent.parent / "assets" / "print.css"

# CSS paper name -> (width_mm, height_mm), portrait.
PAPER_MM = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "B4": (250, 353),
    "B5": (176, 250),
    "LETTER": (215.9, 279.4),
    "LEGAL": (215.9, 355.6),
}
SIZE_TOLERANCE_PT = 2.0

NOT_CHECKED = "图片是否正确显示、公式渲染、宽表/长代码溢出需要渲染页面目视检查"


class ConversionError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def find_chrome(explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ConversionError(f"--chrome path not found: {path}", 2)
        return str(path.resolve())

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            candidates += [
                str(Path(base) / "Google/Chrome/Application/chrome.exe"),
                str(Path(base) / "Microsoft/Edge/Application/msedge.exe"),
            ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    for name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
        "microsoft-edge",
    ):
        found = shutil.which(name)
        if found:
            return found
    raise ConversionError("Chrome/Chromium not found; pass --chrome PATH", 2)


def kill_tree(proc: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)


def run(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    """Run a command; on timeout kill its whole process group, then raise."""
    try:
        proc = subprocess.Popen(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except OSError as exc:
        raise ConversionError(f"Cannot run {cmd[0]}: {exc}", 2) from exc
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        proc.communicate()
        raise ConversionError(f"{Path(cmd[0]).name} timed out after {timeout:g}s") from None
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def pdf_is_complete(pdf: Path) -> bool:
    try:
        with pdf.open("rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 1024))
            return b"%%EOF" in f.read()
    except OSError:
        return False


def print_with_chrome(cmd: list[str], pdf: Path, timeout: float) -> None:
    """Run Chrome until it has written a complete PDF.

    Headless Chrome with a fresh --user-data-dir can keep running after it has
    printed (seen on Chrome 154/macOS), so exit alone cannot be the completion
    signal: once the PDF is complete and its size has stopped changing, the
    process tree is killed. A non-zero exit before that is a failure.
    """
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryFile() as log:
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=os.name == "posix",
            )
        except OSError as exc:
            raise ConversionError(f"Cannot run {cmd[0]}: {exc}", 2) from exc
        last_size, stable_since = -1, time.monotonic()
        try:
            while proc.poll() is None:
                now = time.monotonic()
                if now > deadline:
                    raise ConversionError(f"Chrome timed out after {timeout:g}s")
                size = pdf.stat().st_size if pdf.exists() else 0
                if size != last_size:
                    last_size, stable_since = size, now
                elif size and now - stable_since >= 0.5 and pdf_is_complete(pdf):
                    return
                time.sleep(0.1)
            if proc.returncode != 0:
                log.seek(0)
                tail = log.read().decode("utf-8", "replace").strip()[-1500:]
                raise ConversionError(f"Chrome exited with {proc.returncode}:\n{tail}")
        finally:
            if proc.poll() is None:
                kill_tree(proc)
                proc.wait()


def ast_text(node) -> str:
    """Plain text of a Pandoc JSON AST fragment."""
    if isinstance(node, list):
        return "".join(ast_text(item) for item in node)
    if not isinstance(node, dict):
        return ""
    kind, content = node.get("t"), node.get("c")
    if kind == "Str":
        return content
    if kind in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if kind in ("Code", "Math"):
        return content[1]
    return ast_text(content)


def body_h1_texts(node) -> list[str]:
    """Texts of all level-1 headings in a Pandoc JSON AST fragment."""
    found: list[str] = []
    if isinstance(node, list):
        for item in node:
            found += body_h1_texts(item)
    elif isinstance(node, dict):
        if node.get("t") == "Header" and node["c"][0] == 1:
            found.append(ast_text(node["c"][2]).strip())
        else:
            found += body_h1_texts(node.get("c"))
    return found


def parse_pandoc_warnings(stderr: str) -> list[str]:
    warnings: list[str] = []
    for line in stderr.splitlines():
        if line.startswith("[WARNING]"):
            warnings.append(line[len("[WARNING]"):].strip())
        elif line.strip() and warnings:
            warnings[-1] += " " + line.strip()
    return warnings


def page_css(paper: str, orientation: str, hide_pandoc_title: bool) -> str:
    css = f"\n@page {{ size: {paper} {orientation}; }}\n"
    if hide_pandoc_title:
        css += "header#title-block-header { display: none; }\n"
    return css


def expected_size_pt(paper: str, orientation: str) -> tuple[float, float]:
    width, height = (v * 72 / 25.4 for v in PAPER_MM[paper])
    return (height, width) if orientation == "landscape" else (width, height)


def chrome_args(chrome: str, user_data_dir: Path, pdf: Path, html: Path) -> list[str]:
    args = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-pdf-header-footer",
        f"--user-data-dir={user_data_dir}",
        f"--print-to-pdf={pdf}",
    ]
    if sys.platform.startswith("linux") and hasattr(os, "geteuid") and os.geteuid() == 0:
        args.append("--no-sandbox")
    return args + [html.as_uri()]


def convert(args: argparse.Namespace) -> dict:
    md = args.input.expanduser().resolve()
    if not md.is_file():
        raise ConversionError(f"Markdown file not found: {md}", 2)
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise ConversionError("pandoc not found on PATH", 2)
    chrome = find_chrome(args.chrome)

    output = (args.output.expanduser() if args.output else md.with_suffix(".pdf")).resolve()
    html_copy = args.html.expanduser().resolve() if args.html else None
    if output == md or html_copy in (md, output):
        raise ConversionError("--output/--html must differ from the input and from each other", 2)

    fmt = "markdown+hard_line_breaks" if args.hard_line_breaks else "markdown"
    base = [pandoc, str(md), "-f", fmt]

    with tempfile.TemporaryDirectory(prefix="md-export-", ignore_cleanup_errors=True) as tmp_s:
        tmp = Path(tmp_s)

        # Parse once to learn the document title and whether the body has its own H1.
        proc = run(base + ["-t", "json"], args.timeout)
        if proc.returncode != 0:
            raise ConversionError(f"pandoc failed:\n{proc.stderr.strip()}")
        ast = json.loads(proc.stdout)
        yaml_title = ast_text(ast["meta"].get("title", {})).strip()
        h1_texts = body_h1_texts(ast["blocks"])
        page_title = yaml_title or (h1_texts[0] if h1_texts else "") or md.stem

        css = tmp / "print.css"
        css.write_text(
            ASSET_CSS.read_text(encoding="utf-8")
            + page_css(args.paper_size, args.orientation, hide_pandoc_title=bool(h1_texts)),
            encoding="utf-8",
        )
        html = tmp / "document.html"
        pandoc_cmd = base + [
            "-t", "html5",
            "--standalone",
            "--embed-resources",
            f"--resource-path={md.parent}",
            "--metadata", f"pagetitle={page_title}",
            "-V", "document-css=false",
            f"--css={css}",
            "-o", str(html),
        ]
        if args.math == "mathml":
            pandoc_cmd.append("--mathml")
        proc = run(pandoc_cmd, args.timeout)
        if proc.returncode != 0:
            raise ConversionError(f"pandoc failed:\n{proc.stderr.strip()}")
        warnings = parse_pandoc_warnings(proc.stderr)
        if html_copy:
            html_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(html, html_copy)

        printed = tmp / "printed.pdf"
        print_with_chrome(chrome_args(chrome, tmp / "chrome-profile", printed, html), printed, args.timeout)
        if not printed.is_file() or printed.stat().st_size == 0:
            raise ConversionError("Chrome exited 0 but wrote no PDF; existing output left untouched")

        try:
            with pymupdf.open(printed) as doc:
                pages = doc.page_count
                rect = doc[0].rect if pages else None
        except Exception as exc:
            raise ConversionError(f"Generated PDF cannot be opened: {exc}") from exc
        if not pages:
            raise ConversionError("Generated PDF has zero pages")

        size = (round(rect.width, 2), round(rect.height, 2))
        want = expected_size_pt(args.paper_size, args.orientation)
        if any(abs(got - exp) > SIZE_TOLERANCE_PT for got, exp in zip(size, want)):
            raise ConversionError(
                f"Page size {size[0]} x {size[1]} pt differs from requested "
                f"{args.paper_size} {args.orientation} ({want[0]:.2f} x {want[1]:.2f} pt); "
                "existing output left untouched"
            )

        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        try:
            shutil.copyfile(printed, staging)
            os.replace(staging, output)
        finally:
            staging.unlink(missing_ok=True)

    result = {
        "output": str(output),
        "pages": pages,
        "page_size_pt": list(size),
        "warnings": warnings,
        "not_checked": NOT_CHECKED,
    }
    if html_copy:
        result["html"] = str(html_copy)
    return result


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Markdown to PDF via Pandoc and Chrome.")
    parser.add_argument("input", type=Path, help="Source Markdown file")
    parser.add_argument("--output", type=Path, help="Output PDF (default: next to input, same stem)")
    parser.add_argument(
        "--paper-size",
        type=str.upper,
        choices=sorted(PAPER_MM),
        default="A4",
        help="Paper size, case-insensitive (default: A4)",
    )
    parser.add_argument("--orientation", choices=["portrait", "landscape"], default="portrait")
    parser.add_argument(
        "--math",
        choices=["mathml", "none"],
        default="mathml",
        help="mathml: render $...$ as MathML (default); none: leave TeX as literal text",
    )
    parser.add_argument(
        "--no-hard-line-breaks",
        dest="hard_line_breaks",
        action="store_false",
        help="Treat single newlines as spaces (default: every newline is a line break)",
    )
    parser.add_argument("--html", type=Path, help="Also keep the intermediate self-contained HTML here")
    parser.add_argument("--chrome", help="Chrome/Chromium/Edge executable (default: auto-detect)")
    parser.add_argument("--timeout", type=float, default=120, help="Seconds allowed per Pandoc/Chrome run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = convert(args)
    except ConversionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exc.code
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
