"""Deterministic parser for the AR standalone 10-year summary tables (P1.2).

SPEC-01 §4.1-§4.2, §5.3, §6 V09.  Editions handled:

* AR FY2025-26 "A DECADE OF OPERATIONAL AND FINANCIAL EXCELLENCE - STANDALONE"
  (PDF p.23-24, FY17-FY26)
* AR FY2023-24 "Standalone Performance at a Glance" + "Statement of Income and
  Retained Earnings" (PDF p.23-26, printed p.21-24, FY15-FY24)
* AR FY2021-22 "Standalone Performance at a Glance" + "Statement of Income and
  Retained Earnings" (PDF p.18-21, printed p.16-19, FY13-FY22)

Rules (in order, per line of each table page):

1. FY header = any line with >= 5 ``20yy-yy`` tokens; a trailing ``*`` (also
   ``2019-20 *``) marks that column ``is_restated``.
2. Noise lines are skipped: running titles / folios (``Annual Report 20yy-yy``,
   ``... Performance at a Glance``), the side-margin chapter tabs (lines whose
   first character is right of column 120 and that hold no number), the
   ``(` in million ...`` caption, and the footnotes after ``* Restated``.
3. Block headings (``Physical Performance``, ``FINANCIAL``, ``RATIOS`` ...) set
   ``block``.
4. Data line: values = the last N numeric tokens (N = FY columns); label = the
   text before the first of them; any words right of the last value (side tab)
   are dropped.  A line with fewer than N tokens is aligned by column position
   (nearest header right-edge) and gets ``notes='aligned_by_position'``.
5. A line without numbers right after a data line continues that label, unless
   the next non-empty line is a ``-`` child (then it is a heading, e.g.
   ``Exploration Costs written off`` / ``-Survey Costs`` in AR FY24).
6. Lines starting with ``-`` + capital/``(`` are children; ``parent_label`` is
   the nearest previous non-child label (data line or heading).
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

EXTRACTOR_VERSION = "ten_year/1.0.0"
TEXT_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "public_sources" / "grounding_data" / "text"

# Fixed per-edition configuration (auditable; no guessing at run time).
EDITIONS: dict[str, dict] = {
    "AR_FY2025-26": {
        "file": "ONGC_AR_FY2025-26.txt",
        "start": r"^A DECADE OF OPERATIONAL AND FINANCIAL EXCELLENCE - STANDALONE",
        "max_pages": 2,
    },
    "AR_FY2023-24": {
        "file": "ONGC_AR_FY2023-24.txt",
        "start": r"^Standalone Performance at a Glance",
        "max_pages": 4,
    },
    "AR_FY2021-22": {
        "file": "ONGC_AR_FY2021-22.txt",
        "start": r"^\s*Standalone Performance at a Glance\s*$",
        "max_pages": 4,
    },
}

BLOCKS = {
    "physical performance": "physical",
    "physical": "physical",
    "financial value creation": "financial_value",
    "financial": "financial_value",
    "financial performance": "financial_value",
    "revenues": "financial_value",
    "expenses": "financial_value",
    "statement of income and retained earnings": "financial_value",
    "financial strength": "financial_strength",
    "other information": "other_information",
    "ratio and analysis": "ratio",
    "ratios": "ratio",
    "financial performance ratios": "ratio",
    "balance sheet ratios": "ratio",
    "per share data": "ratio",
}

_FY = re.compile(r"(?<!\d)(20\d\d)-(\d\d)(\s?\*)?")
_NOISE = [
    re.compile(r"annual report 20\d\d-\d\d", re.I),
    re.compile(r"performance at a glance", re.I),
    re.compile(r"a decade of operational and financial excellence", re.I),
    re.compile(r"exploring hidden depths|achieving glorious heights", re.I),
    re.compile(r"^\(?\S?\s*in million", re.I),
    re.compile(r"^stated\)$", re.I),
    re.compile(r"^\d{1,3}$"),
]
_RESTATED_FOOT = re.compile(r"^\s*\*\s*Restated\b")
_CHILD = re.compile(r"^-\s*(?=[A-Z(])")
_TOKEN = re.compile(r"\S+")
SIDE_TAB_COL = 120


# --------------------------------------------------------------------------- helpers
def fy_label(header_token: str) -> str:
    """'2025-26' -> 'FY26'."""
    return "FY" + header_token[5:7]


def _unit(label: str, hint: str | None) -> str:
    low = label.lower()
    if hint == "ratio" or low.endswith(" ratio") or "equity ratio" in low or low == "current ratio":
        return "ratio"
    if "(mmt)" in low:
        return "MMT"
    if "(bcm)" in low:
        return "BCM"
    if "(mmm3)" in low:
        return "mn_m3"
    if "(kt)" in low or "000’ tonnes" in low or "000' tonnes" in low:
        return "kT"
    if "(days)" in low:
        return "days"
    if "number of employees" in low:
        return "count"
    if "per share" in low:
        return "INR_per_share"
    if "(%)" in low:
        return "pct"
    return "INR_mn"


def _tokens(text: str) -> list[tuple[str, int, int]]:
    """Whitespace tokens with (start, end) columns; ratios glued to one token."""
    glued = numbers.RATIO_IN_TEXT.sub(lambda m: (m.group(1) + ":1").ljust(len(m.group(0))), text)
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(glued)]


def _is_noise(text: str) -> bool:
    s = text.strip()
    return any(rx.search(s) for rx in _NOISE)


def _block_of(text: str) -> str | None:
    key = re.sub(r"\s+", " ", text.strip().rstrip(":")).lower()
    return BLOCKS.get(key)


def _clean_label(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(p.strip() for p in parts)).strip()


def _find_start(lines: list[str], pattern: str) -> int:
    rx = re.compile(pattern)
    for i, ln in enumerate(lines):
        if rx.search(ln.replace("\f", "").rstrip("\r")):
            return i + 1
    raise LookupError(f"table header {pattern!r} not found")


# --------------------------------------------------------------------------- parser
def parse(text_path: str | Path, report_vintage: str, extracted_at: str | None = None) -> list[dict]:
    """Parse one edition's 10-year table into bronze rows (one per number)."""
    text_path = str(text_path)
    cfg = EDITIONS[report_vintage]
    extracted_at = extracted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = pages.read_lines(text_path)
    start = _find_start(lines, cfg["start"])
    first_page = pages.page_of_line(text_path, start)
    last_page = first_page + cfg["max_pages"] - 1
    doc = Path(text_path).name

    items: list[dict] = []  # data rows and headings, in order
    columns: list[dict] | None = None  # [{header, fy, restated, right}]
    block = "physical"
    prev_data: dict | None = None  # last data item (for label continuation)
    last_parent: dict | None = None
    footnotes_page = -1
    folio_cache: dict[int, str | None] = {}

    def next_nonempty(idx: int) -> str:
        for j in range(idx + 1, min(idx + 6, len(lines))):
            t = lines[j].replace("\f", "").strip()
            if t and not _is_noise(t):
                return t
        return ""

    for idx in range(start - 1, len(lines)):
        line_no = idx + 1
        page = pages.page_of_line(text_path, line_no)
        if page > last_page:
            break
        raw = lines[idx].replace("\f", "").rstrip("\r").rstrip()
        if page == footnotes_page:
            continue
        if _RESTATED_FOOT.match(raw):
            footnotes_page = page
            prev_data = None
            continue
        stripped = raw.strip()
        if not stripped:
            prev_data = None
            continue

        fy_hits = list(_FY.finditer(raw))
        if len(fy_hits) >= 5:
            cols = [
                {"header": m.group(0).replace(" ", ""), "fy": fy_label(m.group(1) + "-" + m.group(2)),
                 "restated": bool(m.group(3)), "right": m.start() + 7}
                for m in fy_hits
            ]
            if columns is not None and [c["fy"] for c in cols] != [c["fy"] for c in columns]:
                raise ValueError(f"{doc}:{line_no} FY header differs from first header")
            columns = cols
            prev_data = None
            continue
        if columns is None:
            continue  # before the first header (title / caption lines)

        indent = len(raw) - len(raw.lstrip())
        toks = _tokens(raw)
        num_idx = [k for k, (t, _, _) in enumerate(toks) if numbers.is_numeric_token(t)]

        if not num_idx:
            if indent >= SIDE_TAB_COL or _is_noise(stripped):
                continue  # side tab / running title
            blk = _block_of(stripped)
            if blk:
                block = blk
                prev_data = None
                continue
            nxt = next_nonempty(idx)
            if prev_data is not None and not _CHILD.match(nxt):
                prev_data["label_parts"].append(stripped)  # rule 5
                continue
            child = bool(_CHILD.match(stripped))
            head = {"kind": "heading", "label_parts": [_CHILD.sub("", stripped)], "line_no": line_no,
                    "is_child": child, "parent": last_parent if child else None}
            items.append(head)
            if not child:
                last_parent = head
            prev_data = None
            continue

        if _is_noise(stripped):
            continue
        n = len(columns)
        # values = last N numeric tokens, contiguous at the right end of the numeric run
        value_idx = num_idx[-n:]
        first_val = value_idx[0]
        label_text = raw[: toks[first_val][1]].strip()
        # numeric-looking tokens that belong to the label (e.g. leading "- " child marker)
        # child marker: "-Royalty", " -Royalty", "- Crude Oil" (not "-incl. ...")
        child = bool(_CHILD.match(label_text))
        label_text = _CHILD.sub("", label_text) if child else label_text
        if not label_text:
            items.append({"kind": "skipped", "line_no": line_no, "reason": "no label", "raw": raw})
            continue
        vals = [toks[k] for k in value_idx]
        note = None
        if len(vals) < n:
            assign = []
            for _, _, end in vals:
                best = min(range(n), key=lambda c: abs(columns[c]["right"] - end))
                assign.append(best)
            if assign != sorted(set(assign)) or len(set(assign)) != len(assign):
                items.append({"kind": "skipped", "line_no": line_no, "reason": "position alignment failed", "raw": raw})
                prev_data = None
                continue
            col_for = assign
            note = "aligned_by_position"
        else:
            col_for = list(range(n))
        item = {"kind": "data", "label_parts": [label_text], "line_no": line_no, "page": page,
                "is_child": child, "parent": None, "block": block, "note": note,
                "cells": [(columns[c], tok) for c, (tok, _, _) in zip(col_for, vals)]}
        if child:
            item["parent"] = last_parent
        else:
            last_parent = item
        items.append(item)
        prev_data = item

    _LAST_SKIPPED[(text_path, report_vintage)] = [it for it in items if it["kind"] == "skipped"]
    rows: list[dict] = []
    for it in items:
        if it["kind"] != "data":
            continue
        label = _clean_label(it["label_parts"])
        parent = _clean_label(it["parent"]["label_parts"]) if it.get("parent") else None
        page = it["page"]
        if page not in folio_cache:
            folio_cache[page] = pages.folio(text_path, page)
        for col, tok in it["cells"]:
            value, is_nil, hint = numbers.parse_token(tok)
            unit = _unit(label, hint)
            blk = "physical" if unit in ("MMT", "BCM", "kT", "mn_m3") else it["block"]
            eid = hashlib.sha1(f"{doc}|{it['line_no']}|{col['fy']}".encode()).hexdigest()[:16]
            rows.append({
                "extract_id": eid,
                "source_system": "ar_text_ten_year",
                "source_doc": doc,
                "source_page": page,
                "source_page_label": folio_cache[page],
                "source_text_line": it["line_no"],
                "raw_label": label,
                "raw_value_text": tok,
                "parsed_value": value,
                "unit": unit,
                "column_header": col["header"],
                "scope": "standalone",
                "statement_guess": "ten_year_summary",
                "extractor_version": EXTRACTOR_VERSION,
                "extracted_at": extracted_at,
                "report_vintage": report_vintage,
                "fiscal_year": col["fy"],
                "is_restated": col["restated"],
                "is_nil": is_nil,
                "parent_label": parent,
                "block": blk,
                "notes": it["note"],
            })
    return rows


def skipped_lines(text_path: str | Path, report_vintage: str) -> list[dict]:
    """Lines in the table range that looked numeric but were not emitted (after parse())."""
    return _LAST_SKIPPED.get((str(text_path), report_vintage), [])


_LAST_SKIPPED: dict = {}


# --------------------------------------------------------------------------- cross-check
_ALIASES = {
    "net profit pat": "profit after tax pat",
    "profit after tax": "profit after tax pat",
    "total revenues": "total income",
    "net worth equity": "total equity net worth",
    "finance cost": "finance costs",
    "exceptional items": "exceptional items income expenses",
    "corporate tax net": "corporate tax",
    "dividend": "dividend paid in fy",
    "other operating income": "other operating revenue",
    "road and infrastructure": "road and infrastructure cess",  # AR FY22: "Cess" wraps onto the next page
}
# Generic child labels are only comparable together with their parent ("Others" under
# "Work in Progress:" in AR FY26 is not "Others" product sales in AR FY24).
_GENERIC_CHILD = {"others", "current", "non current", "revenue", "capital"}
# Same label, different definition (verified: AR FY26 Total Expenses + DD&A = AR FY24/FY22
# Total Expenses for FY17-FY23 to the rupee million) -> never paired.
_DEFINITION_KEYS = {("AR_FY2025-26", "total expenses"): "total expenses excl dda"}


def norm_label(label: str) -> str:
    s = label.lower().replace("’", "'").replace("&", " and ")
    s = s.replace("(`)", " ").replace("(restated)", " ")
    s = re.sub(r"[^a-z0-9%]+", " ", s)
    s = s.replace("%", " ")
    s = re.sub(r"\bitem\b", "items", s)
    s = re.sub(r"\s+", " ", s).strip()
    return _ALIASES.get(s, s)


def cross_key(row: dict) -> str:
    """Normalised label used to pair rows across editions."""
    key = norm_label(row["raw_label"])
    if row.get("parent_label") and key in _GENERIC_CHILD:
        key = norm_label(row["parent_label"]) + " / " + key
    return _DEFINITION_KEYS.get((row["report_vintage"], key), key)


def _dp(text: str) -> int:
    m = re.search(r"\.(\d+)", text)
    return len(m.group(1)) if m else 0


def _tolerance(unit: str, ta: str, tb: str) -> float:
    if unit == "INR_mn":
        return 1.0
    return 0.5 * 10 ** (-min(_dp(ta), _dp(tb))) + 1e-9


def cross_check(rows_a: list[dict], rows_b: list[dict]) -> list[dict]:
    """Compare overlapping (normalised label, FY) between two editions (V09)."""
    def index(rows):
        out: dict[tuple[str, str], list[dict]] = {}
        for r in rows:
            out.setdefault((cross_key(r), r["fiscal_year"]), []).append(r)
        return out

    va, vb = rows_a[0]["report_vintage"], rows_b[0]["report_vintage"]
    later_is_a = va > vb
    ia, ib = index(rows_a), index(rows_b)
    result = []
    for key in sorted(set(ia) & set(ib)):
        cand_a, cand_b = ia[key], ib[key]
        best = None
        for ra in cand_a:
            for rb in cand_b:
                if ra["unit"] != rb["unit"]:
                    continue
                d = ra["parsed_value"] - rb["parsed_value"]
                if best is None or abs(d) < abs(best[2]):
                    best = (ra, rb, d)
        if best is None:
            continue
        ra, rb, d = best
        later = ra if later_is_a else rb
        tol = _tolerance(ra["unit"], ra["raw_value_text"], rb["raw_value_text"])
        result.append({
            "label": key[0], "fy": key[1],
            "value_a": ra["parsed_value"], "value_b": rb["parsed_value"], "delta": round(d, 6),
            "vintage_a": va, "vintage_b": vb,
            "later_marked_restated": bool(later["is_restated"]),
            "unit": ra["unit"], "passed": abs(d) <= tol,
            "line_a": ra["source_text_line"], "line_b": rb["source_text_line"],
            "multi_candidates": len(cand_a) > 1 or len(cand_b) > 1,
        })
    return result


# --------------------------------------------------------------------------- CLI
def run_all(text_dir: Path = TEXT_DIR) -> tuple[dict[str, list[dict]], list[dict]]:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_ed = {v: parse(text_dir / c["file"], v, stamp) for v, c in EDITIONS.items()}
    eds = list(by_ed)
    checks = []
    for i in range(len(eds)):
        for j in range(i + 1, len(eds)):
            checks.extend(cross_check(by_ed[eds[i]], by_ed[eds[j]]))
    return by_ed, checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="financial_ssot/out/ten_year_raw.parquet")
    ap.add_argument("--text-dir", default=str(TEXT_DIR))
    args = ap.parse_args(argv)
    by_ed, checks = run_all(Path(args.text_dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    all_rows = [r for rows in by_ed.values() for r in rows]
    import pandas as pd  # third-party only for the parquet write

    pd.DataFrame(all_rows).to_parquet(out, index=False)
    cc_path = out.parent / "ten_year_crosscheck.csv"
    with cc_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(checks[0].keys()))
        w.writeheader()
        w.writerows(checks)
    for v, rows in by_ed.items():
        labels = {(r["raw_label"], r["source_text_line"]) for r in rows}
        fys = sorted({r["fiscal_year"] for r in rows})
        print(f"{v}: {len(rows)} rows, {len(labels)} label lines, FYs {fys[0]}..{fys[-1]} ({len(fys)})")
    n_pass = sum(c["passed"] for c in checks)
    n_fail_unflagged = sum((not c["passed"]) and not c["later_marked_restated"] for c in checks)
    print(f"cross-check: {len(checks)} pairs, {n_pass} pass ({100 * n_pass / len(checks):.1f}%), "
          f"{len(checks) - n_pass} fail, {n_fail_unflagged} fail without restated marker")
    print(f"wrote {out} and {cc_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
