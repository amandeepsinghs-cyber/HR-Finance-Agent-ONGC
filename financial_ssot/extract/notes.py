"""Deterministic parser for the AR notes to the standalone accounts (P1.3, SPEC-01 §4.3).

Notes are located by heading text (note numbers move between editions: opex is
Note 35 in AR FY25/FY26 but Note 34 in AR FY24).  Each top-level note runs from
its heading to the next top-level heading; it is split at every sub-heading
(``35.1.``, ``44.2.``) and every sub-region that prints its own date header is
parsed with the statement line engine (``statements.parse_region``), giving
``source_table = 'note_<n>'`` / ``'note_<n>_<m>'`` rows with the same lineage
and flags as the statements.

Notes (SPEC-01 §4.3 table, packet §2):

* Revenue from operations, Other income, Production / opex (Note 35 incl.
  35.1 employee benefits gross), Finance cost (incl. unwinding of discount on
  decommissioning and lease interest), DD&A and impairment, Tax expense (incl.
  the statutory-rate reconciliation), Lease liabilities (22.1 movement),
  Provisions (decommissioning movement), Investments (shares held, in million,
  as a separate ``[no. of shares, million]`` row), Segment reporting (44.2–44.5).
* The Operations production table (``Crude Oil Production (MMT)`` /
  ``Natural Gas Production (BCM)``, ONGC | JV share, 3 FYs) -> ``source_table =
  'production_table'``.

Sub-regions without a date header (text paragraphs) are skipped; nothing is
inferred.  Column-split failures are returned as issues for the Gemini fallback.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from financial_ssot.common import pages
from financial_ssot.extract import statements as st

EXTRACTOR_VERSION = "notes/1.0.0"

# key -> heading text regex (after the note number); matched at line start as "<n>.<tab/space>TEXT"
NOTE_HEADINGS: dict[str, str] = {
    "revenue": r"Revenue from Operations\s*$",
    "other_income": r"Other Income\s*$",
    "opex": r"Production,\s+Transportation,\s+Selling(?:,| and)\s+Distribution",
    "finance_cost": r"Finance Costs?\s*$",
    "dda": r"(?:Depletion|Depreciation),\s+(?:Depreciation|Depletion),\s+Amorti[sz]ation\s+and\s+Impairment",
    "tax": r"Tax Expense\s*$",
    "lease": r"Lease Liabilities\s*$",
    "provisions": r"Provisions\s*$",
    "investments": r"Investments?\s*$",
    "segment": r"Segment Reporting\s*$",
}
_TOP = re.compile(r"^\s*(\d{1,2})\.?[\t ]+([A-Z][^\n]*)$")
_SUB = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){1,3})\.?[\t ]+\S")
MAX_NOTE_PAGES = 6


def _window(cfg: dict) -> tuple[int, int]:
    """Standalone notes live between the standalone BS page and the consolidated BS page."""
    return cfg["standalone"]["balance_sheet"], cfg["consolidated"]["balance_sheet"]


def find_note(text_path: str | Path, key: str, cfg: dict) -> tuple[str, int] | None:
    """(note number, 1-based heading line) of a standalone note, by heading text."""
    rx = re.compile(r"^\s*(\d{1,2})\.?[\t ]+" + NOTE_HEADINGS[key], re.I)
    lo, hi = _window(cfg)
    lines = pages.read_lines(text_path)
    for i, ln in enumerate(lines):
        t = st._UNIT_CAPTION.sub("", ln.replace("\f", "").rstrip("\r")).rstrip()
        m = rx.match(t)
        if m and lo < pages.page_of_line(text_path, i + 1) < hi and int(m.group(1)) >= 5:
            return m.group(1), i + 1
    return None


def note_subregions(text_path: str | Path, num: str, start: int) -> list[tuple[str, list[tuple[int, int, str]]]]:
    """Split a note (heading line ``start``) into (sub-note id, region lines)."""
    lines = pages.read_lines(text_path)
    first_page = pages.page_of_line(text_path, start)
    out: list[tuple[str, list]] = []
    cur_id, cur = num, []
    for idx in range(start - 1, len(lines)):
        pg = pages.page_of_line(text_path, idx + 1)
        if pg >= first_page + MAX_NOTE_PAGES:
            break
        t = lines[idx].replace("\f", "").rstrip("\r")
        if idx >= start:
            m = _TOP.match(t)
            if m and m.group(1) != num and int(m.group(1)) in (int(num) + 1, int(num) + 2):
                break
            ms = _SUB.match(t)
            if ms and ms.group(1).split(".")[0] == num:
                out.append((cur_id, cur))
                cur_id, cur = ms.group(1), []
        cur.append((idx + 1, pg, t))
    out.append((cur_id, cur))
    return [(i, r) for i, r in out if r]


def _has_header(region: list[tuple[int, int, str]]) -> bool:
    cols, first, _ = st._find_header(region)
    return bool(cols) and first < len(region)


def parse(text_path: str | Path, report_vintage: str, page_map: dict | None = None,
          extracted_at: str | None = None) -> list[dict]:
    return parse_with_issues(text_path, report_vintage, page_map, extracted_at)[0]


def parse_with_issues(text_path, report_vintage, page_map=None, extracted_at=None):
    page_map = page_map or st.load_page_map()
    cfg = page_map["editions"][report_vintage]
    extracted_at = extracted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text_path = str(text_path)
    doc = Path(text_path).name
    rows, issues, found = [], [], {}
    folio_cache: dict[int, str | None] = {}

    def folio_of(pg: int):
        if pg not in folio_cache:
            folio_cache[pg] = pages.folio(text_path, pg)
        return folio_cache[pg]

    for key in NOTE_HEADINGS:
        hit = find_note(text_path, key, cfg)
        if hit is None:
            issues.append({"report_vintage": report_vintage, "scope": "standalone", "statement": f"note:{key}",
                           "page": None, "line": None, "check": "locate", "detail": "heading not found"})
            continue
        num, start = hit
        found[key] = (num, pages.page_of_line(text_path, start))
        for sub_id, region in note_subregions(text_path, num, start):
            if not _has_header(region):
                continue
            table = "note_" + sub_id.replace(".", "_")
            r, iss = st.parse_region(region, doc=doc, report_vintage=report_vintage, scope="standalone",
                                     statement=table, extracted_at=extracted_at, folio_of=folio_of)
            for x in r:
                x.update({"source_system": "ar_text_note", "source_table": table, "statement_guess": "note",
                          "extractor_version": EXTRACTOR_VERSION, "note_key": key, "note_ref": x["note_ref"]
                          or sub_id})
            rows.extend(r)
            # notes: subtotal mismatches are flags for review, not parser failures
            issues.extend(i for i in iss if i["check"] != "header")
    prod, piss = production_table(text_path, report_vintage, extracted_at, folio_of)
    rows.extend(prod)
    issues.extend(piss)
    return rows, issues, found


_PROD_ROW = re.compile(r"^\s*(Crude Oil|Natural Gas) Production \((MMT|BCM)\)", re.I)


def production_table(text_path: str, report_vintage: str, extracted_at: str, folio_of):
    """Operations chapter production table (ONGC | JV share by FY), if the edition prints it."""
    lines = pages.read_lines(text_path)
    for i, ln in enumerate(lines[:12000]):
        if _PROD_ROW.match(ln.replace("\f", "")):
            hdr = None
            for j in range(i - 1, max(0, i - 8), -1):
                if len(st._FYTOK.findall(lines[j])) >= 2:
                    hdr = j
                    break
            if hdr is None:
                continue
            region = [(hdr, pages.page_of_line(text_path, hdr), "Production table")]
            for k in range(hdr, min(len(lines), i + 4)):
                t = lines[k].replace("\f", "").rstrip("\r")
                if k > i and t.strip() and not _PROD_ROW.match(t):
                    break
                region.append((k + 1, pages.page_of_line(text_path, k + 1), t))
            rows, iss = st.parse_region(region, doc=Path(text_path).name, report_vintage=report_vintage,
                                        scope="standalone", statement="production_table",
                                        extracted_at=extracted_at, folio_of=folio_of, value_rx=st._VAL3)
            for x in rows:
                x.update({"source_system": "ar_text_note", "source_table": "production_table",
                          "statement_guess": "production", "extractor_version": EXTRACTOR_VERSION,
                          "note_key": "production", "is_subtotal": False, "subtotal_ok": None})
            if any("[JV share]" in x["raw_label"] for x in rows):  # the ONGC | JV share table
                return rows, [x for x in iss if x["check"] == "column_split"]
    return [], []


def run_all(text_dir: Path = st.TEXT_DIR, page_map: dict | None = None):
    page_map = page_map or st.load_page_map()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, issues, located = [], [], {}
    for vintage, cfg in page_map["editions"].items():
        r, i, f = parse_with_issues(text_dir / cfg["file"], vintage, page_map, stamp)
        rows += r
        issues += i
        located[vintage] = f
    return rows, issues, located


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(st.PKG_DIR / "out" / "notes_raw.parquet"))
    ap.add_argument("--text-dir", default=str(st.TEXT_DIR))
    args = ap.parse_args(argv)
    rows, issues, located = run_all(Path(args.text_dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    pd.DataFrame(rows).to_parquet(out, index=False)
    iss_path = out.parent / "notes_parse_issues.csv"
    with iss_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["report_vintage", "scope", "statement", "page", "line", "check", "detail"])
        w.writeheader()
        w.writerows(issues)
    for v, f in located.items():
        n = sum(1 for r in rows if r["report_vintage"] == v)
        print(f"{v}: {n} rows; notes located: " + ", ".join(f"{k}={num}@p{pg}" for k, (num, pg) in f.items()))
    print(f"{len(rows)} rows; {len(issues)} issues -> {iss_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
