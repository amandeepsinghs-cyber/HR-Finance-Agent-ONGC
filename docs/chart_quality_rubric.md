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
| **Table** | Sticky header, right-aligned tabular numbers, inline bars for the main measure, negative in maroon | Centre-aligned numbers |
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
