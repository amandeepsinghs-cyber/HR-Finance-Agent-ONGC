# Yukti AI — Autonomous Overnight Build Plan & Feature Checklist (`BUILD.md`)

**Started:** 2026-10-20 17:35 UTC  
**Target Project:** `ongc-hr-finance-agent` (BigQuery region: `asia-south1`, Cloud Run / Vertex AI)  
**Application Root:** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

---

## 1. Executive Summary & Overnight Objectives

1. **Fix Microphone & Voice Pipeline + Reactive Voice Orb:**
   - Ensure reliable voice capture across both local laptop browsers (Cloud Run HTTPS) and Cloudtop Chrome Remote Desktop (`webkitSpeechRecognition` + `AudioWorklet` without device contention or `peak=0` frame flooding).
   - Make the **AlphaEvolve 3D Particle Voice Orb** visibly react and pulse when the user speaks (driven by real PCM RMS amplitude + speech recognition cadence envelope) and when Yukti (`Leda`) speaks (driven by 24 kHz `AnalyserNode` frequency bins).
2. **BigQuery Single Source of Truth (SSOT) & Full Data Connectivity:**
   - Clean all grain/fan-out traps in `hrfin_gold.mart_*` tables in BigQuery so employee-grain, posting-grain, and monthly-grain tables never duplicate group-level stock columns.
   - Build unified **BigQuery SSOT 360° views/tables** in `hrfin_gold` (`ssot_workforce_employee`, `ssot_work_centre_360`, `ssot_field_economics_360`, `ssot_corporate_annual_360`) reconciling 100% with the 36 Silver tables, 28 Gold objects, and ONGC public calibration targets (`23,117` active employees, `1,199` in Ahmedabad, `₹1,32,508 Cr` FY26 revenue, `1,550` apprentices, etc.).
   - Audit and generate any missing data across all HR, Finance, Operations, HSE/ESG, Procurement, and Governance domains, and connect 100% of tables + `metric_definitions` + `hrfin_docs` policy chunks to the backend agent.
   - Purge any stale cached contracts so all answers and charts come directly from the BigQuery SSOT.
3. **Multi-Turn Conversational Context & Memory:**
   - Pass full multi-turn conversation history, active entity context (`wc_id`, `field_id`, `fiscal_year`, `grade_id`, `discipline_id`), and prior SQL/dataset state across turns in both REST (`/api/turn`) and Live WebSocket (`/ws/live`).
   - Support natural follow-ups (*"what about Mumbai?"*, *"break that down by discipline"*, *"only executives E5 and above"*, *"plot this as a pie chart"*, *"draw a histogram of their age/tenure"*, *"draft a board note on this"*).
4. **Plotly/Dash-Grade Interactive Visualizations & Any-Chart-On-Demand:**
   - Support voice and text requests for **any plot type**: `histogram` (true binned distribution + density curve), `pie`, `donut`, `bar`, `hbar`, `stacked_bar`, `line`, `area`, `combo` (dual-axis), `scatter` / `bubble`, `waterfall`, `treemap`, `heatmap`, `bullet`, `gauge`, `funnel`, `map`, and interactive `table`.
   - Add a **Plotly/Dash-style Interactive Canvas Toolbar** allowing instant 1-click chart type switching (`Bar`, `H-Bar`, `Pie`, `Donut`, `Line`, `Area`, `Histogram`, `Scatter`, `Treemap`, `Waterfall`, `Table`), metric/dimension pivoting, zoom/brush, data-label toggles, and CSV/Excel/PDF/DOCX export.
5. **On-Demand Document Drafting & File Generation:**
   - Generate live data-backed draft documents (Board Notes, Lok Sabha/Rajya Sabha Parliament Replies, Annual General Transfer Proposals, Show-Cause/Vigilance Summaries, Executive Briefings, Custom Analytical Memos) populated from live BigQuery results, with preview on canvas and working `.docx`, `.pdf`, `.xlsx`, and `.md` downloads.
6. **End-to-End Verification & Cloud Run Deployment:**
   - Verify all features via automated tests (BigQuery SSOT reconciliation, multi-turn context, arbitrary chart plotting, document generation, and Playwright UI/voice tests).
   - Deploy Yukti AI to **Google Cloud Run** (`ongc-hr-finance-agent`) so it can be accessed directly via an `https://...run.app` URL (just like Urvi AI / `wellpulse`) in addition to `http://localhost:3200`.

---

## 2. Master Build Checklist

### Phase 1: BigQuery Single Source of Truth (SSOT) & Data Completeness
- [x] **1.1** Audit all 28 `hrfin_gold` tables/views and 63 `hrfin_silver` tables for grain defects, fan-out joins, and missing columns.
- [x] **1.2** Rebuild/clean `hrfin_gold.mart_workforce` in BigQuery so it is strictly 1 row per employee (`22,798` active employees as of Oct-2026 / `23,117` FY26-end, `1,199` in Ahmedabad `WC-AHM`) with zero fan-out from succession/APAR/sanctioned_posts joins.
- [x] **1.3** Create the 4 authoritative **BigQuery SSOT 360° tables** in `hrfin_gold`:
  - `hrfin_gold.ssot_workforce_employee` (employee-grain 360° view with current tenure, continuous stay, cluster tenure, APAR score, FY26 training hours, FY26 overtime, retirement date, succession readiness)
  - `hrfin_gold.ssot_work_centre_360` (work-centre-grain 360° table with regular headcount by cadre/gender/category, sanctioned vs in-position vs vacancies, contract workforce, apprentices, payroll & overtime cost, HSE & environmental incidents, LTIFR, grievances/POSH, production BOE, lifting cost/BOE, capex BE/RE/actual)
  - `hrfin_gold.ssot_field_economics_360` (field × FY 360° table with oil/gas/condensate/BOE production, water cut, downtime, gross/net revenue, levies, opex breakdown, EBITDA, PBT, 2P reserves, RRR, wells drilled, loss-making & divestment flags)
  - `hrfin_gold.ssot_corporate_annual_360` (corporate FY22–FY27 360° table with revenue, EBITDA, PAT, dividend, capex, CSR, headcount, apprentices, LTIFR, renewable MW, MoU score, receivables, actuarial liabilities)
- [x] **1.4** Audit `certified/answer_cache_warmup.json` and `certified/library.yaml`; remove/refresh any stale cached answers and expand certified SQL templates to cover work-centre 360, headcount, payroll, overtime, capex, procurement, training, APAR, succession, grievances, and distributions.
- [x] **1.5** Verify BigQuery SSOT reconciliation with automated Python test suite (`test_ssot_reconciliation.py`).

### Phase 2: Multi-Turn Conversational Context & Follow-Up Engine
- [x] **2.1** Upgrade `session_memory.py` (`SessionContext` & `TurnRecord`) to store structured turn state: `last_query`, `last_sql`, `last_table`, `last_rows` (up to 200 rows), `last_columns`, `active_filters` (`wc_id`, `wc_name`, `field_id`, `fiscal_year`, `cadre`, `grade_id`, `discipline_id`, `state`), and `last_contract`.
- [x] **2.2** Upgrade `/api/turn` (`main.py`) and `websocketClient.ts` / `page.tsx` to transmit `session_id` + recent conversation history (`history: [{role, text}]`) + current `ui_context` on every turn.
- [x] **2.3** Upgrade `turn_runner.py` and `query_data.py` (`live_nl_sql`) to inject multi-turn conversation history, active entity filters, and prior SQL into the router and SQL generator so follow-up questions (*"how many of them are executives?"*, *"break it down by discipline"*, *"what about Mumbai?"*, *"compare with FY25"*) preserve full context.
- [x] **2.4** Add context-aware **Re-Plot / Re-Chart Intent Handler** in `turn_runner.py`: when the user asks *"plot this as a pie chart"*, *"draw a histogram"*, *"show a horizontal bar chart"*, *"make it a donut chart"*, *"show as a scatter plot"*, *"plot a waterfall"*, either re-visualize `session_state.last_rows` immediately or run a distribution/histogram SQL query on the active entity context in BigQuery.

### Phase 3: Plotly/Dash-Grade Charting System & Arbitrary Plot Types
- [x] **3.1** Upgrade backend `chart_rules.py` and contract schema to support all chart kinds: `bar`, `hbar`, `stacked_bar`, `line`, `area`, `combo`, `pie`, `donut`, `histogram`, `scatter`, `waterfall`, `treemap`, `heatmap`, `bullet`, `gauge`, `funnel`, `map`, `table`, `kpi`.
- [x] **3.2** Implement true **Histogram & Distribution Engine** in backend (`chart_rules.py` + `turn_runner.py`) and frontend (`EChartsRenderer.tsx`):
  - Automatically bin raw numeric values or query binned distributions from BigQuery (e.g., employee age histogram, station tenure histogram, salary/overtime distribution, APAR score distribution, field lifting cost distribution, water cut distribution) with mean/median vertical reference lines and smooth density overlay.
- [x] **3.3** Upgrade `EChartsRenderer.tsx` with Plotly/Dash-grade visual best practices:
  - Rich interactive **Chart Type Switcher Bar** (`Bar`, `H-Bar`, `Stacked`, `Pie`, `Donut`, `Line`, `Area`, `Combo`, `Histogram`, `Scatter`, `Treemap`, `Waterfall`, `Heatmap`, `Table`) directly on the canvas header.
  - Dimension & Metric selector pills when the dataset has multiple numeric columns.
  - Rich cross-hair tooltips with Indian currency/number formatting (`₹ Cr`, `Lakh`, `%`, `BOE`), % of total share, and rank.
  - Automatic callout annotations (`markPoint` / `markLine`) for Maximum, Minimum, Average/Target reference line, and automatic maroon highlighting for negative/loss values.
  - Interactive `dataZoom` slider & brush on large category/time series charts and full-featured sortable/searchable DataTable with inline progress bars.

### Phase 4: Voice Input, Reactive Voice Orb, and Live Document Drafting
- [x] **4.1** Upgrade `VoiceOrb.tsx` and `audioAnalyser.ts` so the 3D particle orb visibly moves, ripples, and scales whenever the user speaks:
  - Combine real Web Audio `AnalyserNode` RMS with a speech-cadence harmonic envelope triggered by `webkitSpeechRecognition` (`onaudiostart`, `onsoundstart`, `onspeechstart`, `onresult`) so the orb animates smoothly at 60 FPS even when Chrome Remote Desktop's PCM channel is attenuated.
  - Add a visible live audio waveform / level indicator next to the orb and in the top bar while listening or speaking.
- [x] **4.2** Upgrade `draft_document.py` and `export_tool.py` so the user can ask to generate draft files on **any** topic (not just static templates):
  - Dynamically pull live BigQuery data (or use the current conversation turn's data table) to draft formal ONGC Board Notes, Parliament Replies, Transfer Orders (AGT), Vigilance/HR Memos, and Financial Briefings.
  - Render the formatted document on the Canvas with embedded tables & KPI callouts, and enable 1-click download as **Word (`.docx`)**, **PDF (`.pdf`)**, **Excel (`.xlsx`)**, and **CSV (`.csv`)**.

### Phase 5: End-to-End Testing, Build & Cloud Run Production Deployment
- [x] **5.1** Run end-to-end automated verification suite (`verify_overnight_build.py` + Playwright headless browser check) covering:
  - Single-turn & multi-turn context retention (5+ turn chains)
  - On-demand plotting (`histogram`, `pie`, `donut`, `bar`, `hbar`, `line`, `scatter`, `waterfall`, `treemap`, `table`) from real BigQuery data
  - Live document drafting and `.docx` / `.pdf` / `.xlsx` file generation
  - Voice orb animation reactivity & `/ws/live` Leda voice streaming
- [x] **5.2** Build production frontend & backend and deploy Yukti AI to **Google Cloud Run** (`ongc-hr-finance-agent`) with a live `https://...run.app` URL, while keeping `http://localhost:3200` running locally.
- [x] **5.3** Mark all checklist items `[x]` in `BUILD.md` and write final deployment & verification summary.

---

## 3. Overnight Build Completion & Verification Summary (2026-10-20)

- **Cloud Run Service URL (`asia-south1`):** `https://yukti-ai-89038075859.asia-south1.run.app` (Revision: `yukti-ai-00001-wlt`, 100% traffic)
- **Local Single-Origin UI & Proxy URL:** `http://localhost:3200` (proxies `/api/*` and `/ws/live` to local FastAPI backend on `http://127.0.0.1:8095`)
- **BigQuery Single Source of Truth (`hrfin_gold`):**
  1. `hrfin_gold.ssot_workforce_employee`: **42,171** employee records (**22,798** active as of `2026-10-19`, **74** columns).
  2. `hrfin_gold.ssot_work_centre_360`: **46** work centres (**59** columns; Ahmedabad `WC-AHM` = **1,199** active employees — **698** executives, **501** non-executives, **1,337** sanctioned, **114** vacancies, **1,345** contractors, **₹408.08 Cr** FY26 payroll).
  3. `hrfin_gold.ssot_field_economics_360`: **530** field-year records (**53** producing fields × **10** fiscal years, **52** columns).
  4. `hrfin_gold.ssot_corporate_annual_360`: **10** fiscal years (`FY17`–`FY26`, **34** columns; FY26 revenue **₹1,32,508.00 Cr**).
- **Automated Verification Suites:**
  - `yukti/backend/scripts/test_ssot_reconciliation.py`: **PASSED** (100% cross-table reconciliation across `ssot_workforce_employee`, `ssot_work_centre_360`, and `mart_workforce`).
  - `yukti/backend/scripts/verify_overnight_build.py`: **PASSED** (5-turn multi-turn context chain, live BigQuery histogram engine, pie/donut/scatter/treemap re-plotting, live SSOT document drafting, and `.docx`/`.pdf`/`.xlsx` exports).
  - `yukti/frontend/scripts/verify_ui_overnight.mjs`: **PASSED** (Headless Chrome Playwright E2E test of interactive Plotly/Dash chart switcher toolbar, multi-turn conversation, histogram rendering, and document preview).
