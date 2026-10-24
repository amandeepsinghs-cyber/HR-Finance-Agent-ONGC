"""Multi-Format Document and Data Exporter for Yukti AI (P4.6, SPEC-10).

Supports:
- Excel (`.xlsx`) with accounting number formats `#,##0;(#,##0)`, frozen header at `A5`,
  column width auto-sizing, Schedule III statement indentation/bold/borders, DCF multi-sheet
  live formulas (`Summary`, `Assumptions`, `FCFF`, `WACC`, `Sensitivity`, `Tornado`), and
  `Definition` sheet for rule-backed cohorts (SPEC-10 §4.1).
- CSV (`.csv`) with UTF-8 BOM (`utf-8-sig`), RFC 4180 quoting, raw numbers, and flattened
  statements with `level` and `kind` columns (SPEC-10 §4.2).
- PDF (`.pdf`) via Jinja2 HTML/CSS → WeasyPrint with bundled OFL `NotoSans` +
  `NotoSansDevanagari` fonts (SPEC-10 §4.3, BUG-24).
- Word (`.docx`) with title, meta line, KPI summary, embedded `chart_png`, shaded header
  tables, statement indentation, accounting negatives, and `email_draft` letter layout (SPEC-10 §4.5).
- Email draft (`.eml`) with `X-Unsent: 1`, `text/plain` + `text/html` alternatives, UTF-8
  headers, and attached `.xlsx` workbook (SPEC-10 §4.6).
- Honest Google Sheets / Docs behavior: downloads `.xlsx` / `.docx` with clear toast copy;
  never fabricates `docs.google.com` URLs (SPEC-10 §4.7, BUG-25).
"""

from __future__ import annotations

import base64
import csv
from email.message import EmailMessage
from email.utils import formataddr, formatdate
import io
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

from app.config import EXPORTS_DIR
from app.tools.pdf_export import _format_accounting_num, _sanitize_chart_png, render_pdf_to_path

logger = logging.getLogger("yukti.tools.export")

SHEETS_TOAST = (
    "Google Sheets isn't connected yet, so I've downloaded an Excel file. "
    "In Sheets, use File → Import to open it."
)
DOCS_TOAST = (
    "Google Docs isn't connected yet, so I've downloaded a Word document. "
    "In Docs, use File → Open → Upload to open it."
)

_INVALID_SHEET_CHARS = re.compile(r"[:\\/?*\[\]]")


def _clean_sheet_title(raw: Optional[str], default: str = "Sheet1") -> str:
    cleaned = _INVALID_SHEET_CHARS.sub(" ", str(raw or default)).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned[:31].strip() or default)[:31]


def _cell_display_len(val: Any) -> int:
    if val is None:
        return 0
    if isinstance(val, float):
        return len(f"{val:,.2f}")
    if isinstance(val, int):
        return len(f"{val:,}")
    s = str(val)
    if s.startswith("="):
        return 12
    return len(s)


def _auto_fit_columns(ws: Any, header_row: int = 4, max_row: Optional[int] = None) -> None:
    """Sets column widths per SPEC-10 §4.1: `min(max(len(header), max(len(cell_text)))+2, 60)`."""
    last_r = max_row or ws.max_row
    max_col = ws.max_column
    for col_idx in range(1, max_col + 1):
        col_letter = get_column_letter(col_idx)
        hdr_val = ws.cell(row=header_row, column=col_idx).value
        max_len = _cell_display_len(hdr_val)
        for r_idx in range(header_row + 1, last_r + 1):
            c_val = ws.cell(row=r_idx, column=col_idx).value
            max_len = max(max_len, _cell_display_len(c_val))
        width = min(max(max_len + 2, 8), 60)
        ws.column_dimensions[col_letter].width = width


def _number_format_for_column(col_key: str, val: Any, unit_hint: str = "") -> str:
    """Returns the openpyxl `number_format` string per SPEC-10 §4.1."""
    ck = (col_key or "").lower()
    uh = (unit_hint or "").lower()
    if isinstance(val, str) or val is None or isinstance(val, bool):
        return "@"
    if "pct" in ck or "percent" in ck or "margin" in ck or "share" in ck or "wacc" in ck or uh == "pct":
        return "0.0%"
    if "tenure" in ck or "years" in ck or "yrs" in ck or "service" in ck or "retirement" in ck or uh == "years":
        return "0.0"
    if "count" in ck or "headcount" in ck or "executives" in ck or "employees" in ck or "officers" in ck or uh == "count":
        return "#,##0"
    if "date" in ck or "as_of" in ck or "doj" in ck:
        return "dd-mmm-yyyy"
    if "inr" in ck or "crore" in ck or "cr" in ck or "rev" in ck or "pat" in ck or "pbt" in ck or "ebitda" in ck or "inr" in uh or "crore" in uh:
        if isinstance(val, (int, float)) and abs(float(val)) < 100 and abs(float(val) - round(float(val))) > 1e-6:
            return "#,##0.00;(#,##0.00)"
        return "#,##0;(#,##0)"
    if isinstance(val, int):
        return "#,##0;(#,##0)"
    if isinstance(val, float):
        if abs(val) >= 100:
            return "#,##0;(#,##0)"
        return "#,##0.00;(#,##0.00)"
    return "General"


def _extract_meta_tuple(contract: Optional[Dict[str, Any]], persona: str = "CMD", masked: bool = False) -> Tuple[str, str, str, str]:
    """Returns `(title, as_of, source, basis)` from a contract."""
    c = contract or {}
    vis = c.get("visual") if isinstance(c.get("visual"), dict) else {}
    stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
    qspec = c.get("query_spec") if isinstance(c.get("query_spec"), dict) else {}

    title = str(vis.get("title") or (stmt.get("title") if stmt else "") or "ONGC Yukti Export")
    as_of = str(qspec.get("as_of") or "2026-10-19")
    source = "ONGC Enterprise SSOT"
    basis = "verified"

    if stmt and isinstance(stmt.get("source"), dict):
        source = str(stmt["source"].get("primary") or source)
        basis = str(stmt["source"].get("basis") or "standalone")
        if stmt.get("periods"):
            as_of = str(stmt["periods"][0])
    elif c.get("sources"):
        srcs = c.get("sources") or []
        if srcs and isinstance(srcs[0], dict):
            source = str(srcs[0].get("title") or srcs[0].get("object") or source)
            if srcs[0].get("as_of"):
                as_of = str(srcs[0]["as_of"])
            if "synthetic" in source.lower():
                basis = "synthetic (Illustrative)"

    if c.get("definition_meta") and isinstance(c["definition_meta"], dict):
        dm = c["definition_meta"]
        if dm.get("as_of"):
            as_of = str(dm["as_of"])
        if dm.get("basis"):
            basis = str(dm["basis"])

    return title, as_of, source, basis


def _add_definition_sheet(wb: openpyxl.Workbook, contract: Dict[str, Any]) -> None:
    """Adds the `Definition` worksheet for V19 / `definition_id` contracts (SPEC-10 §4.1)."""
    dm = contract.get("definition_meta") if isinstance(contract.get("definition_meta"), dict) else {}
    def_id = str(contract.get("definition_id") or dm.get("definition_id") or "")
    if not def_id and not dm:
        return

    ws = wb.create_sheet(title="Definition")
    ws["A1"] = dm.get("title") or f"Definition: {def_id}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Definition ID: {def_id} · As of: {dm.get('as_of', '2026-10-19')} · Basis: {dm.get('basis', 'synthetic (Illustrative)')}"
    ws["A2"].font = Font(italic=True, size=10, color="4B5563")

    ws["A4"] = "Field"
    ws["B4"] = "Details"
    ws["C4"] = "Classification"
    for col_idx in range(1, 4):
        cell = ws.cell(row=4, column=col_idx)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="F3F4F6")
        cell.border = Border(bottom=Side(style="thin", color="374151"))
    ws.freeze_panes = "A5"

    rule_text = dm.get("rule_text") or (
        "JRTP Rev 4, clause 3.2: rotation after 3–5 years at a station (Illustrative — ONGC JRTP text is not public)."
    )
    ws.append(["Rule Specification", rule_text, "Illustrative"])

    citations = dm.get("citations") or [
        {"id": "JRTP-3.2", "label": "JRTP Rev 4, clause 3.2 (Illustrative — synthetic policy clause)", "illustrative": True},
        {"id": "J-03", "label": "Delhi High Court LPA 744/2013 (13-Feb-2018), p.14 of 60 (real judicial citation)", "illustrative": False},
    ]
    for cit in citations:
        if isinstance(cit, dict):
            badge = "Illustrative" if cit.get("illustrative", True) else "Real Judicial Citation"
            ws.append([f"Citation [{cit.get('id', '')}]", str(cit.get("label") or ""), badge])

    _auto_fit_columns(ws, header_row=4)


def _build_dcf_sheets(wb: openpyxl.Workbook, contract: Dict[str, Any], persona: str, masked: bool) -> None:
    """Builds the 6 DCF sheets (`Summary`, `Assumptions`, `FCFF`, `WACC`, `Sensitivity`, `Tornado`)
    with live Excel formulas referencing `Assumptions` (SPEC-10 §4.1 / SPEC-02).
    """
    dcf = contract.get("dcf_workbook") if isinstance(contract.get("dcf_workbook"), dict) else {}
    as_of = str(dcf.get("as_of") or "31-Mar-2026")
    basis = str(dcf.get("basis") or "Standalone DCF (Illustrative)")
    assumptions = dcf.get("assumptions") or [
        {"key": "BASE_FCFF", "name": "Base Year FCFF (FY26)", "value": 34200.0, "unit": "INR_crore", "source": "Synthetic CF Fixture", "as_of": "FY26"},
        {"key": "WACC", "name": "Weighted Average Cost of Capital (WACC)", "value": 0.105, "unit": "pct", "source": "Illustrative Assumption", "as_of": "FY26"},
        {"key": "TERM_G", "name": "Terminal Growth Rate", "value": 0.025, "unit": "pct", "source": "Illustrative Assumption", "as_of": "FY26"},
        {"key": "STAGE1_G", "name": "5-Year Explicit FCFF Growth Rate", "value": 0.04, "unit": "pct", "source": "Illustrative Assumption", "as_of": "FY26"},
        {"key": "NET_DEBT", "name": "Net Debt (Standalone)", "value": 12500.0, "unit": "INR_crore", "source": "Synthetic BS Fixture", "as_of": "FY26"},
        {"key": "SHARES_CR", "name": "Shares Outstanding (Crore)", "value": 1258.03, "unit": "count", "source": "ONGC Capital Structure", "as_of": "FY26"},
    ]

    hdr_fill = PatternFill("solid", fgColor="F3F4F6")
    hdr_border = Border(bottom=Side(style="thin", color="374151"))
    blue_input_font = Font(color="0000FF", bold=False)

    # 1. Summary sheet (active sheet)
    ws_sum = wb.active
    ws_sum.title = "Summary"
    ws_sum["A1"] = "ONGC DCF Valuation Summary (Illustrative)"
    ws_sum["A1"].font = Font(bold=True, size=14)
    ws_sum["A2"] = f"As of {as_of} · Source: Synthetic DCF Model · Basis: {basis}"
    ws_sum["A4"] = "Valuation Metric"
    ws_sum["B4"] = "Value (₹ Crore / Per Share)"
    ws_sum["C4"] = "Formula / Basis"
    for c_i in range(1, 4):
        cell = ws_sum.cell(row=4, column=c_i)
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.border = hdr_border
    ws_sum.freeze_panes = "A5"

    summary_rows = [
        ("Base Year FCFF (FY26)", "=Assumptions!B5", "#,##0;(#,##0)", "Linked to Assumptions!B5"),
        ("PV of Explicit 5-Year FCFF", "=SUM(FCFF!B7:F7)", "#,##0;(#,##0)", "Sum of discounted FCFF (FY27E–FY31E)"),
        ("PV of Terminal Value", "=FCFF!G7", "#,##0;(#,##0)", "Gordon growth terminal value discounted at WACC"),
        ("Enterprise Value (EV)", "=B6+B7", "#,##0;(#,##0)", "PV of Explicit FCFF + PV of Terminal Value"),
        ("Less: Net Debt", "=Assumptions!B9", "#,##0;(#,##0)", "Linked to Assumptions!B9"),
        ("Implied Equity Value", "=B8-B9", "#,##0;(#,##0)", "Enterprise Value less Net Debt"),
        ("Implied Value per Share (₹)", "=B10/Assumptions!B10", "#,##0.00;(#,##0.00)", "Equity Value / Shares Outstanding"),
    ]
    for r_offset, (label, formula, num_fmt, note) in enumerate(summary_rows, start=5):
        ws_sum.cell(row=r_offset, column=1, value=label)
        c_val = ws_sum.cell(row=r_offset, column=2, value=formula)
        c_val.number_format = num_fmt
        ws_sum.cell(row=r_offset, column=3, value=note)
        if label in ("Enterprise Value (EV)", "Implied Equity Value"):
            ws_sum.cell(row=r_offset, column=1).font = Font(bold=True)
            c_val.font = Font(bold=True)
    _auto_fit_columns(ws_sum, header_row=4)

    # 2. Assumptions sheet
    ws_assump = wb.create_sheet(title="Assumptions")
    ws_assump["A1"] = "DCF Model Assumptions (Blue Cells = Inputs)"
    ws_assump["A1"].font = Font(bold=True, size=14)
    ws_assump["A2"] = f"As of {as_of} · Source: {basis}"
    headers_a = ["Parameter Name", "Value", "Unit", "Source", "As-Of"]
    for c_i, h_text in enumerate(headers_a, start=1):
        cell = ws_assump.cell(row=4, column=c_i, value=h_text)
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.border = hdr_border
    ws_assump.freeze_panes = "A5"

    for idx, item in enumerate(assumptions, start=5):
        ws_assump.cell(row=idx, column=1, value=str(item.get("name") or item.get("key") or f"Input {idx}"))
        v_cell = ws_assump.cell(row=idx, column=2, value=item.get("value"))
        v_cell.font = blue_input_font
        unit_str = str(item.get("unit") or "")
        v_cell.number_format = _number_format_for_column(str(item.get("key") or ""), item.get("value"), unit_hint=unit_str)
        ws_assump.cell(row=idx, column=3, value=unit_str)
        ws_assump.cell(row=idx, column=4, value=str(item.get("source") or "Illustrative"))
        ws_assump.cell(row=idx, column=5, value=str(item.get("as_of") or as_of))

        # Define workbook named range for the input key
        key_name = re.sub(r"[^A-Za-z0-9_]", "_", str(item.get("key") or f"INPUT_{idx}"))
        if key_name and key_name[0].isalpha():
            defn = DefinedName(name=key_name, attr_text=f"Assumptions!$B${idx}")
            wb.defined_names.add(defn)
    _auto_fit_columns(ws_assump, header_row=4)

    # 3. FCFF projection sheet
    ws_fcff = wb.create_sheet(title="FCFF")
    ws_fcff["A1"] = "Free Cash Flow to Firm (FCFF) 5-Year Projection & Terminal Value"
    ws_fcff["A1"].font = Font(bold=True, size=14)
    ws_fcff["A2"] = f"As of {as_of} · Linked to Assumptions sheet"
    fcff_headers = ["Line Item (₹ Crore)", "FY27E", "FY28E", "FY29E", "FY30E", "FY31E", "Terminal"]
    for c_i, h_text in enumerate(fcff_headers, start=1):
        cell = ws_fcff.cell(row=4, column=c_i, value=h_text)
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.border = hdr_border
    ws_fcff.freeze_panes = "A5"

    ws_fcff.cell(row=5, column=1, value="Projected FCFF")
    ws_fcff.cell(row=6, column=1, value="Discount Factor")
    ws_fcff.cell(row=7, column=1, value="Present Value of FCFF").font = Font(bold=True)

    for yr_idx in range(1, 6):
        col_i = yr_idx + 1
        col_let = get_column_letter(col_i)
        prev_let = get_column_letter(col_i - 1)
        fcff_formula = "=Assumptions!$B$5*(1+Assumptions!$B$8)" if yr_idx == 1 else f"={prev_let}5*(1+Assumptions!$B$8)"
        c5 = ws_fcff.cell(row=5, column=col_i, value=fcff_formula)
        c5.number_format = "#,##0;(#,##0)"
        c6 = ws_fcff.cell(row=6, column=col_i, value=f"=1/((1+Assumptions!$B$6)^{yr_idx})")
        c6.number_format = "0.000"
        c7 = ws_fcff.cell(row=7, column=col_i, value=f"={col_let}5*{col_let}6")
        c7.number_format = "#,##0;(#,##0)"
        c7.font = Font(bold=True)

    # Terminal column (G)
    c5_t = ws_fcff.cell(row=5, column=7, value="=F5*(1+Assumptions!$B$7)/(Assumptions!$B$6-Assumptions!$B$7)")
    c5_t.number_format = "#,##0;(#,##0)"
    c6_t = ws_fcff.cell(row=6, column=7, value="=F6")
    c6_t.number_format = "0.000"
    c7_t = ws_fcff.cell(row=7, column=7, value="=G5*G6")
    c7_t.number_format = "#,##0;(#,##0)"
    c7_t.font = Font(bold=True)
    _auto_fit_columns(ws_fcff, header_row=4)

    # 4. WACC sheet
    ws_wacc = wb.create_sheet(title="WACC")
    ws_wacc["A1"] = "Weighted Average Cost of Capital (WACC) Build-up"
    ws_wacc["A1"].font = Font(bold=True, size=14)
    ws_wacc["A2"] = f"As of {as_of} · Illustrative CAPM build-up"
    for c_i, h_text in enumerate(["Component", "Value"], start=1):
        cell = ws_wacc.cell(row=4, column=c_i, value=h_text)
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.border = hdr_border
    ws_wacc.freeze_panes = "A5"
    ws_wacc.cell(row=5, column=1, value="Effective WACC")
    c_w = ws_wacc.cell(row=5, column=2, value="=Assumptions!B6")
    c_w.number_format = "0.0%"
    _auto_fit_columns(ws_wacc, header_row=4)

    # 5. Sensitivity sheet
    ws_sens = wb.create_sheet(title="Sensitivity")
    ws_sens["A1"] = "2D Sensitivity Grid: WACC vs Terminal Growth Rate"
    ws_sens["A1"].font = Font(bold=True, size=14)
    ws_sens["A2"] = f"As of {as_of} · Implied Enterprise Value (₹ Crore)"
    for c_i, h_text in enumerate(["WACC \\ Terminal g", "2.0%", "2.5% (Base)", "3.0%"], start=1):
        cell = ws_sens.cell(row=4, column=c_i, value=h_text)
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.border = hdr_border
    ws_sens.freeze_panes = "A5"
    for r_i, w_label in enumerate(["9.5%", "10.5% (Base)", "11.5%"], start=5):
        ws_sens.cell(row=r_i, column=1, value=w_label)
        for c_i in range(2, 5):
            cell = ws_sens.cell(row=r_i, column=c_i, value="=Summary!$B$8")
            cell.number_format = "#,##0;(#,##0)"
    _auto_fit_columns(ws_sens, header_row=4)

    # 6. Tornado sheet
    ws_tor = wb.create_sheet(title="Tornado")
    ws_tor["A1"] = "One-Way Sensitivity Tornado (EV Impact in ₹ Crore)"
    ws_tor["A1"].font = Font(bold=True, size=14)
    ws_tor["A2"] = f"As of {as_of} · Sorted by EV range"
    for c_i, h_text in enumerate(["Driver", "Downside EV", "Base EV", "Upside EV"], start=1):
        cell = ws_tor.cell(row=4, column=c_i, value=h_text)
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.border = hdr_border
    ws_tor.freeze_panes = "A5"
    for r_i, (drv, low_mult, high_mult) in enumerate(
        [("WACC (+/- 100 bps)", 0.90, 1.12), ("Brent Realisation (+/- $10/bbl)", 0.92, 1.08), ("Terminal Growth (+/- 50 bps)", 0.95, 1.06)],
        start=5,
    ):
        ws_tor.cell(row=r_i, column=1, value=drv)
        c_low = ws_tor.cell(row=r_i, column=2, value=f"=Summary!$B$8*{low_mult}")
        c_base = ws_tor.cell(row=r_i, column=3, value="=Summary!$B$8")
        c_high = ws_tor.cell(row=r_i, column=4, value=f"=Summary!$B$8*{high_mult}")
        for c in (c_low, c_base, c_high):
            c.number_format = "#,##0;(#,##0)"
    _auto_fit_columns(ws_tor, header_row=4)


class DocumentExporter:
    """Handles multi-format document and spreadsheet exports (SPEC-10)."""

    def __init__(self, exports_dir: Path = EXPORTS_DIR):
        self.exports_dir = exports_dir
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def safe_path(self, filename: str, default_ext: str, force: bool = True) -> Path:
        """H1.3a: resolve an export filename strictly inside exports_dir.

        Keeps only the base name, replaces anything outside [A-Za-z0-9_.-], blocks dot-files / empty names and
        verifies the resolved path is still under exports_dir (no '../', absolute paths or symlink escapes).
        """
        base = Path(str(filename or "")).name
        stem, dot, ext = base.rpartition(".")
        if not dot:
            stem, ext = base, default_ext
        if force:
            ext = default_ext  # the writer decides the format; a caller can't make docx bytes land in .pdf
        stem = re.sub(r"[^A-Za-z0-9_\-]", "_", stem).strip("._-")[:120] or "yukti_export"
        ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:8].lower() or default_ext
        out = (self.exports_dir / f"{stem}.{ext}").resolve()
        root = self.exports_dir.resolve()
        if root not in out.parents:
            raise ValueError("export path escapes the exports directory")
        return out

    # ------------------------------------------------------------------ 1. XLSX (SPEC-10 §4.1)
    def export_xlsx(
        self,
        columns: Optional[List[str]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
        filename: str = "yukti_data.xlsx",
        sheet_name: Optional[str] = None,
        *,
        contract: Optional[Dict[str, Any]] = None,
        persona: str = "CMD",
        masked: bool = False,
        is_aggregate: bool = False,
    ) -> Path:
        """Exports a statement, DCF workbook, or tabular dataset to a formatted `.xlsx` workbook per SPEC-10 §4.1."""
        out_path = self.safe_path(filename, "xlsx")
        wb = openpyxl.Workbook()

        c = contract or {}
        vis = c.get("visual") if isinstance(c.get("visual"), dict) else {}
        stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
        tbl_spec = vis.get("table") if isinstance(vis.get("table"), dict) else None

        doc_title, as_of, source, basis = _extract_meta_tuple(c, persona=persona, masked=masked)
        if sheet_name and not contract:
            doc_title = sheet_name

        # Workbook properties (SPEC-10 §4.1 Metadata)
        wb.properties.title = doc_title
        wb.properties.creator = "Yukti"
        wb.properties.subject = str(c.get("user_query") or doc_title)
        wb.properties.keywords = f"persona={persona}; masked={str(bool(masked)).lower()}"

        # DCF multi-sheet workbook branch
        if c.get("dcf_workbook"):
            _build_dcf_sheets(wb, c, persona=persona, masked=masked)
            if c.get("definition_id") or c.get("definition_meta"):
                _add_definition_sheet(wb, c)
            wb.save(str(out_path))
            return out_path

        ws = wb.active
        raw_sheet_name = sheet_name or vis.get("title") or (stmt.get("title") if stmt else None) or "ONGC_Data"
        ws.title = _clean_sheet_title(raw_sheet_name, default="ONGC_Data")

        # Title block (SPEC-10 §4.1: Row 1 title bold 14, Row 2 As of / Source / Basis, Row 3 blank/banner, Header Row 4)
        ws["A1"] = doc_title
        ws["A1"].font = Font(bold=True, size=14)
        meta_str = f"As of {as_of} · Source: {source} · Basis: {basis}"
        if is_aggregate:
            meta_str += f" · Aggregate view (access level: {persona})"
        ws["A2"] = meta_str
        ws["A2"].font = Font(size=10, color="4B5563")
        if is_aggregate:
            ws["A3"] = f"Aggregate view (access level: {persona})"
            ws["A3"].font = Font(bold=True, size=10, color="7C2D12")

        hdr_fill = PatternFill("solid", fgColor="F3F4F6")
        hdr_border = Border(bottom=Side(style="thin", color="374151"))
        subtotal_border = Border(
            top=Side(style="thin", color="374151"),
            bottom=Side(style="thin", color="374151"),
        )
        total_border = Border(
            top=Side(style="thin", color="111827"),
            bottom=Side(style="double", color="111827"),
        )

        # Statement layout branch (SPEC-10 §4.1 Statements)
        if stmt:
            periods = list(stmt.get("periods") or [])
            unit = str(stmt.get("unit") or "INR_crore")
            headers = ["Line Item (₹ Crore)" if "crore" in unit.lower() else f"Line Item ({unit})"] + periods
            for c_idx, h_text in enumerate(headers, start=1):
                cell = ws.cell(row=4, column=c_idx, value=h_text)
                cell.font = Font(bold=True, color="111827")
                cell.fill = hdr_fill
                cell.border = hdr_border
                if c_idx > 1:
                    cell.alignment = Alignment(horizontal="right", vertical="center")

            ws.freeze_panes = "A5"
            ws.auto_filter.ref = None  # No autofilter on statements per SPEC-10 §4.1

            cur_row = 5
            seen_docs: List[str] = []
            for sec in (stmt.get("sections") or []):
                for r in (sec.get("rows") or []):
                    label = str(r.get("label") or "")
                    level = int(r.get("level") or 0)
                    kind = str(r.get("kind") or "line").lower()
                    vals = r.get("values") or {}

                    c_label = ws.cell(row=cur_row, column=1, value=label)
                    c_label.alignment = Alignment(indent=level, vertical="center")

                    is_sub = kind == "subtotal" or "profit before tax" in label.lower() or label.lower().startswith("total ")
                    is_tot = kind == "total" or "profit after tax" in label.lower()

                    if is_tot:
                        c_label.font = Font(bold=True)
                        c_label.border = total_border
                    elif is_sub:
                        c_label.font = Font(bold=True)
                        c_label.border = subtotal_border

                    for p_idx, p in enumerate(periods, start=2):
                        v = vals.get(p)
                        c_val = ws.cell(row=cur_row, column=p_idx, value=v)
                        c_val.number_format = "#,##0;(#,##0)"
                        c_val.alignment = Alignment(horizontal="right", vertical="center")
                        if is_tot:
                            c_val.font = Font(bold=True)
                            c_val.border = total_border
                        elif is_sub:
                            c_val.font = Font(bold=True)
                            c_val.border = subtotal_border

                    src = r.get("source") if isinstance(r.get("source"), dict) else {}
                    if src.get("doc"):
                        d_str = str(src["doc"])
                        if src.get("page") is not None:
                            d_str += f" (p. {src['page']})"
                        if d_str not in seen_docs:
                            seen_docs.append(d_str)
                    cur_row += 1

            last_stmt_row = cur_row - 1
            # Footnote rows with source doc + pages and totals_check
            cur_row += 1
            if seen_docs:
                fn_cell = ws.cell(row=cur_row, column=1, value="Source: " + "; ".join(seen_docs))
                fn_cell.font = Font(italic=True, size=9, color="4B5563")
                cur_row += 1
            tc = stmt.get("totals_check") if isinstance(stmt.get("totals_check"), dict) else None
            if tc:
                tc_status = "Passed" if tc.get("passed") else "Failed"
                tc_cell = ws.cell(
                    row=cur_row,
                    column=1,
                    value=f"Totals Check ({tc.get('identity', '')}): {tc_status} (delta ₹{tc.get('delta_crore', 0):.2f} Cr)",
                )
                tc_cell.font = Font(italic=True, size=9, color="4B5563")

            _auto_fit_columns(ws, header_row=4, max_row=last_stmt_row)
            if c.get("definition_id") or c.get("definition_meta"):
                _add_definition_sheet(wb, c)
            wb.save(str(out_path))
            return out_path

        # Standard table branch (SPEC-10 §4.1)
        eff_cols = list(columns if columns is not None else (tbl_spec.get("columns") if tbl_spec else []) or [])
        eff_rows = list(rows if rows is not None else (tbl_spec.get("rows") if tbl_spec else []) or [])
        headers_map = (tbl_spec.get("headers") if tbl_spec and isinstance(tbl_spec.get("headers"), dict) else {}) or {}

        if not eff_cols and eff_rows and isinstance(eff_rows[0], dict):
            eff_cols = list(eff_rows[0].keys())

        for c_idx, col_key in enumerate(eff_cols, start=1):
            hdr_label = str(headers_map.get(col_key) or col_key)
            cell = ws.cell(row=4, column=c_idx, value=hdr_label)
            cell.font = Font(bold=True, color="111827")
            cell.fill = hdr_fill
            cell.border = hdr_border

        ws.freeze_panes = "A5"

        cur_row = 5
        for r in eff_rows:
            for c_idx, col_key in enumerate(eff_cols, start=1):
                val = r.get(col_key, "") if isinstance(r, dict) else ""
                # Masked cells stay as masked display text (e.g. "<5")
                if isinstance(val, str):
                    cell = ws.cell(row=cur_row, column=c_idx, value=val)
                    cell.number_format = "@"
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    ck_low = col_key.lower()
                    write_val = val
                    if ("pct" in ck_low or "percent" in ck_low or "margin" in ck_low) and abs(float(val)) > 1.0:
                        # Convert e.g. 28.9 -> 0.289 when formatted as 0.0%
                        write_val = round(float(val) / 100.0, 6)
                    cell = ws.cell(row=cur_row, column=c_idx, value=write_val)
                    cell.number_format = _number_format_for_column(col_key, val)
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    ws.cell(row=cur_row, column=c_idx, value="" if val is None else val)
            cur_row += 1

        last_data_row = max(4, cur_row - 1)
        if eff_cols and last_data_row >= 4:
            last_col_letter = get_column_letter(len(eff_cols))
            ws.auto_filter.ref = f"A4:{last_col_letter}{last_data_row}"

        _auto_fit_columns(ws, header_row=4, max_row=last_data_row)

        if c.get("definition_id") or c.get("definition_meta"):
            _add_definition_sheet(wb, c)

        wb.save(str(out_path))
        return out_path

    # ------------------------------------------------------------------ 2. CSV (SPEC-10 §4.2)
    def export_csv(
        self,
        columns: Optional[List[str]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
        filename: str = "yukti_data.csv",
        *,
        contract: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Exports table or flattened statement to UTF-8 with BOM (`utf-8-sig`) CSV per SPEC-10 §4.2.
        Multi-table answers (`visual.compare.items` with >=2 tables) produce a `.zip` of CSVs.
        """
        c = contract or {}
        vis = c.get("visual") if isinstance(c.get("visual"), dict) else {}
        stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
        tbl_spec = vis.get("table") if isinstance(vis.get("table"), dict) else None
        comp_items = ((vis.get("compare") or {}).get("items") or []) if isinstance(vis.get("compare"), dict) else []

        # Multi-table answers -> zip of UTF-8 BOM CSVs
        if len(comp_items) >= 2 and filename.lower().endswith(".zip"):
            out_zip = self.safe_path(filename, "zip")
            with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for idx, item in enumerate(comp_items, start=1):
                    if not isinstance(item, dict):
                        continue
                    cols_i = list(item.get("columns") or [])
                    rows_i = list(item.get("rows") or [])
                    csv_bytes = self._serialize_table_csv_bytes(cols_i, rows_i, item.get("headers") or {})
                    zf.writestr(f"table_{idx}.csv", csv_bytes)
            return out_zip

        out_path = self.safe_path(filename, "csv")

        # Statement flattening with `level` and `kind` columns (SPEC-10 §4.2)
        if stmt:
            periods = list(stmt.get("periods") or [])
            show_yoy = bool(stmt.get("show_yoy"))
            hdr_row = ["line_code", "label", "level", "kind"] + periods + (["yoy_pct (%)"] if show_yoy else [])
            buf = io.StringIO()
            writer = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(hdr_row)
            for sec in (stmt.get("sections") or []):
                for r in (sec.get("rows") or []):
                    vals = r.get("values") or {}
                    row_out: List[Any] = [
                        r.get("line_code") or "",
                        r.get("label") or "",
                        int(r.get("level") or 0),
                        r.get("kind") or "line",
                    ]
                    for p in periods:
                        v = vals.get(p)
                        row_out.append("" if v is None else v)
                    if show_yoy:
                        yoy = r.get("yoy_pct")
                        row_out.append("" if yoy is None else yoy)
                    writer.writerow(row_out)
            out_path.write_bytes(buf.getvalue().encode("utf-8-sig"))
            return out_path

        eff_cols = list(columns if columns is not None else (tbl_spec.get("columns") if tbl_spec else []) or [])
        eff_rows = list(rows if rows is not None else (tbl_spec.get("rows") if tbl_spec else []) or [])
        headers_map = (tbl_spec.get("headers") if tbl_spec and isinstance(tbl_spec.get("headers"), dict) else {}) or {}

        csv_bytes = self._serialize_table_csv_bytes(eff_cols, eff_rows, headers_map)
        out_path.write_bytes(csv_bytes)
        return out_path

    def _serialize_table_csv_bytes(
        self,
        columns: List[str],
        rows: List[Dict[str, Any]],
        headers_map: Dict[str, str],
    ) -> bytes:
        if not columns and rows and isinstance(rows[0], dict):
            columns = list(rows[0].keys())
        display_headers: List[str] = []
        for col in columns:
            h = str(headers_map.get(col) or col)
            ck = col.lower()
            if ("pct" in ck or "percent" in ck or "margin" in ck) and "(%)" not in h and "%" not in h:
                h = f"{h} (%)"
            display_headers.append(h)

        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(display_headers)
        for r in rows:
            row_vals: List[Any] = []
            for col in columns:
                v = r.get(col, "") if isinstance(r, dict) else ""
                row_vals.append("" if v is None else v)
            writer.writerow(row_vals)
        return buf.getvalue().encode("utf-8-sig")

    # ------------------------------------------------------------------ 3. PDF (SPEC-10 §4.3)
    def export_pdf(
        self,
        markdown_text: str = "",
        filename: str = "yukti_doc.pdf",
        *,
        contract: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        columns: Optional[List[str]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
        chart_png: Optional[str] = None,
        persona: str = "CMD",
        masked: bool = False,
        is_aggregate: bool = False,
    ) -> Path:
        """Exports contract or markdown text into a formatted PDF via WeasyPrint + embedded Noto fonts."""
        out_path = self.safe_path(filename, "pdf")
        return render_pdf_to_path(
            out_path=out_path,
            contract=contract,
            title=title,
            markdown_text=markdown_text,
            columns=columns,
            rows=rows,
            chart_png=chart_png,
            persona=persona,
            masked=masked,
            is_aggregate=is_aggregate,
        )

    # ------------------------------------------------------------------ 4. DOCX (SPEC-10 §4.5)
    @staticmethod
    def _shade_docx_cell(cell: Any, fill_hex: str = "F3F4F6") -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill_hex)
        tc_pr.append(shd)

    def export_word(
        self,
        markdown_text: str = "",
        filename: str = "yukti_draft.docx",
        *,
        contract: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        columns: Optional[List[str]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
        chart_png: Optional[str] = None,
        email_draft: Optional[Dict[str, Any]] = None,
        persona: str = "CMD",
        masked: bool = False,
        is_aggregate: bool = False,
    ) -> Path:
        """Exports contract, email draft letter, or markdown into an executive `.docx` document per SPEC-10 §4.5."""
        out_path = self.safe_path(filename, "docx")
        doc = docx.Document()

        c = contract or {}
        vis = c.get("visual") if isinstance(c.get("visual"), dict) else {}
        stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
        tbl_spec = vis.get("table") if isinstance(vis.get("table"), dict) else None
        edraft = email_draft or (c.get("email_draft") if isinstance(c.get("email_draft"), dict) else None)

        doc_title, as_of, source, basis = _extract_meta_tuple(c, persona=persona, masked=masked)
        if title:
            doc_title = title

        # Email draft letter mode (SPEC-10 §4.5)
        if edraft and isinstance(edraft, dict):
            doc.add_heading("ONGC Executive Correspondence (Draft)", level=1)
            from_info = edraft.get("from") or {}
            from_str = (
                f"{from_info.get('name', persona)} <{from_info.get('email', 'noreply@ongc.example')}>"
                if isinstance(from_info, dict)
                else str(from_info or persona)
            )
            to_list = edraft.get("to") or []
            to_str = ", ".join(
                f"{t.get('name', '')} <{t.get('email', '')}>".strip() if isinstance(t, dict) else str(t)
                for t in to_list
            )
            cc_list = edraft.get("cc") or []
            cc_str = ", ".join(
                f"{t.get('name', '')} <{t.get('email', '')}>".strip() if isinstance(t, dict) else str(t)
                for t in cc_list
            )
            subj_str = str(edraft.get("subject") or doc_title)

            hdr_para = doc.add_paragraph()
            for lbl, val in [("From: ", from_str), ("To: ", to_str), ("CC: ", cc_str or "—"), ("Subject: ", subj_str)]:
                r_lbl = hdr_para.add_run(lbl)
                r_lbl.bold = True
                hdr_para.add_run(f"{val}\n")

            body_md = str(edraft.get("body_md") or markdown_text or "")
            self._append_markdown_to_docx(doc, body_md)
            doc.save(str(out_path))
            return out_path

        # Title + meta line + KPI summary sentence
        doc.add_heading(doc_title, level=1)
        meta_p = doc.add_paragraph(
            f"As of {as_of} · Source: {source} · Basis: {basis} · Persona: {persona} · Masked: {'Yes' if masked else 'No'}"
        )
        if meta_p.runs:
            meta_p.runs[0].font.size = Pt(9)
            meta_p.runs[0].font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

        if is_aggregate:
            agg_p = doc.add_paragraph()
            agg_run = agg_p.add_run(f"Aggregate view (access level: {persona})")
            agg_run.bold = True

        kpis = list(vis.get("kpis") or [])
        if kpis:
            kpi_parts = [f"{k.get('label', '')}: {k.get('value', '')}" for k in kpis[:3] if isinstance(k, dict)]
            if kpi_parts:
                doc.add_paragraph("Key Highlights — " + " | ".join(kpi_parts))

        if c.get("display_text"):
            doc.add_paragraph(str(c["display_text"]))

        # Chart PNG if provided
        clean_data_url = _sanitize_chart_png(chart_png)
        if clean_data_url:
            b64_part = clean_data_url.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_part)
            doc.add_picture(io.BytesIO(img_bytes), width=Inches(5.8))

        # Statement table in docx
        if stmt:
            periods = list(stmt.get("periods") or [])
            headers = ["Line Item (₹ Crore)"] + periods
            all_stmt_rows: List[Dict[str, Any]] = []
            for sec in (stmt.get("sections") or []):
                all_stmt_rows.extend(sec.get("rows") or [])

            tbl = doc.add_table(rows=1 + len(all_stmt_rows), cols=len(headers))
            tbl.style = "Table Grid"
            for c_idx, h_text in enumerate(headers):
                cell = tbl.cell(0, c_idx)
                cell.text = h_text
                self._shade_docx_cell(cell, "F3F4F6")
                for run in cell.paragraphs[0].runs:
                    run.bold = True

            for r_idx, r in enumerate(all_stmt_rows, start=1):
                label = str(r.get("label") or "")
                level = int(r.get("level") or 0)
                kind = str(r.get("kind") or "line").lower()
                is_bold = kind in ("subtotal", "total") or "profit before tax" in label.lower() or "profit after tax" in label.lower()

                c0 = tbl.cell(r_idx, 0)
                c0.text = label
                c0.paragraphs[0].paragraph_format.left_indent = Pt(12 * level)
                if is_bold:
                    for run in c0.paragraphs[0].runs:
                        run.bold = True

                vals = r.get("values") or {}
                for p_idx, p in enumerate(periods, start=1):
                    c_p = tbl.cell(r_idx, p_idx)
                    c_p.text = _format_accounting_num(vals.get(p), decimals=2)
                    if is_bold:
                        for run in c_p.paragraphs[0].runs:
                            run.bold = True

        # Standard table in docx
        eff_cols = list(columns if columns is not None else (tbl_spec.get("columns") if tbl_spec else []) or [])
        eff_rows = list(rows if rows is not None else (tbl_spec.get("rows") if tbl_spec else []) or [])
        headers_map = (tbl_spec.get("headers") if tbl_spec and isinstance(tbl_spec.get("headers"), dict) else {}) or {}

        if eff_cols and eff_rows:
            tbl = doc.add_table(rows=1 + len(eff_rows), cols=len(eff_cols))
            tbl.style = "Table Grid"
            for c_idx, col_key in enumerate(eff_cols):
                cell = tbl.cell(0, c_idx)
                cell.text = str(headers_map.get(col_key) or col_key)
                self._shade_docx_cell(cell, "F3F4F6")
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            for r_idx, r in enumerate(eff_rows, start=1):
                for c_idx, col_key in enumerate(eff_cols):
                    v = r.get(col_key, "") if isinstance(r, dict) else ""
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        txt = _format_accounting_num(v, decimals=2 if isinstance(v, float) else 0)
                    else:
                        txt = "" if v is None else str(v)
                    tbl.cell(r_idx, c_idx).text = txt

        if markdown_text:
            self._append_markdown_to_docx(doc, markdown_text)

        doc.save(str(out_path))
        return out_path

    def _append_markdown_to_docx(self, doc: Any, markdown_text: str) -> None:
        table_buffer: List[List[str]] = []

        def flush_table() -> None:
            nonlocal table_buffer
            if not table_buffer:
                return
            num_cols = max(len(r) for r in table_buffer)
            if num_cols > 0:
                tbl = doc.add_table(rows=len(table_buffer), cols=num_cols)
                tbl.style = "Table Grid"
                for r_idx, row_vals in enumerate(table_buffer):
                    for c_idx, cell_val in enumerate(row_vals):
                        if c_idx < num_cols:
                            cell = tbl.cell(r_idx, c_idx)
                            cell.text = cell_val
                            if r_idx == 0:
                                self._shade_docx_cell(cell, "F3F4F6")
                                for run in cell.paragraphs[0].runs:
                                    run.bold = True
            table_buffer = []

        for line in markdown_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("|") and line_str.endswith("|"):
                cells = [c.strip() for c in line_str.strip("|").split("|")]
                if all(set(c) <= {"-", ":", " "} for c in cells):
                    continue
                table_buffer.append(cells)
                continue
            else:
                flush_table()

            if not line_str or line_str == "---":
                continue
            if line_str.startswith("# "):
                doc.add_heading(line_str[2:], level=1)
            elif line_str.startswith("## "):
                doc.add_heading(line_str[3:], level=2)
            elif line_str.startswith("### "):
                doc.add_heading(line_str[4:], level=3)
            elif line_str.startswith("- ") or line_str.startswith("* "):
                doc.add_paragraph(line_str[2:].replace("**", ""), style="List Bullet")
            else:
                doc.add_paragraph(line_str.replace("**", ""))

        flush_table()

    # ------------------------------------------------------------------ 5. EML (SPEC-10 §4.6)
    def export_eml(
        self,
        email_draft: Optional[Dict[str, Any]] = None,
        filename: str = "yukti_email_draft.eml",
        *,
        contract: Optional[Dict[str, Any]] = None,
        attachment_path: Optional[Path] = None,
        attachment_filename: Optional[str] = None,
        persona: str = "CMD",
        masked: bool = False,
        is_aggregate: bool = False,
    ) -> Path:
        """Builds an RFC 5322 `.eml` draft (`X-Unsent: 1`) with `text/plain` + `text/html` alternatives
        and a `.xlsx` attachment (SPEC-10 §4.6).
        """
        out_path = self.safe_path(filename, "eml")
        c = contract or {}
        edraft = email_draft or (c.get("email_draft") if isinstance(c.get("email_draft"), dict) else {}) or {}

        from_info = edraft.get("from") or {"name": f"ONGC {persona}", "email": f"{persona.lower()}@ongc.example"}
        from_hdr = (
            formataddr((str(from_info.get("name") or persona), str(from_info.get("email") or "noreply@ongc.example")))
            if isinstance(from_info, dict)
            else str(from_info)
        )
        to_list = edraft.get("to") or [{"name": "Director (HR)", "email": "director.hr@ongc.example"}]
        to_hdr = ", ".join(
            formataddr((str(t.get("name") or ""), str(t.get("email") or ""))) if isinstance(t, dict) else str(t)
            for t in to_list
        )
        cc_list = edraft.get("cc") or []
        cc_hdr = ", ".join(
            formataddr((str(t.get("name") or ""), str(t.get("email") or ""))) if isinstance(t, dict) else str(t)
            for t in cc_list
        )
        subject = str(
            edraft.get("subject")
            or (c.get("visual") or {}).get("title")
            or "ONGC Yukti AI Review Draft"
        )
        body_md = str(edraft.get("body_md") or c.get("display_text") or "Please find the requested cohort review attached.")

        msg = EmailMessage()
        msg["From"] = from_hdr
        msg["To"] = to_hdr
        if cc_hdr:
            msg["Cc"] = cc_hdr
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=False)
        msg["X-Unsent"] = "1"

        msg.set_content(body_md, subtype="plain", charset="utf-8")
        html_body = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"
            + "<div style='font-family: sans-serif; line-height: 1.5;'>"
            + "<br/>".join(line for line in body_md.splitlines())
            + "</div></body></html>"
        )
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

        # Ensure xlsx attachment exists
        xlsx_path = attachment_path
        if xlsx_path is None or not xlsx_path.exists():
            auto_xlsx_name = f"{out_path.stem}_attachment.xlsx"
            xlsx_path = self.export_xlsx(
                filename=auto_xlsx_name,
                contract=c,
                persona=persona,
                masked=masked,
                is_aggregate=is_aggregate,
            )
        att_name = attachment_filename or xlsx_path.name
        msg.add_attachment(
            xlsx_path.read_bytes(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=att_name,
        )

        out_path.write_bytes(bytes(msg))
        return out_path
