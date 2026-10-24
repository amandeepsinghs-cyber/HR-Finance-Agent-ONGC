# Yukti AI: Chart Quality Rubric (`chart_quality_rubric.md`)

**Purpose:** a shared, checkable standard for "elegant and most professional" charts (Verbatim 15). It is used at the U1.5 gate (reference charts), U5.9 (every chart type), and in any G4 review that touches a chart.
**Scoring:** each criterion is scored **1–5**. **Pass = every criterion ≥ 4** for the chart type, in **both light and dark** themes, at **1440p and 4K**. The sponsor confirms the final visual (G5).
**Linked:** FEAT-015, D-13, D-14 · tokens: `yukti/frontend/src/design/tokens.json` · theme: `src/charts/theme.ts`

---

## The 8 criteria

| # | Criterion | 5 = excellent | 3 = acceptable | 1 = fails | Checkable signals |
|---|---|---|---|---|---|
| **C1** | **Message first (hierarchy)** | The chart answers the question at a glance: the key entity or value is emphasised (accent or callout) and everything else recedes | Correct data, but no emphasis; the eye wanders | Wrong metric or entity for the question; the key point isn't visible | Title states the insight or subject; ≤ 1 highlighted series or bar; aggregates ("Others") muted and never ranked as a top item |
| **C2** | **Clarity of encoding** | The chart type fits the data shape (FEAT-015 matrix); ± values diverge around zero; part-to-whole only for real wholes | Type works but isn't optimal | Misleading: truncated bar baseline, pie of non-parts, mixed units on one axis | Bars start at 0; negative values maroon and on the opposite side; dual axis only for combo with distinct units |
| **C3** | **Labelling** | Direct labels where possible; units are clear (₹ Cr, %, count); no overlaps; legends only when needed | Some labels collide or the legend is needed for reading | Overlapping labels, unlabeled units, truncated names | Zero label collisions at both sizes; Indian number format (lakh/crore); axis names carry units |
| **C4** | **Colour semantics** | Tokens only; restrained palette (1 accent + neutrals unless categories need hues); maroon = loss or negative only; colour-blind safe | Palette fine but more hues than needed | Arbitrary or rainbow colours; red/green as the only cue; brand saffron used as data | `lint:tokens` OK; ≤ 6 hues visible; every data colour ≥ 3:1 on the card (`lint:contrast`) |
| **C5** | **Density & whitespace** | Generous margins; gridlines faint; no chart junk (3-D, heavy borders, shadows on data); ≤ ~12 categories or a top-N + Other | Slightly busy | Cramped, noisy or illegible | Gridlines use `chart-grid`; ≥ 16 px inner padding; > 12 categories → top-N + "Other" or scroll |
| **C6** | **Interaction & tooltips** | Tooltip shows value, share and rank with consistent formatting; hover emphasis is subtle; zoom only for long series | Basic tooltip | No tooltip, or raw unformatted numbers | Tooltip uses `tooltipCard`; values go through `charts/format.ts` |
| **C7** | **Motion** | Purposeful: enter ≤ 600 ms, type switch morphs (universal transition) ≤ 400 ms, no gratuitous loops; respects reduced-motion | Motion fine but not morphing between types | Jarring or slow animation; layout jump on update | `ANIM` from tokens; `universalTransition` on series; `prefers-reduced-motion` honoured |
| **C8** | **Consistency & legibility** | Same fonts, sizes, radii and spacing as the UI; readable at 5 m (big screen); identical look across chart types | Minor inconsistencies | Mixed fonts or sizes; unreadable on the big screen | Fonts from `--font-sans`; label sizes via `px(t, …)` scale; same title/subtitle treatment for every type |

---

## Reference standards per chart family

| Family | Must have | Must not |
|---|---|---|
| **Bar / H-bar (ranked)** | Sorted; highlight top or bottom per the question; value labels at bar ends; "Others" pinned last and muted | Rank an aggregate bucket; more than ~12 bars without top-N |
| **Diverging bar (± values: P&L, variance)** | Zero line; losses in maroon to the left/bottom; profits in accent | Single-colour bars for ± data |
| **Line / Area** | Time on x; end labels for ≤ 4 series; area only for a single series or a stacked whole | > 6 series without small multiples |
| **Pie / Donut** | ≤ 8 slices (rest → "Other"); centre total on donut; legend with values + % | Pie for non-additive or time data |
| **Histogram** | Bins labelled with ranges; mean and median markers; optional density line | Gaps between bins (they're continuous) |
| **Treemap** | Labels readable via `labelOn()`; negatives flagged | Labels on tiny tiles (hide < min area) |
| **Scatter / Bubble** | Both axes labelled with units; quadrant or reference lines when meaningful | Bubble size without a legend |
| **Waterfall** | Start/end totals distinct; increases accent, decreases maroon | Floating bars without connectors |
| **KPI** | Big tabular number, unit, delta pill (▲/▼ + semantic colour), comparison basis | Delta without basis ("vs FY25") |
| **Table** | Sticky header, right-aligned tabular numbers, inline bars for the main measure (non-statement tables only), negative in maroon | Centre-aligned numbers; inline bars never on statements |
| **Financial Statement (`statement`)** | Source line order preserved; level indentation (16 px/level); bold ruled subtotals & double-ruled totals; `(x)` accounting negatives; Indian FY columns latest-first; source + page + basis footnote | Column sorting controls; inline bars; minus signs `-x` in figure cells; truncation/ellipsis on row labels |
| **Map** | Neutral base map (`chart-map-area`), sequential ramp for magnitude, labelled top locations | Categorical rainbow on a map |

---

## Scorecard template (copy into `docs/reviews/<step>.md`)

| Chart type | Theme | Size | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | Pass? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H-bar | light | 1440p | | | | | | | | | | |

**Known baseline defects to clear** (from [`docs/reviews/U0.5.md`](reviews/U0.5.md)):
- V1 "Others" ranked as the highest bar (C1)
- V2 P&L with no diverging encoding (C2)
- V3 average label overlapping a tick (C3)
- V4 light donut slices with low contrast (C4)
- V6 heavy 11-pill type switcher (C8 / U5.8)

---

## Section F: Finance Rubric Additions (F1–F14, SPEC-09 §4.7)

Applies to `statement`, `waterfall`, `combo`, `sensitivity_grid`, `tornado`, and finance tables.
**9/10 rule:** **9/10 = all ★ criteria pass and ≥ 90% of the rest.**

| ID | Criterion | Measure | Pass |
|---|---|---|---|
| F1 ★ | Numbers match SSOT | every displayed value vs `fact_financial_statement_line` at display precision | 0 mismatches |
| F2 ★ | No fabricated values | every number has lineage (`source.doc/page` or computed-from ids) | 100% |
| F3 ★ | Waterfall closes | last bar = reported PAT (or closing cash), subtotals = reported | Δ ≤ ₹0.5 cr |
| F4 ★ | Line order = source order | statement rows vs SSOT `order` | 100% |
| F5 | Accounting negatives | negatives rendered `(x)` in tables/exports | 100% |
| F6 | Hierarchy visible | indentation by level; subtotal bold + rule; total double rule | all rows |
| F7 | Units explicit | unit in header or axis ("₹ crore", "%") | every visual |
| F8 | FY labelling | Indian FY labels, latest-first in tables, chronological on time axes | 100% |
| F9 | Tabular figures, right-aligned | computed style | all numeric cells |
| F10 | Source footnote | doc + pages + basis + as-of present | 100% |
| F11 | Insight title | title states the finding (contains a number or direction), not "Updated Chart View" | 100% |
| F12 | Density | ≤ 3 KPI tiles above a statement; statement starts above the fold at 1440×900 | pass |
| F13 | Contrast | light + dark ≥ 4.5:1 text, ≥ 3:1 graphical | `lint:contrast` OK |
| F14 | Export fidelity | xlsx/PDF values = screen values; formats per SPEC-10 | 100% |

Scorecards: one per visual type (`statement`, `waterfall`, `combo`, `sensitivity_grid`, `tornado`) in light + dark under `docs/reviews/assets/P4_*`, scored by an independent reviewer (`R`) using [`docs/reviews/P4_scorecard_TEMPLATE.md`](reviews/P4_scorecard_TEMPLATE.md) (no self-scoring by the implementer).

