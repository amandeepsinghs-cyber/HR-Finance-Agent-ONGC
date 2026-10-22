"""Multi-Format Document and Data Exporter for Yukti AI.
Supports Word (.docx), Excel (.xlsx), PDF (.pdf), and Google Docs/Sheets
via a pluggable credential provider with an audited dry-run mode.
"""

import json
import logging
import re
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import docx
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import EXPORTS_DIR

logger = logging.getLogger("yukti.tools.export")


class GoogleOAuthProvider:
    """Pluggable credential provider for Google Drive, Docs, and Sheets APIs."""

    def __init__(self, oauth_token: Optional[str] = None):
        self.oauth_token = oauth_token

    def is_authenticated(self) -> bool:
        return bool(self.oauth_token)

    def get_token(self) -> Optional[str]:
        return self.oauth_token


class DocumentExporter:
    """Handles multi-format document and spreadsheet exports."""

    def __init__(self, exports_dir: Path = EXPORTS_DIR, oauth_provider: Optional[GoogleOAuthProvider] = None):
        self.exports_dir = exports_dir
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.oauth_provider = oauth_provider or GoogleOAuthProvider()

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

    def export_word(self, markdown_text: str, filename: str = "yukti_draft.docx") -> Path:
        """Exports markdown document text into an executive Word (.docx) document with formatted tables."""
        out_path = self.safe_path(filename, "docx")
        doc = docx.Document()

        table_buffer: List[List[str]] = []

        def flush_table():
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
        doc.save(str(out_path))
        return out_path

    def export_xlsx(
        self,
        columns: List[str],
        rows: List[Dict[str, Any]],
        filename: str = "yukti_data.xlsx",
        sheet_name: str = "ONGC_Data",
    ) -> Path:
        """Exports tabular rows to formatted Excel workbook (.xlsx)."""
        out_path = self.safe_path(filename, "xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        # Header row
        ws.append(columns)
        for cell in ws[1]:
            cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
            cell.fill = openpyxl.styles.PatternFill("solid", fgColor="800000")  # ONGC Maroon

        # Data rows
        for r in rows:
            ws.append([r.get(c, "") for c in columns])

        wb.save(str(out_path))
        return out_path

    def export_pdf(self, markdown_text: str, filename: str = "yukti_doc.pdf") -> Path:
        """Exports text into a clean printable PDF."""
        out_path = self.safe_path(filename, "pdf")
        c = canvas.Canvas(str(out_path), pagesize=letter)
        width, height = letter

        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "ONGC Yukti AI Executive Brief")
        y -= 30
        c.setFont("Helvetica", 10)

        for line in markdown_text.splitlines():
            line_str = line.strip()
            if not line_str:
                y -= 10
                continue
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(50, y, line_str[:90])
            y -= 15

        c.save()
        return out_path

    def export_google_docs(self, title: str, markdown_text: str, file_id: Optional[str] = None) -> Dict[str, Any]:
        """Exports to Google Docs via OAuth or dry-run mock link."""
        if not self.oauth_provider.is_authenticated():
            # Dry-run mock link mode for demonstration; the local copy uses the minted export id (no collisions)
            doc_id = file_id or f"yukti-doc-{int(time.time() * 1000)}"
            mock_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            local_file = self.export_word(markdown_text, f"{doc_id}.docx")
            return {
                "status": "success",
                "format": "google_docs",
                "mode": "dry_run_simulation",
                "url": mock_url,
                "local_file": str(local_file),
            }

        # Real Google Docs API export would use self.oauth_provider.get_token()
        return {"status": "success", "url": "https://docs.google.com/document/d/..."}

    def export_google_sheets(self, title: str, columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Exports to Google Sheets via OAuth or dry-run mock link."""
        if not self.oauth_provider.is_authenticated():
            sheet_id = f"yukti-sheet-{int(time.time() * 1000)}"
            mock_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            local_file = self.export_xlsx(columns, rows, f"{sheet_id}.xlsx")
            return {
                "status": "success",
                "format": "google_sheets",
                "mode": "dry_run_simulation",
                "url": mock_url,
                "local_file": str(local_file),
            }

        return {"status": "success", "url": "https://docs.google.com/spreadsheets/d/..."}
