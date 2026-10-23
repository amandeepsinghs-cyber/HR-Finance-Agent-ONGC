"""Physical-page index for `pdftotext -layout` text files (SPEC-01 §4.1).

Convention: `source_page` = 1 + number of form-feed (``\\f``) characters that
precede the first visible character of the line.  A form feed at the start of a
line therefore puts that line on the *new* page (pdftotext emits the ``\\f``
immediately before the first line of each page).

Lines are split on ``\\n`` only: ``str.splitlines()`` would also split on
``\\f`` and break the 1-based line numbering used for lineage.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_FOLIO_AR = re.compile(r"Annual Report 20\d\d-\d\d\s+(\d{1,3})\b", re.IGNORECASE)
_FOLIO_TRAIL = re.compile(r"(?:^|\s)(\d{1,3})\s*$")
_FOLIO_LEAD = re.compile(r"^\s*(\d{1,3})(?:\s|$)")


@lru_cache(maxsize=32)
def _load(text_path: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """Return (lines, page_of_each_line) for a text file (cached)."""
    text = Path(text_path).read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    pages: list[int] = []
    ff_before = 0  # form feeds seen in all previous lines
    for line in lines:
        lead = len(line) - len(line.lstrip("\f"))
        pages.append(1 + ff_before + lead)
        ff_before += line.count("\f")
    return tuple(lines), tuple(pages)


def read_lines(text_path: str | Path) -> list[str]:
    """All lines of the file (``\\n`` split, form feeds kept)."""
    return list(_load(str(text_path))[0])


def page_of_line(text_path: str | Path, line_no: int) -> int:
    """1-based physical PDF page of the 1-based ``line_no``."""
    lines, pages = _load(str(text_path))
    if not 1 <= line_no <= len(lines):
        raise IndexError(f"line {line_no} out of range 1..{len(lines)}")
    return pages[line_no - 1]


def page_lines(text_path: str | Path, pdf_page: int) -> list[tuple[int, str]]:
    """(1-based line number, text without form feeds) for every line on a page."""
    lines, pages = _load(str(text_path))
    return [(i + 1, ln.replace("\f", "")) for i, (ln, p) in enumerate(zip(lines, pages)) if p == pdf_page]


def folio(text_path: str | Path, pdf_page: int) -> str | None:
    """Printed page number (folio) of a physical page, or None.

    Taken from the last non-empty line of the page: ``Annual Report 20xx-yy NN``
    or a leading / trailing 1-3 digit token.
    """
    body = [t for _, t in page_lines(text_path, pdf_page) if t.strip()]
    if not body:
        return None
    last = body[-1].rstrip()
    for rx in (_FOLIO_AR, _FOLIO_TRAIL, _FOLIO_LEAD):
        m = rx.search(last)
        if m:
            return m.group(1)
    return None
