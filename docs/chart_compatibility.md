# Chart compatibility matrix (U5.7)

_Generated from `src/charts/compat.ts` by `scripts/gen_compat_doc.ts`; do not edit by hand._

One engine (`replot(visual, kind)`) serves voice ("show as pie"), typed commands and the toolbar, so all three give the same picture. Re-plots are computed from the answer's original rows (kept in `visual.source`), never from the previous re-plot, so switching back and forth never drifts. No backend call.

**Legend:** ✅ native · 🔄 transform (bins → slices, count by category, top-N + Others, measure selection) · ↪️ nearest alternative shown, with a one-line note

| Data shape | Example | bar | hbar | donut | pie | line | area | histogram | scatter | treemap | waterfall | funnel | grouped_bar | stacked_bar | stacked_100 | combo | heatmap | box | gauge | bullet | table |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Categorical, positive (`categorical`) | Headcount by work centre (14) | ✅ | ✅ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ↪️ | ↪️ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ✅ |
| Categorical with losses (`categorical`) | Field P&L FY26 (12, some negative) | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ↪️ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ✅ |
| Ordinal, multi-measure (`multi_measure`) | Delhi 5+ yrs by grade (count/exempt/due) | ✅ | ✅ | 🔄 | 🔄 | ✅ | ✅ | ✅ | ✅ | 🔄 | ✅ | 🔄 | ✅ | ✅ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ✅ | ✅ |
| Time series (`time`) | Revenue FY22–FY26 | ✅ | ✅ | ↪️ | ↪️ | ✅ | ✅ | ↪️ | ↪️ | ✅ | ✅ | ✅ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ✅ |
| Distribution (binned) (`distribution`) | Age bands | ✅ | ✅ | 🔄 | 🔄 | ✅ | ✅ | ✅ | ↪️ | ✅ | ✅ | ✅ | ✅ | ✅ | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | ✅ | ✅ |
| Records (named people) (`records`) | Delhi roster (419 rows) | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | ↪️ | 🔄 | 🔄 | 🔄 | ✅ | ✅ | ↪️ | ↪️ | ✅ | ✅ | ↪️ | ✅ | ✅ |
| Single value (`single`) | PAT FY26 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | ↪️ | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | ↪️ | ↪️ | ↪️ | ↪️ | ↪️ | 🔄 | ✅ |

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
- **Categorical, positive → line** (alternative): A line implies an order; these categories are shown as bars.
- **Categorical, positive → area** (alternative): A line implies an order; these categories are shown as bars.
- **Categorical, positive → histogram** (alternative): Too few values for a distribution; showing them ranked.
- **Categorical, positive → scatter** (alternative): A scatter plot needs two measures per item; showing the closest view.
- **Categorical, positive → waterfall** (alternative): A waterfall needs gains and losses; showing the values ranked.
- **Categorical, positive → funnel** (alternative): These categories are not stages; showing them ranked.
- **Categorical, positive → stacked_100** (alternative): A 100% stacked bar needs two or more parts per category.
- **Categorical, positive → combo** (alternative): A combo chart needs two measures (e.g. a value and a %); showing the closest view.
- **Categorical, positive → heatmap** (alternative): A heatmap needs two categories and a measure (e.g. work centre × month).
- **Categorical, positive → box** (alternative): A box plot needs individual records per group; showing the summary instead.
- **Categorical, positive → gauge** (alternative): A gauge shows one value against a target.
- **Categorical with losses → donut** (alternative): Shares cannot show losses; showing gains and losses as bars.
- **Categorical with losses → pie** (alternative): Shares cannot show losses; showing gains and losses as bars.
- **Categorical with losses → line** (alternative): A line implies an order; these categories are shown as bars.
- **Categorical with losses → area** (alternative): A line implies an order; these categories are shown as bars.
- **Categorical with losses → histogram** (alternative): Too few values for a distribution; showing them ranked.
- **Categorical with losses → scatter** (alternative): A scatter plot needs two measures per item; showing the closest view.
- **Categorical with losses → treemap** (alternative): Shares cannot show losses; showing gains and losses as bars.
- **Categorical with losses → funnel** (alternative): Shares cannot show losses; showing gains and losses as bars.
- **Categorical with losses → stacked_100** (alternative): A 100% stacked bar cannot show negative values.
- **Categorical with losses → combo** (alternative): A combo chart needs two measures (e.g. a value and a %); showing the closest view.
- **Categorical with losses → heatmap** (alternative): A heatmap needs two categories and a measure (e.g. work centre × month).
- **Categorical with losses → box** (alternative): A box plot needs individual records per group; showing the summary instead.
- **Categorical with losses → gauge** (alternative): A gauge shows one value against a target.
- **Ordinal, multi-measure → heatmap** (alternative): A heatmap needs two categories and a measure (e.g. work centre × month).
- **Ordinal, multi-measure → box** (alternative): A box plot needs individual records per group; showing the summary instead.
- **Ordinal, multi-measure → gauge** (alternative): A gauge shows one value against a target.
- **Time series → donut** (alternative): A pie cannot show change over time; showing columns over time.
- **Time series → pie** (alternative): A pie cannot show change over time; showing columns over time.
- **Time series → histogram** (alternative): A histogram is for distributions; this time series is shown as a line.
- **Time series → scatter** (alternative): A scatter plot needs two measures per item; showing the closest view.
- **Time series → stacked_100** (alternative): A 100% stacked bar needs two or more parts per category.
- **Time series → combo** (alternative): A combo chart needs two measures (e.g. a value and a %); showing the closest view.
- **Time series → heatmap** (alternative): A heatmap needs two categories and a measure (e.g. work centre × month).
- **Time series → box** (alternative): A box plot needs individual records per group; showing the summary instead.
- **Time series → gauge** (alternative): A gauge shows one value against a target.
- **Distribution (binned) → scatter** (alternative): A scatter plot needs two measures per item; showing the closest view.
- **Distribution (binned) → stacked_100** (alternative): A 100% stacked bar needs two or more parts per category.
- **Distribution (binned) → combo** (alternative): A combo chart needs two measures (e.g. a value and a %); showing the closest view.
- **Distribution (binned) → heatmap** (alternative): A heatmap needs two categories and a measure (e.g. work centre × month).
- **Distribution (binned) → box** (alternative): A box plot needs individual records per group; showing the summary instead.
- **Distribution (binned) → gauge** (alternative): A gauge shows one value against a target.
- **Records (named people) → scatter** (alternative): A scatter plot needs two measures per item; showing the closest view.
- **Records (named people) → stacked_100** (alternative): A 100% stacked bar needs two or more parts per category.
- **Records (named people) → combo** (alternative): A combo chart needs two measures (e.g. a value and a %); showing the closest view.
- **Records (named people) → gauge** (alternative): A gauge shows one value against a target.
- **Single value → scatter** (alternative): A scatter plot needs two measures per item; showing the closest view.
- **Single value → stacked_100** (alternative): A 100% stacked bar needs two or more parts per category.
- **Single value → combo** (alternative): A combo chart needs two measures (e.g. a value and a %); showing the closest view.
- **Single value → heatmap** (alternative): A heatmap needs two categories and a measure (e.g. work centre × month).
- **Single value → box** (alternative): A box plot needs individual records per group; showing the summary instead.
- **Single value → gauge** (alternative): A gauge shows one value against a target.
