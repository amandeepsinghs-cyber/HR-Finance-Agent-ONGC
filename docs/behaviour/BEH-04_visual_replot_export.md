# BEH-04: Visual Re-plot & Export Behaviour

**Features:** FEAT-025, FEAT-026, FEAT-027 · **Specs:** [SPEC-09](../specs/SPEC-09_statement_visual_chart_portfolio.md), [SPEC-10](../specs/SPEC-10_export_suite.md) · **Steps:** P4.1–P4.7 · **Verbatims:** V7, V15, V21, V2

> **BLUF.** A statement is always a statement table; "express as waterfall" gives a signed bridge that ends at reported PAT or an honest "can't" — never a fabricated bridge or a false "I've switched…". Explicit chart words win; incompatible requests get the nearest allowed kind with a one-line note. Every table/chart exports honestly to xlsx/CSV/PDF/PNG/SVG/docx, with ₹ and Hindi rendered correctly, and "Google Sheets/Docs" download with a truthful toast.

**Conventions:** numbers in `{}` come from verified SSOT rows (SPEC-01) at test time; until P1 lands, fixture `yukti/contracts/fixtures/bridge/pnl_fixture_synthetic.json` (labelled synthetic) is used.

---

## A. Statements are tables

| ID | Given | When | Then |
|---|---|---|---|
| BEH-04.01 | CMD | "Show the income statement for FY22 to FY26" | `visual.type=statement`, `statement=pnl`, periods `FY26…FY22` (latest-first), indented lines, bold subtotals with rules, negatives `(x)`, ₹ crore header, footnote with AR doc + pages; ≤ 3 KPI tiles |
| BEH-04.02 | after .01 | click a column header | No sort (order preserved) |
| BEH-04.03 | after .01 | "Show this as a histogram" | Table stays; note "A histogram needs a distribution; the income statement is shown as a table. Say 'waterfall' for a bridge." |
| BEH-04.04 | CMD | "Show revenue, EBITDA and PAT for FY24 in tabular form" | `table` (or statement subset) — "tabular form" recognised (diag_C §B) |
| BEH-04.05 | CMD | "Balance sheet FY25" | statement `balance_sheet`; `totals_check.passed=true` (A = E + L) shown in footnote |

## B. Waterfall

| ID | Given | When | Then |
|---|---|---|---|
| BEH-04.10 | after .01 (FY26 selected) | "Can you express it as a waterfall?" | `chart.kind=waterfall`, rows typed `delta/total`; first bar Revenue from operations; deductions negative (maroon), subtotals only if present in SSOT; last bar = reported PAT ±₹0.5 cr; connector lines; title "FY26: ₹{rev} cr revenue to ₹{pat} cr PAT" |
| BEH-04.11 | same | 🎙 "इसे वॉटरफॉल में दिखाओ" | Identical chart to .10; Hindi narration |
| BEH-04.12 | multi-year statement | "waterfall" | Asks "Which year?" chips FY26/FY25/… (bridge is single-period) unless one period is selected |
| BEH-04.13 | KPI visual "PAT FY26" (single value) | "express this as a waterfall" | BridgeError copy: "I can't build a reliable bridge from a single number. Here is the profit and loss bridge for FY26 instead." → if statement lines exist, shows bridge; else "…Here is the statement table." **Never** "I've switched the screen view to a waterfall" without a chart (fedback2 regression) |
| BEH-04.14 | P&L lacking an EBITDA line | "waterfall" | Bridge without any EBITDA bar; no "OPEX & Levies"/"DD&A" synthetic bars; grep test on code (SPEC-09 AC2) |
| BEH-04.15 | Bridge where subtotal mismatch > ₹0.5 cr (corrupt fixture) | "waterfall" | BridgeError "lines don't add up to the reported PBT"; table remains; error logged |
| BEH-04.16 | after .10 | "back to the table" | Statement table restored exactly (from stored visual, not re-query) |
| BEH-04.17 | after .10 | tap the "Statutory levies" bar, or chip "Why did Statutory levies change?" | SPEC-08 §6 grounded-why answer for that `line_code` and FY pair (BEH-03.07 shape: attribution + cited AR evidence); waterfall stays in the feed above (SPEC-09 §4.3 drill) |

## C. Explicit kind & re-plot

| ID | Given | When | Then |
|---|---|---|---|
| BEH-04.20 | CMD | "Show revenue vs profit for the last 5 years as a line chart" | `line` (not waterfall; BUG-22) |
| BEH-04.21 | CMD | "Plot revenue and PAT trend over 10 years" | `line` |
| BEH-04.22 | CMD | "Revenue and PAT margin for 5 years" | `combo` dual axis: revenue bars (₹ cr, left), margin line (%, right) |
| BEH-04.23 | headcount by WC | "make it a pie" | donut top-7 + Others with note |
| BEH-04.24 | headcount by WC × grade | "100% stacked" | `stacked100`, each bar sums to 100% |
| BEH-04.25 | Delhi roster | "box plot of tenure by level" | `box` per level with median/IQR/whiskers |
| BEH-04.26 | monthly overtime by WC | "heatmap" | `heatmap` month × WC, values labelled |
| BEH-04.27 | Brent × FX sensitivity result (SPEC-02) | default | `sensitivity_grid`, base cell outlined, exact values |
| BEH-04.28 | DCF one-way sensitivities | default | `tornado` sorted by range |
| BEH-04.29 | revenue time series | "show as pie" | column over time + note "Shares of time periods aren't meaningful" |
| BEH-04.30 | Delhi by level | "histogram" | ordered column (categorical), note once |
| BEH-04.31 | age of Delhi staff (per-record) | "histogram" | true `histogram` with bins + median marker |
| BEH-04.32 | any chart | "line chart" then "go back" | previous kind restored; re-plots always from original rows (no drift) |

## D. Export

| ID | Given | When | Then |
|---|---|---|---|
| BEH-04.40 | statement .01 | "Export this to Excel" | xlsx: title rows, frozen header, FY columns latest-first, `#,##0;(#,##0)` (or Indian format per SPEC-10 Q1), indents by level, bold subtotals, source footnote; filename `yukti_pnl_standalone_fy22-fy26_cmd_….xlsx` |
| BEH-04.41 | statement .01 | "Download as PDF" | PDF with embedded Noto fonts; `pdftotext` contains `₹` and no `■`; table header repeats across pages; chart image if a chart was visible |
| BEH-04.42 | Hindi-titled answer | "पीडीएफ डाउनलोड करो" | PDF Devanagari title rendered; `pdffonts` lists NotoSansDevanagari embedded |
| BEH-04.43 | waterfall .10 | "Download the chart as PNG" | PNG 2× with title, unit and source drawn in; audit row written |
| BEH-04.44 | any chart | "SVG" | valid SVG download |
| BEH-04.45 | roster | "export as CSV" | UTF-8 BOM CSV; Excel opens Hindi names intact |
| BEH-04.46 | any table | "Export this statement to Sheets" (fb4 chip) | xlsx downloads; toast "Google Sheets isn't connected yet, so I've downloaded an Excel file. In Sheets, use File → Import to open it."; no `docs.google.com` URL |
| BEH-04.47 | any table | "Export to Google Docs" | docx downloads; matching toast; no fake link (BUG-25) |
| BEH-04.48 | any | "Export to Word" | docx with table + chart image |
| BEH-04.49 | E2_HR, roster masked | "export this" | `_aggregate` xlsx, no Name column, banner "Aggregate view (access level: E2_HR)" |
| BEH-04.50 | E2_HR | GET `/api/export/{CMD's export_id}` | 403 |

## E. Visual quality gates (per SPEC-09 §4.7)

| ID | Check | Pass |
|---|---|---|
| BEH-04.60 | F1–F4 ★ on statement + waterfall scorecards | all pass |
| BEH-04.61 | Light + dark screenshots for statement, waterfall, combo, heatmap, box, sensitivity grid, tornado | R-O score ≥ 9/10 |
| BEH-04.62 | Orb visible in docked mode while listening/thinking/speaking | screenshot |
