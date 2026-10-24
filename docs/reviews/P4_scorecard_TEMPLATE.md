# Finance Visuals Rubric Scorecard Template (`P4.8`, SPEC-09 §4.7)

**Reviewer:** `<independent reviewer R>` · **Date:** `YYYY-MM-DD` · **Branch / SHA:** `v3/P4-visual @ <sha>`
**Rubric:** [`docs/chart_quality_rubric.md` §F](../chart_quality_rubric.md) · **9/10 Rule:** All `★` criteria (`F1–F4`) must pass (`100%`) and `≥ 90%` of applicable non-`★` criteria (`F5–F14`) must pass across both light and dark themes at `1440×900`.

---

## 1. Summary Matrix (5 Visuals × 2 Themes)

| Visual | Theme | Screenshot | `★` Pass (`F1–F4`) | Non-`★` Pass (`F5–F14`) | Overall (`≥ 9/10`?) |
|---|---|---|---|---|---|
| `statement` | Light | [`assets/P4_statement_light.png`](assets/P4_statement_light.png) | / 3 applicable | / 10 | |
| `statement` | Dark | [`assets/P4_statement_dark.png`](assets/P4_statement_dark.png) | / 3 applicable | / 10 | |
| `waterfall` | Light | [`assets/P4_waterfall_light.png`](assets/P4_waterfall_light.png) | / 3 applicable | / 7 applicable | |
| `waterfall` | Dark | [`assets/P4_waterfall_dark.png`](assets/P4_waterfall_dark.png) | / 3 applicable | / 7 applicable | |
| `combo` | Light | [`assets/P4_combo_light.png`](assets/P4_combo_light.png) | / 2 applicable | / 6 applicable | |
| `combo` | Dark | [`assets/P4_combo_dark.png`](assets/P4_combo_dark.png) | / 2 applicable | / 6 applicable | |
| `sensitivity_grid` | Light | [`assets/P4_sensitivity_grid_light.png`](assets/P4_sensitivity_grid_light.png) | / 2 applicable | / 6 applicable | |
| `sensitivity_grid` | Dark | [`assets/P4_sensitivity_grid_dark.png`](assets/P4_sensitivity_grid_dark.png) | / 2 applicable | / 6 applicable | |
| `tornado` | Light | [`assets/P4_tornado_light.png`](assets/P4_tornado_light.png) | / 2 applicable | / 6 applicable | |
| `tornado` | Dark | [`assets/P4_tornado_dark.png`](assets/P4_tornado_dark.png) | / 2 applicable | / 6 applicable | |

---

## 2. Per-Criterion Evaluation (`F1–F14`)

### 2.1 `statement` (`P4_statement_light.png` / `P4_statement_dark.png`)

| ID | Criterion | Measure | Pass threshold | Light (`✅`/`❌`/`N/A`) | Dark (`✅`/`❌`/`N/A`) | Evidence (file:line / screenshot / test) |
|---|---|---|---|---|---|---|
| F1 ★ | Numbers match SSOT | every displayed value vs `fact_financial_statement_line` / fixture at display precision | 0 mismatches | | | |
| F2 ★ | No fabricated values | every number has lineage (`source.doc/page` or computed-from ids) | 100% | | | |
| F3 ★ | Waterfall closes | last bar = reported PAT, subtotals = reported | Δ ≤ ₹0.5 cr | N/A | N/A | |
| F4 ★ | Line order = source order | statement rows vs SSOT `order` | 100% | | | |
| F5 | Accounting negatives | negatives rendered `(x)` in tables/exports | 100% | | | |
| F6 | Hierarchy visible | indentation by level; subtotal bold + rule; total double rule | all rows | | | |
| F7 | Units explicit | unit in header or axis ("₹ crore", "%") | every visual | | | |
| F8 | FY labelling | Indian FY labels, latest-first in tables, chronological on time axes | 100% | | | |
| F9 | Tabular figures, right-aligned | computed style | all numeric cells | | | |
| F10 | Source footnote | doc + pages + basis + as-of present | 100% | | | |
| F11 | Insight title | title states the finding (contains a number or direction), not "Updated Chart View" | 100% | | | |
| F12 | Density | ≤ 3 KPI tiles above a statement; statement starts above the fold at 1440×900 | pass | | | |
| F13 | Contrast | light + dark ≥ 4.5:1 text, ≥ 3:1 graphical | `lint:contrast` OK | | | |
| F14 | Export fidelity | xlsx/PDF values = screen values; formats per SPEC-10 | 100% | | | |

### 2.2 `waterfall` (`P4_waterfall_light.png` / `P4_waterfall_dark.png`)

| ID | Criterion | Measure | Pass threshold | Light (`✅`/`❌`/`N/A`) | Dark (`✅`/`❌`/`N/A`) | Evidence (file:line / screenshot / test) |
|---|---|---|---|---|---|---|
| F1 ★ | Numbers match SSOT | every displayed value vs `fact_financial_statement_line` / fixture at display precision | 0 mismatches | | | |
| F2 ★ | No fabricated values | every number has lineage (`source.doc/page` or computed-from ids) | 100% | | | |
| F3 ★ | Waterfall closes | last bar = reported PAT, subtotals = reported | Δ ≤ ₹0.5 cr | | | |
| F4 ★ | Line order = source order | bridge bars follow statement order | 100% | | | |
| F7 | Units explicit | unit in header or axis ("₹ crore", "%") | every visual | | | |
| F8 | FY labelling | Indian FY labels | 100% | | | |
| F10 | Source footnote | doc + pages + basis + as-of present | 100% | | | |
| F11 | Insight title | title states the finding (contains a number or direction) | 100% | | | |
| F13 | Contrast | light + dark ≥ 4.5:1 text, ≥ 3:1 graphical | `lint:contrast` OK | | | |
| F14 | Export fidelity | PNG/SVG/xlsx/PDF values = screen values | 100% | | | |

### 2.3 `combo` (`P4_combo_light.png` / `P4_combo_dark.png`)

| ID | Criterion | Measure | Pass threshold | Light (`✅`/`❌`/`N/A`) | Dark (`✅`/`❌`/`N/A`) | Evidence (file:line / screenshot / test) |
|---|---|---|---|---|---|---|
| F1 ★ | Numbers match SSOT | every displayed value vs fixture at display precision | 0 mismatches | | | |
| F2 ★ | No fabricated values | every number has lineage | 100% | | | |
| F7 | Units explicit | left axis `₹ Cr`, right axis `%` | every visual | | | |
| F8 | FY labelling | chronological FY22→FY26 on time axis | 100% | | | |
| F10 | Source footnote | doc + pages + basis + as-of present | 100% | | | |
| F11 | Insight title | title states the finding (contains a number or direction) | 100% | | | |
| F13 | Contrast | light + dark ≥ 4.5:1 text, ≥ 3:1 graphical | `lint:contrast` OK | | | |
| F14 | Export fidelity | PNG/SVG/xlsx/PDF values = screen values | 100% | | | |

### 2.4 `sensitivity_grid` (`P4_sensitivity_grid_light.png` / `P4_sensitivity_grid_dark.png`)

| ID | Criterion | Measure | Pass threshold | Light (`✅`/`❌`/`N/A`) | Dark (`✅`/`❌`/`N/A`) | Evidence (file:line / screenshot / test) |
|---|---|---|---|---|---|---|
| F1 ★ | Numbers match SSOT | exact cell values (`₹/share`), `n/m` where `WACC − g < 1pp`, base outlined | 0 mismatches | | | |
| F2 ★ | No fabricated values | every number has lineage | 100% | | | |
| F7 | Units explicit | row (`WACC (%)`), col (`Terminal g (%)`), output (`₹/share`) | every visual | | | |
| F9 | Tabular figures | exact figures in all 81 cells | all numeric cells | | | |
| F10 | Source footnote | caption + source present | 100% | | | |
| F11 | Insight title | title states subject & encoding | 100% | | | |
| F13 | Contrast | light + dark ≥ 4.5:1 text, ≥ 3:1 graphical | `lint:contrast` OK | | | |
| F14 | Export fidelity | PNG/SVG/xlsx/PDF values = screen values | 100% | | | |

### 2.5 `tornado` (`P4_tornado_light.png` / `P4_tornado_dark.png`)

| ID | Criterion | Measure | Pass threshold | Light (`✅`/`❌`/`N/A`) | Dark (`✅`/`❌`/`N/A`) | Evidence (file:line / screenshot / test) |
|---|---|---|---|---|---|---|
| F1 ★ | Numbers match SSOT | bars sorted by `|high − low|` desc, centred on base line | 0 mismatches | | | |
| F2 ★ | No fabricated values | every number has lineage | 100% | | | |
| F7 | Units explicit | driver input ranges on y-axis, `₹/share` on x-axis & bar ends | every visual | | | |
| F10 | Source footnote | caption + source present | 100% | | | |
| F11 | Insight title | title states subject & encoding | 100% | | | |
| F13 | Contrast | light + dark ≥ 4.5:1 text, ≥ 3:1 graphical | `lint:contrast` OK | | | |
| F14 | Export fidelity | PNG/SVG/xlsx/PDF values = screen values | 100% | | | |
