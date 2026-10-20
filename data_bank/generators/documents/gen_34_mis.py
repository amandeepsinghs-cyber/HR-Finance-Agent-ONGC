"""gen_34_mis.py: Monthly Asset Performance Report (MIS) Generator for Step 3.4.

Generates monthly performance reports for each producing asset work centre across
the 24-month horizon (Oct-2024 -> Sep-2026):
- 14 assets * 24 months = 336 reports.
- Formatted as 3-page executive reports with tables, KPI callouts, and 2 trend charts.
- Rendered as scanned image-only PDFs (120 DPI greyscale with realistic scan noise)
  under landing/documents/scanned/mis/.
- Exact provenance SQL queries saved to landing/documents/_provenance/mis/MIS_{wc_id}_{month}.sql.
- Sidecar JSON containing rendered numeric figures saved to landing/documents/_provenance/mis/MIS_{wc_id}_{month}.json.
- Updates landing/documents/DOC_MANIFEST_34_37.csv.
"""

import os
import io
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import multiprocessing as mp

import duckdb
import pandas as pd
import numpy as np
import yaml
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pdf2image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LANDING_DIR = PROJECT_ROOT / "landing"
DOCUMENTS_DIR = LANDING_DIR / "documents"
SCANNED_MIS_DIR = DOCUMENTS_DIR / "scanned" / "mis"
PROVENANCE_MIS_DIR = DOCUMENTS_DIR / "_provenance" / "mis"
TEMPLATES_DIR = DOCUMENTS_DIR / "templates"
MANIFEST_PATH = DOCUMENTS_DIR / "DOC_MANIFEST_34_37.csv"

# Global SEED for deterministic execution
SEED = 20261019


def load_reference_mappings():
    """Load asset work centres and field name mappings dynamically from reference YAML."""
    ref_wc_path = PROJECT_ROOT / "world_bible" / "reference" / "work_centres.yaml"
    with open(ref_wc_path, "r", encoding="utf-8") as f:
        data_wc = yaml.safe_load(f)
    assets = [w for w in data_wc.get("work_centres", []) if w.get("type") == "asset"]

    ref_fld_path = PROJECT_ROOT / "world_bible" / "reference" / "fields.yaml"
    with open(ref_fld_path, "r", encoding="utf-8") as f:
        data_fld = yaml.safe_load(f)
    field_map = {f["field_id"]: f["name"] for f in data_fld.get("fields", [])}

    return assets, field_map


def get_month_sequence() -> List[str]:
    """Generate the 24-month horizon from 2024-10 to 2026-09."""
    months = []
    # 2024: Oct, Nov, Dec
    for m in range(10, 13):
        months.append(f"2024-{m:02d}")
    # 2025: Jan -> Dec
    for m in range(1, 13):
        months.append(f"2025-{m:02d}")
    # 2026: Jan -> Sep
    for m in range(1, 10):
        months.append(f"2026-{m:02d}")
    return months


def get_relative_months(month_str: str):
    """Compute previous month and same month last year."""
    parts = month_str.split("-")
    yr = int(parts[0])
    mo = int(parts[1])

    # Previous month
    if mo == 1:
        prev_yr = yr - 1
        prev_mo = 12
    else:
        prev_yr = yr
        prev_mo = mo - 1
    prev_month_str = f"{prev_yr}-{prev_mo:02d}"

    # Same month last year
    ly_yr = yr - 1
    ly_month_str = f"{ly_yr}-{mo:02d}"

    return prev_month_str, ly_month_str


def build_provenance_sql_text(wc_id: str, month: str, prev_m: str, ly_m: str) -> str:
    """Format provenance SQL queries documenting how every metric is derived."""
    return f"""-- ============================================================================
-- Provenance SQL for Monthly Asset Performance Report (Step 3.4)
-- Asset Work Centre: {wc_id}
-- Reporting Month: {month}
-- Comparisons: Previous Month ({prev_m}), Same Month Last Year ({ly_m})
-- ============================================================================

-- Query 1: Physical Hydrocarbon Production & Well Downtime
SELECT 
    month,
    COALESCE(SUM(oil_production_mt), 0.0) as oil_production_mt,
    COALESCE(SUM(gas_production_mmscm), 0.0) as gas_production_mmscm,
    COALESCE(SUM(condensate_production_mt), 0.0) as condensate_production_mt,
    COALESCE(SUM(total_production_boe), 0.0) as total_production_boe,
    COALESCE(AVG(water_cut_pct), 0.0) as water_cut_pct,
    COALESCE(SUM(water_produced_m3), 0.0) as water_produced_m3,
    COALESCE(SUM(active_producing_wells), 0) as active_producing_wells,
    COALESCE(SUM(well_downtime_hours), 0.0) as well_downtime_hours,
    COALESCE(AVG(operational_uptime_pct), 0.0) as operational_uptime_pct
FROM 'landing/db_exports/production_monthly.csv'
WHERE asset_wc_id = '{wc_id}' AND month IN ('{month}', '{prev_m}', '{ly_m}')
GROUP BY month
ORDER BY month;

-- Query 2: Operating Expenditure (OPEX) by Cost Head & Cost Element
SELECT 
    cost_head,
    cost_element_name,
    COALESCE(SUM(amount_inr), 0.0) as amount_inr
FROM 'landing/sap/COSP_COSS.csv'
WHERE wc_id = '{wc_id}' AND month = '{month}'
GROUP BY cost_head, cost_element_name
ORDER BY amount_inr DESC;

-- Query 3: Capital Expenditure (Capex Actual vs Budget Estimate BE)
SELECT 
    COALESCE(SUM(budget_estimate_be_inr_cr), 0.0) as be_inr_cr,
    COALESCE(SUM(revised_estimate_re_inr_cr), 0.0) as re_inr_cr,
    COALESCE(SUM(actual_spend_inr_cr), 0.0) as actual_spend_inr_cr,
    (COALESCE(SUM(actual_spend_inr_cr), 0.0) - COALESCE(SUM(budget_estimate_be_inr_cr), 0.0)) as variance_vs_be_cr
FROM capex_budget
WHERE asset_wc_id = '{wc_id}' AND month = '{month}';

-- Query 4: Manpower In-Position Headcount Snapshot
SELECT 
    COALESCE(SUM(headcount), 0) as total_headcount,
    COALESCE(SUM(active_headcount), 0) as active_headcount,
    COALESCE(SUM(on_leave_headcount), 0) as on_leave_headcount
FROM 'landing/sap/headcount_monthly_snapshot.csv'
WHERE wc_id = '{wc_id}' AND month = '{month}';

-- Query 5: Payroll Overtime Hours & Expenditure
SELECT 
    COALESCE(COUNT(DISTINCT PERNR), 0) as paid_employees,
    COALESCE(SUM(overtime_hours), 0.0) as total_overtime_hours,
    COALESCE(SUM(overtime_amount_inr), 0.0) as total_overtime_amount_inr
FROM 'landing/sap/PY_CLUSTER_EXP.csv'
WHERE wc_id = '{wc_id}' AND FPPER = '{month}';

-- Query 6: Health, Safety & Environment (HSE) Incidents
SELECT 
    COALESCE(COUNT(*), 0) as total_incidents,
    COALESCE(SUM(CASE WHEN lost_time_injury_flag = TRUE THEN 1 ELSE 0 END), 0) as lti_count,
    COALESCE(SUM(days_lost), 0) as total_days_lost,
    COALESCE(SUM(CASE WHEN fatigue_factor_flag = TRUE THEN 1 ELSE 0 END), 0) as fatigue_incidents
FROM 'landing/db_exports/hse_incident_log.csv'
WHERE wc_id = '{wc_id}' AND month = '{month}';
"""


def render_report_pdf(report_data: Dict[str, Any]) -> bytes:
    """Build a 3-page professional ONGC Monthly Asset Performance Report using ReportLab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=26,
        bottomMargin=26,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#003366"),
        alignment=1,  # Center
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#444444"),
        alignment=1,
    )
    sec_hdr_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#003366"),
        spaceBefore=6,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
    )
    cell_right = ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=2,  # Right
    )

    wc_id = report_data["wc_id"]
    asset_name = report_data["asset_name"]
    sector = report_data["sector"]
    op_type = report_data["onshore_offshore"]
    month = report_data["month"]

    story = []

    # =========================================================================
    # PAGE 1: PRODUCTION & OPERATIONAL PERFORMANCE
    # =========================================================================
    story.append(Paragraph("OIL AND NATURAL GAS CORPORATION LIMITED", title_style))
    story.append(
        Paragraph(
            f"<b>MONTHLY ASSET PERFORMANCE REPORT — {month}</b><br/>"
            f"Asset: <b>{asset_name}</b> ({wc_id}) &nbsp;|&nbsp; Sector: <b>{sector}</b> &nbsp;|&nbsp; Operations: <b>{op_type.upper()}</b>",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Hydrocarbon Production & Well Operational Summary", sec_hdr_style))

    # Production Comparison Table
    cur_p = report_data["prod_current"]
    prev_p = report_data["prod_prev"]
    ly_p = report_data["prod_ly"]

    def calc_pct_chg(cur, base):
        if base and base > 0:
            pct = ((cur - base) / base) * 100.0
            sign = "+" if pct >= 0 else ""
            return f"{sign}{pct:.1f}%"
        return "N/A"

    oil_cur = cur_p.get("oil_production_mt", 0.0)
    oil_prev = prev_p.get("oil_production_mt", 0.0)
    oil_ly = ly_p.get("oil_production_mt", 0.0)

    gas_cur = cur_p.get("gas_production_mmscm", 0.0)
    gas_prev = prev_p.get("gas_production_mmscm", 0.0)
    gas_ly = ly_p.get("gas_production_mmscm", 0.0)

    boe_cur = cur_p.get("total_production_boe", 0.0)
    boe_prev = prev_p.get("total_production_boe", 0.0)
    boe_ly = ly_p.get("total_production_boe", 0.0)

    wc_cur = cur_p.get("water_cut_pct", 0.0)
    wc_prev = prev_p.get("water_cut_pct", 0.0)
    wc_ly = ly_p.get("water_cut_pct", 0.0)

    dt_cur = cur_p.get("well_downtime_hours", 0.0)
    dt_prev = prev_p.get("well_downtime_hours", 0.0)
    dt_ly = ly_p.get("well_downtime_hours", 0.0)

    wells_cur = cur_p.get("active_producing_wells", 0)
    wells_prev = prev_p.get("active_producing_wells", 0)
    wells_ly = ly_p.get("active_producing_wells", 0)

    upt_cur = cur_p.get("operational_uptime_pct", 0.0)
    upt_prev = prev_p.get("operational_uptime_pct", 0.0)
    upt_ly = ly_p.get("operational_uptime_pct", 0.0)

    prod_tbl_data = [
        [
            Paragraph("<b>Operational Metric</b>", cell_bold),
            Paragraph("<b>Unit</b>", cell_bold),
            Paragraph(f"<b>{month}</b>", cell_bold),
            Paragraph("<b>Prev Month</b>", cell_bold),
            Paragraph("<b>Same Mo LY</b>", cell_bold),
            Paragraph("<b>MoM (%)</b>", cell_bold),
            Paragraph("<b>YoY (%)</b>", cell_bold),
        ],
        [
            Paragraph("Crude Oil Production", cell_style),
            Paragraph("MT", cell_style),
            Paragraph(f"{oil_cur:,.1f}", cell_right),
            Paragraph(f"{oil_prev:,.1f}", cell_right),
            Paragraph(f"{oil_ly:,.1f}", cell_right),
            Paragraph(calc_pct_chg(oil_cur, oil_prev), cell_right),
            Paragraph(calc_pct_chg(oil_cur, oil_ly), cell_right),
        ],
        [
            Paragraph("Natural Gas Production", cell_style),
            Paragraph("MMSCM", cell_style),
            Paragraph(f"{gas_cur:,.2f}", cell_right),
            Paragraph(f"{gas_prev:,.2f}", cell_right),
            Paragraph(f"{gas_ly:,.2f}", cell_right),
            Paragraph(calc_pct_chg(gas_cur, gas_prev), cell_right),
            Paragraph(calc_pct_chg(gas_cur, gas_ly), cell_right),
        ],
        [
            Paragraph("Total Production (BOE)", cell_style),
            Paragraph("BOE", cell_style),
            Paragraph(f"{boe_cur:,.0f}", cell_right),
            Paragraph(f"{boe_prev:,.0f}", cell_right),
            Paragraph(f"{boe_ly:,.0f}", cell_right),
            Paragraph(calc_pct_chg(boe_cur, boe_prev), cell_right),
            Paragraph(calc_pct_chg(boe_cur, boe_ly), cell_right),
        ],
        [
            Paragraph("Average Water Cut", cell_style),
            Paragraph("%", cell_style),
            Paragraph(f"{wc_cur:.1f}%", cell_right),
            Paragraph(f"{wc_prev:.1f}%", cell_right),
            Paragraph(f"{wc_ly:.1f}%", cell_right),
            Paragraph(f"{wc_cur - wc_prev:+.1f}%", cell_right),
            Paragraph(f"{wc_cur - wc_ly:+.1f}%", cell_right),
        ],
        [
            Paragraph("Total Well Downtime", cell_style),
            Paragraph("Hours", cell_style),
            Paragraph(f"{dt_cur:,.1f}", cell_right),
            Paragraph(f"{dt_prev:,.1f}", cell_right),
            Paragraph(f"{dt_ly:,.1f}", cell_right),
            Paragraph(calc_pct_chg(dt_cur, dt_prev), cell_right),
            Paragraph(calc_pct_chg(dt_cur, dt_ly), cell_right),
        ],
        [
            Paragraph("Active Producing Wells", cell_style),
            Paragraph("Wells", cell_style),
            Paragraph(f"{int(wells_cur)}", cell_right),
            Paragraph(f"{int(wells_prev)}", cell_right),
            Paragraph(f"{int(wells_ly)}", cell_right),
            Paragraph(f"{int(wells_cur - wells_prev):+d}", cell_right),
            Paragraph(f"{int(wells_cur - wells_ly):+d}", cell_right),
        ],
        [
            Paragraph("Operating Facilities Uptime", cell_style),
            Paragraph("%", cell_style),
            Paragraph(f"{upt_cur:.1f}%", cell_right),
            Paragraph(f"{upt_prev:.1f}%", cell_right),
            Paragraph(f"{upt_ly:.1f}%", cell_right),
            Paragraph(f"{upt_cur - upt_prev:+.1f}%", cell_right),
            Paragraph(f"{upt_cur - upt_ly:+.1f}%", cell_right),
        ],
    ]

    t_prod = Table(prod_tbl_data, colWidths=[150, 45, 70, 70, 70, 65, 65])
    t_prod.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_prod)
    story.append(Spacer(1, 8))

    # Field Breakdown Table
    story.append(Paragraph("Field-Wise Production Contribution (Current Month)", sec_hdr_style))
    fld_rows = [
        [
            Paragraph("<b>Field Name & ID</b>", cell_bold),
            Paragraph("<b>Oil (MT)</b>", cell_bold),
            Paragraph("<b>Gas (MMSCM)</b>", cell_bold),
            Paragraph("<b>Total (BOE)</b>", cell_bold),
            Paragraph("<b>Water Cut (%)</b>", cell_bold),
            Paragraph("<b>Active Wells</b>", cell_bold),
            Paragraph("<b>Downtime (Hrs)</b>", cell_bold),
        ]
    ]
    field_map = report_data.get("field_name_map", {})
    for fld in report_data["fields_data"][:6]:
        fid = str(fld.get("field_id", ""))
        fname = field_map.get(fid, fid)
        fld_title = f"{fname} ({fid})" if fname != fid else fid
        fld_rows.append(
            [
                Paragraph(fld_title, cell_style),
                Paragraph(f"{fld.get('oil_production_mt', 0.0):,.1f}", cell_right),
                Paragraph(f"{fld.get('gas_production_mmscm', 0.0):,.2f}", cell_right),
                Paragraph(f"{fld.get('total_production_boe', 0.0):,.0f}", cell_right),
                Paragraph(f"{fld.get('water_cut_pct', 0.0):.1f}%", cell_right),
                Paragraph(f"{int(fld.get('active_producing_wells', 0))}", cell_right),
                Paragraph(f"{fld.get('well_downtime_hours', 0.0):,.1f}", cell_right),
            ]
        )
    t_fld = Table(fld_rows, colWidths=[145, 65, 65, 70, 60, 60, 70])
    t_fld.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F497D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_fld)
    story.append(Spacer(1, 6))

    # Executive Cost, Capex & Manpower Summary Block on Page 1
    story.append(Paragraph("Financial, Manpower & HSE Executive Snapshot", sec_hdr_style))
    tot_opex_p1 = report_data["total_opex_inr"] / 10000000.0
    lift_inr_p1 = report_data["lifting_cost_inr_per_boe"]
    be_cr_p1 = report_data["capex_be_inr_cr"]
    act_cr_p1 = report_data["capex_actual_spend_inr_cr"]
    util_pct_p1 = (act_cr_p1 / be_cr_p1 * 100.0) if be_cr_p1 > 0 else 0.0
    hc_tot_p1 = report_data["total_headcount"]
    hc_act_p1 = report_data["active_headcount"]
    hc_lv_p1 = report_data["on_leave_headcount"]
    ot_hrs_p1 = report_data["total_overtime_hours"]
    ot_amt_p1 = report_data["total_overtime_amount_inr"] / 100000.0
    hse_cnt_p1 = report_data["hse_incidents_count"]
    lti_cnt_p1 = report_data["hse_lti_count"]

    summary_rows = [
        [
            Paragraph(f"<b>Operating Spend:</b> ₹ {tot_opex_p1:,.2f} Cr &nbsp;|&nbsp; <b>Lifting Cost:</b> ₹ {lift_inr_p1:,.2f} / BOE", cell_style),
            Paragraph(f"<b>Capex Spend:</b> ₹ {act_cr_p1:,.2f} Cr vs BE ₹ {be_cr_p1:,.2f} Cr ({util_pct_p1:.1f}% burn)", cell_style),
        ],
        [
            Paragraph(f"<b>Manpower Strength:</b> {int(hc_tot_p1):,d} on roll ({int(hc_act_p1):,d} active, {int(hc_lv_p1):,d} on leave)", cell_style),
            Paragraph(f"<b>Overtime & Safety:</b> {ot_hrs_p1:,.0f} OT hrs (₹ {ot_amt_p1:,.2f}L) &nbsp;|&nbsp; {int(hse_cnt_p1)} HSE Incidents ({int(lti_cnt_p1)} LTI)", cell_style),
        ],
    ]
    t_summary = Table(summary_rows, colWidths=[268, 267])
    t_summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B0C4DE")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_summary)
    story.append(Spacer(1, 6))

    # Chart 1: Trailing 6-Month Production Trend
    trend_data = report_data["trend_data"]
    fig, ax1 = plt.subplots(figsize=(6.8, 1.7), dpi=100)
    months_labels = [row["month"][5:] for row in trend_data]
    oil_vals = [row["oil_mt"] for row in trend_data]
    gas_vals = [row["gas_mmscm"] for row in trend_data]

    x_idx = np.arange(len(months_labels))
    width = 0.35

    ax1.bar(x_idx - width / 2, oil_vals, width, label="Oil (MT)", color="#003366")
    ax1.set_ylabel("Oil Production (MT)", color="#003366", fontsize=7.5)
    ax1.tick_params(axis="y", labelcolor="#003366", labelsize=7)
    ax1.set_xticks(x_idx)
    ax1.set_xticklabels(months_labels, fontsize=7.5)
    ax1.grid(True, linestyle="--", alpha=0.3, axis="y")

    ax2 = ax1.twinx()
    ax2.plot(x_idx, gas_vals, color="#C00000", marker="o", linewidth=1.8, label="Gas (MMSCM)")
    ax2.set_ylabel("Gas (MMSCM)", color="#C00000", fontsize=7.5)
    ax2.tick_params(axis="y", labelcolor="#C00000", labelsize=7)

    plt.title(f"Trailing Production Trend ({asset_name})", fontsize=8.5, fontweight="bold", pad=3)
    fig.tight_layout()
    chart1_buf = io.BytesIO()
    plt.savefig(chart1_buf, format="png", bbox_inches="tight")
    plt.close(fig)
    chart1_buf.seek(0)
    story.append(RLImage(chart1_buf, width=535, height=122))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: FINANCIAL & CAPITAL EXPENDITURE PERFORMANCE
    # =========================================================================
    story.append(Paragraph("OIL AND NATURAL GAS CORPORATION LIMITED", title_style))
    story.append(
        Paragraph(
            f"<b>FINANCIAL & CAPITAL EXPENDITURE REVIEW — {month}</b><br/>"
            f"Asset: <b>{asset_name}</b> ({wc_id})",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Operating Expenditure (OPEX) & Lifting Cost Analysis", sec_hdr_style))

    tot_opex = report_data["total_opex_inr"]
    lift_inr = report_data["lifting_cost_inr_per_boe"]
    tot_opex_cr = tot_opex / 10000000.0

    kpi_callout_data = [
        [
            Paragraph("<b>Total Operating Cost (OPEX)</b>", cell_bold),
            Paragraph("<b>Lifting Cost per BOE</b>", cell_bold),
        ],
        [
            Paragraph(f"₹ {tot_opex_cr:,.2f} Crores", cell_bold),
            Paragraph(f"₹ {lift_inr:,.2f} / BOE", cell_bold),
        ],
    ]
    t_kpi = Table(kpi_callout_data, colWidths=[268, 267])
    t_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#B0C4DE")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_kpi)
    story.append(Spacer(1, 6))

    # Cost Breakdown Table
    cost_rows = [
        [
            Paragraph("<b>Cost Head / Operating Element</b>", cell_bold),
            Paragraph("<b>Description</b>", cell_bold),
            Paragraph("<b>Amount (₹ Lakhs)</b>", cell_bold),
            Paragraph("<b>Share (%)</b>", cell_bold),
        ]
    ]
    cost_items = report_data["cost_elements"]
    for c_item in cost_items[:8]:
        amt = c_item.get("amount_inr", 0.0)
        amt_lakh = amt / 1e5
        pct = (amt / tot_opex * 100.0) if tot_opex > 0 else 0.0
        cost_rows.append(
            [
                Paragraph(str(c_item.get("cost_head", "")), cell_style),
                Paragraph(str(c_item.get("cost_element_name", "")), cell_style),
                Paragraph(f"{amt_lakh:,.2f}", cell_right),
                Paragraph(f"{pct:.1f}%", cell_right),
            ]
        )
    t_cost = Table(cost_rows, colWidths=[150, 205, 100, 80])
    t_cost.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F497D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_cost)
    story.append(Spacer(1, 8))

    # Section 3: Capex vs BE
    story.append(Paragraph("3. Capital Expenditure (Capex Actual vs Budget Estimate BE)", sec_hdr_style))
    be_cr = report_data["capex_be_inr_cr"]
    act_cr = report_data["capex_actual_spend_inr_cr"]
    re_cr = report_data["capex_re_inr_cr"]
    var_cr = report_data["capex_variance_cr"]
    util_pct = (act_cr / be_cr * 100.0) if be_cr > 0 else 0.0

    capex_kpi_data = [
        [
            Paragraph("<b>Budget Estimate (BE)</b>", cell_bold),
            Paragraph("<b>Revised Estimate (RE)</b>", cell_bold),
            Paragraph("<b>Actual Spend Incurred</b>", cell_bold),
            Paragraph("<b>Budget Utilization (%)</b>", cell_bold),
        ],
        [
            Paragraph(f"₹ {be_cr:,.2f} Cr", cell_bold),
            Paragraph(f"₹ {re_cr:,.2f} Cr", cell_bold),
            Paragraph(f"₹ {act_cr:,.2f} Cr", cell_bold),
            Paragraph(f"{util_pct:.1f}%", cell_bold),
        ],
    ]
    t_cap_kpi = Table(capex_kpi_data, colWidths=[135, 135, 135, 130])
    t_cap_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#B0C4DE")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_cap_kpi)
    story.append(Spacer(1, 6))

    # Capex Breakdown Table
    cap_rows = [
        [
            Paragraph("<b>Capex Budget Head / Scheme</b>", cell_bold),
            Paragraph("<b>Budget Estimate (₹ Cr)</b>", cell_bold),
            Paragraph("<b>Actual Spend (₹ Cr)</b>", cell_bold),
            Paragraph("<b>Variance (₹ Cr)</b>", cell_bold),
        ]
    ]
    for c_head in report_data["capex_heads"][:5]:
        b = c_head.get("be_cr", 0.0)
        a = c_head.get("actual_cr", 0.0)
        p_name = c_head.get("project_name", "")
        p_id = c_head.get("prj_id", "")
        c_h = c_head.get("capex_head", "")
        if p_name and p_id:
            head_title = f"{p_name} ({p_id}) — {c_h}"
        else:
            head_title = str(c_h)
        cap_rows.append(
            [
                Paragraph(head_title, cell_style),
                Paragraph(f"{b:,.2f}", cell_right),
                Paragraph(f"{a:,.2f}", cell_right),
                Paragraph(f"{a - b:+,.2f}", cell_right),
            ]
        )
    t_cap = Table(cap_rows, colWidths=[235, 100, 100, 100])
    t_cap.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_cap)
    story.append(Spacer(1, 6))

    # Chart 2: Capex Spend vs BE Comparison
    fig2, ax = plt.subplots(figsize=(6.8, 1.8), dpi=100)
    categories = [row["capex_head"][:20] for row in report_data["capex_heads"][:5]]
    be_vals = [row["be_cr"] for row in report_data["capex_heads"][:5]]
    act_vals = [row["actual_cr"] for row in report_data["capex_heads"][:5]]

    if len(categories) > 0:
        y_pos = np.arange(len(categories))
        bar_h = 0.35
        ax.barh(y_pos - bar_h / 2, be_vals, bar_h, label="Budget Estimate (BE)", color="#708090")
        ax.barh(y_pos + bar_h / 2, act_vals, bar_h, label="Actual Spend", color="#003366")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories, fontsize=7)
        ax.set_xlabel("INR Crores", fontsize=7.5)
        ax.grid(True, linestyle="--", alpha=0.3, axis="x")
        ax.legend(fontsize=7, loc="lower right")
        plt.title(f"Capex Spend vs BE ({month})", fontsize=8.5, fontweight="bold", pad=3)
    else:
        ax.text(0.5, 0.5, "No Capex Heads Recorded", ha="center", va="center")
    fig2.tight_layout()
    chart2_buf = io.BytesIO()
    plt.savefig(chart2_buf, format="png", bbox_inches="tight")
    plt.close(fig2)
    chart2_buf.seek(0)
    story.append(RLImage(chart2_buf, width=535, height=130))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: MANPOWER & HSE SAFETY LOG
    # =========================================================================
    story.append(Paragraph("OIL AND NATURAL GAS CORPORATION LIMITED", title_style))
    story.append(
        Paragraph(
            f"<b>MANPOWER & HSE SAFETY LOG — {month}</b><br/>"
            f"Asset: <b>{asset_name}</b> ({wc_id})",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. Manpower Strength, Overtime & Labor Productivity", sec_hdr_style))

    hc_tot = report_data["total_headcount"]
    hc_act = report_data["active_headcount"]
    hc_lv = report_data["on_leave_headcount"]
    ot_hrs = report_data["total_overtime_hours"]
    ot_amt = report_data["total_overtime_amount_inr"] / 1e5  # Lakhs
    paid_emp = report_data["paid_employees"]
    boe_per_emp = (boe_cur / hc_tot) if hc_tot > 0 else 0.0

    hc_tbl_data = [
        [
            Paragraph("<b>Manpower Metric</b>", cell_bold),
            Paragraph("<b>Value</b>", cell_bold),
            Paragraph("<b>Operational Benchmark / Note</b>", cell_bold),
        ],
        [
            Paragraph("Total In-Position Headcount", cell_style),
            Paragraph(f"{int(hc_tot):,d}", cell_right),
            Paragraph("Substantive ONGC regular establishment", cell_style),
        ],
        [
            Paragraph("Active On-Duty Headcount", cell_style),
            Paragraph(f"{int(hc_act):,d}", cell_right),
            Paragraph("Personnel deployed at surface/drilling sites", cell_style),
        ],
        [
            Paragraph("Employees on Leave / Deputation", cell_style),
            Paragraph(f"{int(hc_lv):,d}", cell_right),
            Paragraph("Authorized privilege / sick / special leaves", cell_style),
        ],
        [
            Paragraph("Employees Processed on Payroll", cell_style),
            Paragraph(f"{int(paid_emp):,d}", cell_right),
            Paragraph("Monthly SAP PY cluster wage disbursement", cell_style),
        ],
        [
            Paragraph("Total Overtime Hours Worked", cell_style),
            Paragraph(f"{ot_hrs:,.1f}", cell_right),
            Paragraph("Maintenance, emergency shift coverages", cell_style),
        ],
        [
            Paragraph("Overtime Expenditure", cell_style),
            Paragraph(f"₹ {ot_amt:,.2f} Lakhs", cell_right),
            Paragraph("Overtime disbursement as per DPE rules", cell_style),
        ],
        [
            Paragraph("Labor Productivity (BOE / Employee)", cell_style),
            Paragraph(f"{boe_per_emp:,.1f} BOE", cell_right),
            Paragraph("Monthly hydrocarbon output per regular worker", cell_style),
        ],
    ]
    t_hc = Table(hc_tbl_data, colWidths=[195, 110, 230])
    t_hc.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_hc)
    story.append(Spacer(1, 8))

    # Discipline Breakdown
    story.append(Paragraph("Key Technical Disciplines Distribution", sec_hdr_style))
    disc_rows = [
        [
            Paragraph("<b>Discipline</b>", cell_bold),
            Paragraph("<b>Headcount</b>", cell_bold),
            Paragraph("<b>Share of Total Staff (%)</b>", cell_bold),
        ]
    ]
    for d in report_data["disciplines_data"][:5]:
        c = d.get("hc", 0)
        pct = (c / hc_tot * 100.0) if hc_tot > 0 else 0.0
        disc_rows.append(
            [
                Paragraph(str(d.get("discipline_id", "")), cell_style),
                Paragraph(f"{int(c):,d}", cell_right),
                Paragraph(f"{pct:.1f}%", cell_right),
            ]
        )
    t_disc = Table(disc_rows, colWidths=[235, 150, 150])
    t_disc.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F497D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_disc)
    story.append(Spacer(1, 8))

    # Section 5: HSE Incident Log
    story.append(Paragraph("5. Health, Safety & Environment (HSE) Incident Log", sec_hdr_style))
    hse_cnt = report_data["hse_incidents_count"]
    lti_cnt = report_data["hse_lti_count"]
    days_lost = report_data["hse_days_lost"]
    fatigue_cnt = report_data["hse_fatigue_count"]

    hse_kpi_data = [
        [
            Paragraph("<b>Total Incidents Recorded</b>", cell_bold),
            Paragraph("<b>Lost Time Injuries (LTI)</b>", cell_bold),
            Paragraph("<b>Cumulative Days Lost</b>", cell_bold),
            Paragraph("<b>Fatigue-Linked Flags</b>", cell_bold),
        ],
        [
            Paragraph(f"{int(hse_cnt)}", cell_bold),
            Paragraph(f"{int(lti_cnt)}", cell_bold),
            Paragraph(f"{int(days_lost)}", cell_bold),
            Paragraph(f"{int(fatigue_cnt)}", cell_bold),
        ],
    ]
    t_hse_kpi = Table(hse_kpi_data, colWidths=[135, 135, 135, 130])
    t_hse_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#B0C4DE")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_hse_kpi)
    story.append(Spacer(1, 6))

    # Incident Details Table
    inc_rows = [
        [
            Paragraph("<b>Incident ID</b>", cell_bold),
            Paragraph("<b>Date</b>", cell_bold),
            Paragraph("<b>Type / Category</b>", cell_bold),
            Paragraph("<b>Severity</b>", cell_bold),
            Paragraph("<b>Days Lost</b>", cell_bold),
            Paragraph("<b>Brief Description</b>", cell_bold),
        ]
    ]
    incidents = report_data["hse_incidents_list"]
    if len(incidents) > 0:
        for inc in incidents[:4]:
            inc_rows.append(
                [
                    Paragraph(str(inc.get("incident_id", "")), cell_style),
                    Paragraph(str(inc.get("incident_date", "")), cell_style),
                    Paragraph(str(inc.get("incident_type", "")), cell_style),
                    Paragraph(str(inc.get("severity_tier", "")), cell_style),
                    Paragraph(str(inc.get("days_lost", 0)), cell_right),
                    Paragraph(str(inc.get("brief_description", ""))[:45] + "...", cell_style),
                ]
            )
    else:
        inc_rows.append(
            [
                Paragraph("N/A", cell_style),
                Paragraph(month, cell_style),
                Paragraph("Nil Incident", cell_style),
                Paragraph("Tier-0", cell_style),
                Paragraph("0", cell_right),
                Paragraph("Zero lost time injuries or reportable incidents recorded.", cell_style),
            ]
        )

    t_inc = Table(inc_rows, colWidths=[75, 65, 95, 65, 55, 180])
    t_inc.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_inc)
    story.append(Spacer(1, 10))

    # Institutional Sign-off Block
    sig_data = [
        [
            Paragraph("<b>Prepared by:</b><br/>Asset Production Review & MIS Cell", cell_style),
            Paragraph("<b>Reviewed by:</b><br/>Head of Finance & Head of HR", cell_style),
            Paragraph(f"<b>Approved by:</b><br/>Executive Director — Asset Manager ({asset_name})", cell_style),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[180, 180, 175])
    t_sig.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (1, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(KeepTogether(t_sig))

    doc.build(story)
    return buf.getvalue()


def convert_to_scanned_pdf(clean_pdf_bytes: bytes, report_seed: int, target_pdf_path: Path):
    """Render clean PDF bytes into a scanned, greyscale, image-only PDF with realistic noise."""
    np.random.seed(report_seed)

    # Convert to images at 120 DPI
    imgs = pdf2image.convert_from_bytes(clean_pdf_bytes, dpi=120)

    scanned_images = []
    for page_idx, img in enumerate(imgs):
        # 1. Grayscale
        gray = img.convert("L")

        # 2. Slight rotation (-0.25 to +0.25 degrees)
        angle = np.random.uniform(-0.25, 0.25)
        rotated = gray.rotate(angle, expand=False, fillcolor=255)

        # 3. Add realistic sensor grain & paper noise
        arr = np.array(rotated, dtype=np.float32)
        noise = np.random.normal(0, 1.8, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)

        scanned_img = Image.fromarray(arr)
        scanned_images.append(scanned_img)

    # Save as image-only PDF
    scanned_images[0].save(
        target_pdf_path,
        format="PDF",
        resolution=120.0,
        save_all=True,
        append_images=scanned_images[1:],
    )


def process_report_task(task_args: Dict[str, Any]):
    """Worker task to render and save a single MIS report."""
    wc_id = task_args["wc_id"]
    month = task_args["month"]
    report_data = task_args["report_data"]
    figures_dict = task_args["figures"]
    provenance_sql_str = task_args["provenance_sql"]
    task_seed = task_args["seed"]

    pdf_filename = f"MIS_{wc_id}_{month}.pdf"
    sql_filename = f"MIS_{wc_id}_{month}.sql"
    json_filename = f"MIS_{wc_id}_{month}.json"

    pdf_out_path = SCANNED_MIS_DIR / pdf_filename
    sql_out_path = PROVENANCE_MIS_DIR / sql_filename
    json_out_path = PROVENANCE_MIS_DIR / json_filename

    # 1. Write Provenance SQL
    with open(sql_out_path, "w", encoding="utf-8") as f:
        f.write(provenance_sql_str)

    # 2. Write Sidecar JSON
    sidecar_content = {
        "doc_id": f"DOC-MIS-{wc_id}-{month}",
        "wc_id": wc_id,
        "asset_name": report_data["asset_name"],
        "month": month,
        "figures": figures_dict,
    }
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(sidecar_content, f, indent=2)

    # 3. Build ReportLab clean PDF
    clean_pdf = render_report_pdf(report_data)

    # 4. Render to scanned image-only PDF
    convert_to_scanned_pdf(clean_pdf, task_seed, pdf_out_path)

    return {
        "doc_id": f"DOC-MIS-{wc_id}-{month}",
        "title": f"Monthly Asset Performance Report - {report_data['short_name']} ({month})",
        "type": "mis_report",
        "asset_wc_id": wc_id,
        "month": month,
        "format": "pdf",
        "provenance_sql": f"landing/documents/_provenance/mis/{sql_filename}",
        "questions_served": "C11, C14, T1, X10",
    }


def main():
    t_start = time.time()
    print("Initializing Step 3.4 & 3.7 generation...")

    SCANNED_MIS_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_MIS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    assets, field_map = load_reference_mappings()
    months = get_month_sequence()
    print(f"Loaded {len(assets)} producing asset work centres and {len(months)} reporting months.")
    print(f"Total reports to generate: {len(assets)} * {len(months)} = {len(assets) * len(months)}")

    # 1. In-memory DuckDB setup
    print("Loading landing CSV & Excel tables into in-memory DuckDB...")
    t_db = time.time()
    con = duckdb.connect()
    con.execute(f"CREATE TABLE prod AS SELECT * FROM '{LANDING_DIR}/db_exports/production_monthly.csv'")
    con.execute(f"CREATE TABLE cosp AS SELECT * FROM '{LANDING_DIR}/sap/COSP_COSS.csv'")
    con.execute(f"CREATE TABLE hc AS SELECT * FROM '{LANDING_DIR}/sap/headcount_monthly_snapshot.csv'")
    con.execute(f"CREATE TABLE py AS SELECT * FROM '{LANDING_DIR}/sap/PY_CLUSTER_EXP.csv'")
    con.execute(f"CREATE TABLE hse AS SELECT * FROM '{LANDING_DIR}/db_exports/hse_incident_log.csv'")
    df_capex = pd.read_excel(LANDING_DIR / "excel" / "capex_be_re_actuals.xlsx")
    con.register("capex_t", df_capex)
    con.execute("CREATE TABLE capex_budget AS SELECT * FROM capex_t")
    print(f"DuckDB in-memory load completed in {time.time() - t_db:.2f}s")

    # 2. Pre-extract all data for each (asset, month)
    print("Extracting query metrics for all 336 reports...")
    t_extract = time.time()
    tasks = []

    for a_idx, asset in enumerate(assets):
        wc_id = asset["wc_id"]
        asset_name = asset["name"]
        short_name = asset["short_name"]
        sector = asset["sector"]
        onshore_offshore = asset["onshore_offshore"]

        for m_idx, month in enumerate(months):
            prev_m, ly_m = get_relative_months(month)
            report_seed = (SEED + a_idx * 1000 + m_idx) % 2147483647

            # Query Production (Current, Prev, LY)
            df_p = con.execute(
                """
                SELECT 
                    month,
                    COALESCE(SUM(oil_production_mt), 0.0) as oil_production_mt,
                    COALESCE(SUM(gas_production_mmscm), 0.0) as gas_production_mmscm,
                    COALESCE(SUM(condensate_production_mt), 0.0) as condensate_production_mt,
                    COALESCE(SUM(total_production_boe), 0.0) as total_production_boe,
                    COALESCE(AVG(water_cut_pct), 0.0) as water_cut_pct,
                    COALESCE(SUM(active_producing_wells), 0) as active_producing_wells,
                    COALESCE(SUM(well_downtime_hours), 0.0) as well_downtime_hours,
                    COALESCE(AVG(operational_uptime_pct), 0.0) as operational_uptime_pct
                FROM prod
                WHERE asset_wc_id = ? AND month IN (?, ?, ?)
                GROUP BY month
            """,
                [wc_id, month, prev_m, ly_m],
            ).df()

            p_map = {row["month"]: row.to_dict() for _, row in df_p.iterrows()}
            cur_p = p_map.get(month, {})
            prev_p = p_map.get(prev_m, {})
            ly_p = p_map.get(ly_m, {})

            # Fields breakdown
            df_fld = con.execute(
                """
                SELECT 
                    field_id,
                    COALESCE(SUM(oil_production_mt), 0.0) as oil_production_mt,
                    COALESCE(SUM(gas_production_mmscm), 0.0) as gas_production_mmscm,
                    COALESCE(SUM(total_production_boe), 0.0) as total_production_boe,
                    COALESCE(AVG(water_cut_pct), 0.0) as water_cut_pct,
                    COALESCE(SUM(active_producing_wells), 0) as active_producing_wells,
                    COALESCE(SUM(well_downtime_hours), 0.0) as well_downtime_hours
                FROM prod
                WHERE asset_wc_id = ? AND month = ?
                GROUP BY field_id
                ORDER BY total_production_boe DESC
            """,
                [wc_id, month],
            ).df()

            # Trailing 6-month trend
            df_trend = con.execute(
                """
                SELECT 
                    month,
                    COALESCE(SUM(oil_production_mt), 0.0) as oil_mt,
                    COALESCE(SUM(gas_production_mmscm), 0.0) as gas_mmscm
                FROM prod
                WHERE asset_wc_id = ? AND month <= ?
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6
            """,
                [wc_id, month],
            ).df()
            trend_data = df_trend.iloc[::-1].to_dict(orient="records")

            # Operating cost breakdown
            df_cosp = con.execute(
                """
                SELECT 
                    cost_head,
                    cost_element_name,
                    COALESCE(SUM(amount_inr), 0.0) as amount_inr
                FROM cosp
                WHERE wc_id = ? AND month = ?
                GROUP BY cost_head, cost_element_name
                ORDER BY amount_inr DESC
            """,
                [wc_id, month],
            ).df()
            tot_opex_inr = float(df_cosp["amount_inr"].sum()) if len(df_cosp) > 0 else 0.0
            tot_boe = float(cur_p.get("total_production_boe", 0.0))
            lifting_cost_inr = (tot_opex_inr / tot_boe) if tot_boe > 0 else 0.0

            # Capex
            df_cap = con.execute(
                """
                SELECT 
                    COALESCE(SUM(budget_estimate_be_inr_cr), 0.0) as be_inr_cr,
                    COALESCE(SUM(revised_estimate_re_inr_cr), 0.0) as re_inr_cr,
                    COALESCE(SUM(actual_spend_inr_cr), 0.0) as actual_spend_inr_cr,
                    (COALESCE(SUM(actual_spend_inr_cr), 0.0) - COALESCE(SUM(budget_estimate_be_inr_cr), 0.0)) as variance_vs_be_cr
                FROM capex_budget
                WHERE asset_wc_id = ? AND month = ?
            """,
                [wc_id, month],
            ).df()
            cap_row = df_cap.iloc[0].to_dict() if len(df_cap) > 0 else {}

            df_cap_heads = con.execute(
                """
                SELECT 
                    project_name,
                    prj_id,
                    capex_head,
                    COALESCE(SUM(budget_estimate_be_inr_cr), 0.0) as be_cr,
                    COALESCE(SUM(actual_spend_inr_cr), 0.0) as actual_cr
                FROM capex_budget
                WHERE asset_wc_id = ? AND month = ?
                GROUP BY project_name, prj_id, capex_head
                ORDER BY actual_cr DESC
            """,
                [wc_id, month],
            ).df()

            # Headcount
            df_hc = con.execute(
                """
                SELECT 
                    COALESCE(SUM(headcount), 0) as total_headcount,
                    COALESCE(SUM(active_headcount), 0) as active_headcount,
                    COALESCE(SUM(on_leave_headcount), 0) as on_leave_headcount
                FROM hc
                WHERE wc_id = ? AND month = ?
            """,
                [wc_id, month],
            ).df()
            hc_row = df_hc.iloc[0].to_dict() if len(df_hc) > 0 else {}

            df_disc = con.execute(
                """
                SELECT 
                    discipline_id,
                    COALESCE(SUM(headcount), 0) as hc
                FROM hc
                WHERE wc_id = ? AND month = ?
                GROUP BY discipline_id
                ORDER BY hc DESC
                LIMIT 5
            """,
                [wc_id, month],
            ).df()

            # Payroll Overtime
            df_py = con.execute(
                """
                SELECT 
                    COALESCE(COUNT(DISTINCT PERNR), 0) as paid_employees,
                    COALESCE(SUM(overtime_hours), 0.0) as total_overtime_hours,
                    COALESCE(SUM(overtime_amount_inr), 0.0) as total_overtime_amount_inr
                FROM py
                WHERE wc_id = ? AND FPPER = ?
            """,
                [wc_id, month],
            ).df()
            py_row = df_py.iloc[0].to_dict() if len(df_py) > 0 else {}

            # HSE Incidents
            df_hse_sum = con.execute(
                """
                SELECT 
                    COALESCE(COUNT(*), 0) as total_incidents,
                    COALESCE(SUM(CASE WHEN lost_time_injury_flag = TRUE THEN 1 ELSE 0 END), 0) as lti_count,
                    COALESCE(SUM(days_lost), 0) as total_days_lost,
                    COALESCE(SUM(CASE WHEN fatigue_factor_flag = TRUE THEN 1 ELSE 0 END), 0) as fatigue_incidents
                FROM hse
                WHERE wc_id = ? AND month = ?
            """,
                [wc_id, month],
            ).df()
            hse_sum_row = df_hse_sum.iloc[0].to_dict() if len(df_hse_sum) > 0 else {}

            df_hse_list = con.execute(
                """
                SELECT 
                    incident_id,
                    incident_date,
                    incident_type,
                    severity_tier,
                    days_lost,
                    brief_description
                FROM hse
                WHERE wc_id = ? AND month = ?
                ORDER BY incident_date DESC
                LIMIT 5
            """,
                [wc_id, month],
            ).df()

            report_data = {
                "wc_id": wc_id,
                "asset_name": asset_name,
                "short_name": short_name,
                "sector": sector,
                "onshore_offshore": onshore_offshore,
                "month": month,
                "field_name_map": field_map,
                "prod_current": cur_p,
                "prod_prev": prev_p,
                "prod_ly": ly_p,
                "fields_data": df_fld.to_dict(orient="records"),
                "trend_data": trend_data,
                "cost_elements": df_cosp.to_dict(orient="records"),
                "total_opex_inr": tot_opex_inr,
                "lifting_cost_inr_per_boe": lifting_cost_inr,
                "capex_be_inr_cr": float(cap_row.get("be_inr_cr", 0.0)),
                "capex_re_inr_cr": float(cap_row.get("re_inr_cr", 0.0)),
                "capex_actual_spend_inr_cr": float(cap_row.get("actual_spend_inr_cr", 0.0)),
                "capex_variance_cr": float(cap_row.get("variance_vs_be_cr", 0.0)),
                "capex_heads": df_cap_heads.to_dict(orient="records"),
                "total_headcount": int(hc_row.get("total_headcount", 0)),
                "active_headcount": int(hc_row.get("active_headcount", 0)),
                "on_leave_headcount": int(hc_row.get("on_leave_headcount", 0)),
                "disciplines_data": df_disc.to_dict(orient="records"),
                "paid_employees": int(py_row.get("paid_employees", 0)),
                "total_overtime_hours": float(py_row.get("total_overtime_hours", 0.0)),
                "total_overtime_amount_inr": float(py_row.get("total_overtime_amount_inr", 0.0)),
                "hse_incidents_count": int(hse_sum_row.get("total_incidents", 0)),
                "hse_lti_count": int(hse_sum_row.get("lti_count", 0)),
                "hse_days_lost": int(hse_sum_row.get("total_days_lost", 0)),
                "hse_fatigue_count": int(hse_sum_row.get("fatigue_incidents", 0)),
                "hse_incidents_list": df_hse_list.to_dict(orient="records"),
            }

            # 15 exactly computed figures stored for sidecar & verification
            figures = {
                "oil_production_mt": float(cur_p.get("oil_production_mt", 0.0)),
                "gas_production_mmscm": float(cur_p.get("gas_production_mmscm", 0.0)),
                "total_production_boe": float(cur_p.get("total_production_boe", 0.0)),
                "water_cut_pct": float(cur_p.get("water_cut_pct", 0.0)),
                "well_downtime_hours": float(cur_p.get("well_downtime_hours", 0.0)),
                "active_producing_wells": float(cur_p.get("active_producing_wells", 0)),
                "total_opex_inr": tot_opex_inr,
                "lifting_cost_inr_per_boe": lifting_cost_inr,
                "total_headcount": int(hc_row.get("total_headcount", 0)),
                "total_overtime_hours": float(py_row.get("total_overtime_hours", 0.0)),
                "total_overtime_amount_inr": float(py_row.get("total_overtime_amount_inr", 0.0)),
                "hse_incidents_count": int(hse_sum_row.get("total_incidents", 0)),
                "capex_be_inr_cr": float(cap_row.get("be_inr_cr", 0.0)),
                "capex_actual_spend_inr_cr": float(cap_row.get("actual_spend_inr_cr", 0.0)),
                "oil_production_mt_prev_month": float(prev_p.get("oil_production_mt", 0.0)),
                "oil_production_mt_same_month_last_year": float(ly_p.get("oil_production_mt", 0.0)),
            }

            provenance_sql = build_provenance_sql_text(wc_id, month, prev_m, ly_m)

            tasks.append(
                {
                    "wc_id": wc_id,
                    "month": month,
                    "report_data": report_data,
                    "figures": figures,
                    "provenance_sql": provenance_sql,
                    "seed": report_seed,
                }
            )

    print(f"Data extraction for {len(tasks)} reports finished in {time.time() - t_extract:.2f}s")

    # 3. Parallel rendering of 336 reports
    num_cpus = min(os.cpu_count() or 4, 24)
    print(f"Rendering {len(tasks)} scanned PDF reports using {num_cpus} worker processes...")
    t_render = time.time()
    with mp.Pool(processes=num_cpus) as pool:
        manifest_rows = pool.map(process_report_task, tasks)

    print(f"All {len(tasks)} scanned PDFs rendered in {time.time() - t_render:.2f}s")

    # 4. Add template entries to Manifest
    template_manifest_entries = [
        {
            "doc_id": "DOC-TMPL-BOARD-NOTE",
            "title": "Board Note Template: Field Economics & Turnaround Options",
            "type": "template",
            "asset_wc_id": "",
            "month": "",
            "format": "docx",
            "provenance_sql": "",
            "questions_served": "C14, T1",
        },
        {
            "doc_id": "DOC-TMPL-AGT-PROPOSAL",
            "title": "Annual General Transfer (AGT) Proposal Sheet Template FY27",
            "type": "template",
            "asset_wc_id": "",
            "month": "",
            "format": "xlsx",
            "provenance_sql": "",
            "questions_served": "H10",
        },
        {
            "doc_id": "DOC-TMPL-PARLIAMENT-REPLY",
            "title": "Parliament Question Reply Template (Lok Sabha / Rajya Sabha)",
            "type": "template",
            "asset_wc_id": "",
            "month": "",
            "format": "docx",
            "provenance_sql": "",
            "questions_served": "X7",
        },
        {
            "doc_id": "DOC-TMPL-QUARTERLY-PNL",
            "title": "Quarterly Asset Performance & Operating P&L Review Template",
            "type": "template",
            "asset_wc_id": "",
            "month": "",
            "format": "xlsx",
            "provenance_sql": "",
            "questions_served": "F10",
        },
    ]

    all_manifest_rows = manifest_rows + template_manifest_entries
    df_manifest = pd.DataFrame(all_manifest_rows)
    df_manifest.to_csv(MANIFEST_PATH, index=False)
    print(f"Wrote {len(df_manifest)} entries to {MANIFEST_PATH}")
    print(f"Total Step 3.4 execution finished in {time.time() - t_start:.2f}s")


if __name__ == "__main__":
    main()
