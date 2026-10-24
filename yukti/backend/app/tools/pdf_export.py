"""Server-side HTML → PDF exporter using Jinja2 + WeasyPrint with bundled Noto fonts (P4.6, SPEC-10 §4.3, BUG-24).

Uses Pango/HarfBuzz via WeasyPrint so Devanagari conjuncts/matras and the Indian Rupee symbol (₹) shape
and embed cleanly (`pdffonts` shows `NotoSans` and `NotoSansDevanagari` embedded; `pdftotext` has 0 `■`).
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import jinja2
import weasyprint

logger = logging.getLogger("yukti.tools.pdf_export")

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BACKEND_ROOT / "app" / "templates" / "export"
FONTS_DIR = BACKEND_ROOT / "assets" / "fonts"

MAX_CHART_PNG_BYTES = 4 * 1024 * 1024  # 4 MB cap per SPEC-10 §3


def _format_accounting_num(val: Any, decimals: int = 2) -> str:
    if val is None or val == "":
        return "—"
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, (int, float)):
        num = float(val)
        neg = num < 0
        abs_v = abs(num)
        if decimals == 0 or (abs_v >= 100 and abs(abs_v - round(abs_v)) < 1e-6):
            s = f"{abs_v:,.0f}"
        else:
            s = f"{abs_v:,.{decimals}f}"
        return f"({s})" if neg else s
    return str(val)


def _format_table_cell(col_key: str, val: Any) -> Tuple[str, bool]:
    """Returns `(formatted_text, is_numeric)` for a generic table cell."""
    if val is None or val == "":
        return "—", False
    if isinstance(val, str):
        # Masked cell like "<5" stays as "<5", right-aligned if count column
        if val.startswith("<") and val[1:].isdigit():
            return val, True
        return val, False
    if isinstance(val, bool):
        return str(val), False
    if isinstance(val, (int, float)):
        ck = (col_key or "").lower()
        if "pct" in ck or "percent" in ck or "margin" in ck or "share" in ck:
            return f"{float(val):.1f}%", True
        if "year" in ck or "tenure" in ck or "yrs" in ck or "service" in ck or "retirement" in ck:
            if isinstance(val, int) and val > 1900:
                return str(val), False
            return f"{float(val):.1f}", True
        if "count" in ck or "headcount" in ck or "executives" in ck or "employees" in ck:
            return f"{int(round(float(val))):,}", True
        if "inr" in ck or "rev" in ck or "pat" in ck or "pbt" in ck or "ebitda" in ck or "capex" in ck or "amount" in ck:
            return f"₹{_format_accounting_num(val, decimals=2)}", True
        if isinstance(val, int):
            return f"{val:,}", True
        return f"{float(val):,.2f}", True
    return str(val), False


def _sanitize_chart_png(chart_png: Optional[str]) -> Optional[str]:
    """Validates a `data:image/png;base64,...` or raw base64 PNG string (max 4 MB)."""
    if not chart_png or not isinstance(chart_png, str):
        return None
    raw = chart_png.strip()
    if raw.startswith("data:image/"):
        parts = raw.split(",", 1)
        if len(parts) != 2:
            return None
        header, b64_part = parts[0], parts[1]
        if "base64" not in header:
            return None
    else:
        b64_part = raw
    try:
        decoded = base64.b64decode(b64_part, validate=False)
    except Exception:
        return None
    if not decoded or len(decoded) > MAX_CHART_PNG_BYTES:
        return None
    # Verify PNG magic header (\x89PNG\r\n\x1a\n)
    if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    clean_b64 = base64.b64encode(decoded).decode("ascii")
    return f"data:image/png;base64,{clean_b64}"


def _parse_markdown_tables_and_paragraphs(markdown_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extracts markdown pipe tables and plain paragraphs for legacy markdown PDF calls."""
    tables: List[Dict[str, Any]] = []
    paragraphs: List[str] = []
    buf: List[List[str]] = []

    def flush_buf() -> None:
        nonlocal buf
        if not buf:
            return
        headers = buf[0]
        data_rows = buf[1:]
        cols = [{"key": h, "header": h, "is_num": False} for h in headers]
        formatted_rows = []
        for r in data_rows:
            row_cells = []
            for idx, h in enumerate(headers):
                v = r[idx] if idx < len(r) else ""
                row_cells.append({"text": v, "is_num": False})
            formatted_rows.append(row_cells)
        tables.append({"title": None, "columns": cols, "rows": formatted_rows})
        buf = []

    for line in (markdown_text or "").splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= {"-", ":", " "} for c in cells):
                continue
            buf.append(cells)
            continue
        flush_buf()
        if not s or s == "---":
            continue
        clean = re.sub(r"^#+\s*", "", s).replace("**", "")
        paragraphs.append(clean)
    flush_buf()
    return tables, paragraphs


def build_pdf_context(
    contract: Optional[Dict[str, Any]] = None,
    *,
    title: Optional[str] = None,
    markdown_text: Optional[str] = None,
    columns: Optional[List[str]] = None,
    rows: Optional[List[Dict[str, Any]]] = None,
    chart_png: Optional[str] = None,
    persona: str = "CMD",
    masked: bool = False,
    is_aggregate: bool = False,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """Builds the template context dictionary for `report.html.j2`."""
    c = contract or {}
    vis = c.get("visual") if isinstance(c.get("visual"), dict) else {}
    stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
    tbl_spec = vis.get("table") if isinstance(vis.get("table"), dict) else None
    qspec = c.get("query_spec") if isinstance(c.get("query_spec"), dict) else {}

    lang = str(c.get("language") or "en")
    doc_title = title or vis.get("title") or (stmt.get("title") if stmt else None) or "ONGC Yukti AI Report (₹)"
    doc_subtitle = vis.get("subtitle") or ""

    # Meta line fields
    as_of = str(qspec.get("as_of") or "2026-10-19")
    source_label = "ONGC Enterprise SSOT"
    basis = "verified"
    is_synthetic = False

    if stmt and isinstance(stmt.get("source"), dict):
        st_src = stmt["source"]
        source_label = str(st_src.get("primary") or source_label)
        basis = str(st_src.get("basis") or "standalone")
        if not st_src.get("verified", True) or "synthetic" in source_label.lower() or "synthetic" in basis.lower():
            is_synthetic = True
    elif c.get("sources"):
        srcs = c.get("sources") or []
        if srcs and isinstance(srcs[0], dict):
            source_label = str(srcs[0].get("title") or srcs[0].get("object") or source_label)
            if srcs[0].get("as_of"):
                as_of = str(srcs[0]["as_of"])
            if "synthetic" in source_label.lower() or "illustrative" in source_label.lower():
                is_synthetic = True
                basis = "synthetic (Illustrative)"

    if c.get("definition_meta") and isinstance(c["definition_meta"], dict):
        dm = c["definition_meta"]
        if dm.get("as_of"):
            as_of = str(dm["as_of"])
        if dm.get("basis"):
            basis = str(dm["basis"])
        if "synthetic" in basis.lower() or "illustrative" in basis.lower():
            is_synthetic = True

    kpis = list(vis.get("kpis") or [])[:3]
    display_text = str(c.get("display_text") or "")

    chart_data_url = _sanitize_chart_png(chart_png)
    has_chart_visual = bool(vis.get("chart") or vis.get("type") == "chart")
    chart_missing_note = has_chart_visual and not chart_data_url

    statement_table: Optional[Dict[str, Any]] = None
    tables: List[Dict[str, Any]] = []
    footnotes: List[str] = []
    num_col_count = 0

    if stmt:
        periods = list(stmt.get("periods") or [])
        num_col_count = max(num_col_count, len(periods) + (1 if stmt.get("show_yoy") else 0))
        unit = str(stmt.get("unit") or "INR_crore")
        unit_label = "₹ Crore" if "crore" in unit.lower() or "inr" in unit.lower() else unit
        flat_rows = []
        seen_docs = set()
        for sec in (stmt.get("sections") or []):
            sec_label = sec.get("label")
            if sec_label:
                flat_rows.append({
                    "kind": "section",
                    "level": 0,
                    "label": sec_label,
                    "period_cells": ["" for _ in periods],
                    "yoy_cell": "",
                    "note_ref": "",
                })
            for r in (sec.get("rows") or []):
                vals = r.get("values") or {}
                p_cells = [_format_accounting_num(vals.get(p), decimals=2) for p in periods]
                yoy = r.get("yoy_pct")
                yoy_str = f"{float(yoy):+.1f}%" if isinstance(yoy, (int, float)) else "—"
                src = r.get("source") if isinstance(r.get("source"), dict) else {}
                if src.get("doc"):
                    doc_str = str(src["doc"])
                    if src.get("page"):
                        doc_str += f" (p. {src['page']})"
                    seen_docs.add(doc_str)
                flat_rows.append({
                    "kind": str(r.get("kind") or "line"),
                    "level": min(max(int(r.get("level") or 0), 0), 3),
                    "label": str(r.get("label") or ""),
                    "period_cells": p_cells,
                    "yoy_cell": yoy_str,
                    "note_ref": str(r.get("note_ref") or ""),
                })
        statement_table = {
            "unit_label": unit_label,
            "periods": periods,
            "show_yoy": bool(stmt.get("show_yoy")),
            "rows": flat_rows,
        }
        if seen_docs:
            footnotes.append("Source documents: " + "; ".join(sorted(seen_docs)))
        tc = stmt.get("totals_check") if isinstance(stmt.get("totals_check"), dict) else None
        if tc:
            status_str = "Passed" if tc.get("passed") else "Failed"
            footnotes.append(f"Totals check ({tc.get('identity', 'Identity')}): {status_str} (delta: ₹{tc.get('delta_crore', 0):.2f} Cr)")

    # Standard visual.table or explicit columns/rows
    eff_cols = list(columns if columns is not None else (tbl_spec.get("columns") if tbl_spec else []) or [])
    eff_rows = list(rows if rows is not None else (tbl_spec.get("rows") if tbl_spec else []) or [])
    headers_map = (tbl_spec.get("headers") if tbl_spec and isinstance(tbl_spec.get("headers"), dict) else {}) or {}

    if eff_cols and eff_rows:
        col_defs = []
        for col in eff_cols:
            # Determine if column is numeric from first non-empty row
            is_num = False
            for r in eff_rows:
                v = r.get(col) if isinstance(r, dict) else None
                if v is not None and v != "":
                    _, is_num = _format_table_cell(col, v)
                    break
            if is_num:
                num_col_count += 1
            col_defs.append({
                "key": col,
                "header": str(headers_map.get(col) or col),
                "is_num": is_num,
            })
        formatted_rows = []
        for r in eff_rows:
            row_cells = []
            for cd in col_defs:
                k = cd["key"]
                raw_v = r.get(k) if isinstance(r, dict) else ""
                txt, cell_num = _format_table_cell(k, raw_v)
                row_cells.append({"text": txt, "is_num": cd["is_num"] or cell_num})
            formatted_rows.append(row_cells)
        tables.append({"title": None, "columns": col_defs, "rows": formatted_rows})

    markdown_paragraphs: List[str] = []
    if markdown_text:
        md_tables, md_paras = _parse_markdown_tables_and_paragraphs(markdown_text)
        tables.extend(md_tables)
        markdown_paragraphs.extend(md_paras)

    if c.get("definition_meta") and isinstance(c["definition_meta"], dict):
        dm = c["definition_meta"]
        if dm.get("rule_text"):
            footnotes.append(f"Definition ({dm.get('definition_id', 'Rule')}): {dm['rule_text']}")
        for cit in (dm.get("citations") or []):
            if isinstance(cit, dict) and cit.get("label"):
                footnotes.append(f"Citation [{cit.get('id', '')}]: {cit['label']}")

    ts_str = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now_ts if now_ts is not None else time.time()))
    illustrative_tag = " · Illustrative (synthetic data)" if is_synthetic else ""
    footer_text = f"Generated by Yukti (युक्ति) on {ts_str}{illustrative_tag}"

    css_path = TEMPLATES_DIR / "report.css"
    css_text = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    return {
        "language": lang,
        "title": doc_title,
        "subtitle": doc_subtitle,
        "as_of": as_of,
        "source_label": source_label,
        "basis": basis,
        "persona": (persona or "CMD").upper(),
        "masked": bool(masked),
        "is_aggregate": bool(is_aggregate),
        "kpis": kpis,
        "display_text": display_text,
        "chart_data_url": chart_data_url,
        "chart_missing_note": chart_missing_note,
        "statement_table": statement_table,
        "tables": tables,
        "markdown_paragraphs": markdown_paragraphs,
        "footnotes": footnotes,
        "footer_text": footer_text,
        "landscape": num_col_count > 6,
        "fonts_dir_uri": FONTS_DIR.resolve().as_uri(),
        "css_text": css_text,
    }


class _SafeWeasyPrintURLFetcher(weasyprint.urls.URLFetcher):
    """S5: Restricts WeasyPrint resource fetching to `data:image/png;base64,...` and bundled font files under `FONTS_DIR`."""

    def __init__(self) -> None:
        super().__init__(allowed_protocols={"data", "file"}, allow_redirects=False)
        self._fonts_root = FONTS_DIR.resolve()

    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> Any:
        from urllib.parse import unquote, urlparse

        u = str(url or "").strip()
        if u.startswith("data:image/png;base64,"):
            return super().fetch(u, headers=headers)
        if u.startswith("file://"):
            parsed = urlparse(u)
            target_path = Path(unquote(parsed.path)).resolve()
            if self._fonts_root in target_path.parents or target_path == self._fonts_root:
                return super().fetch(u, headers=headers)
        raise ValueError(f"Blocked external or non-font URL in PDF renderer: {u[:80]}")


_SAFE_URL_FETCHER = _SafeWeasyPrintURLFetcher()


def render_pdf_to_path(
    out_path: Path,
    contract: Optional[Dict[str, Any]] = None,
    *,
    title: Optional[str] = None,
    markdown_text: Optional[str] = None,
    columns: Optional[List[str]] = None,
    rows: Optional[List[Dict[str, Any]]] = None,
    chart_png: Optional[str] = None,
    persona: str = "CMD",
    masked: bool = False,
    is_aggregate: bool = False,
    now_ts: Optional[float] = None,
) -> Path:
    """Renders the Jinja2 HTML report template and compiles it to `out_path` via WeasyPrint."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
    )
    template = env.get_template("report.html.j2")
    ctx = build_pdf_context(
        contract=contract,
        title=title,
        markdown_text=markdown_text,
        columns=columns,
        rows=rows,
        chart_png=chart_png,
        persona=persona,
        masked=masked,
        is_aggregate=is_aggregate,
        now_ts=now_ts,
    )
    html_str = template.render(**ctx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    weasyprint.HTML(
        string=html_str,
        base_url=str(BACKEND_ROOT),
        url_fetcher=_SAFE_URL_FETCHER,
    ).write_pdf(str(out_path))
    return out_path
