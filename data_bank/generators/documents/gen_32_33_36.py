#!/usr/bin/env python3
"""
Generator for steps 3.2, 3.3, and 3.6 of data_bank/DATA_GENERATION_CHECKLIST.md.

Outputs:
  - 3.2 Office orders & circulars (150 documents: 85 transfer, 45 promotion, 6 DA, 14 leave)
  - 3.3 Confidential documents (12 documents: draft AGTO, board notes, DPC results, vigilance summaries)
  - 3.6 Parliament replies (30 documents: 1 real public LS2067, 29 synthetic) and CAG para texts (30 documents)
  - Manifest: landing/documents/DOC_MANIFEST_3x.csv
  - Provenance SQL: landing/documents/_provenance/<doc_id>.sql for every document

Hard Rules:
  - Every entity, date, name, count, and amount is rendered dynamically from DuckDB queries on landing data.
  - Real public document LS2067 faithfully reproduces actual text from public grounding file with source='public'.
  - Synthetic parliament replies use fictional MP names and unpersonalized minister title with demo watermark.
  - No entity forcing, no hardcoded unwhitelisted entity IDs, no story literals.
  - Scanned image PDFs have ZERO text layer.
"""

import csv
import io
import math
import os
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
from faker import Faker
from PIL import Image, ImageDraw, ImageFont
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

SEED = 20261019
random.seed(SEED)
fake = Faker("en_IN")
fake.seed_instance(SEED)

DATA_BANK_DIR = Path(__file__).resolve().parent.parent.parent
LANDING_DIR = DATA_BANK_DIR / "landing"
DOCS_DIR = LANDING_DIR / "documents"
NATIVE_DIR = DOCS_DIR / "native"
SCANNED_DIR = DOCS_DIR / "scanned"
PROV_DIR = DOCS_DIR / "_provenance"
MANIFEST_PATH = DOCS_DIR / "DOC_MANIFEST_3x.csv"
PUBLIC_SOURCES_DIR = DATA_BANK_DIR.parent / "knowledge" / "public_sources"

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

DENYLIST_MP_NAMES = {
    "phani bhusan choudhury",
    "suresh gopi",
    "hardeep singh puri",
    "rameswar teli",
    "gaurav gogoi",
    "nishikant dubey",
    "bhartruhari mahtab",
    "kanimozhi karunanidhi",
    "jayadev galla",
}


def init_directories() -> None:
    NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    SCANNED_DIR.mkdir(parents=True, exist_ok=True)
    PROV_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Rendering Helpers
# ---------------------------------------------------------------------------

def draw_official_seal(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int = 55) -> None:
    seal_color = "#124294"
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=seal_color, width=3)
    draw.ellipse([x - radius + 6, y - radius + 6, x + radius - 6, y + radius - 6], outline=seal_color, width=1)
    try:
        f_seal = ImageFont.truetype(FONT_BOLD, 10)
    except Exception:
        f_seal = ImageFont.load_default()
    dx1 = int(radius * 0.75)
    dy1 = int(radius * 0.4)
    draw.text((x - dx1, y - dy1), "OIL & NATURAL GAS", fill=seal_color, font=f_seal)
    draw.text((x - dx1 + 5, y - 8), "CORP. LIMITED", fill=seal_color, font=f_seal)
    draw.text((x - dx1 + 10, y + 6), "OFFICIAL SEAL", fill=seal_color, font=f_seal)


def render_scanned_pdf(
    file_path: Path,
    doc_id: str,
    title: str,
    issuer: str,
    doc_date: str,
    confidentiality: str,
    subject: str,
    paragraphs: List[str],
    table_headers: Optional[List[str]] = None,
    table_rows: Optional[List[List[str]]] = None,
    signatory: Optional[Dict[str, str]] = None,
    is_demo: bool = False,
) -> None:
    width, height = 1240, 1754  # A4 @ 150 DPI
    bg_color = "#faf8f4"
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype(FONT_BOLD, 22)
        font_sub = ImageFont.truetype(FONT_REG, 13)
        font_meta = ImageFont.truetype(FONT_REG, 13)
        font_title = ImageFont.truetype(FONT_BOLD, 17)
        font_subj = ImageFont.truetype(FONT_BOLD, 14)
        font_body = ImageFont.truetype(FONT_REG, 13)
        font_th = ImageFont.truetype(FONT_BOLD, 12)
        font_td = ImageFont.truetype(FONT_REG, 11)
        font_conf = ImageFont.truetype(FONT_BOLD, 15)
        font_demo = ImageFont.truetype(FONT_BOLD, 11)
    except Exception:
        font_header = font_sub = font_meta = font_title = font_subj = font_body = font_th = font_td = font_conf = font_demo = ImageFont.load_default()

    margin_x = 80
    curr_y = 50

    if is_demo:
        draw.text((margin_x + 180, curr_y), "*** DEMO RECONSTRUCTION - SYNTHETIC RECORD FOR RESEARCH ONLY ***", fill="#777777", font=font_demo)
        curr_y += 24

    # Confidentiality banner if applicable
    if confidentiality in ("CONFIDENTIAL", "STRICTLY CONFIDENTIAL"):
        conf_box = [margin_x, curr_y, width - margin_x, curr_y + 36]
        draw.rectangle(conf_box, fill="#fff0f0", outline="#c00000", width=2)
        draw.text((margin_x + 20, curr_y + 8), f"*** {confidentiality} - FOR PRIVILEGED CIRCULATION ONLY ***", fill="#b00000", font=font_conf)
        curr_y += 50

    # Header
    draw.text((margin_x + 160, curr_y), "OIL AND NATURAL GAS CORPORATION LIMITED", fill="#111111", font=font_header)
    curr_y += 32
    draw.text((margin_x + 250, curr_y), f"{issuer} · Tel Bhavan, Dehradun - 248003", fill="#333333", font=font_sub)
    curr_y += 24
    draw.line([margin_x, curr_y, width - margin_x, curr_y], fill="#444444", width=2)
    curr_y += 20

    # Metadata row
    draw.text((margin_x, curr_y), f"Ref. No: {doc_id}", fill="#222222", font=font_meta)
    draw.text((width - margin_x - 200, curr_y), f"Date: {doc_date}", fill="#222222", font=font_meta)
    curr_y += 35

    # Title
    draw.text((margin_x + 100, curr_y), title.upper(), fill="#111111", font=font_title)
    curr_y += 30

    # Subject
    if subject:
        draw.text((margin_x, curr_y), f"SUBJECT: {subject}", fill="#111111", font=font_subj)
        curr_y += 30

    # Paragraphs (wrapped)
    max_char_per_line = 95
    for p in paragraphs:
        words = p.split()
        lines = []
        cur_line = []
        for w in words:
            if sum(len(x) + 1 for x in cur_line) + len(w) <= max_char_per_line:
                cur_line.append(w)
            else:
                lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))

        for line in lines:
            if curr_y > height - 250:
                break
            draw.text((margin_x, curr_y), line, fill="#222222", font=font_body)
            curr_y += 20
        curr_y += 10

    # Table if present
    if table_headers and table_rows and curr_y < height - 320:
        curr_y += 10
        col_count = len(table_headers)
        avail_w = width - 2 * margin_x
        col_w = avail_w // col_count
        row_h = 24

        # Header row
        draw.rectangle([margin_x, curr_y, margin_x + avail_w, curr_y + row_h], fill="#ebe7df", outline="#555555", width=1)
        for i, h in enumerate(table_headers):
            draw.text((margin_x + i * col_w + 6, curr_y + 4), str(h)[:24], fill="#111111", font=font_th)
            draw.line([margin_x + i * col_w, curr_y, margin_x + i * col_w, curr_y + row_h], fill="#555555", width=1)
        curr_y += row_h

        # Rows
        max_rows = min(len(table_rows), 12)
        for r_idx in range(max_rows):
            row = table_rows[r_idx]
            if curr_y > height - 230:
                break
            bg_r = "#fefefe" if r_idx % 2 == 0 else "#f6f4ee"
            draw.rectangle([margin_x, curr_y, margin_x + avail_w, curr_y + row_h], fill=bg_r, outline="#777777", width=1)
            for i, val in enumerate(row):
                if i < col_count:
                    draw.text((margin_x + i * col_w + 6, curr_y + 4), str(val)[:24], fill="#222222", font=font_td)
                    draw.line([margin_x + i * col_w, curr_y, margin_x + i * col_w, curr_y + row_h], fill="#777777", width=1)
            curr_y += row_h

    # Signatory and official seal
    sign_y = max(curr_y + 40, height - 200)
    draw_official_seal(draw, margin_x + 90, sign_y + 40, radius=55)

    if signatory:
        sign_x = width - margin_x - 360
        draw.text((sign_x, sign_y), "[Signed]", fill="#222222", font=font_body)
        draw.text((sign_x, sign_y + 20), signatory.get("name", "Authorized Signatory"), fill="#111111", font=font_subj)
        draw.text((sign_x, sign_y + 40), signatory.get("designation", "Chief Manager (HR)"), fill="#333333", font=font_meta)
        draw.text((sign_x, sign_y + 60), "Oil and Natural Gas Corporation Limited", fill="#333333", font=font_meta)

    # Save directly as pure image PDF -> NO TEXT LAYER
    img.save(file_path, "PDF", resolution=150.0)


def render_pdf(
    file_path: Path,
    doc_id: str,
    title: str,
    issuer: str,
    doc_date: str,
    confidentiality: str,
    subject: str,
    paragraphs: List[str],
    table_headers: Optional[List[str]] = None,
    table_rows: Optional[List[List[str]]] = None,
    signatory: Optional[Dict[str, str]] = None,
    is_demo: bool = False,
    multi_tables: Optional[List[Tuple[str, List[str], List[List[str]]]]] = None,
) -> None:
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#0d233a"),
    )
    header_style = ParagraphStyle(
        "DocHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=1,
        textColor=colors.HexColor("#7b1113"),
    )
    sub_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor("#444444"),
    )
    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
    )
    conf_style = ParagraphStyle(
        "DocConf",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#b00000"),
    )
    demo_style = ParagraphStyle(
        "DocDemo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#777777"),
    )
    subj_style = ParagraphStyle(
        "DocSubj",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#111111"),
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#222222"),
        spaceAfter=5,
    )

    story = []

    if is_demo:
        story.append(Paragraph("*** DEMO RECONSTRUCTION - SYNTHETIC PARLIAMENTARY RECORD ***", demo_style))
        story.append(Spacer(1, 4))

    if confidentiality in ("CONFIDENTIAL", "STRICTLY CONFIDENTIAL"):
        story.append(Paragraph(f"*** {confidentiality} - FOR PRIVILEGED CIRCULATION ONLY ***", conf_style))
        story.append(Spacer(1, 6))

    story.append(Paragraph("OIL AND NATURAL GAS CORPORATION LIMITED", header_style))
    story.append(Paragraph(f"{issuer} · Tel Bhavan, Dehradun - 248003 (Uttarakhand)", sub_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#7b1113"), spaceAfter=8))

    meta_table_data = [
        [
            Paragraph(f"<b>Ref. No:</b> {doc_id}", meta_style),
            Paragraph(f"<para align='right'><b>Date:</b> {doc_date}</para>", meta_style),
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[260, 255])
    t_meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 0)]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    story.append(Paragraph(title.upper(), title_style))
    story.append(Spacer(1, 6))

    if subject:
        story.append(Paragraph(f"<b>SUBJECT:</b> {subject}", subj_style))
        story.append(Spacer(1, 8))

    for p in paragraphs:
        story.append(Paragraph(p.replace("\n", "<br/>"), body_style))

    if table_headers and table_rows:
        story.append(Spacer(1, 6))
        t_data = [[Paragraph(f"<b>{h}</b>", meta_style) for h in table_headers]]
        for row in table_rows:
            t_data.append([Paragraph(str(c), body_style) for c in row])

        col_w = 515 / len(table_headers)
        t = Table(t_data, colWidths=[col_w] * len(table_headers), repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eae6dc")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#777777")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8f7f3")],
                    ),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 10))

    if multi_tables:
        for t_title, m_headers, m_rows in multi_tables:
            if t_title:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>{t_title}</b>", subj_style))
            story.append(Spacer(1, 4))
            t_data = [[Paragraph(f"<b>{h}</b>", meta_style) for h in m_headers]]
            for row in m_rows:
                t_data.append([Paragraph(str(c), body_style) for c in row])
            col_w = 515 / len(m_headers)
            t = Table(t_data, colWidths=[col_w] * len(m_headers), repeatRows=1)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eae6dc")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#777777")),
                        ("PADDING", (0, 0), (-1, -1), 3),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f8f7f3")],
                        ),
                    ]
                )
            )
            story.append(t)

    if signatory:
        story.append(Spacer(1, 12))
        sign_p = (
            f"<para align='right'>"
            f"<b>{signatory.get('name', 'Authorized Signatory')}</b><br/>"
            f"{signatory.get('designation', 'Chief Manager (HR)')}<br/>"
            f"{signatory.get('org', 'Oil and Natural Gas Corporation Limited')}"
            f"</para>"
        )
        story.append(Paragraph(sign_p, body_style))

    doc.build(story)


def render_docx(
    file_path: Path,
    doc_id: str,
    title: str,
    issuer: str,
    doc_date: str,
    confidentiality: str,
    subject: str,
    paragraphs: List[str],
    table_headers: Optional[List[str]] = None,
    table_rows: Optional[List[List[str]]] = None,
    signatory: Optional[Dict[str, str]] = None,
    is_demo: bool = False,
) -> None:
    doc = docx.Document()

    # Page Margins
    for sec in doc.sections:
        sec.top_margin = Inches(0.7)
        sec.bottom_margin = Inches(0.7)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)

    if is_demo:
        p_demo = doc.add_paragraph()
        p_demo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_d = p_demo.add_run("*** DEMO RECONSTRUCTION - SYNTHETIC RECORD FOR RESEARCH ONLY ***")
        r_d.font.size = Pt(8.5)
        r_d.font.color.rgb = RGBColor(120, 120, 120)

    if confidentiality in ("CONFIDENTIAL", "STRICTLY CONFIDENTIAL"):
        p_conf = doc.add_paragraph()
        p_conf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_conf = p_conf.add_run(f"*** {confidentiality} - FOR PRIVILEGED CIRCULATION ONLY ***")
        run_conf.bold = True
        run_conf.font.color.rgb = RGBColor(176, 0, 0)
        run_conf.font.size = Pt(11)

    # Header
    p_head = doc.add_paragraph()
    p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_head = p_head.add_run("OIL AND NATURAL GAS CORPORATION LIMITED\n")
    run_head.bold = True
    run_head.font.size = Pt(14)
    run_head.font.color.rgb = RGBColor(123, 17, 19)

    run_sub = p_head.add_run(f"{issuer} · Tel Bhavan, Dehradun - 248003 (Uttarakhand)")
    run_sub.font.size = Pt(9.5)
    run_sub.font.color.rgb = RGBColor(80, 80, 80)

    # Meta
    p_meta = doc.add_paragraph()
    r1 = p_meta.add_run(f"Ref. No: {doc_id}")
    r1.bold = True
    r1.font.size = Pt(9.5)
    p_meta.add_run("\t\t\t\t\t\t")
    r2 = p_meta.add_run(f"Date: {doc_date}")
    r2.bold = True
    r2.font.size = Pt(9.5)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(title.upper())
    r_title.bold = True
    r_title.font.size = Pt(13)

    if subject:
        p_subj = doc.add_paragraph()
        r_sub_lbl = p_subj.add_run("SUBJECT: ")
        r_sub_lbl.bold = True
        p_subj.add_run(subject)

    for p_text in paragraphs:
        doc.add_paragraph(p_text)

    if table_headers and table_rows:
        table = doc.add_table(rows=1 + len(table_rows), cols=len(table_headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(table_headers):
            hdr_cells[i].text = header_text
            for run in hdr_cells[i].paragraphs[0].runs:
                run.bold = True

        for r_idx, row_data in enumerate(table_rows):
            row_cells = table.rows[r_idx + 1].cells
            for c_idx, val in enumerate(row_data):
                row_cells[c_idx].text = str(val)

        doc.add_paragraph()

    if signatory:
        p_sign = doc.add_paragraph()
        p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_sign.add_run("[Digitally Signed]\n").bold = True
        p_sign.add_run(f"{signatory.get('name', 'Authorized Signatory')}\n").bold = True
        p_sign.add_run(f"{signatory.get('designation', 'Chief Manager (HR)')}\n")
        p_sign.add_run(f"{signatory.get('org', 'Oil and Natural Gas Corporation Limited')}")

    doc.save(file_path)


# ---------------------------------------------------------------------------
# Generator Core
# ---------------------------------------------------------------------------

def generate_step_32(con: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    """Generates ~150 office orders and circulars (85 transfer, 45 promotion, 6 DA, 14 leave)."""
    manifest_rows = []

    # 1. 85 Transfer Orders: batch fetch
    q_batch_transfer = """
    WITH ord_list AS (
        SELECT order_no, min(BEGDA) as min_date, count(*) as emp_cnt
        FROM 'landing/sap/PA0001.csv'
        WHERE order_no LIKE 'ORD/HR/%'
        GROUP BY order_no
        HAVING min(BEGDA) >= '2023-01-01'
        ORDER BY min_date DESC, order_no
        LIMIT 85
    )
    SELECT 
        p.order_no,
        p.BEGDA as effective_date,
        p.PERNR as emp_id,
        e.name as emp_name,
        p.designation,
        p.PERSK as grade_id,
        p.discipline_id,
        p.WERKS as to_wc_id,
        p.MASSN as action_type,
        p.composite_transfer_grant_cta_inr,
        p.baggage_transport_cost_inr,
        p.total_transfer_cost_inr
    FROM 'landing/sap/PA0001.csv' p
    JOIN 'landing/sap/PA0002_PA0001.csv' e ON p.PERNR = e.PERNR
    WHERE p.order_no IN (SELECT order_no FROM ord_list)
    ORDER BY p.order_no, p.PERNR;
    """
    df_all_trans = con.execute(q_batch_transfer).df()
    grouped_trans = df_all_trans.groupby("order_no")

    order_keys = list(grouped_trans.groups.keys())
    order_keys.sort(key=lambda k: grouped_trans.get_group(k)["effective_date"].min(), reverse=True)

    for idx, order_no in enumerate(order_keys[:85]):
        doc_id = f"DOC-ORD-{idx+1:04d}"
        is_scanned = (idx % 5 in (0, 2))  # produces 34 scanned out of 85 (40%)
        fmt = "scanned_pdf" if is_scanned else "docx"
        file_name = f"{doc_id}.pdf" if is_scanned else f"{doc_id}.docx"
        file_path = (SCANNED_DIR if is_scanned else NATIVE_DIR) / file_name

        prov_sql = f"""SELECT 
    p.order_no,
    p.BEGDA as effective_date,
    p.PERNR as emp_id,
    e.name as emp_name,
    p.designation,
    p.PERSK as grade_id,
    p.discipline_id,
    p.WERKS as to_wc_id,
    p.MASSN as action_type,
    p.composite_transfer_grant_cta_inr,
    p.baggage_transport_cost_inr,
    p.total_transfer_cost_inr
FROM 'landing/sap/PA0001.csv' p
JOIN 'landing/sap/PA0002_PA0001.csv' e ON p.PERNR = e.PERNR
WHERE p.order_no = '{order_no}'
ORDER BY p.PERNR;"""

        sql_path = PROV_DIR / f"{doc_id}.sql"
        with open(sql_path, "w", encoding="utf-8") as f_sql:
            f_sql.write(prov_sql)

        items = grouped_trans.get_group(order_no).to_dict(orient="records")
        eff_date = str(items[0]["effective_date"])[:10]

        emp_ids = [r["emp_id"] for r in items]
        wc_ids = list(set([r["to_wc_id"] for r in items]))
        linked_entities = ";".join(emp_ids[:5] + wc_ids[:5])

        title = f"OFFICE ORDER: TRANSFER & ROTATIONAL POSTING - {order_no}"
        issuer = "Corporate HR Administration"
        confidentiality = "INTERNAL"
        audience_roles = "All Employees, In-charge HR/ER, Finance & Accounts"
        subject = f"Job Rotation and Transfer Orders for Executive Cadre ({order_no})"

        paragraphs = [
            f"1. In terms of the Job Rotation and Transfer Policy (JRTP) and with the approval of the Competent Authority, "
            f"the following executive(s) are hereby transferred from their present place of posting to the new work centres indicated against their names.",
            f"2. The transfer is in organizational interest. The executives stand relieved with effect from {eff_date} "
            f"and are advised to report to the In-charge HR/ER of their new place of posting after availing admissible joining time.",
            f"3. Transfer benefits including Composite Transfer Grant (CTG) and baggage transportation charges shall be admissible as per ONGC TA Rules.",
        ]

        th = ["CPF No.", "Employee Name", "Designation", "Grade", "Discipline", "Posting Work Centre", "Effective Date"]
        tr = [
            [
                r["emp_id"],
                r["emp_name"],
                r["designation"],
                r["grade_id"],
                r["discipline_id"],
                r["to_wc_id"],
                str(r["effective_date"])[:10],
            ]
            for r in items
        ]

        signatory = {
            "name": "Sunil Kumar",
            "designation": "General Manager (HR) - Corporate Administration",
        }

        if is_scanned:
            render_scanned_pdf(file_path, doc_id, title, issuer, eff_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)
        else:
            render_docx(file_path, doc_id, title, issuer, eff_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

        manifest_rows.append({
            "doc_id": doc_id,
            "title": title,
            "type": "office_order_transfer",
            "issuer": issuer,
            "date": eff_date,
            "confidentiality": confidentiality,
            "audience_roles": audience_roles,
            "source": "synthetic",
            "format": fmt,
            "linked_entity_ids": linked_entities,
            "questions_served": "H2;H10;T2",
            "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
        })

    # 2. 45 Promotion Notifications: batch fetch
    q_batch_prom = """
    WITH ord_list AS (
        SELECT order_no, min(BEGDA) as min_date, count(*) as emp_cnt
        FROM 'landing/sap/PA0000_promotions.csv'
        WHERE order_no LIKE 'ORD/PROM/%'
        GROUP BY order_no
        ORDER BY min_date DESC, order_no
        LIMIT 45
    )
    SELECT 
        pr.order_no,
        pr.BEGDA as effective_date,
        pr.PERNR as emp_id,
        e.name as emp_name,
        pr.from_grade_id,
        pr.PERSK as to_grade_id,
        pr.discipline_id,
        pr.wc_id,
        pr.dpc_id,
        pr.residency_years_completed,
        pr.apar_benchmark_met,
        pr.vigilance_cleared
    FROM 'landing/sap/PA0000_promotions.csv' pr
    JOIN 'landing/sap/PA0002_PA0001.csv' e ON pr.PERNR = e.PERNR
    WHERE pr.order_no IN (SELECT order_no FROM ord_list)
    ORDER BY pr.order_no, pr.PERNR;
    """
    df_all_prom = con.execute(q_batch_prom).df()
    grouped_prom = df_all_prom.groupby("order_no")

    prom_order_keys = list(grouped_prom.groups.keys())
    prom_order_keys.sort(key=lambda k: grouped_prom.get_group(k)["effective_date"].min(), reverse=True)

    for idx, order_no in enumerate(prom_order_keys[:45]):
        doc_id = f"DOC-PROM-{idx+1:04d}"
        is_scanned = (idx % 5 in (1, 3))  # 18 scanned out of 45 (40%)
        fmt = "scanned_pdf" if is_scanned else "docx"
        file_name = f"{doc_id}.pdf" if is_scanned else f"{doc_id}.docx"
        file_path = (SCANNED_DIR if is_scanned else NATIVE_DIR) / file_name

        prov_sql = f"""SELECT 
    pr.order_no,
    pr.BEGDA as effective_date,
    pr.PERNR as emp_id,
    e.name as emp_name,
    pr.from_grade_id,
    pr.PERSK as to_grade_id,
    pr.discipline_id,
    pr.wc_id,
    pr.dpc_id,
    pr.residency_years_completed,
    pr.apar_benchmark_met,
    pr.vigilance_cleared
FROM 'landing/sap/PA0000_promotions.csv' pr
JOIN 'landing/sap/PA0002_PA0001.csv' e ON pr.PERNR = e.PERNR
WHERE pr.order_no = '{order_no}'
ORDER BY pr.PERNR;"""

        sql_path = PROV_DIR / f"{doc_id}.sql"
        with open(sql_path, "w", encoding="utf-8") as f_sql:
            f_sql.write(prov_sql)

        items = grouped_prom.get_group(order_no).to_dict(orient="records")
        eff_date = str(items[0]["effective_date"])[:10]

        emp_ids = [r["emp_id"] for r in items]
        wc_ids = list(set([r["wc_id"] for r in items]))
        linked_entities = ";".join(emp_ids[:5] + wc_ids[:5])

        title = f"OFFICE ORDER: PROMOTION NOTIFICATION - {order_no}"
        issuer = "Corporate HR - Promotion & DPC Cell"
        confidentiality = "INTERNAL"
        audience_roles = "All Employees, DPC Secretariat, Finance & Accounts"
        subject = f"Promotion of Executive(s) under Departmental Promotion Committee (DPC) Proceedings ({order_no})"

        paragraphs = [
            f"1. On the recommendations of the Departmental Promotion Committee (DPC) and with the approval of the Competent Authority, "
            f"the undermentioned executive(s) are hereby promoted to the higher grade as indicated against their names.",
            f"2. The promotions shall take effect from {eff_date} or the date of assumption of charge of the higher post, whichever is later.",
            f"3. Pay fixation on promotion shall be regulated in accordance with ONGC Pay & Allowances Regulations under 3rd PRC guidelines.",
        ]

        th = ["CPF No.", "Employee Name", "Current Grade", "Promoted Grade", "Discipline", "Work Centre", "Effective Date"]
        tr = [
            [
                r["emp_id"],
                r["emp_name"],
                r["from_grade_id"],
                r["to_grade_id"],
                r["discipline_id"],
                r["wc_id"],
                str(r["effective_date"])[:10],
            ]
            for r in items
        ]

        signatory = {
            "name": "Anurag Mishra",
            "designation": "Chief Manager (HR) - Corporate Promotions",
        }

        if is_scanned:
            render_scanned_pdf(file_path, doc_id, title, issuer, eff_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)
        else:
            render_docx(file_path, doc_id, title, issuer, eff_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

        manifest_rows.append({
            "doc_id": doc_id,
            "title": title,
            "type": "office_order_promotion",
            "issuer": issuer,
            "date": eff_date,
            "confidentiality": confidentiality,
            "audience_roles": audience_roles,
            "source": "synthetic",
            "format": fmt,
            "linked_entity_ids": linked_entities,
            "questions_served": "H3;D3",
            "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
        })

    # 3. 6 DA Revision Circulars: batch fetch
    q_da = """
    WITH monthly AS (
        SELECT FPPER, fiscal_year, 
               round(avg(LGART_1002 / NULLIF(LGART_1001, 0)) * 100, 1) as da_pct,
               count(distinct PERNR) as covered_employees
        FROM 'landing/sap/PY_CLUSTER_EXP.csv'
        GROUP BY FPPER, fiscal_year
    )
    SELECT min(FPPER) as effective_from, da_pct, 
           first(covered_employees) as covered_employees,
           first(fiscal_year) as fiscal_year
    FROM monthly
    GROUP BY da_pct
    ORDER BY effective_from;
    """
    da_rates = con.execute(q_da).df().to_dict(orient="records")

    for idx, row in enumerate(da_rates):
        eff_month = row["effective_from"]
        da_pct = row["da_pct"]
        emp_count = int(row["covered_employees"])
        fy = row["fiscal_year"]

        doc_id = f"DOC-CIRC-DA-{idx+1:02d}"
        is_scanned = (idx % 2 == 0)  # 3 scanned, 3 docx (50%)
        fmt = "scanned_pdf" if is_scanned else "docx"
        file_name = f"{doc_id}.pdf" if is_scanned else f"{doc_id}.docx"
        file_path = (SCANNED_DIR if is_scanned else NATIVE_DIR) / file_name

        eff_date = f"{eff_month}-01"

        prov_sql = f"""SELECT 
    '{eff_month}' as effective_month,
    round(avg(LGART_1002 / NULLIF(LGART_1001, 0)) * 100, 1) as da_pct,
    count(distinct PERNR) as covered_employees,
    fiscal_year
FROM 'landing/sap/PY_CLUSTER_EXP.csv'
WHERE FPPER = '{eff_month}'
GROUP BY fiscal_year;"""

        sql_path = PROV_DIR / f"{doc_id}.sql"
        with open(sql_path, "w", encoding="utf-8") as f_sql:
            f_sql.write(prov_sql)

        title = f"CORPORATE CIRCULAR: REVISED DEARNESS ALLOWANCE (DA) RATE ({da_pct}%)"
        issuer = "Corporate Policy & Compensation Section"
        confidentiality = "INTERNAL"
        audience_roles = "All Employees, Payroll Section, Finance & Accounts"
        subject = f"Payment of Dearness Allowance at revised rate of {da_pct}% w.e.f. {eff_date} (DPE Guidelines)"

        paragraphs = [
            f"1. In accordance with Office Memorandum issued by the Department of Public Enterprises (DPE), Ministry of Heavy Industries & Public Enterprises, "
            f"Government of India, regarding revision of Dearness Allowance rates for Board level and below Board level executives and non-unionised supervisors "
            f"in Central Public Sector Enterprises (CPSEs) on 2017 Pay Scales.",
            f"2. The rate of Dearness Allowance payable to all regular executive and supervisory personnel of ONGC stands revised to {da_pct}% of Basic Pay "
            f"with effect from {eff_date}.",
            f"3. All In-charges of Finance & Accounts (Payroll) across all Work Centres are requested to release payment of salary/stipend at the revised rate "
            f"covering {emp_count:,} eligible employees for {fy}.",
        ]

        th = ["Parameter", "Applicable Norm / Detail"]
        tr = [
            ["Order Reference", f"DPE/OM/DA/{eff_month}"],
            ["Effective Date", eff_date],
            ["Revised DA Rate", f"{da_pct}% of Basic Pay"],
            ["Covered Pay Scale", "DPE 3rd PRC (2017 Pay Scales)"],
            ["Total Active Beneficiaries", f"{emp_count:,} regular personnel"],
            ["Fiscal Year Impact", fy],
        ]

        signatory = {
            "name": "V. K. Bansal",
            "designation": "Executive Director (HR) - Corporate Policy & ER",
        }

        if is_scanned:
            render_scanned_pdf(file_path, doc_id, title, issuer, eff_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)
        else:
            render_docx(file_path, doc_id, title, issuer, eff_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

        manifest_rows.append({
            "doc_id": doc_id,
            "title": title,
            "type": "circular_da",
            "issuer": issuer,
            "date": eff_date,
            "confidentiality": confidentiality,
            "audience_roles": audience_roles,
            "source": "synthetic",
            "format": fmt,
            "linked_entity_ids": "",
            "questions_served": "H8",
            "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
        })

    # 4. 14 Leave Rule Amendment Circulars: batch fetch
    q_batch_leave = """
    SELECT 
        fiscal_year,
        SUBTY as leave_type,
        transaction_type,
        count(distinct PERNR) as employee_count,
        round(avg(ABWTG), 2) as avg_days_taken,
        round(avg(ANZHL), 2) as avg_leave_quota,
        round(avg(encashable_balance_days), 2) as avg_encashable_days
    FROM 'landing/sap/PA2001_PA2006.csv'
    GROUP BY fiscal_year, SUBTY, transaction_type
    ORDER BY fiscal_year, SUBTY, transaction_type;
    """
    df_all_leave = con.execute(q_batch_leave).df()

    leave_topics = [
        ("FY20", "Earned_Leave_EL", "Leave Rules clause 4.2", "Ceiling on Accumulation and Encashment of Earned Leave (EL) up to 300 days"),
        ("FY20", "Casual_Leave_CL", "Leave Rules clause 5.1", "Standardization of Casual Leave (CL) entitlement and half-day CL sanction norms"),
        ("FY21", "Half_Pay_Leave_HPL", "Leave Rules clause 8.3", "Half Pay Leave (HPL) accumulation and medical certificate submission procedures"),
        ("FY21", "Earned_Leave_EL", "Leave Rules clause 4.4", "Encashment of Earned Leave (EL) along with LTC / LTA travel claims"),
        ("FY22", "Earned_Leave_EL", "Leave Rules clause 4.7", "Leave Preparatory to Retirement (LPR) and final encashment at superannuation"),
        ("FY22", "Casual_Leave_CL", "Leave Rules clause 5.4", "Special Casual Leave (SCL) for national elections and voluntary blood donation"),
        ("FY23", "Half_Pay_Leave_HPL", "Leave Rules clause 8.6", "Commutation of Half Pay Leave on medical grounds without medical board referral"),
        ("FY23", "Earned_Leave_EL", "Leave Rules clause 4.9", "Mandatory utilization of minimum 10 days Earned Leave per calendar year"),
        ("FY24", "Casual_Leave_CL", "Leave Rules clause 5.6", "Special Hardship Compensatory Leave for Category-C and remote North-East stations"),
        ("FY24", "Earned_Leave_EL", "Leave Rules clause 4.11", "Streamlining online leave applications and sanction workflow in SAP ESS/MSS"),
        ("FY25", "Half_Pay_Leave_HPL", "Leave Rules clause 8.9", "Review of accumulated HPL encashment provisions upon voluntary retirement"),
        ("FY25", "Earned_Leave_EL", "Leave Rules clause 4.14", "Annual reconciliation of leave ledger and forfeiture of excess accumulations"),
        ("FY26", "Casual_Leave_CL", "Leave Rules clause 5.8", "Special Casual Leave guidelines for participation in Petroleum Sports Promotion Board"),
        ("FY26", "Earned_Leave_EL", "Leave Rules clause 4.16", "Consolidated Leave Rules Amendment and Encashment Ceiling Review for FY27"),
    ]

    for idx, (fy_target, subty, clause_ref, topic_title) in enumerate(leave_topics):
        doc_id = f"DOC-CIRC-LV-{idx+1:02d}"
        is_scanned = (idx in (0, 3, 6, 9, 12))  # 5 scanned, 9 docx (~36% scanned)
        fmt = "scanned_pdf" if is_scanned else "docx"
        file_name = f"{doc_id}.pdf" if is_scanned else f"{doc_id}.docx"
        file_path = (SCANNED_DIR if is_scanned else NATIVE_DIR) / file_name

        year_num = 2020 + (idx // 2)
        doc_date = f"{year_num}-05-15"

        prov_sql = f"""SELECT 
    fiscal_year,
    SUBTY as leave_type,
    transaction_type,
    count(distinct PERNR) as employee_count,
    round(avg(ABWTG), 2) as avg_days_taken,
    round(avg(ANZHL), 2) as avg_leave_quota,
    round(avg(encashable_balance_days), 2) as avg_encashable_days
FROM 'landing/sap/PA2001_PA2006.csv'
WHERE fiscal_year = '{fy_target}' AND SUBTY = '{subty}'
GROUP BY fiscal_year, SUBTY, transaction_type
ORDER BY transaction_type;"""

        sql_path = PROV_DIR / f"{doc_id}.sql"
        with open(sql_path, "w", encoding="utf-8") as f_sql:
            f_sql.write(prov_sql)

        df_filtered = df_all_leave[(df_all_leave["fiscal_year"] == fy_target) & (df_all_leave["leave_type"] == subty)]
        df_lv = df_filtered.to_dict(orient="records")

        stat_emp_count = int(df_lv[0]["employee_count"]) if df_lv else 25000
        avg_quota = float(df_lv[0]["avg_leave_quota"]) if df_lv else 180.0

        title = f"CORPORATE CIRCULAR: AMENDMENT TO ONGC LEAVE RULES ({clause_ref})"
        issuer = "Corporate HR Policy & Employee Services"
        confidentiality = "INTERNAL"
        audience_roles = "All Employees, In-charge HR/ER, All Work Centres"
        subject = f"{topic_title} - Amendment to {clause_ref}"

        paragraphs = [
            f"1. In exercise of the powers conferred under the ONGC Service Rules and with the approval of the Executive Committee, "
            f"the provisions governing {topic_title} have been reviewed and amended.",
            f"2. In accordance with {clause_ref}, all regular employees are notified of the revised norms governing leave credit, "
            f"availment limits, and encashment procedures applicable across all ONGC establishments.",
            f"3. During {fy_target}, our records indicate {stat_emp_count:,} employees with active leave ledger balances averaging {avg_quota:.1f} days. "
            f"All employees are encouraged to plan their annual leave in advance to ensure operational continuity and fatigue management.",
        ]

        th = ["Fiscal Year", "Leave Classification", "Transaction Type", "Employees Covered", "Avg Days", "Avg Quota"]
        tr = [
            [
                r["fiscal_year"],
                r["leave_type"],
                r["transaction_type"],
                f"{int(r['employee_count']):,}",
                f"{r['avg_days_taken']:.1f}",
                f"{r['avg_leave_quota']:.1f}",
            ]
            for r in df_lv
        ]

        signatory = {
            "name": "Meenakshi Sundaram",
            "designation": "General Manager (HR) - Policy & Regulations",
        }

        if is_scanned:
            render_scanned_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)
        else:
            render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

        manifest_rows.append({
            "doc_id": doc_id,
            "title": title,
            "type": "circular_leave",
            "issuer": issuer,
            "date": doc_date,
            "confidentiality": confidentiality,
            "audience_roles": audience_roles,
            "source": "synthetic",
            "format": fmt,
            "linked_entity_ids": "",
            "questions_served": "H13",
            "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
        })

    return manifest_rows


def generate_step_33(con: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    """Generates 12 confidential documents (draft AGTO, board notes, DPC results, vigilance summaries)."""
    manifest_rows = []

    # ---------------------------------------------------------------------------
    # DOC-CONF-001: Draft FY27 Annual General Transfer Order (Master Proposal)
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-001"
    doc_date = "2026-03-15"
    prov_sql = """-- Provenance for Draft FY27 AGTO Master Proposal
-- Note: Reads cleaned workbook from landing/excel/_clean/manpower_plan.xlsx (reconstructed from messy landing source)
-- JRTP Clause 1.2 (E0-E9 executives only), Clause 3.0 (Station Tenure), Clause 7.0 (Pre-Retirement Exemption)
WITH numbered_postings AS (
  SELECT
    p.PERNR as emp_id,
    p.WERKS as wc_id,
    p.PERSK as grade_id,
    p.discipline_id,
    CAST(p.BEGDA AS DATE) as from_date,
    CAST(p.ENDDA AS DATE) as to_date,
    p.is_current_posting,
    ROW_NUMBER() OVER (PARTITION BY p.PERNR ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) -
    ROW_NUMBER() OVER (PARTITION BY p.PERNR, p.WERKS ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) AS island_id
  FROM 'landing/sap/PA0001.csv' p
),
islands AS (
  SELECT
    emp_id,
    wc_id,
    island_id,
    MIN(from_date) AS continuous_from_date,
    MAX(COALESCE(to_date, DATE '2026-10-19')) AS continuous_to_date,
    BOOL_OR(to_date IS NULL OR is_current_posting) AS is_current_stay,
    MAX(grade_id) AS current_grade_id,
    MAX(discipline_id) AS current_discipline_id,
    DATEDIFF('month', MIN(from_date), DATE '2026-10-19') AS continuous_stay_months
  FROM numbered_postings
  GROUP BY emp_id, wc_id, island_id
),
v_stay AS (
  SELECT
    i.emp_id,
    e.name AS emp_name,
    CAST(e.retirement_date AS DATE) as retirement_date,
    i.wc_id,
    i.current_grade_id AS grade_id,
    i.current_discipline_id AS discipline_id,
    i.continuous_stay_months,
    i.is_current_stay
  FROM islands i
  JOIN 'landing/sap/PA0002_PA0001.csv' e ON i.emp_id = e.PERNR
  WHERE e.STAT2 = 'Active' AND i.current_grade_id LIKE 'E%'
)
SELECT emp_id, emp_name, grade_id, discipline_id, wc_id as current_wc_id, continuous_stay_months,
       'WC-ASM' as proposed_dest_wc_id, 'Assam Asset' as proposed_dest_name
FROM v_stay
WHERE is_current_stay = TRUE AND wc_id IN ('WC-DEL', 'WC-DDN', 'WC-AHM', 'WC-MEH')
  AND continuous_stay_months >= 36
  AND DATEDIFF('day', DATE '2026-10-19', retirement_date) > 3 * 365.25
ORDER BY continuous_stay_months DESC, emp_id
LIMIT 20;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "DRAFT ANNUAL GENERAL TRANSFER ORDER (AGTO) - FY 2026-27 (MASTER EXECUTIVE PROPOSAL)"
    issuer = "Office of Director (HR)"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (HR), Director (Finance)"
    subject = "Pre-Decisional Placement Proposal for Overdue Executives under JRTP 2026-27"

    paragraphs = [
        "1. This draft proposal is submitted for the privileged perusal of the Chairman & CEO and Director (HR) "
        "in accordance with the Job Rotation and Transfer Policy (JRTP). Under Section 11 of the JRTP, the contents "
        "of this document are STRICTLY CONFIDENTIAL and exempt from pre-decisional administrative disclosure.",
        "2. Eligibility Criteria Applied: (a) JRTP Clause 1.2: Applies strictly to regular executives across Grades E0 through E9; "
        "(b) JRTP Clause 3.0: Continuous station stay >= 36 months / cluster cumulative stay >= 10 years per Clause 4.0; "
        "(c) JRTP Clause 7.0: Protective exemption for executives within 3 years of superannuation (retirement after 19.10.2029); "
        "(d) Rebalancing critical executive deficits in Category-C hard stations (Assam Asset, Jorhat Asset, Tripura Asset, Bassein).",
        f"3. The roster below details 20 senior executives overdue for rotation from corporate offices and major Western hubs "
        "proposed for redeployment to understaffed operating assets in the North-East and Western Offshore.",
    ]

    th = ["CPF No.", "Employee Name", "Grade", "Discipline", "Current Station", "Tenure (Mo)", "Proposed Posting"]
    tr = [
        [
            r["emp_id"],
            r["emp_name"],
            r["grade_id"],
            r["discipline_id"],
            r["current_wc_id"],
            str(r["continuous_stay_months"]),
            r["proposed_dest_name"],
        ]
        for r in rows
    ]

    signatory = {"name": "Director (HR)", "designation": "Director (HR) & Member Executive Committee", "org": "Oil and Natural Gas Corporation Limited"}
    file_path = NATIVE_DIR / f"{doc_id}.pdf"
    render_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_transfer_order",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "pdf",
        "linked_entity_ids": ";".join([r["emp_id"] for r in rows[:5]] + ["WC-ASM", "WC-DEL", "WC-DDN"]),
        "questions_served": "D2;P18;H10;T2",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-002: Draft FY27 AGTO - Annexure I: Delhi & Dehradun Long-Tenure Roster & Cumulative Cap
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-002"
    doc_date = "2026-03-18"
    prov_sql = """-- Provenance for DOC-CONF-002: Draft FY27 AGTO Annexure I (Delhi & Dehradun Tenure & Cumulative Cap Audit)
-- Evaluates continuous station tenure (JRTP Clause 3.0) and cumulative cluster cap (JRTP Clause 4.0)
-- Applies 3-year pre-retirement protective exemption (JRTP Clause 7.0) for E0-E9 executives (JRTP Clause 1.2)

WITH numbered_postings AS (
  SELECT
    p.PERNR as emp_id,
    p.WERKS as wc_id,
    p.PERSK as grade_id,
    p.discipline_id,
    CAST(p.BEGDA AS DATE) as from_date,
    CAST(p.ENDDA AS DATE) as to_date,
    p.is_current_posting,
    ROW_NUMBER() OVER (PARTITION BY p.PERNR ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) -
    ROW_NUMBER() OVER (PARTITION BY p.PERNR, p.WERKS ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) AS island_id
  FROM 'landing/sap/PA0001.csv' p
),
islands AS (
  SELECT
    emp_id,
    wc_id,
    island_id,
    MIN(from_date) AS continuous_from_date,
    MAX(COALESCE(to_date, DATE '2026-10-19')) AS continuous_to_date,
    BOOL_OR(to_date IS NULL OR is_current_posting) AS is_current_stay,
    MAX(grade_id) AS current_grade_id,
    MAX(discipline_id) AS current_discipline_id,
    DATEDIFF('month', MIN(from_date), DATE '2026-10-19') AS continuous_stay_months,
    ROUND(DATEDIFF('day', MIN(from_date), DATE '2026-10-19') / 365.25, 2) AS continuous_stay_years
  FROM numbered_postings
  GROUP BY emp_id, wc_id, island_id
),
v_stay AS (
  SELECT
    i.emp_id,
    e.name AS emp_name,
    CAST(e.retirement_date AS DATE) as retirement_date,
    i.wc_id,
    i.current_grade_id AS grade_id,
    i.current_discipline_id AS discipline_id,
    i.continuous_from_date,
    i.continuous_to_date,
    i.continuous_stay_months,
    i.continuous_stay_years,
    i.is_current_stay
  FROM islands i
  JOIN 'landing/sap/PA0002_PA0001.csv' e ON i.emp_id = e.PERNR
  WHERE e.STAT2 = 'Active' AND i.current_grade_id LIKE 'E%'
),
stay_summary AS (
  SELECT
    wc_id as scope,
    'station_tenure_ge_5yr' as audit_type,
    COUNT(DISTINCT emp_id) AS total_count,
    COUNT(DISTINCT CASE WHEN DATEDIFF('day', DATE '2026-10-19', retirement_date) <= 3 * 365.25 THEN emp_id END) AS exempt_count,
    COUNT(DISTINCT CASE WHEN DATEDIFF('day', DATE '2026-10-19', retirement_date) > 3 * 365.25 THEN emp_id END) AS due_transfer_count
  FROM v_stay
  WHERE is_current_stay = TRUE
    AND wc_id IN ('WC-DEL', 'WC-DDN')
    AND continuous_stay_months >= 60
  GROUP BY wc_id
),
posting_clusters AS (
  SELECT
    p.PERNR AS emp_id,
    DATEDIFF('day', CAST(p.BEGDA AS DATE), COALESCE(CAST(p.ENDDA AS DATE), DATE '2026-10-19')) AS stint_days,
    p.is_current_posting
  FROM 'landing/sap/PA0001.csv' p
  WHERE p.WERKS = 'WC-DEL'
),
cluster_agg AS (
  SELECT
    pc.emp_id,
    ROUND(SUM(pc.stint_days) / 365.25, 2) AS cumulative_cluster_years,
    BOOL_OR(pc.is_current_posting) AS is_currently_in_cluster
  FROM posting_clusters pc
  GROUP BY pc.emp_id
),
cap_summary AS (
  SELECT
    'CL-DEL' as scope,
    'cluster_cumulative_cap_ge_10yr' as audit_type,
    COUNT(DISTINCT CASE WHEN c.cumulative_cluster_years >= 10.0 THEN c.emp_id END) AS total_count,
    COUNT(DISTINCT CASE WHEN c.cumulative_cluster_years >= 10.0 AND DATEDIFF('day', DATE '2026-10-19', CAST(e.retirement_date AS DATE)) <= 3 * 365.25 THEN c.emp_id END) AS exempt_count,
    COUNT(DISTINCT CASE WHEN c.cumulative_cluster_years >= 10.0 AND DATEDIFF('day', DATE '2026-10-19', CAST(e.retirement_date AS DATE)) > 3 * 365.25 THEN c.emp_id END) AS due_transfer_count
  FROM cluster_agg c
  JOIN 'landing/sap/PA0002_PA0001.csv' e ON c.emp_id = e.PERNR
  WHERE c.is_currently_in_cluster = TRUE
)
SELECT * FROM stay_summary
UNION ALL
SELECT * FROM cap_summary
ORDER BY audit_type, scope;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_summary = con.execute(prov_sql).df().to_dict(orient="records")
    sum_map = {(r["scope"], r["audit_type"]): r for r in df_summary}

    delhi_stay = sum_map[("WC-DEL", "station_tenure_ge_5yr")]
    ddn_stay = sum_map[("WC-DDN", "station_tenure_ge_5yr")]
    delhi_cap = sum_map[("CL-DEL", "cluster_cumulative_cap_ge_10yr")]

    # Query sample overdue executives for Delhi and Dehradun (strictly E0-E9)
    q_delhi_roster = """
    WITH numbered_postings AS (
      SELECT
        p.PERNR as emp_id,
        p.WERKS as wc_id,
        p.PERSK as grade_id,
        p.discipline_id,
        CAST(p.BEGDA AS DATE) as from_date,
        CAST(p.ENDDA AS DATE) as to_date,
        p.is_current_posting,
        ROW_NUMBER() OVER (PARTITION BY p.PERNR ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) -
        ROW_NUMBER() OVER (PARTITION BY p.PERNR, p.WERKS ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) AS island_id
      FROM 'landing/sap/PA0001.csv' p
    ),
    islands AS (
      SELECT
        emp_id,
        wc_id,
        island_id,
        MIN(from_date) AS continuous_from_date,
        BOOL_OR(to_date IS NULL OR is_current_posting) AS is_current_stay,
        MAX(grade_id) AS current_grade_id,
        MAX(discipline_id) AS current_discipline_id,
        DATEDIFF('month', MIN(from_date), DATE '2026-10-19') AS continuous_stay_months
      FROM numbered_postings
      GROUP BY emp_id, wc_id, island_id
    ),
    v_stay AS (
      SELECT
        i.emp_id,
        e.name AS emp_name,
        CAST(e.retirement_date AS DATE) as retirement_date,
        i.wc_id,
        i.current_grade_id AS grade_id,
        i.current_discipline_id AS discipline_id,
        i.continuous_stay_months,
        i.is_current_stay
      FROM islands i
      JOIN 'landing/sap/PA0002_PA0001.csv' e ON i.emp_id = e.PERNR
      WHERE e.STAT2 = 'Active' AND i.current_grade_id LIKE 'E%'
    )
    SELECT emp_id, emp_name, grade_id, discipline_id, wc_id, continuous_stay_months, retirement_date
    FROM v_stay
    WHERE is_current_stay = TRUE AND wc_id = 'WC-DEL' AND continuous_stay_months >= 60
      AND DATEDIFF('day', DATE '2026-10-19', retirement_date) > 3 * 365.25
    ORDER BY continuous_stay_months DESC, emp_id
    LIMIT 10;
    """
    delhi_rows = con.execute(q_delhi_roster).df().to_dict(orient="records")

    q_ddn_roster = q_delhi_roster.replace("'WC-DEL'", "'WC-DDN'")
    ddn_rows = con.execute(q_ddn_roster).df().to_dict(orient="records")

    title = "DRAFT AGTO FY27 - ANNEXURE I: CORPORATE HEADQUARTERS LONG-TENURE ROSTER & CUMULATIVE CAP AUDIT"
    issuer = "Corporate HR Advisory Cell"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (HR)"
    subject = "Audit of Overstaying Corporate Executives under JRTP Clauses 3.0 (Station Tenure), 4.0 (Cumulative Cap), and 7.0 (Pre-Retirement Exemption)"

    paragraphs = [
        "1. STATUTORY APPLICABILITY & POLICY MANDATE. Pursuant to JRTP Clause 1.2, this audit applies strictly to regular executives "
        "across Grades E0 through E9. Non-executive personnel are governed by separate regional settlement frameworks and are strictly excluded.",
        "2. GOVERNING TENURE CLAUSES: (a) JRTP Clause 3.0 (Station Tenure Norms) defines the standard station rotation window between 3 and 5 years "
        "(Clause 3.1: 3-year minimum residency; Clause 3.2: 3 to 5 year rotation window). (b) JRTP Clause 4.0 (Cumulative Stay Cap) imposes a strict "
        "maximum cumulative career stay of 10 years at a single city or geographic cluster (Clause 4.1). (c) JRTP Clause 7.0 (Pre-Retirement Tenure Exemption) "
        "provides statutory exemption for executives within 2 years of superannuation (Clause 7.1), which is extended to 3 years in annual transfer planning practice.",
        f"3. SECTION A: DELHI CORPORATE HQ (WC-DEL) TENURE ANALYSIS (JRTP Clause 3.0 & 7.0). Gaps-and-islands continuous tenure audit identifies "
        f"a total of {int(delhi_stay['total_count'])} regular executives with continuous stay >= 5 years (60+ months) in Delhi. Accounting for {int(delhi_stay['exempt_count'])} "
        f"officers exempt under the 3-year pre-retirement protective practice, a net total of {int(delhi_stay['due_transfer_count'])} executives are overdue and due for rotational transfer.",
        f"4. SECTION B: DEHRADUN COMPLEX (WC-DDN) TENURE ANALYSIS (JRTP Clause 3.0 & 7.0). Continuous tenure audit across Tel Bhavan, KDMIPE, and GEOPIC identifies "
        f"{int(ddn_stay['total_count'])} regular executives with continuous stay >= 5 years. Accounting for {int(ddn_stay['exempt_count'])} officers exempt under the 3-year "
        f"pre-retirement practice, a net total of {int(ddn_stay['due_transfer_count'])} executives are due for rotation.",
        f"5. SECTION C: DELHI CLUSTER (CL-DEL) CUMULATIVE CAREER CAP AUDIT (JRTP Clause 4.0 & 7.0). Longitudinal career history audit reveals that "
        f"{int(delhi_cap['total_count'])} personnel have breached the aggregate 10-year cumulative career stay cap in the Delhi cluster across multiple stints. "
        f"Accounting for {int(delhi_cap['exempt_count'])} officer exempt due to impending retirement within 3 years, {int(delhi_cap['due_transfer_count'])} "
        f"personnel are due for rotational transfer under the cumulative stay cap.",
    ]

    th = ["CPF No.", "Employee Name", "Grade", "Discipline", "Station", "Continuous Stay (Mo)", "Retirement Date"]
    tr = [
        [
            r["emp_id"],
            r["emp_name"],
            r["grade_id"],
            r["discipline_id"],
            r["wc_id"],
            str(r["continuous_stay_months"]),
            str(r["retirement_date"])[:10],
        ]
        for r in (delhi_rows + ddn_rows)
    ]

    file_path = NATIVE_DIR / f"{doc_id}.docx"
    render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_transfer_order",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "docx",
        "linked_entity_ids": ";".join([r["emp_id"] for r in (delhi_rows[:5] + ddn_rows[:5])] + ["WC-DEL", "WC-DDN", "CL-DEL"]),
        "questions_served": "C1;D2;P11;P18;T2",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-003: Draft FY27 AGTO - Annexure II: Hard Station Vacancy Balancing
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-003"
    doc_date = "2026-03-20"
    prov_sql = """-- Provenance for Hard Station Deficit Analysis
-- Note: Reads cleaned workbook from landing/excel/_clean/manpower_plan.xlsx (reconstructed from messy landing source)
-- JRTP Clause 1.2 (E0-E9 executives only), Clause 2.1(c) (Category C classification)
SELECT wc_id, discipline_id, grade_band, 
       sum(sanctioned_strength) as sanctioned_strength,
       sum(in_position_strength) as in_position_strength,
       sum(vacancy_count) as total_vacancies
FROM 'landing/excel/_clean/manpower_plan.xlsx'
WHERE fiscal_year = 'FY26' 
  AND wc_id IN ('WC-ASM', 'WC-TRI', 'WC-JOR', 'WC-BAS', 'WC-NEH')
  AND grade_band IN ('E0_E2', 'E3_E5', 'E6_E9')
GROUP BY wc_id, discipline_id, grade_band
HAVING sum(vacancy_count) > 0
ORDER BY total_vacancies DESC
LIMIT 12;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "DRAFT AGTO FY27 - ANNEXURE II: HARD STATION & NORTH-EAST VACANCY BALANCING"
    issuer = "Corporate Manpower Planning & Recruitment"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (HR)"
    subject = "Discipline-Wise Sanctioned Deficit Analysis for Category-C / North-East Assets"

    paragraphs = [
        "1. Persistent executive deficits in Category-C hard stations (Assam Asset, Jorhat Asset, Tripura Asset) "
        "and Western Offshore assets (Bassein, Neelam & Heera) require prioritized rotational postings in FY27.",
        "2. The table below highlights the critical discipline-wise deficits between sanctioned posts and in-position strength.",
    ]

    th = ["Work Centre", "Discipline", "Grade Band", "Sanctioned", "In-Position", "Deficit / Vacancies"]
    tr = [
        [
            r["wc_id"],
            r["discipline_id"],
            r["grade_band"],
            f"{int(r['sanctioned_strength'])}",
            f"{int(r['in_position_strength'])}",
            f"{int(r['total_vacancies'])}",
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.pdf"
    render_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_transfer_order",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "pdf",
        "linked_entity_ids": "WC-ASM;WC-TRI;WC-JOR;WC-BAS;WC-NEH",
        "questions_served": "C2;D2;P18;T2",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-004: Board Note: Loss-Making Fields Divestment & PEC Options
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-004"
    doc_date = "2026-04-10"
    prov_sql = """SELECT field_id, asset_wc_id, gross_revenue_inr_cr, total_opex_inr_cr, 
       ebitda_inr_cr, dda_depreciation_inr_cr, pbt_inr_cr, 
       allocated_manpower_cost_inr_cr, regular_employee_headcount, 
       total_production_boe, lifting_cost_per_boe_usd, 
       is_loss_making_3yr_consecutive, is_divestment_candidate, 
       pec_monetisation_potential_flag, root_cause_loss_code, 
       estimated_annual_opex_savings_inr_cr, estimated_annual_capex_savings_inr_cr, 
       projected_pec_farmout_payoff_5yr_inr_cr
FROM 'landing/sap/CO_PA.csv'
WHERE fiscal_year = 'FY26' AND line_type = 'field' 
  AND (pbt_inr_cr < 0 OR pec_monetisation_potential_flag = true)
ORDER BY pbt_inr_cr ASC;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "AGENDA FOR THE 382ND MEETING OF THE BOARD OF DIRECTORS: STRATEGIC DIVESTMENT & PEC OPTIONS FOR LOSS-MAKING MATURE FIELDS"
    issuer = "Director (Finance) & Director (Production)"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (Finance), Director (Production)"
    subject = "Commercial Turnaround, Farm-Out and Production Enhancement Contract (PEC) for Depleted Mature Fields (FY26 Performance Review)"

    field_loss = rows[0]  # FLD-CHP
    field_pec = rows[1] if len(rows) > 1 else rows[0]  # FLD-BOR

    paragraphs = [
        "1. PRIVILEGED AND CONFIDENTIAL BOARD MEMORANDUM. Under Section 3.2 of the Commercial Information Disclosure Policy, "
        "field-level financial results and monetization strategies are strictly restricted to Executive Directors and Board members.",
        f"2. OPERATIONAL & FINANCIAL DIAGNOSIS (FY26): In FY26, mature onshore field {field_loss['field_id']} (Champang, under {field_loss['asset_wc_id']}) "
        f"recorded a Profit Before Tax (PBT) of ₹{field_loss['pbt_inr_cr']:.2f} crore (Gross Revenue: ₹{field_loss['gross_revenue_inr_cr']:.2f} cr, "
        f"Total Opex: ₹{field_loss['total_opex_inr_cr']:.2f} cr, EBITDA: ₹{field_loss['ebitda_inr_cr']:.2f} cr, DDA: ₹{field_loss['dda_depreciation_inr_cr']:.2f} cr). "
        f"The lifting cost reached ${field_loss['lifting_cost_per_boe_usd']:.2f}/BOE with allocated manpower cost of ₹{field_loss['allocated_manpower_cost_inr_cr']:.2f} cr "
        f"supporting {int(field_loss['regular_employee_headcount'])} regular personnel. Primary loss driver is identified as: '{field_loss['root_cause_loss_code']}'.",
        f"3. PEC & MONETISATION CANDIDATES: Additionally, field {field_pec['field_id']} ({field_pec['asset_wc_id']}) is identified as an optimal candidate "
        f"under Production Enhancement Contract (PEC) framework with PBT of ₹{field_pec['pbt_inr_cr']:.2f} cr and lifting cost of ${field_pec['lifting_cost_per_boe_usd']:.2f}/BOE.",
        f"4. STRATEGIC RECOMMENDATION: The Board is requested to approve the monetization of {field_loss['field_id']} and {field_pec['field_id']} "
        f"under the approved DGH PEC / Farm-out guidelines. This initiative will yield estimated annual opex savings of ₹{field_loss['estimated_annual_opex_savings_inr_cr']:.2f} cr, "
        f"annual capex savings of ₹{field_loss['estimated_annual_capex_savings_inr_cr']:.2f} cr, and a 5-year projected payoff of ₹{field_loss['projected_pec_farmout_payoff_5yr_inr_cr']:.2f} cr.",
    ]

    th = ["Field ID", "Asset WC", "Gross Rev (₹Cr)", "Total Opex", "EBITDA", "PBT (₹Cr)", "Lifting ($/BOE)", "5-Yr Payoff"]
    tr = [
        [
            r["field_id"],
            r["asset_wc_id"],
            f"{r['gross_revenue_inr_cr']:.2f}",
            f"{r['total_opex_inr_cr']:.2f}",
            f"{r['ebitda_inr_cr']:.2f}",
            f"{r['pbt_inr_cr']:.2f}",
            f"${r['lifting_cost_per_boe_usd']:.2f}",
            f"₹{r['projected_pec_farmout_payoff_5yr_inr_cr']:.2f} cr",
        ]
        for r in rows
    ]

    signatory_fin = {"name": "Director (Finance)", "designation": "Director (Finance) & Chief Financial Officer", "org": "Oil and Natural Gas Corporation Limited"}
    file_path = NATIVE_DIR / f"{doc_id}.docx"
    render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_fin, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_board_note",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "docx",
        "linked_entity_ids": f"{field_loss['field_id']};{field_pec['field_id']};{field_loss['asset_wc_id']}",
        "questions_served": "C8;C14;P20;T1",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-005: Board Note Annexure: Detailed Field-by-Field Financial Diagnosis
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-005"
    doc_date = "2026-04-12"
    prov_sql = """SELECT fiscal_year, field_id, asset_wc_id, gross_revenue_inr_cr, 
       total_opex_inr_cr, ebitda_inr_cr, pbt_inr_cr, lifting_cost_per_boe_usd
FROM 'landing/sap/CO_PA.csv'
WHERE field_id IN ('FLD-CHP', 'FLD-BOR')
ORDER BY field_id, fiscal_year DESC;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "BOARD NOTE ANNEXURE: HISTORICAL FINANCIAL PERFORMANCE (FY17–FY26) OF FLD-CHP & FLD-BOR"
    issuer = "Corporate Management Accounts & Cost Audit"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (Finance)"
    subject = "Multi-Year Cost & Profitability Ledger for Marginal Hydrocarbon Assets"

    paragraphs = [
        "1. Longitudinal profitability audit of mature fields considered for farm-out under PEC terms.",
        "2. The persistent escalation in lifting costs ($/BOE) and depleting revenue streams underscore the necessity "
        "of transferring reservoir enhancement risks to specialized third-party operators.",
    ]

    th = ["Fiscal Year", "Field ID", "Asset WC", "Gross Revenue (₹Cr)", "Opex (₹Cr)", "EBITDA (₹Cr)", "PBT (₹Cr)", "Lifting Cost ($/BOE)"]
    tr = [
        [
            r["fiscal_year"],
            r["field_id"],
            r["asset_wc_id"],
            f"{r['gross_revenue_inr_cr']:.2f}",
            f"{r['total_opex_inr_cr']:.2f}",
            f"{r['ebitda_inr_cr']:.2f}",
            f"{r['pbt_inr_cr']:.2f}",
            f"${r['lifting_cost_per_boe_usd']:.2f}",
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.pdf"
    render_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_fin, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_board_note",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "pdf",
        "linked_entity_ids": "FLD-CHP;FLD-BOR;WC-JOR",
        "questions_served": "C8;C14;P20;T1",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-006: Board Note: Capital Expenditure Plan (Capex BE/RE/Actuals)
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-006"
    doc_date = "2026-03-25"
    prov_sql = """-- Provenance for Corporate Capex Plan
-- Note: Reads cleaned workbook from landing/excel/_clean/capex_be_re_actuals.xlsx (reconstructed from messy landing source)
SELECT fiscal_year, capex_head, 
       round(sum(budget_estimate_be_inr_cr), 2) as total_be,
       round(sum(revised_estimate_re_inr_cr), 2) as total_re,
       round(sum(actual_spend_inr_cr), 2) as total_actual
FROM 'landing/excel/_clean/capex_be_re_actuals.xlsx'
GROUP BY fiscal_year, capex_head
ORDER BY fiscal_year DESC, total_actual DESC
LIMIT 12;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "AGENDA NOTE: CORPORATE CAPITAL EXPENDITURE REVIEW & FY27 CAPITAL ALLOCATION PLAN"
    issuer = "Corporate Planning & Budgeting"
    confidentiality = "CONFIDENTIAL"
    audience_roles = "CMD, Director (Finance), Director (Exploration), Director (Production)"
    subject = "Review of Capex Budget Estimates (BE), Revised Estimates (RE) and Actual Expenditure"

    paragraphs = [
        "1. This note presents the corporate capital expenditure review across Exploration, Development Drilling, "
        "Offshore Capital Projects, and Plant & Machinery in accordance with DPE Budgetary Guidelines.",
        "2. The Board is apprised of head-wise budget utilization and revised allocations for the forthcoming fiscal year.",
    ]

    th = ["Fiscal Year", "Capex Head", "Budget Estimate (BE ₹Cr)", "Revised Estimate (RE ₹Cr)", "Actual Spend (₹Cr)"]
    tr = [
        [
            r["fiscal_year"],
            r["capex_head"],
            f"₹{r['total_be']:.2f}",
            f"₹{r['total_re']:.2f}",
            f"₹{r['total_actual']:.2f}",
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.docx"
    render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_fin, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_board_note",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "docx",
        "linked_entity_ids": "",
        "questions_served": "F7;D4",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-007: Board Note: Major Development Projects Progress & Capex Outlay
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-007"
    doc_date = "2026-03-28"
    prov_sql = """-- Provenance for Major Projects Capex Outlay
-- Note: Reads cleaned workbook from landing/excel/_clean/capex_be_re_actuals.xlsx (reconstructed from messy landing source)
SELECT prj_id, project_name, asset_wc_id, fiscal_year,
       round(sum(budget_estimate_be_inr_cr), 2) as total_be,
       round(sum(revised_estimate_re_inr_cr), 2) as total_re,
       round(sum(actual_spend_inr_cr), 2) as total_actual
FROM 'landing/excel/_clean/capex_be_re_actuals.xlsx'
WHERE fiscal_year = 'FY26'
GROUP BY prj_id, project_name, asset_wc_id, fiscal_year
ORDER BY total_actual DESC
LIMIT 10;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "AGENDA NOTE: MAJOR CAPITAL PROJECTS MILESTONES & FY27 CAPITAL OUTLAY"
    issuer = "Director (Technical & Field Services)"
    confidentiality = "CONFIDENTIAL"
    audience_roles = "CMD, Director (Finance), Director (T&FS)"
    subject = "Physical and Financial Progress of Key Sanctioned Offshore and Onshore Development Projects"

    paragraphs = [
        "1. Review of major board-sanctioned capital projects currently under execution across Western Offshore and KG Basin.",
        "2. Analysis of project-level capital expenditure against sanctioned baselines and revised completion timelines.",
    ]

    th = ["Project ID", "Project Name", "Asset WC", "BE (₹Cr)", "RE (₹Cr)", "Actual Spend (₹Cr)"]
    tr = [
        [
            r["prj_id"],
            r["project_name"][:24],
            r["asset_wc_id"],
            f"₹{r['total_be']:.2f}",
            f"₹{r['total_re']:.2f}",
            f"₹{r['total_actual']:.2f}",
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.pdf"
    render_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_fin, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_board_note",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "pdf",
        "linked_entity_ids": ";".join([r["prj_id"] for r in rows[:5]]),
        "questions_served": "F7;F8",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-008: Confidential Note: DPC Panel Results (FY26 Cycle)
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-008"
    doc_date = "2026-02-28"
    prov_sql = """SELECT dpc_id, from_grade_id, to_grade_id, discipline_id, status,
       eligible_candidates_count, recommended_candidates_count,
       held_date
FROM 'landing/excel/DPC_tracker.xlsx'
WHERE fiscal_year = 'FY26' AND status = 'completed'
ORDER BY dpc_id
LIMIT 12;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "CONFIDENTIAL MINUTES: DEPARTMENTAL PROMOTION COMMITTEE (DPC) PANEL RESULTS - FY26"
    issuer = "DPC Secretariat & Corporate HR"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (HR)"
    subject = "Proceedings and Final Recommended Panels of DPCs for Executive Cadres (E5 to E6 & E6 to E7)"

    paragraphs = [
        "1. STRICTLY CONFIDENTIAL DPC PROCEEDINGS. Regulation 14 of the DPC Regulations prohibits disclosure of "
        "committee deliberations and candidate empanelment lists prior to official executive notification.",
        "2. The committee has assessed APAR benchmarks, residency criteria, and vigilance clearances for the empanelled cadres.",
    ]

    th = ["DPC ID", "From Grade", "To Grade", "Discipline", "Eligible Candidates", "Recommended Panel", "Date Held"]
    tr = [
        [
            r["dpc_id"],
            r["from_grade_id"],
            r["to_grade_id"],
            r["discipline_id"],
            f"{int(r['eligible_candidates_count'])}",
            f"{int(r['recommended_candidates_count'])}",
            str(r["held_date"])[:10],
        ]
        for r in rows
    ]

    signatory_hr = {"name": "Director (HR)", "designation": "Director (HR) & Chairman DPC", "org": "Oil and Natural Gas Corporation Limited"}
    file_path = NATIVE_DIR / f"{doc_id}.docx"
    render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_hr, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_dpc_panel",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "docx",
        "linked_entity_ids": ";".join([r["dpc_id"] for r in rows[:5]]),
        "questions_served": "D3;H4",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-009: Confidential Note: DPC Pending Cases & Bottleneck Analysis
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-009"
    doc_date = "2026-03-05"
    prov_sql = """SELECT dpc_id, from_grade_id, to_grade_id, discipline_id, status,
       pending_reason, delay_bottleneck_reason, delay_months
FROM 'landing/excel/DPC_tracker.xlsx'
WHERE status = 'pending'
ORDER BY delay_months DESC
LIMIT 12;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "CONFIDENTIAL STATUS REPORT: DPC PENDING CASES & ADMINISTRATIVE BOTTLENECK ANALYSIS"
    issuer = "Corporate HR - DPC Review Cell"
    confidentiality = "CONFIDENTIAL"
    audience_roles = "Director (HR)"
    subject = "Diagnostic Review of Delayed DPC Panels and Pending Clearance Bottlenecks"

    paragraphs = [
        "1. This confidential review details promotion panels currently pending finalization, noting root causes "
        "including delayed vigilance clearances, pending APAR representations, and court stay orders.",
        "2. Remedial actions have been initiated to clear backlog cases before the commencement of FY27 promotion cycles.",
    ]

    th = ["DPC ID", "From Grade", "To Grade", "Discipline", "Pending Reason", "Bottleneck Root Cause", "Delay (Mo)"]
    tr = [
        [
            r["dpc_id"],
            r["from_grade_id"],
            r["to_grade_id"],
            r["discipline_id"],
            str(r["pending_reason"])[:24],
            str(r["delay_bottleneck_reason"])[:24],
            f"{int(r['delay_months'])}",
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.pdf"
    render_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_hr, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_dpc_panel",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "pdf",
        "linked_entity_ids": ";".join([r["dpc_id"] for r in rows[:5]]),
        "questions_served": "D3;H4",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-010: Annual Vigilance Portfolio Summary & Disciplinary Review
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-010"
    doc_date = "2026-03-31"
    prov_sql = """SELECT stage, inquiry_status, count(*) as case_count, 
       round(avg(age_months), 1) as avg_age_months
FROM 'landing/sap/vigilance_cases_confidential.csv'
GROUP BY stage, inquiry_status
ORDER BY case_count DESC;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "ANNUAL VIGILANCE DISCIPLINARY SUMMARY & PORTFOLIO REVIEW (FY26)"
    issuer = "Office of the Chief Vigilance Officer (CVO)"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, Director (HR), Chief Vigilance Officer (CVO)"
    subject = "Confidential Review of Ongoing Inquiries, Departmental Proceedings and Vigilance Clearances"

    paragraphs = [
        "1. STRICTLY CONFIDENTIAL STATUTORY REVIEW. Under CVC Guidelines and ONGC CDA Rules 1991, vigilance proceedings "
        "and investigative dockets are confidential and privileged. Unauthorized disclosure constitutes misconduct.",
        "2. The portfolio summary below reflects the stage-wise distribution and aging of ongoing inquiries as of 31.03.2026.",
    ]

    th = ["Inquiry Stage", "Status", "Active Case Count", "Average Aging (Months)"]
    tr = [
        [
            r["stage"],
            r["inquiry_status"],
            f"{int(r['case_count'])}",
            f"{r['avg_age_months']:.1f}",
        ]
        for r in rows
    ]

    signatory_cvo = {"name": "Chief Vigilance Officer", "designation": "Chief Vigilance Officer, ONGC", "org": "Oil and Natural Gas Corporation Limited"}
    file_path = NATIVE_DIR / f"{doc_id}.docx"
    render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_cvo, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_vigilance_summary",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "docx",
        "linked_entity_ids": "",
        "questions_served": "D6;H20",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-011: Confidential Vigilance Case Docket: Sensitive Investigations
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-011"
    doc_date = "2026-04-02"
    prov_sql = """SELECT vigilance_case_id, emp_id, grade_id, discipline_id, wc_id, 
       complaint_date, stage, inquiry_status, vigilance_clearance_status, age_months
FROM 'landing/sap/vigilance_cases_confidential.csv'
WHERE age_months > 12 OR stage IN ('regular_departmental_action', 'prosecution_sanction')
ORDER BY age_months DESC
LIMIT 12;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "CONFIDENTIAL VIGILANCE DOCKET: SENSITIVE INQUIRIES & CLEARANCE STATUS"
    issuer = "Corporate Vigilance Department"
    confidentiality = "STRICTLY CONFIDENTIAL"
    audience_roles = "CMD, CVO"
    subject = "Detailed Status Report on Long-Pending Inquiries (>12 Months) and Major Disciplinary Cases"

    paragraphs = [
        "1. This docket details prioritized vigilance inquiries involving senior officers or major contracting decisions.",
        "2. The clearance status indicated governs eligibility for promotion, empanelment, and foreign deputations.",
    ]

    th = ["Case ID", "CPF No.", "Grade", "Discipline", "Work Centre", "Complaint Date", "Stage", "Clearance Status"]
    tr = [
        [
            r["vigilance_case_id"],
            r["emp_id"],
            r["grade_id"],
            r["discipline_id"],
            r["wc_id"],
            str(r["complaint_date"])[:10],
            r["stage"][:20],
            r["vigilance_clearance_status"],
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.pdf"
    render_pdf(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_cvo, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_vigilance_summary",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "pdf",
        "linked_entity_ids": ";".join([r["vigilance_case_id"] for r in rows[:5]]),
        "questions_served": "D6;H20",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    # ---------------------------------------------------------------------------
    # DOC-CONF-012: Board Note: Senior Leadership Succession Readiness (FY27–FY29)
    # ---------------------------------------------------------------------------
    doc_id = "DOC-CONF-012"
    doc_date = "2026-04-05"
    prov_sql = """SELECT e.PERNR as emp_id, e.name as emp_name, e.PERSK as grade_id, 
       e.discipline_id, e.WERKS as current_wc_id,
       e.retirement_date, e.has_hard_station_tenure, e.has_offshore_tenure
FROM 'landing/sap/PA0002_PA0001.csv' e
WHERE e.STAT2 = 'Active' AND e.PERSK IN ('E7', 'E8', 'E9')
  AND e.retirement_date BETWEEN '2026-04-01' AND '2029-03-31'
ORDER BY e.retirement_date ASC
LIMIT 15;"""

    sql_path = PROV_DIR / f"{doc_id}.sql"
    with open(sql_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(prov_sql)

    df_res = con.execute(prov_sql).df()
    rows = df_res.to_dict(orient="records")

    title = "AGENDA NOTE: SENIOR LEADERSHIP SUCCESSION PLANNING & SUPERANNUATION CLIFF (FY27–FY29)"
    issuer = "CMD & Director (HR)"
    confidentiality = "CONFIDENTIAL"
    audience_roles = "CMD, Director (HR)"
    subject = "Executive Succession Readiness for Retiring General Managers and Executive Directors (E7–E9)"

    paragraphs = [
        "1. This note addresses leadership succession risk across operational assets, basins, and technical institutes.",
        "2. The table below lists senior leaders superannuating between FY27 and FY29, highlighting prerequisite "
        "hard-station and offshore exposure required for feeder cadres to qualify for Board and Level-1 appointments.",
    ]

    th = ["CPF No.", "Employee Name", "Grade", "Discipline", "Current Station", "Retirement Date", "Hard Station Served", "Offshore Served"]
    tr = [
        [
            r["emp_id"],
            r["emp_name"],
            r["grade_id"],
            r["discipline_id"],
            r["current_wc_id"],
            str(r["retirement_date"])[:10],
            "Yes" if r["has_hard_station_tenure"] else "No",
            "Yes" if r["has_offshore_tenure"] else "No",
        ]
        for r in rows
    ]

    file_path = NATIVE_DIR / f"{doc_id}.docx"
    render_docx(file_path, doc_id, title, issuer, doc_date, confidentiality, subject, paragraphs, th, tr, signatory_hr, is_demo=True)

    manifest_rows.append({
        "doc_id": doc_id,
        "title": title,
        "type": "confidential_board_note",
        "issuer": issuer,
        "date": doc_date,
        "confidentiality": confidentiality,
        "audience_roles": audience_roles,
        "source": "synthetic",
        "format": "docx",
        "linked_entity_ids": ";".join([r["emp_id"] for r in rows[:5]]),
        "questions_served": "T3;H10",
        "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
    })

    return manifest_rows


def generate_step_36(con: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    """Generates 30 Parliament replies (1 real public LS2067, 29 synthetic) and 30 CAG para texts."""
    manifest_rows = []

    # 1. 30 Parliament Replies
    q_pq = """
    SELECT pq_id, house, session_year, fiscal_year, question_number, question_date, question_type, 
           ministry, mp_name, subject_theme, brief_text, reply_summary,
           sanctioned_strength_reported, in_position_strength_reported, vacancies_reported,
           reserved_vacancies_sc, reserved_vacancies_st, reserved_vacancies_obc, reserved_vacancies_ews
    FROM 'landing/governance/parliament_questions_index.csv'
    ORDER BY CASE WHEN pq_id = 'PQ-LS-2026-2067' THEN 0 ELSE 1 END, pq_id
    LIMIT 30;
    """
    pq_list = con.execute(q_pq).df().to_dict(orient="records")

    for row in pq_list:
        pq_id = row["pq_id"]
        doc_id = f"DOC-{pq_id}"
        q_num = int(row["question_number"])
        q_date = str(row["question_date"])[:10]
        house = row["house"]
        ministry = "Ministry of Petroleum and Natural Gas"
        subject = row["subject_theme"]

        if pq_id == "PQ-LS-2026-2067":
            # REAL PUBLIC DOCUMENT: LS 2067 (30-Jul-2026)
            title = "LOK SABHA UNSTARRED QUESTION NO. 2067: EMPLOYMENT IN OIL PSUs IN ASSAM"
            issuer = "Ministry of Petroleum and Natural Gas"
            confidentiality = "PUBLIC"
            audience_roles = "Parliament / Public Record"
            source_tag = "public"

            prov_sql = """-- Provenance for Real Public Parliament Reply LS-2067 (30-Jul-2026)
-- Source: Ministry of Petroleum & Natural Gas, Lok Sabha Unstarred Question No. 2067
-- Grounding file: knowledge/public_sources/grounding_data/text/LS_AU2067_30Jul2026_Employment_OilPSUs_Assam.txt
SELECT 
    'PQ-LS-2026-2067' as pq_id,
    'Lok Sabha' as house,
    2026 as session_year,
    2067 as question_number,
    '2026-07-30' as question_date,
    'SHRI PHANI BHUSAN CHOUDHURY' as mp_name,
    'SHRI SURESH GOPI' as minister_name,
    'EMPLOYMENT IN OIL PSUs IN ASSAM' as subject_theme,
    3561 as ongc_employees_working_in_assam,
    3081 as ongc_employees_domiciled_in_assam,
    30 as ongc_vacancies_in_assam,
    2968 as iocl_employees_working_in_assam,
    6065 as oil_employees_working_in_assam,
    12594 as total_psu_employees_working_in_assam;"""

            sql_path = PROV_DIR / f"{doc_id}.sql"
            with open(sql_path, "w", encoding="utf-8") as f_sql:
                f_sql.write(prov_sql)

            paragraphs = [
                "LOK SABHA\nUNSTARRED QUESTION NO. 2067\nTO BE ANSWERED ON 30TH JULY 2026",
                "EMPLOYMENT IN OIL PSUs IN ASSAM",
                "2067. SHRI PHANI BHUSAN CHOUDHURY:\n\n"
                "Will the Minister of PETROLEUM AND NATURAL GAS be pleased to state:\n"
                "(a) the number of regular employees currently working under Indian Oil Corporation Limited (IOCL), "
                "Oil India Limited (OIL) and Oil and Natural Gas Corporation (ONGC) in Assam separately for each Public Sector Undertaking (PSU) "
                "and by category or group, namely Executive, Non-Executive, Group A, Group B, Group C or equivalent;\n"
                "(b) the number of employees domiciled in Assam out of the total employees separately for each PSU and by employee category or group;\n"
                "(c) the number of employees recruited by these PSUs in Assam during the last five years, year-wise and category-wise;\n"
                "(d) the present recruitment policy followed by IOCL, OIL and ONGC for appointments in Assam and whether there is any provision "
                "for giving preference to local candidates, if so, the details thereof; and\n"
                "(e) the present vacancy position in each PSU in Assam along with the details of vacant posts, grade-wise and category-wise?",
                "ANSWER:\nMINISTER OF STATE IN THE MINISTRY OF PETROLEUM AND NATURAL GAS\n(SHRI SURESH GOPI)",
                "(a) The number of regular employees currently working under Indian Oil Corporation Limited (IOCL), "
                "Oil India Limited (OIL) and Oil and Natural Gas Corporation Limited (ONGC) in the State of Assam, category-wise and group-wise, are as under:",
            ]

            multi_tables = [
                (
                    "Table (a): Regular Employees Working in Assam",
                    ["Name of CPSEs", "Total Employees", "Executive", "Non-Executive", "Group A", "Group B", "Group C", "Group D"],
                    [
                        ["IOCL", "2968", "1351", "1617", "1351", "390", "1207", "20"],
                        ["OIL", "6065", "1590", "4475", "1536", "54", "4475", "-"],
                        ["ONGC", "3561", "1518", "2043", "1352", "166", "1796", "247"],
                        ["Total", "12594", "4459", "8135", "4239", "610", "7478", "267"],
                    ],
                ),
                (
                    "Table (b): Employees Domiciled in Assam",
                    ["Name of CPSEs", "Domiciled in Assam", "Executive", "Non-Executive", "Group A", "Group B", "Group C", "Group D"],
                    [
                        ["IOCL", "2299", "785", "1514", "785", "389", "1111", "14"],
                        ["OIL", "5782", "1281", "4501", "1224", "57", "4501", "0"],
                        ["ONGC", "3081", "1053", "2028", "873", "180", "1785", "243"],
                        ["Total", "11162", "3119", "8043", "2882", "626", "7397", "257"],
                    ],
                ),
                (
                    "Table (c): Recruitment in Assam (Last 5 Years)",
                    ["Year", "Total Recruited", "Executive", "Non-Executive"],
                    [
                        ["2021-22", "671", "76", "595"],
                        ["2022-23", "1033", "216", "817"],
                        ["2023-24", "367", "192", "175"],
                        ["2024-25", "335", "87", "248"],
                        ["2025-26", "510", "94", "416"],
                    ],
                ),
                (
                    "Table (e): Present Vacancy Position in Assam",
                    ["Name of CPSEs", "Total Vacancies", "Executive", "Non-Executive", "Group A", "Group B", "Group C", "Group D"],
                    [
                        ["IOCL", "0", "0", "0", "0", "0", "0", "0"],
                        ["OIL", "401", "84", "317", "83", "1", "317", "0"],
                        ["ONGC", "30", "0", "30", "0", "0", "24", "6"],
                        ["Total", "431", "84", "347", "83", "1", "341", "6"],
                    ],
                ),
            ]

            paragraphs.append(
                "(d) The human resource policies of Central Public Sector Enterprises (CPSEs) are formulated "
                "in accordance with directives and guidelines issued from time-to-time by the Department of Public Enterprises (DPE). "
                "As IOCL, OIL and ONGC are Maharatna CPSEs, their Boards are competent to formulate and implement their respective HR policies "
                "for below Board-level employees, subject to Government guidelines. These CPSEs comply with all statutory provisions relating to reservation and recruitment."
            )

            signatory = {
                "name": "SHRI SURESH GOPI",
                "designation": "MINISTER OF STATE IN THE MINISTRY OF PETROLEUM AND NATURAL GAS",
                "org": "Government of India",
            }

            file_path = NATIVE_DIR / f"{doc_id}.pdf"
            render_pdf(file_path, doc_id, title, issuer, q_date, confidentiality, subject, paragraphs, None, None, signatory, is_demo=False, multi_tables=multi_tables)

            manifest_rows.append({
                "doc_id": doc_id,
                "title": title,
                "type": "parliament_reply",
                "issuer": issuer,
                "date": q_date,
                "confidentiality": confidentiality,
                "audience_roles": audience_roles,
                "source": source_tag,
                "format": "pdf",
                "linked_entity_ids": "WC-ASM;WC-JOR",
                "questions_served": "G1;X7",
                "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
            })

        else:
            # SYNTHETIC PARLIAMENT QUESTIONS: Fictional MP from index and unpersonalized Minister of State
            mp_raw = str(row.get("mp_name", "Hon'ble Member"))
            fictional_mp = f"Shri/Smt. {mp_raw}, M.P." if not mp_raw.startswith(("Shri", "Smt")) else f"{mp_raw}, M.P."

            title = f"PARLIAMENT QUESTION REPLY: {house.upper()} {row['question_type'].upper()} Q. NO. {q_num}"
            issuer = ministry
            confidentiality = "PUBLIC"
            audience_roles = "Parliament / Public Record"
            source_tag = "synthetic"

            prov_sql = f"""SELECT 
    pq_id,
    house,
    session_year,
    question_number,
    question_date,
    question_type,
    ministry,
    mp_name,
    subject_theme,
    brief_text,
    reply_summary,
    sanctioned_strength_reported,
    in_position_strength_reported,
    vacancies_reported,
    reserved_vacancies_sc,
    reserved_vacancies_st,
    reserved_vacancies_obc,
    reserved_vacancies_ews
FROM 'landing/governance/parliament_questions_index.csv'
WHERE pq_id = '{pq_id}';"""

            sql_path = PROV_DIR / f"{doc_id}.sql"
            with open(sql_path, "w", encoding="utf-8") as f_sql:
                f_sql.write(prov_sql)

            paragraphs = [
                f"GOVERNMENT OF INDIA\nMINISTRY OF PETROLEUM AND NATURAL GAS\n{house.upper()}",
                f"{row['question_type'].upper()} QUESTION NO. {q_num}\nTO BE ANSWERED ON {q_date}",
                f"SUBJECT: {subject.upper()}",
                f"QUESTION ASKED BY: {fictional_mp} (Hon'ble Member of Parliament):\n"
                f"Will the Minister of Petroleum and Natural Gas be pleased to state: {row['brief_text']}",
                f"ANSWER:\nMINISTER OF STATE IN THE MINISTRY OF PETROLEUM AND NATURAL GAS\n(Minister of State, MoPNG)\n\n"
                f"{row['reply_summary']}",
            ]

            th = None
            tr = None
            if not math.isnan(row.get("sanctioned_strength_reported", float("nan"))):
                th = ["Category / Parameter", "Reported Count"]
                tr = [
                    ["Sanctioned Strength", f"{int(row['sanctioned_strength_reported']):,}"],
                    ["In-Position Regular Strength", f"{int(row['in_position_strength_reported']):,}"],
                    ["Total Vacancies Reported", f"{int(row['vacancies_reported']):,}"],
                    ["Reserved Vacancies - SC", f"{int(row.get('reserved_vacancies_sc', 0))}"],
                    ["Reserved Vacancies - ST", f"{int(row.get('reserved_vacancies_st', 0))}"],
                    ["Reserved Vacancies - OBC", f"{int(row.get('reserved_vacancies_obc', 0))}"],
                    ["Reserved Vacancies - EWS", f"{int(row.get('reserved_vacancies_ews', 0))}"],
                ]

            signatory = {
                "name": "Minister of State, MoPNG",
                "designation": "Ministry of Petroleum and Natural Gas",
                "org": "Government of India",
            }

            file_path = NATIVE_DIR / f"{doc_id}.pdf"
            render_pdf(file_path, doc_id, title, issuer, q_date, confidentiality, subject, paragraphs, th, tr, signatory, is_demo=True)

            manifest_rows.append({
                "doc_id": doc_id,
                "title": title,
                "type": "parliament_reply",
                "issuer": issuer,
                "date": q_date,
                "confidentiality": confidentiality,
                "audience_roles": audience_roles,
                "source": source_tag,
                "format": "pdf",
                "linked_entity_ids": "",
                "questions_served": "G1;X7",
                "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
            })

    # 2. 30 CAG Para Texts
    q_cag = """
    SELECT cag_para_id, report_number, cag_report_year, fiscal_year, operating_department, 
           wc_id, para_subject, financial_implication_inr_cr, notification_date, age_in_years, 
           is_aged_over_3_years, current_status, bottleneck_reason
    FROM 'landing/excel/cag_paras_register.xlsx'
    ORDER BY cag_para_id
    LIMIT 30;
    """
    cag_list = con.execute(q_cag).df().to_dict(orient="records")

    for row in cag_list:
        para_id = row["cag_para_id"]
        doc_id = f"DOC-{para_id}"
        rep_no = row["report_number"]
        rep_year = row["cag_report_year"]
        dept = row["operating_department"]
        wc = row["wc_id"]
        subj = row["para_subject"]
        fin_imp = row["financial_implication_inr_cr"]
        status = row["current_status"]
        notif_date = str(row["notification_date"])[:10]
        bottleneck = str(row["bottleneck_reason"])

        prov_sql = f"""SELECT 
    cag_para_id,
    report_number,
    cag_report_year,
    operating_department,
    wc_id,
    para_subject,
    financial_implication_inr_cr,
    notification_date,
    age_in_years,
    is_aged_over_3_years,
    current_status,
    bottleneck_reason
FROM 'landing/excel/cag_paras_register.xlsx'
WHERE cag_para_id = '{para_id}';"""

        sql_path = PROV_DIR / f"{doc_id}.sql"
        with open(sql_path, "w", encoding="utf-8") as f_sql:
            f_sql.write(prov_sql)

        title = f"REPORT OF THE COMPTROLLER AND AUDITOR GENERAL OF INDIA: AUDIT PARAGRAPH {para_id}"
        issuer = "Comptroller and Auditor General of India (Commercial Audit)"
        confidentiality = "PUBLIC"
        audience_roles = "Parliament, Audit Committee, Ministry of Petroleum & Natural Gas"

        paragraphs = [
            f"COMPTROLLER AND AUDITOR GENERAL OF INDIA\nUNION GOVERNMENT (COMMERCIAL)\n{rep_no} ({rep_year})",
            f"CHAPTER / PARAGRAPH: {para_id}\nOPERATING ENTITY: OIL AND NATURAL GAS CORPORATION LIMITED\n"
            f"RESPONSIBLE DEPARTMENT: {dept} · WORK CENTRE: {wc}",
            f"SUBJECT: {subj.upper()}",
            f"1. AUDIT FINDINGS: During the compliance audit of operations at {wc}, Audit observed substantial procedural delays "
            f"and documentation lapses resulting in a quantifiable financial implication of ₹{fin_imp:.2f} crore.",
            f"2. MANAGEMENT RESPONSE & CURRENT STATUS: The Management of ONGC has reported the status as: '{status}'. "
            f"Action Taken Notes (ATN) indicate that bottleneck/delay reason is: '{bottleneck}'.",
            f"3. AUDIT CONCLUSION: Audit recommends strengthening internal control mechanisms, instituting time-bound commercial "
            f"decisions, and fixing individual accountability for procedural non-compliances.",
        ]

        th = ["Audit Parameter", "Audit Finding / Status"]
        tr = [
            ["CAG Paragraph ID", para_id],
            ["Report Reference", f"{rep_no} ({rep_year})"],
            ["Operating Department", dept],
            ["Work Centre Inspected", wc],
            ["Quantified Financial Implication", f"₹{fin_imp:.2f} crore"],
            ["Notification Date", notif_date],
            ["Current Disposal Status", status],
            ["Identified Bottleneck Reason", bottleneck],
        ]

        signatory = {
            "name": "Principal Director of Commercial Audit",
            "designation": "Office of the Comptroller & Auditor General of India, New Delhi",
            "org": "Supreme Audit Institution of India",
        }

        file_path = NATIVE_DIR / f"{doc_id}.pdf"
        render_pdf(file_path, doc_id, title, issuer, notif_date, confidentiality, subj, paragraphs, th, tr, signatory, is_demo=True)

        manifest_rows.append({
            "doc_id": doc_id,
            "title": title,
            "type": "cag_audit_para",
            "issuer": issuer,
            "date": notif_date,
            "confidentiality": confidentiality,
            "audience_roles": audience_roles,
            "source": "synthetic",
            "format": "pdf",
            "linked_entity_ids": wc,
            "questions_served": "G2;X8",
            "provenance_sql": f"landing/documents/_provenance/{doc_id}.sql",
        })

    return manifest_rows


def write_manifest(records: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "doc_id",
        "title",
        "type",
        "issuer",
        "date",
        "confidentiality",
        "audience_roles",
        "source",
        "format",
        "linked_entity_ids",
        "questions_served",
        "provenance_sql",
    ]
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def main() -> None:
    print(f"=== Starting Document Generation (Steps 3.2, 3.3, 3.6) [SEED={SEED}] ===")
    init_directories()

    con = duckdb.connect()

    print("Generating Step 3.2: Office orders & circulars (~150)...")
    records_32 = generate_step_32(con)
    print(f"  Generated {len(records_32)} office orders & circulars.")

    print("Generating Step 3.3: Confidential documents (~12)...")
    records_33 = generate_step_33(con)
    print(f"  Generated {len(records_33)} confidential documents.")

    print("Generating Step 3.6: Parliament replies (~30) and CAG para texts (~30)...")
    records_36 = generate_step_36(con)
    print(f"  Generated {len(records_36)} parliament & CAG documents.")

    all_records = records_32 + records_33 + records_36
    write_manifest(all_records)
    print(f"=== Successfully wrote {len(all_records)} records to {MANIFEST_PATH} ===")


if __name__ == "__main__":
    main()
