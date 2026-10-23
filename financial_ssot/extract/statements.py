"""Deterministic parser for the AR primary statements (P1.3, SPEC-01 §4.3).

Statements: standalone + consolidated Balance Sheet (``balance_sheet``),
Statement of Profit and Loss (``pnl``) and Statement of Cash Flows
(``cash_flow``) of each own-year AR listed in ``page_map.yaml``.  Every printed
number becomes one bronze row (current year, comparative, and the 1-Apr opening
column when present) with physical-page lineage and the raw text line.

Rules (in order, per line of the statement region):

1. Region = from the statement title line (``page_map.yaml`` regex; the page is
   asserted against the verified page in the map) to the first end marker
   (``Accompanying notes``, ``As per our report``, ``FOR AND ON BEHALF``,
   ``Reconciliation of Liabilities``, ``Statement of Changes in Equity`` ...).
2. Column header = the dates printed between the title and the first data
   line (``As at March 31, 2026``, ``Year ended March 31, 2026``,
   ``April 01, 2022^``).  A trailing ``*`` / ``^`` / ``(Restated)`` marks the
   column ``is_restated``.  ``April 1`` columns are ``period_type='opening'``.
3. Values = the trailing run of 2-decimal tokens or nil dashes (``-``);
   accounting negatives ``(894.31)``; Indian grouping ``1,50,046.64``.  Tokens
   are mapped to columns by their right edge (edges learned per page from the
   lines with the most values).  Cash-flow pages carry two sub-columns per year
   (detail | block total); a value in the block-total sub-column on a line that
   also has a detail value is the AR's unlabelled block subtotal and becomes its
   own row ``[subtotal] <heading>`` (it is printed, so it is kept, never computed).
4. The ``Note No.`` reference (``30``, ``33 & 34``, ``6A``, ``48.4``) is the
   label tail separated by >= 2 spaces; roman prefixes (``III``, ``I.``) go to
   ``roman_ref``; the formula text (``(I+II)``) stays in ``raw_label``.
5. A line without values continues the previous data label when it starts in
   lower case or the previous label ends with a connector (``towards``, ``of``,
   ``and`` ...); a heading line immediately followed by a data line whose label
   starts in lower case is merged into it.  Other no-value lines are headings
   and build ``section_path``.
6. Side-tab noise (chapter tabs right of column 100 such as ``Overview``,
   running titles, folios) is dropped.

Self-validation (flags only, values are never altered):

* ``subtotal_ok`` on every total-like row: the printed total equals the sum of
  a contiguous run of the preceding rows (already-verified totals replace their
  components), roman formulas such as ``(VII-VIII)`` are evaluated.
* ``pnl_chain_ok``, ``bs_identity_ok``, ``cash_tie_ok`` per (AR, scope, period).
Failures go to ``financial_ssot/out/statements_parse_issues.csv`` (page +
line) for the O-owned Gemini fallback.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from financial_ssot.common import numbers, pages

EXTRACTOR_VERSION = "statements/1.0.0"
PKG_DIR = Path(__file__).resolve().parents[1]
TEXT_DIR = PKG_DIR.parent / "knowledge" / "public_sources" / "grounding_data" / "text"
PAGE_MAP = Path(__file__).resolve().parent / "page_map.yaml"
STATEMENTS = ("balance_sheet", "pnl", "cash_flow")
SCOPES = ("standalone", "consolidated")
TOL = 0.011  # ₹ mn: one paisa-of-a-million rounding step + float noise


# --------------------------------------------------------------------------- page map
def load_page_map(path: Path = PAGE_MAP) -> dict:
    """Minimal YAML-subset loader (2-space indented mappings, scalars, # comments).

    The package has no PyYAML dependency; the map only uses nested mappings.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #")[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val = line.strip().partition(":")
        key = key.strip().strip("'\"")
        val = val.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            if (val[0] == val[-1]) and val[0] in "'\"":
                val = val[1:-1]
            parent[key] = int(val) if re.fullmatch(r"-?\d+", val) else val
    return root


# --------------------------------------------------------------------------- regexes
_MONTHS = ("january|february|march|april|may|june|july|august|september|october|"
           "november|december")
_DATE = re.compile(
    rf"(?:(?P<m1>{_MONTHS})\s+(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?,?\s*(?P<y1>20\d\d)"
    rf"|(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m2>{_MONTHS}),?\s*(?P<y2>20\d\d))"
    r"(?P<mark>\s?[\*\^]|\s*\(Restated\))?",
    re.I,
)
_FYTOK = re.compile(r"(?<![\d-])(20\d\d)\s?-\s?(\d\d)(?![\d-])(?P<mark>\s?[\*\^])?")
_VAL2 = re.compile(r"^\(?-?\d{1,3}(?:,\d{2,3})*\.\d{2}\)?$|^\(?-?\d+\.\d{2}\)?$")
_VAL3 = re.compile(r"^\(?-?\d{1,3}(?:,\d{2,3})*\.\d{2,3}\)?$|^\(?-?\d+\.\d{2,3}\)?$")  # production (MMT/BCM)
_NOTE_TAIL = re.compile(
    r"\s{2,}(?P<note>\d{1,2}(?:\.\d{1,2})?[A-Z]?(?:\s*(?:&|and|,)\s*\d{1,2}(?:\.\d{1,2})?[A-Z]?)*)\s*$")
_ROMAN = re.compile(r"^(?P<r>X{0,3}(?:IX|IV|V?I{1,3}|V|X))(?:\.\s+|\s{2,}|\s+(?=[A-Z(]))(?=\S)")
_FORMULA = re.compile(r"\(\s*([IVX]+(?:\s*[+\-]\s*[IVX]+)+)\s*\)")
_END = [
    re.compile(r"^\s*(the\s+)?accompanying notes", re.I),
    re.compile(r"^\s*see accompanying notes", re.I),
    re.compile(r"as per our report|in terms of our report", re.I),
    re.compile(r"for and on behalf of", re.I),
    re.compile(r"reconcil\w* of liabilities", re.I),
    re.compile(r"statement of changes in equity", re.I),
    re.compile(r"^\s*(material accounting|significant accounting) policies", re.I),
]
_TAB_WORDS = re.compile(
    r"^(overview|standalone financial statements|consolidated financial statements|"
    r"annexures to the board.s report|board.s report|statutory reports|financial statements|"
    r"corporate overview|independent auditors.? report|management discussion.*|corporate governance.*|uniﬁed\. digital\..*|"
    r"unified\. digital\..*)$", re.I)
_NOISE = [
    re.compile(r"annual report 20\d\d-\d\d", re.I),
    re.compile(r"^\(?\s*`?\s*in million\)?$", re.I),
    re.compile(r"^\(\s*`\s*in\s*mi", re.I),
    re.compile(r"^\d{1,3}$"),
    re.compile(r"^particulars\b", re.I),
    re.compile(r"^note\s*(no\.?)?$", re.I),
    re.compile(r"^no\.$", re.I),
    re.compile(r"^(as at|year ended|for the year ended)$", re.I),
]
_CONNECT_END = re.compile(r"(\b(and|of|in|to|towards|for|on|from|by|the|with|at|or|under|net|"
                          r"relating|arising)|[,/&\-–(])\s*$", re.I)
_TOTAL = re.compile(
    r"^(total\b|sub-?\s?total\b|net cash\b|net increase|net decrease|operating profit before|"
    r"cash generated from operations|cash and cash equivalents (as )?at the end|equity attributable to owners|\[subtotal\])", re.I)
_MARKER = re.compile(r"^(\(?[a-z]{1,4}[\).]|\(\d+\)|\d+\))\s")
_UNIT_CAPTION = re.compile(r"\(\s*`?\s*in\s+million\s*\)", re.I)
_FY_SHORT = lambda year: "FY" + str(year)[2:]  # noqa: E731


def _date_iso(m: re.Match) -> tuple[str, bool]:
    mon = (m.group("m1") or m.group("m2")).lower()
    day = int(m.group("d1") or m.group("d2"))
    year = int(m.group("y1") or m.group("y2"))
    mi = _MONTHS.split("|").index(mon) + 1
    return f"{year:04d}-{mi:02d}-{day:02d}", bool(m.group("mark"))


def period_of(iso: str) -> tuple[str, str]:
    """period_end ISO -> (fiscal_year, period_type).

    ``YYYY-03-31`` -> FY of that March, ``annual``.  ``YYYY-04-01`` -> the FY
    that starts that day (1-Apr-2022 opens FY23), ``opening``.
    """
    y, m, d = (int(x) for x in iso.split("-"))
    if m == 4 and d == 1:
        return _FY_SHORT(y + 1), "opening"
    return _FY_SHORT(y if m <= 3 else y + 1), "annual"


# --------------------------------------------------------------------------- line model
_TOKEN = re.compile(r"\S+")


def _strip_side_tab(raw: str) -> str:
    """Drop chapter-tab words printed right of column 100 on a data line."""
    m = re.search(r"\s{3,}([A-Za-z’'\.\s&ﬁ]+)$", raw)
    if m and m.start(1) >= 100 and _TAB_WORDS.match(m.group(1).strip()):
        return raw[: m.start()].rstrip()
    return raw


def split_line(raw: str, value_rx: re.Pattern = _VAL2) -> dict:
    """Split one layout line into label / note / roman / value tokens (with right edges)."""
    raw = _strip_side_tab(raw.rstrip())
    toks = [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(raw)]
    vals: list[tuple[str, int, int]] = []
    k = len(toks) - 1
    while k >= 0:
        t = toks[k][0]
        if value_rx.match(t) or t in numbers.NIL_TOKENS or re.fullmatch(r"\d{1,3}(?:,\d{2,3})*\.\d{2}\)", t):
            vals.insert(0, toks[k])
            k -= 1
            continue
        break
    # a leading dash child marker ("- current year") is never a value
    if vals and k < 0 and vals[0][0] in numbers.NIL_TOKENS and len(vals) > 1 and False:
        pass
    label_end = toks[k][2] if k >= 0 else 0
    if k < 0 and vals and vals[0][0] in numbers.NIL_TOKENS and vals[0][1] < 12:
        # "-     Exceptional Items -" pattern cannot occur without a label; keep dash as label
        vals = vals[1:]
        label_end = toks[0][2]
    label = raw[:label_end]
    indent = len(label) - len(label.lstrip())
    label = label.strip()
    note = None
    m = _NOTE_TAIL.search(label)
    if m and m.start() > 0:
        note = re.sub(r"\s+", " ", m.group("note"))
        label = label[: m.start()].rstrip()
    if note is None and indent >= 40 and re.fullmatch(r"\d{1,2}(?:\.\d{1,2})?[A-Z]?", label):
        note, label = label, ""  # value line carrying only the Note No. (label wrapped above)
    roman = None
    m = _ROMAN.match(label)
    if m:
        roman = m.group("r")
        label = label[m.end():].strip()
    return {"label": label, "note": note, "roman": roman, "indent": indent,
            "vals": [(t, s, e) for t, s, e in vals]}


def _marker_level(label: str, roman: str | None) -> float:
    if roman:
        return 1
    if re.match(r"^(i{1,3}|iv|v|vi{0,3})\)\s", label):
        return 1  # cash-flow section "i) CASH FLOWS FROM ..."
    if re.match(r"^\(\d+\)", label):
        return 2
    if re.match(r"^\((?:i{1,3}|iv|v|vi{1,3}|ix|x)\)", label):
        return 4
    if re.match(r"^(\([a-z]\)|[a-z]\)|[a-z]\.)\s?", label):
        return 3
    if re.match(r"^\d+\)", label):
        return 5
    if re.match(r"^[-–]\s*", label):
        return 7
    letters = re.sub(r"[^A-Za-z]", "", label)
    if letters and letters.isupper() and len(letters) > 2:
        return 2.5
    return 5.5


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------- region parser
def _is_noise(stripped: str) -> bool:
    return any(rx.search(stripped) for rx in _NOISE) or bool(_TAB_WORDS.match(stripped))


_YEAR = re.compile(r"(?<![\d\-.,])(20\d\d)(?![\d\-])(?P<mark>\s?[\*\^]|\s*\(Restated\))?")


def header_columns(lines: list[str]) -> list[dict]:
    """Date columns of a header block (title excluded).

    Each ``20yy`` token is one column.  Its month/day come from the text left of
    it on the same line or from the line above in the same x-range, so headers
    wrapped as ``Year ended March`` / ``31, 2019`` are read correctly.  ONGC
    statement columns are March 31 (period end) or April 1 (opening).
    """
    found: list[dict] = []
    for i, raw in enumerate(lines):
        for m in _YEAR.finditer(raw):
            left = raw[max(0, m.start() - 18): m.start()]
            above = " ".join(lines[j][max(0, m.start() - 24): m.end() + 14] for j in (i - 1, i - 2) if j >= 0)
            ctx = (left + " " + above).lower()
            year = int(m.group(1))
            if "april" in left.lower() or ("april" in above.lower() and "march" not in left.lower()):
                iso = f"{year}-04-01"
            elif "march" in ctx or "31" in left:
                iso = f"{year}-03-31"
            else:
                continue
            restated = bool(m.group("mark")) or "restated" in raw[m.end(): m.end() + 14].lower()
            hdr = _clean((left.split("  ")[-1] if "  " in left else left) + " " + m.group(0))
            found.append({"period_end": iso, "restated": restated, "right": m.end(1), "header": hdr})
        for m in _FYTOK.finditer(raw):  # "2025-26" style note headers
            y = int(m.group(1)) + 1
            found.append({"period_end": f"{y}-03-31", "restated": bool(m.group("mark")),
                          "right": m.end(2), "header": _clean(m.group(0))})
    return _order_columns(found)


def _find_header(region: list[tuple[int, int, str]], value_rx: re.Pattern | None = None) -> tuple[list[dict], int, int]:
    """Date columns of the header block -> (columns, body start index, first data line index)."""
    for i, (_, _, raw) in enumerate(region):
        if i == 0:
            continue  # title line (its date is the statement date, not a column)
        sl = split_line(raw, value_rx or _VAL2)
        if sl["vals"] and sl["label"] and not _YEAR.search(raw):
            head = [r for _, _, r in region[1:i]]
            last_date = max((j for j, r in enumerate(head) if _YEAR.search(r)), default=-1)
            return header_columns(head), 1 + last_date + 1, i
    return [], len(region), len(region)


def _order_columns(found: list[dict]) -> list[dict]:
    found = sorted(found, key=lambda c: c["right"])
    out: list[dict] = []
    for c in found:  # one entry per printed column (a date may appear once)
        if out and c["period_end"] == out[-1]["period_end"] and abs(c["right"] - out[-1]["right"]) < 6:
            continue
        out.append(c)
    return out


def _learn_edges(lines: list[dict], k: int) -> list[float] | None:
    full = [ln["vals"] for ln in lines if len(ln["vals"]) == k]
    if not full:
        return None
    edges = []
    for j in range(k):
        es = sorted(v[j][2] for v in full)
        edges.append(es[len(es) // 2])
    return edges


def _assign(vals: list[tuple[str, int, int]], edges: list[float]) -> list[int] | None:
    """Monotone nearest-edge assignment of value tokens to column slots."""
    out = []
    for _, _, e in vals:
        best = min(range(len(edges)), key=lambda j: abs(edges[j] - e))
        out.append(best)
    if out != sorted(out) or len(set(out)) != len(out):
        return None
    return out


def parse_region(region: list[tuple[int, int, str]], *, doc: str, report_vintage: str, scope: str,
                 statement: str, extracted_at: str, folio_of=None,
                 value_rx: re.Pattern = _VAL2) -> tuple[list[dict], list[dict]]:
    """Parse the lines of one statement (``(line_no, page, text)``) into bronze rows.

    Returns (rows, issues).
    """
    issues: list[dict] = []
    columns, first_data, first_value_line = _find_header(region, value_rx)
    if not columns:
        issues.append({"report_vintage": report_vintage, "scope": scope, "statement": statement,
                       "page": region[0][1], "line": region[0][0], "check": "header",
                       "detail": "no date columns found"})
        return [], issues
    n = len(columns)
    header_lines = [r for _, _, r in region[1:first_value_line]]
    header_text = " ".join(header_lines)
    sub_names = None  # (first sub-column, second sub-column) when both are facts, not detail|subtotal
    if re.search(r"No\.?\s*in\s*million|No\.\s*of\s*shares|Number\s+of\s+shares", header_text, re.I):
        sub_names = ("[no. of shares, million]", None)
    elif re.search(r"ONGC\s+JVs?\W?\s*Share", header_text, re.I):
        sub_names = ("[ONGC]", "[JV share]")
    if not sub_names:
        _column_groups(columns, header_lines)

    # pass 1: split lines, drop noise, learn sub-column structure per page
    parsed: list[dict] = []
    for line_no, page, raw in region[first_data:]:
        text = raw.replace("\f", "").replace("\xa0", " ").rstrip("\r").rstrip()
        text = _UNIT_CAPTION.sub("", text).rstrip()
        stripped = text.strip()
        if not stripped:
            parsed.append({"blank": True, "line_no": line_no, "page": page})
            continue
        sl = split_line(text, value_rx)
        if not sl["vals"]:
            first_col = len(text) - len(text.lstrip())
            if _is_noise(stripped) or (first_col >= 100) or _DATE.search(stripped) and re.search(
                    r"as at|year ended", stripped, re.I):
                continue
        elif _DATE.search(stripped) and not sl["label"]:
            continue
        sl.update({"blank": False, "line_no": line_no, "page": page, "raw": stripped})
        parsed.append(sl)

    data_lines = [p for p in parsed if not p["blank"] and p["vals"]]
    k_max = max((len(p["vals"]) for p in data_lines), default=n)
    sub = 2 if k_max >= 2 * n else 1  # cash flow: detail | block-total per year
    year_edges: dict[int, list[float]] = {}
    sub_edges: dict[int, list[float]] = {}
    for pg in sorted({p["page"] for p in data_lines}):
        on_pg = [p for p in data_lines if p["page"] == pg]
        e = _learn_edges(on_pg, n)
        if e:
            year_edges[pg] = e
        if sub == 2:
            e2 = _learn_edges(on_pg, 2 * n)
            if e2:
                sub_edges[pg] = e2
    stmt_year_edges = _learn_edges(data_lines, n) or [float(c["right"]) for c in columns]
    stmt_sub_edges = _learn_edges(data_lines, 2 * n) if sub == 2 else None

    # pass 2: items (data rows / headings) with label continuation
    items: list[dict] = []
    stack: list[dict] = []  # heading stack: {level, indent, text}
    prev_data: dict | None = None
    pending_head: dict | None = None
    prev_blank = True
    last_heading = "block"
    for p in parsed:
        if p["blank"]:
            prev_data, pending_head, prev_blank = None, None, True
            continue
        label, vals = p["label"], p["vals"]
        if not vals:
            starts_lower = bool(re.match(r"^[a-z(]", label)) and not re.match(r"^(\(?[a-z]{1,4}[\).]|\(\d)", label)
            if prev_data is not None and not prev_blank and (
                    starts_lower or (_CONNECT_END.search(prev_data["label"]) and _marker_level(label, p["roman"]) >= 5.5)):
                prev_data["label"] = _clean(prev_data["label"] + " " + label)
                prev_data["text_extra"].append((p["line_no"], p["raw"]))
                continue
            if pending_head is not None and not prev_blank and (
                    starts_lower or _CONNECT_END.search(pending_head["text"])):
                pending_head["text"] = _clean(pending_head["text"] + " " + label)
                if p["note"] and not pending_head.get("note"):
                    pending_head["note"] = p["note"]
                continue
            lvl = _marker_level(label, p["roman"])
            while stack and stack[-1]["level"] >= lvl and not (
                    p["indent"] > stack[-1]["indent"] + 1 and stack[-1]["level"] != lvl):
                stack.pop()
            head = {"level": lvl, "indent": p["indent"], "text": label, "roman": p["roman"],
                    "note": p["note"], "line_no": p["line_no"]}
            stack.append(head)
            items.append({"kind": "heading", **head})
            last_heading = label
            pending_head, prev_data, prev_blank = head, None, False
            continue

        # data line
        if pending_head is not None and not prev_blank and (
                not label or (re.match(r"^[a-z]", label) and not _MARKER.match(label))
                or re.match(r"^\(face value", label, re.I)) \
                and stack and stack[-1] is pending_head:
            # heading wrapped onto the value line ("Net cash (used in)/generated" + "by ...")
            stack.pop()
            items = [it for it in items if not (it["kind"] == "heading" and it["line_no"] == pending_head["line_no"])]
            label = _clean(pending_head["text"] + " " + label)
            p["roman"] = p["roman"] or pending_head["roman"]
            p["note"] = p["note"] or pending_head["note"]
            p["text_extra_pre"] = [(pending_head["line_no"], None)]
        lvl = _marker_level(label, p["roman"])
        while stack and stack[-1]["level"] >= lvl and not (
                p["indent"] > stack[-1]["indent"] + 1 and stack[-1]["level"] != lvl):
            stack.pop()
        # column mapping -> {year column: [(sub, token)]}
        by_col: dict[int, list[tuple[int, str]]] = {}
        ye = year_edges.get(p["page"]) or stmt_year_edges
        if sub == 1 and len(vals) > n and vals[0][2] < ye[0] - 8 and re.fullmatch(r"\d{1,2}\.\d{1,2}", vals[0][0]):
            # a 2-dp Note No. in the note column ("58.10"), not a value
            p["note"] = p["note"] or vals[0][0]
            vals = vals[1:]
        nv = len(vals)
        if nv == n:
            for c, (tok, _, _) in enumerate(vals):
                by_col[c] = [(0, tok)]
        elif nv == 2 * n and sub == 2:
            for c in range(n):
                by_col[c] = [(0, vals[2 * c][0]), (1, vals[2 * c + 1][0])]
        else:
            se = sub_edges.get(p["page"]) or stmt_sub_edges
            slots = None
            if nv > n and se:
                slots = _assign(vals, se)
                if slots is not None:
                    for (tok, _, _), s in zip(vals, slots):
                        by_col.setdefault(s // 2, []).append((s % 2, tok))
            elif nv < n:
                if sub == 2 and se and p["page"] in sub_edges:
                    slots = _assign(vals, se)
                    slots = [s // 2 for s in slots] if slots is not None else None
                if slots is None or len(set(slots)) != len(slots):
                    slots = _assign(vals, year_edges.get(p["page"]) or stmt_year_edges)
                if slots is not None:
                    for (tok, _, _), c in zip(vals, slots):
                        by_col[c] = [(0, tok)]
            if slots is None:
                issues.append({"report_vintage": report_vintage, "scope": scope, "statement": statement,
                               "page": p["page"], "line": p["line_no"], "check": "column_split",
                               "detail": f"cannot map {nv} values to {n} columns: {p['raw'][:120]}"})
                prev_data, pending_head, prev_blank = None, None, False
                continue
        main_cells, subtotal_cells = [], []
        for c, cell in sorted(by_col.items()):
            if len(cell) == 2:
                main_cells.append((c, cell[0][1]))
                subtotal_cells.append((c, cell[1][1]))
            else:
                main_cells.append((c, cell[0][1]))
        section = " > ".join(_clean(h["text"]) for h in stack)
        last = items[-1] if items and items[-1]["kind"] == "data" else None
        if (not prev_blank and last is not None and not subtotal_cells and len(last["cells"]) < n
                and not last.get("block_subtotal")
                and (not label or last["unlabelled"])
                and not ({c for c, _ in last["cells"]} & {c for c, _ in main_cells})):
            # pdftotext split one printed row over two lines (one value per line)
            last["cells"] = sorted(last["cells"] + main_cells)
            if label:
                last.update({"label": label, "unlabelled": False, "note": p["note"] or last["note"],
                             "roman": p["roman"] or last["roman"],
                             "is_total": bool(_TOTAL.match(label)) or bool(_FORMULA.search(label))})
            last["merged_lines"] = last.get("merged_lines", []) + [p["line_no"]]
            last["raw"] = last["raw"] + " | " + p["raw"]
            prev_data = last if not last["unlabelled"] else None
            pending_head, prev_blank = None, False
            continue
        if not label:
            item = {"kind": "data", "label": "[unlabelled line]", "unlabelled": True}
        else:
            item = {"kind": "data", "label": label, "unlabelled": False}
        item.update({"note": p["note"], "roman": p["roman"], "line_no": p["line_no"], "page": p["page"],
                     "raw": p["raw"], "cells": main_cells, "section": section, "text_extra": [],
                     "is_total": (not label) or bool(_TOTAL.match(label)) or bool(_FORMULA.search(label))})
        items.append(item)
        prev_data = item if label else None
        pending_head, prev_blank = None, False
        if subtotal_cells and sub_names:
            # both sub-columns are facts (shares | amount, ONGC | JV share): two labelled rows
            first, second = sub_names
            base = item["label"]
            item["label"] = f"{base} {second}" if second else base
            item["cells"] = subtotal_cells
            item["is_total"] = False if second else item["is_total"]
            items.append({**item, "label": f"{base} {first}", "cells": main_cells, "is_total": False,
                          "unit_hint": "mn_shares" if "shares" in first else None})
            item["sub_pair"] = True
        elif subtotal_cells:
            head_txt = _clean(last_heading)
            items.append({"kind": "data", "label": f"[subtotal] {head_txt}", "unlabelled": False,
                          "note": None, "roman": None, "line_no": p["line_no"], "page": p["page"],
                          "raw": p["raw"], "cells": subtotal_cells, "section": section, "text_extra": [],
                          "is_total": True, "block_subtotal": True})
            prev_data = item

    rows = _emit(items, columns, doc=doc, report_vintage=report_vintage, scope=scope, statement=statement,
                 extracted_at=extracted_at, folio_of=folio_of)
    issues.extend(_check_subtotals(rows, report_vintage, scope, statement))
    return rows, issues


def _unit_of(label: str, section: str) -> str | None:
    low = label.lower()
    for tag, unit in (("(mmt)", "MMT"), ("(bcm)", "BCM"), ("(mmscm)", "MMSCM"), ("(mmm3)", "mn_m3"),
                      ("(us$/bbl)", "USD_per_bbl"), ("(us$/mmbtu)", "USD_per_mmbtu")):
        if tag in low:
            return unit
    return None


def _column_groups(columns: list[dict], header_lines: list[str]) -> None:
    """Name column groups printed above the dates (e.g. 'Segment revenue' | 'Segment profit/(loss)')."""
    phrases: list[tuple[int, str]] = []
    for ln in header_lines:
        if _YEAR.search(ln) or _FYTOK.search(ln):
            continue
        for m in re.finditer(r"\S+(?: \S+)*", ln):
            t = m.group(0).strip()
            if m.start() < 40 or re.match(r"^(year ended|as at|march|note|no\.|particulars|\(?`)", t, re.I):
                continue
            phrases.append((m.start(), t))
    if len({t for _, t in phrases}) < 2:
        return
    phrases.sort()
    for c in columns:
        cands = [t for st, t in phrases if st <= c["right"] - 3]
        if cands:
            c["group"] = cands[-1]


def _emit(items, columns, *, doc, report_vintage, scope, statement, extracted_at, folio_of) -> list[dict]:
    rows: list[dict] = []
    seq = 0
    eps_mode = False
    for it in items:
        if it["kind"] == "heading":
            if re.search(r"earnings per (equity )?share", it["text"], re.I):
                eps_mode = True
            continue
        seq += 1
        unit = "INR_per_share" if (eps_mode or re.search(r"\(in\s*`\)|^\(?[ab]?\)?\s*(basic|diluted)\b", it["label"], re.I)) else "INR_mn"
        if re.search(r"earnings per (equity )?share", it["label"], re.I):
            unit = "INR_per_share"
        unit = it.get("unit_hint") or _unit_of(it["label"], it["section"]) or unit
        for c, tok in it["cells"]:
            col = columns[c]
            value, is_nil, _ = numbers.parse_token(tok)
            fy, ptype = period_of(col["period_end"])
            eid = hashlib.sha1(f"{doc}|{it['line_no']}|{scope}|{statement}|{c}|{it['label']}".encode()).hexdigest()[:16]
            rows.append({
                "extract_id": eid,
                "source_system": "ar_text_statement",
                "source_doc": doc,
                "source_page": it["page"],
                "source_page_label": folio_of(it["page"]) if folio_of else None,
                "source_text_line": it["line_no"],
                "source_text": it["raw"],
                "raw_label": _clean(it["label"]),
                "raw_value_text": tok,
                "parsed_value": value,
                "unit": unit,
                "column_header": col["header"],
                "column_group": col.get("group"),
                "column_index": c,
                "scope": scope,
                "statement": statement,
                "statement_guess": statement,
                "source_table": f"{scope}_{statement}",
                "extractor_version": EXTRACTOR_VERSION,
                "extracted_at": extracted_at,
                "extraction_method": "text_parse",
                "report_vintage": report_vintage,
                "fiscal_year": fy,
                "period_type": ptype,
                "period_end": col["period_end"],
                "is_restated": col["restated"],
                "is_nil": is_nil,
                "note_ref": it["note"],
                "roman_ref": it["roman"],
                "section_path": it["section"],
                "line_seq": seq,
                "is_subtotal": bool(it["is_total"]),
                "subtotal_ok": None,
                "subtotal_components": None,
                "notes": ("unlabelled_block_subtotal" if it.get("block_subtotal") else
                          "unlabelled_line" if it.get("unlabelled") else
                          "split_row_merged:" + ",".join(map(str, it["merged_lines"])) if it.get("merged_lines")
                          else None),
            })
    return rows


# --------------------------------------------------------------------------- validation
def _check_subtotals(rows: list[dict], report_vintage: str, scope: str, statement: str) -> list[dict]:
    """Set ``subtotal_ok`` on total-like rows (flags only)."""
    issues = []
    by_col: dict[int, list[dict]] = {}
    for r in rows:
        by_col.setdefault(r["column_index"], []).append(r)
    for col_rows in by_col.values():
        reduced: list[dict] = []  # running list; verified totals replace their components
        roman_val: dict[str, float] = {}
        seen_totals: list[dict] = []
        for r in col_rows:
            if r["unit"] != "INR_mn":
                continue
            lab = r["raw_label"]
            if r["roman_ref"]:
                roman_val[r["roman_ref"]] = r["parsed_value"]
            m_ref = re.search(r"\(([IVX]+)\)\s*$", lab)
            if m_ref and not r["roman_ref"]:
                roman_val[m_ref.group(1)] = r["parsed_value"]
            if not r["is_subtotal"]:
                reduced.append(r)
                continue
            ok, comps = False, None
            fm = _FORMULA.search(lab)
            if fm:
                expr = re.sub(r"\s+", "", fm.group(1))
                terms = re.findall(r"([+\-]?)([IVX]+)", expr)
                if all(t in roman_val for _, t in terms):
                    total = sum((-1 if s == "-" else 1) * roman_val[t] for s, t in terms)
                    ok = abs(total - r["parsed_value"]) <= TOL * len(terms)
                    comps = "formula " + expr
            if not ok:
                acc = 0.0
                for j in range(len(reduced) - 1, -1, -1):
                    v = reduced[j]["parsed_value"]
                    if re.match(r"^(\[subtotal\]\s*)?less\b", reduced[j]["raw_label"], re.I) and v > 0:
                        v = -v  # "Less : Cash Credit/Bank OD" is printed positive and deducted
                    acc += v
                    cnt = len(reduced) - j
                    if abs(acc - r["parsed_value"]) <= TOL + 0.005 * cnt:
                        ok = True
                        comps = "sum lines " + ",".join(str(x["source_text_line"]) for x in reduced[j:])
                        del reduced[j:]
                        break
            repeat = None
            if not ok and r["notes"] == "unlabelled_line":
                # printed check figure that repeats an earlier total (CF: net change under closing cash)
                repeat = next((x for x in reversed(seen_totals)
                               if abs(x["parsed_value"] - r["parsed_value"]) <= TOL), None)
                if repeat is not None:
                    ok, comps = True, f"repeats line {repeat['source_text_line']}"
            r["subtotal_ok"] = ok
            r["subtotal_components"] = comps
            if repeat is None:
                reduced.append(r)
            seen_totals.append(r)
            if not ok:
                issues.append({"report_vintage": report_vintage, "scope": scope, "statement": statement,
                               "page": r["source_page"], "line": r["source_text_line"], "check": "subtotal",
                               "detail": f"{r['fiscal_year']} {r['period_type']} '{lab}' = {r['raw_value_text']} "
                                         "not reproduced by any contiguous run of preceding lines"})
    return issues


def _find(rows, statement, period_end, rx, first=True):
    hits = [r for r in rows if r["statement"] == statement and r["period_end"] == period_end
            and re.search(rx, r["raw_label"], re.I)]
    if not hits:
        return None
    return hits[0] if first else hits[-1]


_CHECK_FIELDS = {"pnl_chain_ok": {"pat"}, "bs_identity_ok": {"total_assets", "total_equity_and_liabilities"},
                 "cash_tie_ok": {"cf_closing_cce", "bs_cce", "cf_overdraft"}}


def cross_checks(rows: list[dict], report_vintage: str, scope: str) -> list[dict]:
    """pnl_chain_ok / bs_identity_ok / cash_tie_ok per period; sets the flags on the rows."""
    results = []
    for pe in sorted({r["period_end"] for r in rows}):
        res = {"report_vintage": report_vintage, "scope": scope, "period_end": pe,
               "fiscal_year": period_of(pe)[0], "period_type": period_of(pe)[1]}
        # P&L chain
        pat = _find(rows, "pnl", pe, r"^profit for the (year|period)\b(?!.*attributable)")
        pbt = _find(rows, "pnl", pe, r"^profit before tax\b", first=False)
        tax = _find(rows, "pnl", pe, r"^total tax expense")
        if pat is not None:
            if pat.get("subtotal_ok") and pat.get("subtotal_components", "").startswith("formula"):
                res["pnl_chain_ok"] = True
            elif pbt is not None and tax is not None:
                res["pnl_chain_ok"] = abs(pbt["parsed_value"] - tax["parsed_value"] - pat["parsed_value"]) <= TOL
            else:
                res["pnl_chain_ok"] = bool(pat.get("subtotal_ok"))
            res["pat"] = pat["parsed_value"]
        # BS identity
        ta = _find(rows, "balance_sheet", pe, r"^total assets$")
        tel = _find(rows, "balance_sheet", pe, r"^total equity and liabilities$")
        if ta is not None and tel is not None:
            res["bs_identity_ok"] = abs(ta["parsed_value"] - tel["parsed_value"]) <= TOL and bool(tel["subtotal_ok"])
            res["total_assets"] = ta["parsed_value"]
            res["total_equity_and_liabilities"] = tel["parsed_value"]
        elif ta is not None:
            res["bs_identity_ok"] = False
        # cash tie
        cf_close = _find(rows, "cash_flow", pe, r"^cash and cash equivalents (as )?at the end")
        bs_cce = _find(rows, "balance_sheet", pe, r"cash and cash equivalents")
        if cf_close is not None and bs_cce is not None:
            res["cf_closing_cce"] = cf_close["parsed_value"]
            res["bs_cce"] = bs_cce["parsed_value"]
            if abs(cf_close["parsed_value"] - bs_cce["parsed_value"]) <= TOL:
                res["cash_tie_ok"], res["cash_tie_method"] = True, "direct"
            else:
                # The AR's CF cash is net of bank overdraft / cash credit; the printed components
                # table ("Less: Cash Credit/Bank OD") reconciles it to BS cash.  Both are printed.
                od = _find(rows, "cash_flow", pe, r"cash credit|bank od|overdraft")
                res["cash_tie_ok"] = od is not None and abs(
                    bs_cce["parsed_value"] - abs(od["parsed_value"]) - cf_close["parsed_value"]) <= TOL
                if od is not None:
                    res["cf_overdraft"] = abs(od["parsed_value"])
                    res["cash_tie_method"] = f"net_of_overdraft (line {od['source_text_line']})"
        results.append(res)
        for r in rows:
            if r["period_end"] == pe:
                for f in ("pnl_chain_ok", "bs_identity_ok", "cash_tie_ok"):
                    r[f] = res.get(f)
    return results


# --------------------------------------------------------------------------- driver
def _title_rx(cfg: dict, scope: str, statement: str) -> re.Pattern:
    return re.compile(cfg["statement_regex"][statement].replace("{scope}", scope.capitalize()))


def locate(text_path: str | Path, title_rx: re.Pattern, expected_page: int | None) -> int:
    """1-based line index of the statement title on the expected page."""
    lines = pages.read_lines(text_path)
    hits = []
    for i, ln in enumerate(lines):
        if title_rx.search(ln.replace("\f", "").strip()):
            hits.append(i + 1)
    if not hits:
        raise LookupError(f"{Path(text_path).name}: title {title_rx.pattern!r} not found")
    if expected_page is None:
        return hits[0]
    for h in hits:
        if pages.page_of_line(text_path, h) == expected_page:
            return h
    found = sorted({pages.page_of_line(text_path, h) for h in hits})
    raise LookupError(f"{Path(text_path).name}: {title_rx.pattern!r} not on page {expected_page} (found {found})")


def region_lines(text_path: str | Path, start_line: int, max_pages: int = 6) -> list[tuple[int, int, str]]:
    lines = pages.read_lines(text_path)
    first_page = pages.page_of_line(text_path, start_line)
    out = []
    for idx in range(start_line - 1, len(lines)):
        pg = pages.page_of_line(text_path, idx + 1)
        if pg >= first_page + max_pages:
            break
        t = lines[idx].replace("\f", "").rstrip("\r")
        if idx >= start_line and any(rx.search(t) for rx in _END):
            break
        out.append((idx + 1, pg, t))
    return out


def parse(text_path: str | Path, report_vintage: str, scope: str, statements: tuple[str, ...] = STATEMENTS,
          page_map: dict | None = None, extracted_at: str | None = None) -> list[dict]:
    """All statement rows of one AR + scope (flags set; see ``parse_with_issues``)."""
    return parse_with_issues(text_path, report_vintage, scope, statements, page_map, extracted_at)[0]


def parse_with_issues(text_path, report_vintage, scope, statements=STATEMENTS, page_map=None,
                      extracted_at=None) -> tuple[list[dict], list[dict], list[dict]]:
    page_map = page_map or load_page_map()
    cfg = page_map["editions"][report_vintage]
    extracted_at = extracted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text_path = str(text_path)
    doc = Path(text_path).name
    rows, issues = [], []
    folio_cache: dict[int, str | None] = {}

    def folio_of(pg: int):
        if pg not in folio_cache:
            folio_cache[pg] = pages.folio(text_path, pg)
        return folio_cache[pg]

    for st in statements:
        exp = cfg.get(scope, {}).get(st)
        if exp is None:
            continue
        start = locate(text_path, _title_rx(page_map, scope, st), exp)
        region = region_lines(text_path, start)
        r, iss = parse_region(region, doc=doc, report_vintage=report_vintage, scope=scope, statement=st,
                              extracted_at=extracted_at, folio_of=folio_of)
        rows.extend(r)
        issues.extend(iss)
    checks = cross_checks(rows, report_vintage, scope)
    for c in checks:
        for f in ("pnl_chain_ok", "bs_identity_ok", "cash_tie_ok"):
            if c.get(f) is False:
                pg = next((r["source_page"] for r in rows if r["period_end"] == c["period_end"] and
                           r["statement"] == {"pnl_chain_ok": "pnl", "bs_identity_ok": "balance_sheet",
                                              "cash_tie_ok": "cash_flow"}[f]), None)
                issues.append({"report_vintage": report_vintage, "scope": scope,
                               "statement": f.replace("_ok", ""), "page": pg, "line": None, "check": f,
                               "detail": f"{c['fiscal_year']} {c['period_type']} {c['period_end']}: "
                                         + ", ".join(f"{k}={v}" for k, v in c.items()
                                                     if isinstance(v, float) and k in _CHECK_FIELDS[f])})
    return rows, issues, checks


def run_all(text_dir: Path = TEXT_DIR, page_map: dict | None = None):
    page_map = page_map or load_page_map()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_rows, all_issues, all_checks = [], [], []
    for vintage, cfg in page_map["editions"].items():
        for scope in SCOPES:
            if scope not in cfg:
                continue
            r, i, c = parse_with_issues(text_dir / cfg["file"], vintage, scope, page_map=page_map, extracted_at=stamp)
            all_rows += r
            all_issues += i
            all_checks += c
    return all_rows, all_issues, all_checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(PKG_DIR / "out" / "statements_raw.parquet"))
    ap.add_argument("--text-dir", default=str(TEXT_DIR))
    args = ap.parse_args(argv)
    rows, issues, checks = run_all(Path(args.text_dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd  # third-party only for the parquet write

    pd.DataFrame(rows).to_parquet(out, index=False)
    iss_path = out.parent / "statements_parse_issues.csv"
    fields = ["report_vintage", "scope", "statement", "page", "line", "check", "detail"]
    with iss_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(issues)
    chk_path = out.parent / "statements_checks.csv"
    keys = sorted({k for c in checks for k in c}, key=lambda k: (k not in ("report_vintage", "scope", "period_end",
                                                                            "fiscal_year", "period_type"), k))
    with chk_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(checks)
    summary: dict[tuple, dict] = {}
    for r in rows:
        key = (r["report_vintage"], r["scope"], r["statement"])
        s = summary.setdefault(key, {"rows": 0, "lines": set(), "tot": 0, "tot_ok": 0})
        s["rows"] += 1
        s["lines"].add((r["source_text_line"], r["raw_label"]))
        if r["is_subtotal"] and r["unit"] == "INR_mn" and r["notes"] != "unlabelled_line":
            s["tot"] += 1
            s["tot_ok"] += bool(r["subtotal_ok"])
    for (v, sc, st), s in sorted(summary.items()):
        print(f"{v:14s} {sc:12s} {st:13s} rows={s['rows']:4d} lines={len(s['lines']):3d} "
              f"subtotals_ok={s['tot_ok']}/{s['tot']}")
    print(f"{len(rows)} rows; {len(issues)} issues -> {iss_path}; checks -> {chk_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
