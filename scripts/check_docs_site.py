"""Check a built MkDocs site for math that MathJax cannot parse.

A LaTeX command such as ``\\frac`` written inside a non-raw Python string (or
pasted through a tool that interprets escapes) silently becomes a control
character: ``"\\f"`` is a form feed, ``"\\b"`` a backspace, ``"\\a"`` a bell and
so on.  MathJax then shows "Math input error" on the published page.  This
script scans every built HTML page for such characters and checks known
equations survive the build verbatim.

Usage: ``python scripts/check_docs_site.py site``
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

# C0 control characters other than tab, newline and carriage return.
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ARITHMATEX_BLOCK = re.compile(
    r'<(?P<tag>div|span) class="arithmatex">(?P<body>.*?)</(?P=tag)>', re.DOTALL
)

# Equations that must reach the reader unchanged (page -> literal TeX).
REQUIRED_TEX = {
    "workflows/recent_literature/index.html": (r"\frac5{12}z^5",),
}


def check_site(site: Path) -> list[str]:
    problems: list[str] = []
    pages = sorted(site.rglob("*.html"))
    if not pages:
        return [f"{site}: no HTML pages found"]

    math_blocks = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        relative = page.relative_to(site).as_posix()
        for match in CONTROL_CHARACTERS.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            problems.append(
                f"{relative}:{line}: control character U+{ord(match.group()):04X}"
            )
        for block in ARITHMATEX_BLOCK.finditer(text):
            math_blocks += 1
            body = html.unescape(block.group("body"))
            if CONTROL_CHARACTERS.search(body):
                problems.append(f"{relative}: control character inside math {body!r}")

    if math_blocks == 0:
        problems.append("no arithmatex math blocks found; is pymdownx.arithmatex on?")

    for relative, literals in REQUIRED_TEX.items():
        page = site / relative
        if not page.is_file():
            problems.append(f"{relative}: page missing from built site")
            continue
        text = html.unescape(page.read_text(encoding="utf-8"))
        for literal in literals:
            if literal not in text:
                problems.append(f"{relative}: expected TeX {literal!r} not found")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    problems = check_site(Path(argv[1]))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"{argv[1]}: math source is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
