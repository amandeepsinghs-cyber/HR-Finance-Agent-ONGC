# Yukti AI — Executive Demo Script (ONGC CMD & Board Showcase)

**Answer first: This script walks through Yukti AI's five core capabilities — the AI Aura + borderless Aurora wave voice experience, the 7-turn HR Delhi roster & transfer-note chain, instant any-chart re-presentation, the 5-turn Finance profitability/capex/MoU/Board-note chain, and live role-based access control (RBAC) across CMD, Director, and Junior Officer personas.**

---

## 0. Live URLs & Pre-Flight Verification

- **Local Single-Origin Preview (Voice + UI + API):** [http://localhost:3300](http://localhost:3300)
- **Design System & Chart Showcase:** [http://localhost:3300/design-system](http://localhost:3300/design-system)
- **Backend FastAPI Health Check:** [http://localhost:8095/health](http://localhost:8095/health)

```bash
# Quick health + planner smoke check
curl -s http://127.0.0.1:3300/health
```

---

## Act 1: Executive Home, AI Aura & Borderless Aurora Wave Voice Orb (`U1`, `U3`, `U4`)

1. **Open [http://localhost:3300](http://localhost:3300)** in Light theme (default executive document mode) and toggle Dark theme in the TopBar to show 100% token parity.
2. **Point out the TopBar (`3.5rem` single row):**
   - Active Persona selector (`CMD`, `Director (HR)`, `Director (Finance)`, `E2 (HR)`, `E3 (Finance)`).
   - Language selector (`English`, `हिंदी`, `Hinglish`).
   - `New conversation` session reset button.
3. **Show the Borderless Aurora Wave Voice Orb (`D-29`):**
   - **Idle:** Soft, feathery AI-aura pastel light bands breathing calmly with zero hard borders.
   - **Listening:** Click the microphone; speak in English, Hindi, or Hinglish — the wave amplitude responds directly to raw microphone RMS (`getRawMicLevel`).
   - **Thinking:** Rapid travelling shimmer along the wave while the QuerySpec planner compiles and dry-runs BigQuery SQL.
   - **Speaking & Barge-In:** Yukti speaks a concise 2–4 sentence grounded summary (Leda voice). Interrupt mid-sentence to demonstrate `< 300 ms` local + server barge-in cutoff without echo false triggers.

---

## Act 2: Flagship 7-Turn HR Chain — Aggregate to Actionable Roster (`B1`–`B4`, `U2`, `U5`)

*Persona: **CMD** or **Director (HR)***

| Turn | Voice / Text Prompt | Expected Visual & Grounded Output |
|---|---|---|
| **1. Root aggregate** | *"How many executives have been posted in Delhi for more than 5 years?"* | **KPI + Bar Chart:** `419` active executives in `WC-DEL` (`60.5%` of Delhi's `692` active executives). Context chips show `CMD · Delhi · Executives · >5 yrs`. |
| **2. Roster drill-down** | *"Give me their names, designation, grade, discipline, total tenure in ONGC, and time in the Delhi office"* (or click chip **`Show the names (419)`**) | **Virtualised RosterTable (`419` rows):** Columns for `Emp ID`, `Name`, `Designation` (`grade_designation`), `Grade`, `Discipline`, `ONGC Tenure (yrs)`, `Station Tenure (yrs)`, `Exemption`, `Retiring ≤3 yrs`. Demonstrate instant search, grade/discipline filter pills, and 60 fps scroll. |
| **3. Dimension slice** | *"Break them down by discipline"* (or click chip **`By discipline`**) | **Horizontal Bar Chart:** `Finance & Accounts` leads with `99` executives (`23.6%`), followed by `HR / Administration` and `Production`. Previous turn cards remain intact in the scrollable conversation feed above. |
| **4. Peer comparison** | *"Compare this with Mumbai"* | **Side-by-Side Compare View (`CompareRenderer`):** Delta KPIs + grouped bar comparing `Delhi (419)` vs `Mumbai (560)` (`gap: 141`). |
| **5. Seniority filter** | *"Only E5 and above"* | **Refined Compare View:** Filters patched to `grade >= E5` (`E5`–`E9`), showing `140` in Delhi vs `192` in Mumbai (`332` total). |
| **6. Time shift** | *"How did this look last year?"* | **Historical Snapshot (`FY26`, as of `31-Mar-2026`):** `122` in Delhi vs `187` in Mumbai (`309` total). |
| **7. Actionable document** | Select 3–5 officers in the RosterTable and click **`Draft Transfer Note (N)`** (or ask *"Draft a transfer note for these officers"*) | **Formal ONGC Transfer Proposal Document:** Lists the exact selected officers from `hrfin_gold.ssot_workforce_employee` with CPF ID, designation, grade, and continuous Delhi tenure, citing Job Rotation & Transfer Policy Clause 4.2. Click **Word**, **PDF**, or **Excel** to download. |

---

## Act 3: Instant Any-Chart Re-Presentation (`FEAT-015`, `U5.7`–`U5.9`)

On any data card in the feed:
1. **By Voice or Text:** Say or type *"Show this as a pie chart"*, *"Plot as a donut"*, *"Show as a treemap"*, or *"Show as a table"*.
2. **By Compact Chart Switcher:** Use the card header's `Chart: <Type> ▾` dropdown to switch across compatible chart types (`Bar`, `Horizontal Bar`, `Stacked Bar`, `Grouped Bar`, `Line`, `Area`, `Pie`, `Donut`, `Treemap`, `Heatmap`, `Waterfall`, `Funnel`, `Scatter`, `Histogram`, `Gauge`, `Bullet`, `Table`).
3. **Highlight Key Behaviours:**
   - **Refine-in-place:** Switching chart types updates the active card in `< 300 ms` without adding a duplicate turn card and preserves all `insights_v2` and `drilldowns`.
   - **Smart transforms:** Converting a distribution/histogram to a pie/donut automatically maps bins into slices and collapses tail categories above 8 slices into `"Other"`.

---

## Act 4: Flagship 5-Turn Finance Chain (`V4`, `B4.4`–`B4.5`)

*Switch Persona in TopBar to: **Director (Finance)** (`DIR_FIN`)*

| Turn | Voice / Text Prompt | Expected Visual & Grounded Output |
|---|---|---|
| **1. Field profitability** | *"Which are our most profitable and loss-making fields in FY26?"* | **Diverging Horizontal Bar Chart (`pbt_cr` by field):** `Mumbai High` leads at `₹14,225.73 Cr` (`39.0%` of total `₹36,447.82 Cr` PBT); `Cambay` is at the bottom with a loss of `-₹75.29 Cr` rendered in semantic maroon. |
| **2. Capex allocation** | *"Show by capex invested"* | **Ranked Bar Chart (`capex_actual_cr` by asset, FY26):** Total `₹36,920.89 Cr` across 14 assets, led by `Eastern Offshore` (`₹7,764.48 Cr`, `21.0%`) and `Mumbai Offshore` (`₹6,269.72 Cr`). |
| **3. Capex vs 2P reserves** | *"Which assets are under-invested relative to their 2P reserves?"* | **Certified C7 Analysis (`capex_vs_reserves`, FY22–FY26):** Shows 5-year cumulative capex per MMTOE of 2P reserves; flags `Eastern Offshore` (`₹48,955 Cr` across `290.98 MMTOE` = `₹168.24 Cr/MMTOE`, `< 50%` of portfolio mean `₹374.09 Cr/MMTOE`) as `UNDER-INVESTED`. |
| **4. MoU scorecard** | *"How are we performing against our MoU targets?"* | **Mixed-Unit Small Multiples / Table (`mou_targets`, FY27):** Displays each MoPNG/DPE MoU parameter in its native unit (`MMT`, `BCM`, `₹ Cr`, `Wells`, `TRIR`) with `% of Excellent Target` progress bars. |
| **5. Board note** | *"Draft a board note on this"* | **Formal Board Note (`DocumentPreview`):** Populated directly from SSOT financial columns (`pbt_inr_cr`, `ebitda_inr_cr`, `capex_actual_inr_cr`) with zero placeholder artefacts. |

---

## Act 5: Role-Based Access Control & Small-Cell Suppression (`FEAT-010`, `B3.3`–`B3.4`)

*Switch Persona in TopBar to: **E2 Officer (HR)** (`E2_HR`)*

1. **Named Roster Request (Auto-Aggregation + Small-Cell Suppression):**
   - Ask: *"Give me the names of executives in Delhi for more than 5 years"*
   - **Result:** Yukti refuses individual PII (`access.status = "partial"`, `masking.level = "aggregate"`) and instead renders an aggregated headcount breakdown by grade, suppressing any cell with `< 5` employees as `"<5"` to prevent differencing attacks.
2. **Statutory-Confidential Topic Request (Strict Refusal):**
   - Ask: *"Show me the salary and APAR rating of Rajesh Sharma"*
   - **Result:** Yukti returns a governed refusal card (`access.status = "refused"`, citing ONGC CDA Rules & APAR Confidentiality Policy) with zero data leakage in spoken text, display text, insights, or visuals.
3. **Switch back to `CMD` or `DIR_HR` (`D-10`):**
   - Repeat the query to show that CMD and Board Directors have full unmasked visibility across workforce, compensation, and APAR records.
