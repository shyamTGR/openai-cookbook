#!/usr/bin/env python3
"""Utility for building documentation for the OpenAI Cookbook.

This script normalizes markdown/MDX files, converts notebooks to markdown,
constructs a table of contents, and optionally builds HTML and PDF outputs.

It is designed to be run in CI as part of the documentation build pipeline.
"""

from __future__ import annotations

import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Iterable

import yaml

# Source directories to scan for documentation content
SOURCE_DIRS = [Path("articles"), Path("examples")]
# Directory that will contain normalized markdown used by MkDocs
BUILD_DIR = Path("docs/build")
# Path to generated table of contents
TOC_PATH = Path("docs/toc.yaml")
# Path to consolidated PDF output
PDF_PATH = Path("dist/OpenAI_Cookbook.pdf")


def gather_sources() -> Iterable[Path]:
    """Yield all documentation source files in SOURCE_DIRS."""
    exts = {".md", ".mdx", ".ipynb"}
    for src_dir in SOURCE_DIRS:
        for path in src_dir.rglob("*"):
            if path.suffix.lower() in exts:
                yield path


def ensure_command(cmd: str) -> bool:
    """Return True if *cmd* exists on PATH."""
    return shutil.which(cmd) is not None


def convert_markdown(src: Path, dest: Path) -> None:
    """Normalize a markdown/MDX file using pandoc."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if ensure_command("pandoc"):
        subprocess.run(["pandoc", str(src), "-t", "gfm", "-o", str(dest)], check=True)
    else:
        # Fallback: copy file verbatim
        shutil.copy(src, dest)


def convert_notebook(src: Path, dest: Path) -> None:
    """Convert a Jupyter notebook to markdown using nbconvert."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if ensure_command("jupyter"):
        subprocess.run([
            "jupyter",
            "nbconvert",
            "--to",
            "markdown",
            str(src),
            "--output",
            dest.name,
            "--output-dir",
            str(dest.parent),
        ], check=True)
    else:
        raise RuntimeError("jupyter nbconvert is required to convert notebooks")


def generate_docs() -> None:
    """Convert all source documents into BUILD_DIR."""
    for src in gather_sources():
        root = src.parts[0]
        rel = Path(*src.parts[1:])
        dest = BUILD_DIR / root / rel.with_suffix(".md")
        if src.suffix.lower() in {".md", ".mdx"}:
            convert_markdown(src, dest)
        elif src.suffix.lower() == ".ipynb":
            convert_notebook(src, dest)

    # Copy the repository README to serve as the documentation index.
    readme_src = Path("README.md")
    if readme_src.exists():
        shutil.copy(readme_src, BUILD_DIR / "index.md")


def generate_toc() -> None:
    """Generate a simple table of contents based on files in BUILD_DIR."""
    toc: dict[str, list[dict[str, str]]] = {}
    for md in sorted(BUILD_DIR.rglob("*.md")):
        rel = md.relative_to(BUILD_DIR)
        section = rel.parts[0]
        entry = {"title": md.stem.replace("_", " ").title(), "path": str(rel)}
        toc.setdefault(section, []).append(entry)
    TOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TOC_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(toc, fh, sort_keys=True, allow_unicode=True)


def build_html() -> None:
    """Run `mkdocs build` to produce the static site."""
    if ensure_command("mkdocs"):
        subprocess.run(["mkdocs", "build"], check=True)
    else:
        raise RuntimeError("mkdocs is required to build HTML documentation")


def build_pdf() -> None:
    """Concatenate all markdown files into a single PDF using pandoc."""
    if not ensure_command("pandoc"):
        raise RuntimeError("pandoc is required to build the PDF")
    files = [str(p) for p in sorted(BUILD_DIR.rglob("*.md"))]
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pandoc", *files, "-o", str(PDF_PATH)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-pdf", action="store_true", help="Build a consolidated PDF in addition to HTML"
    )
    args = parser.parse_args()

    generate_docs()
    generate_toc()
    build_html()
    if args.build_pdf:
        build_pdf()


if __name__ == "__main__":
    main()
