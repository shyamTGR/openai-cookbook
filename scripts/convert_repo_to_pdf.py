#!/usr/bin/env python3
"""Generate a single PDF containing all notebooks and Markdown files.

The script walks the repository, converts each `.ipynb` notebook to
Markdown (removing notebook boilerplate like shebang lines), collects all
Markdown files, and renders the combined content to HTML using Pygments
for dark-mode code highlighting. The HTML is then converted to a PDF via
`wkhtmltopdf` using `pdfkit`.

Usage:
    python scripts/convert_repo_to_pdf.py
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from nbconvert import MarkdownExporter
import nbformat
from pygments.formatters import HtmlFormatter
import pdfkit

# Patterns to drop from source text
DROP_PATTERNS = [
    re.compile(r"^#!/usr/bin/env python"),
    re.compile(r"^# coding: utf-8"),
]


def clean_text(text: str) -> str:
    """Remove boilerplate lines and stray whitespace."""
    lines = []
    for line in text.splitlines():
        if any(p.match(line.strip()) for p in DROP_PATTERNS):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines)


def notebook_to_markdown(path: Path) -> str:
    nb = nbformat.read(path, as_version=4)
    exporter = MarkdownExporter()
    body, _ = exporter.from_notebook_node(nb)
    return clean_text(body)


def markdown_file_to_markdown(path: Path) -> str:
    return clean_text(path.read_text(encoding="utf-8"))


def build_markdown(repo_root: Path) -> str:
    paths = sorted(repo_root.rglob("*.ipynb")) + sorted(repo_root.rglob("*.md"))
    sections = []
    for path in paths:
        try:
            if path.suffix == ".ipynb":
                content = notebook_to_markdown(path)
            else:
                content = markdown_file_to_markdown(path)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"Skipping {path} due to {exc}")
            continue
        rel = path.relative_to(repo_root)
        sections.append(f"# {rel}\n\n{content}\n")
    return "\n".join(sections)


def render_html(markdown_text: str, css_path: Path) -> str:
    html_body = markdown.markdown(
        markdown_text,
        extensions=["fenced_code", "codehilite"],
        extension_configs={"codehilite": {"guess_lang": False, "pygments_style": "monokai"}},
    )
    formatter = HtmlFormatter(style="monokai")
    style_defs = formatter.get_style_defs('.codehilite')
    css = css_path.read_text(encoding="utf-8")
    return (
        "<html><head><meta charset='utf-8'><style>" +
        style_defs + "\n" + css +
        "</style></head><body>" +
        html_body +
        "</body></html>"
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    css_path = Path(__file__).with_name("pdf_style.css")
    markdown_text = build_markdown(repo_root)
    html = render_html(markdown_text, css_path)
    html_path = repo_root / "openai_cookbook.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = repo_root / "openai_cookbook.pdf"
    pdfkit.from_file(str(html_path), str(pdf_path))
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
