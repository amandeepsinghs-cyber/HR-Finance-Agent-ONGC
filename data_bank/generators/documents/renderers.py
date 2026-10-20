"""Renderers for ONGC internal rulebook reconstructions.

Produces:
1. Native DOCX files using python-docx
2. Native PDF files using ReportLab (with running headers, footers, and diagonal watermarks)
3. Scanned image-only PDFs (no text layer, slight rotation/contrast jitter) using pdf2image and PIL
"""

import io
import math
import random
import re
import zipfile
from pathlib import Path
from typing import List

import reportlab.rl_config
reportlab.rl_config.invariant = 1

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_path
import pypdf

import reportlab
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from generators.documents.rulebook_models import Rulebook


class NumberedWatermarkCanvas(canvas.Canvas):
    """Canvas that computes total pages and prints running headers, footers, and diagonal watermarks on every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int):
        self.saveState()

        # 1. Translucent Diagonal Watermark across the center
        self.saveState()
        self.setFont("Helvetica-Bold", 34)
        # Light grey color
        self.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.35))
        self.translate(306, 396)
        self.rotate(45)
        self.drawCentredString(0, 15, "DEMO RECONSTRUCTION")
        self.setFont("Helvetica-Bold", 16)
        self.drawCentredString(0, -18, "NOT AN OFFICIAL ONGC DOCUMENT")
        self.restoreState()

        # 2. Running Header (on all pages except cover if desired, but we place watermark banner on all)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        self.drawString(45, 755, "OIL AND NATURAL GAS CORPORATION LIMITED — DEMO RECONSTRUCTION")
        self.drawRightString(567, 755, "INTERNAL CONTROLLED")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.6)
        self.line(45, 748, 567, 748)

        # 3. Running Footer
        self.line(45, 48, 567, 48)
        self.drawString(45, 34, "DEMO RECONSTRUCTION — not an official ONGC document")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(567, 34, page_str)

        self.restoreState()


def render_pdf(rulebook: Rulebook, out_path: Path) -> int:
    """Renders a Rulebook to a native PDF using ReportLab with professional ONGC styling."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom typography
    c_primary = colors.HexColor("#0B2545")    # Navy
    c_secondary = colors.HexColor("#134074")  # Deep blue
    c_accent = colors.HexColor("#8D0801")     # Crimson/Rust
    c_dark = colors.HexColor("#1D2D44")       # Dark Slate
    c_light = colors.HexColor("#EEF4F8")      # Light tint

    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=21, leading=26,
        textColor=c_primary, alignment=1, spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        "CoverSubTitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=12, leading=16,
        textColor=c_secondary, alignment=1, spaceAfter=20
    )
    banner_style = ParagraphStyle(
        "BannerText", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=9, leading=13,
        textColor=c_accent, alignment=1
    )
    h1_style = ParagraphStyle(
        "ChapH1", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=15, leading=19,
        textColor=c_primary, spaceBefore=16, spaceAfter=8,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        "ClauseH2", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=11, leading=15,
        textColor=c_secondary, spaceBefore=12, spaceAfter=5,
        keepWithNext=True
    )
    h3_style = ParagraphStyle(
        "SubclauseH3", parent=styles["Heading3"],
        fontName="Helvetica-Bold", fontSize=9.5, leading=13,
        textColor=c_dark, spaceBefore=6, spaceAfter=3,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        "RuleBody", parent=styles["BodyText"],
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=colors.HexColor("#2D3748"), spaceAfter=6
    )
    quote_style = ParagraphStyle(
        "QuoteBox", parent=styles["Italic"],
        fontName="Helvetica-Oblique", fontSize=8.5, leading=12,
        textColor=colors.HexColor("#4A5568"), spaceAfter=6
    )
    table_cell_style = ParagraphStyle(
        "TableCell", parent=styles["Normal"],
        fontName="Helvetica", fontSize=8, leading=11,
        textColor=colors.HexColor("#1A202C")
    )
    table_hdr_style = ParagraphStyle(
        "TableHdr", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=8.5, leading=11.5,
        textColor=colors.white
    )

    story = []

    # --- COVER PAGE ---
    story.append(Spacer(1, 20))
    story.append(Paragraph("OIL AND NATURAL GAS CORPORATION LIMITED", ParagraphStyle(
        "CorpHeader", fontName="Helvetica-Bold", fontSize=14, leading=18, alignment=1, textColor=c_primary
    )))
    story.append(Paragraph("Corporate Policy, Governance & Regulatory Affairs Directorate", ParagraphStyle(
        "CorpSub", fontName="Helvetica", fontSize=10, leading=14, alignment=1, textColor=colors.HexColor("#4A5568")
    )))
    story.append(Paragraph("Registered Office: Deendayal Urja Bhawan, 5, Nelson Mandela Marg, Vasant Kunj, New Delhi - 110070", ParagraphStyle(
        "CorpAddr", fontName="Helvetica", fontSize=8, leading=11, alignment=1, textColor=colors.HexColor("#718096")
    )))
    story.append(Spacer(1, 25))

    # Watermark Banner
    banner_data = [[
        Paragraph("<b>DEMO RECONSTRUCTION — NOT AN OFFICIAL ONGC DOCUMENT</b><br/>"
                  "<i>This document is a synthetic research reconstruction compiled from publicly available circulars, "
                  "court judgments, and statutory guidelines. It is prepared strictly for automated verification, "
                  "policy benchmarking, and question-answering evaluation.</i>", banner_style)
    ]]
    t_banner = Table(banner_data, colWidths=[522])
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFF5F5")),
        ('BOX', (0,0), (-1,-1), 1, c_accent),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 35))

    story.append(Paragraph(rulebook.title.upper(), title_style))
    story.append(Paragraph(f"<b>Controlled Document Identifier:</b> {rulebook.ref_code}", subtitle_style))
    story.append(Paragraph(f"<b>Effective Date:</b> {rulebook.effective_date}", subtitle_style))
    story.append(Spacer(1, 25))

    # Metadata Summary Table
    meta_rows = [
        [Paragraph("<b>Custodian Group</b>", table_cell_style), Paragraph(rulebook.issuer, table_cell_style)],
        [Paragraph("<b>Approving Authority</b>", table_cell_style), Paragraph(rulebook.approving_authority, table_cell_style)],
        [Paragraph("<b>Security Classification</b>", table_cell_style), Paragraph(rulebook.classification, table_cell_style)],
        [Paragraph("<b>Target Audience</b>", table_cell_style), Paragraph("All Regular Executives across Work Centres, Plants, Basins & Corporate Offices", table_cell_style)],
        [Paragraph("<b>Status / Verification</b>", table_cell_style), Paragraph("Demo Policy Reconstruction (Consistent with 78 public ONGC source documents)", table_cell_style)],
    ]
    t_meta = Table(meta_rows, colWidths=[160, 362])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), c_light),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(PageBreak())

    # --- AMENDMENT HISTORY & DOCUMENT CONTROL ---
    story.append(Paragraph("DOCUMENT CONTROL & RECORD OF REVISIONS", h1_style))
    story.append(Paragraph(
        "This official rulebook is maintained under strict version control by the designated Custodian Group. "
        "Any amendment or modification must be recommended by the Executive Committee and approved by the Board of Directors.",
        body_style
    ))
    story.append(Spacer(1, 8))

    amend_rows = [[
        Paragraph("<b>Revision No.</b>", table_hdr_style),
        Paragraph("<b>Effective Date</b>", table_hdr_style),
        Paragraph("<b>Approving Authority</b>", table_hdr_style),
        Paragraph("<b>Summary of Modifications / Addenda</b>", table_hdr_style)
    ]]
    for am in rulebook.amendment_history:
        amend_rows.append([
            Paragraph(f"<b>{am.revision_no}</b>", table_cell_style),
            Paragraph(am.date, table_cell_style),
            Paragraph(am.authority, table_cell_style),
            Paragraph(am.summary_of_changes, table_cell_style)
        ])
    t_amend = Table(amend_rows, colWidths=[65, 75, 110, 272])
    t_amend.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_amend)
    story.append(Spacer(1, 14))

    # --- TABLE OF CONTENTS SUMMARY ---
    story.append(Paragraph("ARRANGEMENT OF CHAPTERS & SCHEDULES", h1_style))
    toc_rows = [[Paragraph("<b>Chapter / Section</b>", table_hdr_style), Paragraph("<b>Title & Core Content Scope</b>", table_hdr_style)]]
    for ch in rulebook.chapters:
        clauses_summary = ", ".join(c.clause_ref for c in ch.clauses)
        toc_rows.append([
            Paragraph(f"<b>Chapter {ch.chapter_num}</b>", table_cell_style),
            Paragraph(f"<b>{ch.title}</b><br/><i>Encompassing: {clauses_summary}</i>", table_cell_style)
        ])
    for an in rulebook.annexures:
        toc_rows.append([
            Paragraph(f"<b>{an.annexure_id}</b>", table_cell_style),
            Paragraph(f"<b>{an.title}</b><br/><i>{an.description}</i>", table_cell_style)
        ])
    toc_rows.append([
        Paragraph("<b>Concordance</b>", table_cell_style),
        Paragraph("<b>Real Policy Registry Concordance</b> (Citations to public judgments & official circulars)", table_cell_style)
    ])
    t_toc = Table(toc_rows, colWidths=[120, 402])
    t_toc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # --- PREAMBLE & DEFINITIONS ---
    story.append(Paragraph("PREAMBLE & STATUTORY CONTEXT", h1_style))
    story.append(Paragraph(rulebook.preamble, body_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("INTERPRETATION & DEFINITIONS", h1_style))
    story.append(Paragraph(
        "In this rulebook, unless the context otherwise requires, the following terms and expressions shall have the meanings assigned to them:",
        body_style
    ))
    story.append(Spacer(1, 6))

    def_rows = [[Paragraph("<b>Defined Term</b>", table_hdr_style), Paragraph("<b>Official Definition & Interpretation</b>", table_hdr_style)]]
    for term, definition in rulebook.definitions.items():
        def_rows.append([
            Paragraph(f"<b>{term}</b>", table_cell_style),
            Paragraph(definition, table_cell_style)
        ])
    t_def = Table(def_rows, colWidths=[150, 372])
    t_def.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_def)
    story.append(PageBreak())

    # --- CHAPTERS & CLAUSES ---
    for ch in rulebook.chapters:
        story.append(Paragraph(f"CHAPTER {ch.chapter_num}: {ch.title.upper()}", h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=c_primary, spaceBefore=2, spaceAfter=10))

        for cl in ch.clauses:
            story.append(Paragraph(f"<b>{cl.clause_ref}: {cl.clause_title}</b>", h2_style))

            # Plain text paragraphs
            for line in cl.clause_text.split("\n"):
                clean_line = line.strip()
                if clean_line:
                    story.append(Paragraph(clean_line, body_style))

            # Subclauses breakdown
            if cl.subclauses:
                story.append(Spacer(1, 3))
                for sc in cl.subclauses:
                    story.append(Paragraph(f"<b>({sc.ref}) {sc.title}:</b> {sc.text}", h3_style))
                story.append(Spacer(1, 4))

            # Table within clause if present
            if cl.table_headers and cl.table_rows:
                story.append(Spacer(1, 4))
                t_rows = [[Paragraph(f"<b>{h}</b>", table_hdr_style) for h in cl.table_headers]]
                for r in cl.table_rows:
                    t_rows.append([Paragraph(str(cell), table_cell_style) for cell in r])
                # Distribute width evenly
                num_cols = len(cl.table_headers)
                col_w = 522.0 / num_cols
                t_cl = Table(t_rows, colWidths=[col_w] * num_cols)
                t_cl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), c_secondary),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(t_cl)
                story.append(Spacer(1, 6))

            # Source basis badge / note
            badge_text = f"<i>Statutory / Judicial Basis: Cites {cl.source_basis} | Policy Question Mappings: {cl.maps_to_question_ids}</i>"
            story.append(Paragraph(badge_text, quote_style))
            story.append(Spacer(1, 8))

        # PageBreak after each major chapter to give realistic multi-page pacing
        story.append(PageBreak())

    # --- ANNEXURES & SCHEDULES ---
    for an in rulebook.annexures:
        story.append(Paragraph(f"{an.annexure_id.upper()}: {an.title.upper()}", h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=8))
        story.append(Paragraph(an.description, body_style))
        story.append(Spacer(1, 8))

        if an.table_headers and an.table_rows:
            a_rows = [[Paragraph(f"<b>{h}</b>", table_hdr_style) for h in an.table_headers]]
            for r in an.table_rows:
                a_rows.append([Paragraph(str(cell), table_cell_style) for cell in r])
            num_cols = len(an.table_headers)
            if num_cols == 4:
                col_widths = [110, 130, 202, 80]
            elif num_cols == 5:
                col_widths = [80, 110, 100, 142, 90]
            elif num_cols == 6:
                col_widths = [70, 100, 80, 112, 90, 70]
            else:
                col_widths = [522.0 / num_cols] * num_cols
            t_an = Table(a_rows, colWidths=col_widths)
            t_an.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), c_primary),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(t_an)
            story.append(Spacer(1, 6))

        if an.notes:
            story.append(Paragraph(f"<b>Note:</b> {an.notes}", quote_style))
            story.append(Spacer(1, 8))

        story.append(PageBreak())

    # --- REAL EXCERPTS CONCORDANCE ---
    story.append(Paragraph("ANNEXURE: CONCORDANCE WITH PUBLIC SOURCES & REAL EXCERPTS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_primary, spaceBefore=2, spaceAfter=8))
    story.append(Paragraph(
        "To ensure absolute legal and historical fidelity, this demo reconstruction is strictly aligned with the authentic "
        "publicly available policy documents, judicial decisions of High Courts and the Supreme Court of India, "
        "DPE pay guidelines, and official ONGC circulars registered in the Policy Registry.",
        body_style
    ))
    story.append(Spacer(1, 8))

    conc_rows = [[
        Paragraph("<b>Public Doc ID</b>", table_hdr_style),
        Paragraph("<b>Source Title / Court Citation</b>", table_hdr_style),
        Paragraph("<b>Reconstructed Clauses</b>", table_hdr_style),
        Paragraph("<b>Authentic Verbatim Anchor Quote</b>", table_hdr_style)
    ]]
    for cr in rulebook.real_excerpts_concordance:
        conc_rows.append([
            Paragraph(f"<b>{cr['doc_id']}</b>", table_cell_style),
            Paragraph(cr['title'], table_cell_style),
            Paragraph(cr['clause_ref'], table_cell_style),
            Paragraph(f"<i>\"{cr['verbatim_quote']}\"</i>", table_cell_style)
        ])
    t_conc = Table(conc_rows, colWidths=[70, 160, 112, 180])
    t_conc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_secondary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_conc)

    # Build document
    doc.build(story, canvasmaker=NumberedWatermarkCanvas)

    # Return total pages
    reader = pypdf.PdfReader(str(out_path))
    return len(reader.pages)


def render_docx(rulebook: Rulebook, out_path: Path):
    """Renders a Rulebook to a native DOCX using python-docx."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    # Set 0.75-inch margins
    for sec in doc.sections:
        sec.top_margin = Inches(0.75)
        sec.bottom_margin = Inches(0.75)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)

        # Header
        header = sec.header
        hp = header.paragraphs[0]
        hp.text = "OIL AND NATURAL GAS CORPORATION LIMITED — DEMO RECONSTRUCTION"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.runs[0].font.name = "Calibri"
        hp.runs[0].font.size = Pt(8.5)
        hp.runs[0].font.color.rgb = RGBColor(100, 116, 139)

        # Footer
        footer = sec.footer
        fp = footer.paragraphs[0]
        fp.text = "DEMO RECONSTRUCTION — not an official ONGC document | Internal Controlled"
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fp.runs[0].font.name = "Calibri"
        fp.runs[0].font.size = Pt(8.5)
        fp.runs[0].font.color.rgb = RGBColor(100, 116, 139)

    # Title Block
    p_org = doc.add_paragraph()
    r_org = p_org.add_run("OIL AND NATURAL GAS CORPORATION LIMITED\n")
    r_org.bold = True
    r_org.font.size = Pt(16)
    r_org.font.color.rgb = RGBColor(11, 37, 69)

    r_sub = p_org.add_run("Corporate Policy, Governance & Regulatory Affairs Directorate\n"
                          "Registered Office: Deendayal Urja Bhawan, 5, Nelson Mandela Marg, Vasant Kunj, New Delhi - 110070\n")
    r_sub.font.size = Pt(9.5)
    r_sub.font.color.rgb = RGBColor(71, 85, 105)
    p_org.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Watermark Notice Box
    p_banner = doc.add_paragraph()
    r_b1 = p_banner.add_run("DEMO RECONSTRUCTION — NOT AN OFFICIAL ONGC DOCUMENT\n")
    r_b1.bold = True
    r_b1.font.size = Pt(10)
    r_b1.font.color.rgb = RGBColor(141, 8, 1)
    r_b2 = p_banner.add_run("This document is a synthetic research reconstruction compiled from authentic circulars, "
                            "court judgments, and statutory guidelines for automated verification and evaluation.")
    r_b2.italic = True
    r_b2.font.size = Pt(9)
    p_banner.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Document Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(f"\n{rulebook.title.upper()}\n")
    r_title.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(11, 37, 69)

    r_id = p_title.add_run(f"Reference Code: {rulebook.ref_code} | Effective Date: {rulebook.effective_date}")
    r_id.font.size = Pt(11)
    r_id.font.color.rgb = RGBColor(19, 64, 116)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()

    # Amendment History
    doc.add_heading("RECORD OF REVISIONS & AMENDMENTS", level=1)
    t_am = doc.add_table(rows=1, cols=4)
    t_am.style = 'Table Grid'
    hdr_cells = t_am.rows[0].cells
    hdr_cells[0].text = "Revision No."
    hdr_cells[1].text = "Effective Date"
    hdr_cells[2].text = "Approving Authority"
    hdr_cells[3].text = "Summary of Modifications"
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].bold = True

    for am in rulebook.amendment_history:
        row = t_am.add_row().cells
        row[0].text = am.revision_no
        row[1].text = am.date
        row[2].text = am.authority
        row[3].text = am.summary_of_changes

    # Preamble & Definitions
    doc.add_heading("PREAMBLE & OBJECTIVES", level=1)
    doc.add_paragraph(rulebook.preamble)

    doc.add_heading("DEFINITIONS & INTERPRETATION", level=1)
    for term, definition in rulebook.definitions.items():
        p_def = doc.add_paragraph()
        r_t = p_def.add_run(f"{term}: ")
        r_t.bold = True
        p_def.add_run(definition)

    doc.add_page_break()

    # Chapters & Clauses
    for ch in rulebook.chapters:
        doc.add_heading(f"CHAPTER {ch.chapter_num}: {ch.title.upper()}", level=1)
        for cl in ch.clauses:
            doc.add_heading(f"{cl.clause_ref}: {cl.clause_title}", level=2)
            for line in cl.clause_text.split("\n"):
                if line.strip():
                    doc.add_paragraph(line.strip())

            for sc in cl.subclauses:
                p_sc = doc.add_paragraph()
                r_sc = p_sc.add_run(f"({sc.ref}) {sc.title}: ")
                r_sc.bold = True
                p_sc.add_run(sc.text)

            p_src = doc.add_paragraph()
            r_s = p_src.add_run(f"[Source Basis: Cites {cl.source_basis} | Policy Question Mappings: {cl.maps_to_question_ids}]")
            r_s.italic = True
            r_s.font.size = Pt(8.5)
            r_s.font.color.rgb = RGBColor(100, 116, 139)

        doc.add_page_break()

    # Annexures
    for an in rulebook.annexures:
        doc.add_heading(f"{an.annexure_id}: {an.title}", level=1)
        doc.add_paragraph(an.description)
        if an.table_headers and an.table_rows:
            t = doc.add_table(rows=1, cols=len(an.table_headers))
            t.style = 'Table Grid'
            for idx, h in enumerate(an.table_headers):
                c = t.rows[0].cells[idx]
                c.text = h
                c.paragraphs[0].runs[0].bold = True
            for r in an.table_rows:
                row_cells = t.add_row().cells
                for idx, val in enumerate(r):
                    row_cells[idx].text = str(val)
        if an.notes:
            p_n = doc.add_paragraph()
            p_n.add_run(f"Note: {an.notes}").italic = True
        doc.add_page_break()

    # Concordance
    doc.add_heading("ANNEXURE: CONCORDANCE WITH REAL PUBLIC EXCERPTS", level=1)
    t_c = doc.add_table(rows=1, cols=4)
    t_c.style = 'Table Grid'
    c_hdrs = t_c.rows[0].cells
    c_hdrs[0].text = "Doc ID"
    c_hdrs[1].text = "Source Document / Citation"
    c_hdrs[2].text = "Reconstructed Clauses"
    c_hdrs[3].text = "Authentic Anchor Quote"
    for cell in c_hdrs:
        cell.paragraphs[0].runs[0].bold = True
    for cr in rulebook.real_excerpts_concordance:
        row = t_c.add_row().cells
        row[0].text = cr['doc_id']
        row[1].text = cr['title']
        row[2].text = cr['clause_ref']
        row[3].text = f'"{cr["verbatim_quote"]}"'

    # Save docx to buffer, then normalize zip entry timestamps for determinism
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    in_zip = zipfile.ZipFile(buf, "r")
    with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as out_zip:
        for item in sorted(in_zip.infolist(), key=lambda x: x.filename):
            data = in_zip.read(item.filename)
            zinfo = zipfile.ZipInfo(item.filename, (2026, 10, 19, 0, 0, 0))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            out_zip.writestr(zinfo, data)


def render_scanned_pdf(input_pdf_path: Path, output_pdf_path: Path) -> int:
    """Renders a scanned, image-only PDF with zero text layer using pdf2image and PIL."""
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(str(input_pdf_path), dpi=140)

    scanned_pages: List[Image.Image] = []
    # Seeded random for determinism
    rng = random.Random(20261019)

    for img in images:
        # Convert to grayscale
        gray = img.convert('L')
        # Slight contrast adjustment
        enh = ImageEnhance.Contrast(gray).enhance(1.08)
        # Subtle rotation jitter (-0.25 to +0.25 deg) to emulate scanner feeding
        skew_angle = rng.uniform(-0.25, 0.25)
        skewed = enh.rotate(skew_angle, resample=Image.BICUBIC, fillcolor=255)
        scanned_pages.append(skewed)

    # Save as PDF via PIL (pure image pages, 0 text layer) into memory buffer
    buf = io.BytesIO()
    scanned_pages[0].save(
        buf,
        format='PDF',
        save_all=True,
        append_images=scanned_pages[1:],
        resolution=140.0
    )
    raw_pdf = buf.getvalue()

    # Normalize CreationDate and ModDate in PDF trailer for determinism
    fixed_pdf = re.sub(rb'/CreationDate \(D:\d+Z\)', b'/CreationDate (D:20261019000000Z)', raw_pdf)
    fixed_pdf = re.sub(rb'/ModDate \(D:\d+Z\)', b'/ModDate (D:20261019000000Z)', fixed_pdf)
    with open(output_pdf_path, "wb") as f:
        f.write(fixed_pdf)

    # Verify zero text layer
    reader = pypdf.PdfReader(str(output_pdf_path))
    num_pages = len(reader.pages)
    total_text = "".join(p.extract_text() for p in reader.pages)
    assert len(total_text.strip()) == 0, f"Scanned PDF has unexpected text layer: {repr(total_text[:100])}"
    return num_pages
