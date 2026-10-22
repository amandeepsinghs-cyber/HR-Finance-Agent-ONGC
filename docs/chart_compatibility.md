# Chart compatibility matrix (U5.7)

_Generated from `src/charts/compat.ts` by `scripts/gen_compat_doc.ts`; do not edit by hand._

One engine (`replot(visual, kind)`) serves voice ("show as pie"), typed commands and the toolbar, so all three give the same picture. Re-plots are computed from the answer's original rows (kept in `visual.source`), never from the previous re-plot, so switching back and forth never drifts. No backend call.

**Legend:** ✅ native · 🔄 transform (bins → slices, count by category, top-N + Others, measure selection) · ↪️ nearest alternative shown, with a one-line note

| Data shape | Example | bar | hbar | donut | pie | line | area | histogram | scatter | treemap | waterfall | funnel | grouped_bar | stacked_bar | bullet | table |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Categorical, positive (`categorical`) | Headcount by work centre (14) | ✅ | ✅ | 🔄 | 🔄 | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ |
| Categorical with losses (`categorical`) | Field P&L FY26 (12, some negative) | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ |
| Ordinal, multi-measure (`multi_measure`) | Delhi 5+ yrs by grade (count/exempt/due) | ✅ | ✅ | 🔄 | 🔄 | ✅ | ✅ | ✅ | ✅ | 🔄 | ✅ | 🔄 | ✅ | ✅ | ↪️ | ✅ |
| Time series (`time`) | Revenue FY22–FY26 | ✅ | ✅ | ↪️ | ↪️ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ |
| Distribution (binned) (`distribution`) | Age bands | ✅ | ✅ | 🔄 | 🔄 | ✅ | ✅ | ✅ | ↪️ | ✅ | ↪️ | ✅ | ↪️ | ↪️ | ↪️ | ✅ |
| Records (named people) (`records`) | Delhi roster (419 rows) | 🔄 | 🔄 | 🔄 | 🔄 | ↪️ | ↪️ | 🔄 | ↪️ | 🔄 | ↪️ | 🔄 | ↪️ | ↪️ | ↪️ | ✅ |
| Single value (`single`) | PAT FY26 | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ |

## Transform rules
- **Histogram → pie/donut/treemap/funnel/bar:** slices (bars) are exactly the histogram bins, in bin order.
- **Records → pie/bar:** count people by the first low-cardinality column (e.g. grade); records → histogram bins the main numeric column (e.g. years of stay).
- **Many categories → pie/donut:** top 9 + "Others (n)".
- **Multi-measure → part-of-whole:** uses the selected metric (Metric menu / `{ metric }`).
- **Losses → pie/donut/treemap/funnel:** not allowed (a part-of-whole can't be negative) → diverging bars.
- **Time → pie:** shares of periods aren't meaningful → columns over time.
- **Nominal categories → line/area/histogram:** implies order that doesn't exist → bars (histogram allowed as a value distribution when ≥ 8 items).
- **Bullet:** needs a target column; otherwise ranked bars. **Scatter:** needs two measures.

## Notes shown to the user
- **Categorical, positive → donut** (transform): Top 7 shown; the remaining 7 are grouped as Others.
- **Categorical, positive → pie** (transform): Top 7 shown; the remaining 7 are grouped as Others.
- **Categorical, positive → line** (alternative): A line suggests a trend over time; these are separate categories, so here is a bar chart.
- **Categorical, positive → area** (alternative): An area suggests a trend over time; these are separate categories, so here is a bar chart.
- **Categorical, positive → histogram** (alternative): Only 14 values — too few for a distribution, so here is a ranked bar chart.
- **Categorical, positive → scatter** (alternative): A scatter plot needs two measures; there is one here.
- **Categorical, positive → waterfall** (alternative): A waterfall shows gains and losses building a total; these are all positive, so a ranked bar chart.
- **Categorical, positive → funnel** (alternative): A funnel needs ordered stages; these are separate categories, so a ranked bar chart.
- **Categorical, positive → grouped_bar** (alternative): There is only one measure, so a simple bar chart.
- **Categorical, positive → stacked_bar** (alternative): There is only one measure, so a simple bar chart.
- **Categorical, positive → bullet** (alternative): There is no target to compare against, so a ranked bar chart.
- **Categorical with losses → donut** (alternative): A donut can't show losses, so gains and losses are shown as bars.
- **Categorical with losses → pie** (alternative): A pie can't show losses, so gains and losses are shown as bars.
- **Categorical with losses → line** (alternative): A line suggests a trend over time; these are separate categories, so here is a bar chart.
- **Categorical with losses → area** (alternative): An area suggests a trend over time; these are separate categories, so here is a bar chart.
- **Categorical with losses → histogram** (alternative): Only 12 values — too few for a distribution, so here is a ranked bar chart.
- **Categorical with losses → scatter** (alternative): A scatter plot needs two measures; there is one here.
- **Categorical with losses → treemap** (alternative): A treemap can't show losses, so gains and losses are shown as bars.
- **Categorical with losses → funnel** (alternative): A funnel can't show losses, so gains and losses are shown as bars.
- **Categorical with losses → grouped_bar** (alternative): There is only one measure, so a simple bar chart.
- **Categorical with losses → stacked_bar** (alternative): There is only one measure, so a simple bar chart.
- **Categorical with losses → bullet** (alternative): There is no target to compare against, so a ranked bar chart.
- **Ordinal, multi-measure → donut** (transform): Showing Count; pick another metric from the menu.
- **Ordinal, multi-measure → pie** (transform): Showing Count; pick another metric from the menu.
- **Ordinal, multi-measure → treemap** (transform): Showing Count; pick another metric from the menu.
- **Ordinal, multi-measure → funnel** (transform): Showing Count; pick another metric from the menu.
- **Ordinal, multi-measure → bullet** (alternative): There is no target to compare against, so a ranked bar chart.
- **Time series → donut** (alternative): Shares of time periods aren't meaningful, so here is a column chart over time.
- **Time series → pie** (alternative): Shares of time periods aren't meaningful, so here is a column chart over time.
- **Time series → histogram** (alternative): This is a trend over time, so a line chart fits better than a histogram.
- **Time series → scatter** (alternative): This is a trend over time, so a line chart fits better than a scatter.
- **Time series → treemap** (alternative): Shares of time periods aren't meaningful, so here is a column chart over time.
- **Time series → funnel** (alternative): Shares of time periods aren't meaningful, so here is a column chart over time.
- **Time series → grouped_bar** (alternative): There is only one measure, so a simple column chart.
- **Time series → stacked_bar** (alternative): There is only one measure, so a simple column chart.
- **Time series → bullet** (alternative): There is no target to compare against.
- **Distribution (binned) → donut** (transform): Slices are the histogram bins.
- **Distribution (binned) → pie** (transform): Slices are the histogram bins.
- **Distribution (binned) → scatter** (alternative): A scatter doesn't suit a distribution; showing the histogram.
- **Distribution (binned) → waterfall** (alternative): A waterfall doesn't suit a distribution; showing the histogram.
- **Distribution (binned) → grouped_bar** (alternative): A grouped bar doesn't suit a distribution; showing the histogram.
- **Distribution (binned) → stacked_bar** (alternative): A stacked bar doesn't suit a distribution; showing the histogram.
- **Distribution (binned) → bullet** (alternative): A bullet doesn't suit a distribution; showing the histogram.
- **Records (named people) → bar** (transform): Counted people by grade.
- **Records (named people) → hbar** (transform): Counted people by grade.
- **Records (named people) → donut** (transform): Counted people by grade.
- **Records (named people) → pie** (transform): Counted people by grade.
- **Records (named people) → line** (alternative): A line doesn't fit individual records; showing the distribution instead.
- **Records (named people) → area** (alternative): An area doesn't fit individual records; showing the distribution instead.
- **Records (named people) → histogram** (transform): Distribution of stay (years) across 419 people.
- **Records (named people) → scatter** (alternative): A scatter doesn't fit individual records; showing the distribution instead.
- **Records (named people) → treemap** (transform): Counted people by grade.
- **Records (named people) → waterfall** (alternative): A waterfall doesn't fit individual records; showing the distribution instead.
- **Records (named people) → funnel** (transform): Counted people by grade.
- **Records (named people) → grouped_bar** (alternative): A grouped bar doesn't fit individual records; showing the distribution instead.
- **Records (named people) → stacked_bar** (alternative): A stacked bar doesn't fit individual records; showing the distribution instead.
- **Records (named people) → bullet** (alternative): A bullet doesn't fit individual records; showing the distribution instead.
- **Single value → bar** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → hbar** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → donut** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → pie** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → line** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → area** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → histogram** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → scatter** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → treemap** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → waterfall** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → funnel** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → grouped_bar** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → stacked_bar** (alternative): This answer is a single number, so there is nothing to chart.
- **Single value → bullet** (alternative): This answer is a single number, so there is nothing to chart.
