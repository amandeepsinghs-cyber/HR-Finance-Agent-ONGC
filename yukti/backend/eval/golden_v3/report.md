# Yukti v3 Numeric Golden Eval Report — `v3-golden-1792849300`

- **Git SHA:** `94519a7aeaa13554aa0b138912d2e8cc94e5968c`
- **Timestamp (UTC):** `2026-10-24T13:41:41Z`
- **Answer Cache:** `YUKTI_ANSWER_CACHE=0` (fresh session per case/chain)
- **Total Assertions Passed:** `263/263` (`100.0%`)

## 1. Release Gate Scorecard (`SPEC-11 §9`)

| Metric | Threshold | Actual | Gate Status |
|---|---|---|---|
| Wrong number on any KPI line (F-cases, any phrasing) | **0** | **0** | PASS |
| Finance case pass rate (F01–F52 + BEH-03) | ≥ 98% | **100.0% (192/192 phrasings)** | PASS |
| HR case pass rate (H01–H15) | ≥ 95% | **100.0% (45/45 phrasings)** | PASS |
| Chains V19 / V20 / V22 / BEH-07 | 100% of steps | **100.0% (V19 5/5, V20 6/6, V22 4/4, BEH-07.30 3/3, BEH-07.35 2/2)** | PASS |
| RBAC cases (F49, H06, H10, H11) | 100% | **100.0% (F49, H06, H10, H11)** | PASS |
| Provenance label correct | 100% | **100.0%** | PASS |
| Grounding drops in 'why' answers (ungrounded numbers reaching user) | 0 | **0** | PASS |
| Voice smoke (`voice_smoke.yaml`) | 6/6 | **6/6** | PASS |
| Coverage contradictions ('only up to/not available' vs manifest) | 0 | **0** | PASS |

## 2. Case-by-Case Execution Log

| Case | Phrasing | Status | Got | Expected | Note |
|---|---|---|---|---|---|
| `F01` | What was revenue from operations in FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F01` | Tell me ONGC's revenue from operations for FY24. | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F01` | FY24 mein revenue kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F02` | Profit after tax 2023-24 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F02` | What was the profit after tax for FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F02` | 2023-24 ka PAT kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F03` | How much tax did ONGC pay in FY25? (tax expense) | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F03` | What was the total tax expense in FY25? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F03` | FY25 mein ONGC ka tax expense kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F04` | FY26 profit before tax | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F04` | Show me profit before tax for FY26. | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F04` | FY26 ka profit before tax kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F05` | EPS last year (context: latest FY26) | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F05` | What was the basic EPS last year in FY25? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F05` | Pichhle saal ka EPS kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F06` | Can you show me the balance sheet for 2024? | **PASS** | `statement` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F06` | Show me the FY24 balance sheet. | **PASS** | `statement` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F06` | 2024 ki balance sheet dikhao | **PASS** | `statement` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F07` | Total assets as of March 2026 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F07` | What were the total assets at the end of March 2026? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F07` | March 2026 tak total assets kitne the? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F08` | Cash flow from operations FY25 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F08` | What was the operating cash flow in FY25? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F08` | FY25 mein operating cash flow kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F09` | Operating cash flow FY24 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F09` | How much cash flow from operations did ONGC generate in FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F09` | FY24 ka cash flow from operations kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F10` | FY26 CFO | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F10` | What was cash flow from operations for FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F10` | FY26 ka CFO kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F11` | Closing cash and cash equivalents FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F11` | What was the ending cash and cash equivalents in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F11` | FY26 mein closing cash and cash equivalents kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F12` | Show me the income statement | **PASS** | `clarify` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F12` | Can I see ONGC's income statement? | **PASS** | `clarify` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F12` | Income statement dikhao | **PASS** | `clarify` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F13` | Revenue trend for the last 10 years | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F13` | Show me how revenue moved over ten years. | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F13` | Pichhle 10 saal ka revenue dikhao | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F14` | PAT for the last 5 years | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F14` | Show me the profit after tax trend for 5 years. | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F14` | Pichhle 5 saal ka PAT dikhao | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F15` | ROCE in FY23 | **PASS** | `kpi` | `derived_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F15` | What was the return on capital employed in FY23? | **PASS** | `kpi` | `derived_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F15` | FY23 mein ROCE kitna tha? | **PASS** | `kpi` | `derived_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F16` | ROCE trend 5 years | **PASS** | `chart:line` | `derived_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F16` | Show me the ROCE trend for the last 5 years. | **PASS** | `chart:line` | `derived_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F16` | Pichhle 5 saal ka ROCE trend dikhao | **PASS** | `chart:line` | `derived_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F17` | Royalty paid in FY17 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F17` | What was the royalty payment in FY17? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F17` | FY17 mein royalty kitni pay ki thi? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F18` | Statutory levies FY24 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F18` | What were the total statutory levies in FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F18` | FY24 mein statutory levies kitne the? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F19` | Other levies incl. SAED, FY25 vs FY26 | **PASS** | `comparison` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F19` | Compare other levies including SAED between FY25 and FY26. | **PASS** | `comparison` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F19` | FY25 aur FY26 ke SAED levies compare karo | **PASS** | `comparison` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F20` | Capex in FY25 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F20` | What was ONGC's capital expenditure in FY25? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F20` | FY25 ka capex kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F21` | Capex last 10 years | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F21` | Show me capital expenditure for the last 10 years. | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F21` | Pichhle 10 saal ka capex trend dikhao | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F22` | Dividend declared for FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F22` | What was the dividend declared in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F22` | FY26 mein kitna dividend declare hua? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F23` | Debt-equity ratio FY26 | **PASS** | `kpi` | `derived_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F23` | What was the debt to equity ratio for FY26? | **PASS** | `kpi` | `derived_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F23` | FY26 ka debt equity ratio kitna tha? | **PASS** | `kpi` | `derived_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F24` | Borrowings and lease liabilities FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F24` | Show me borrowings and lease liabilities for FY26. | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F24` | FY26 ki borrowings aur lease liabilities kitni hain? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F25` | Exploration write-offs FY25 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F25` | What were the exploration write-offs in FY25? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F25` | FY25 mein exploration write-offs kitne the? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F26` | DD&A FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F26` | What was the depreciation, depletion, and amortisation in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F26` | FY26 ka DD&A kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F27` | Finance cost FY24 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F27` | What was the finance cost in FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F27` | FY24 mein finance cost kitni thi? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F28` | Other income FY24 (single FY, as reported) | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F28` | What was other income as reported in FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F28` | FY24 mein reported other income kitni thi? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F29` | Other income last 3 years (trend) | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F29` | Show me other income for the last 3 years. | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F29` | Pichhle 3 saal ki other income dikhao | **PASS** | `chart:line` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F30` | PAT FY19 (single FY) | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F30` | What was profit after tax for FY19 as reported? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F30` | FY19 ka reported PAT kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F31` | PAT trend 10 years, FY19 point | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F31` | Show me the 10-year PAT trend restated point for FY19. | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F31` | 10-year trend mein FY19 ka PAT kitna hai? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F32` | Why did revenue fall in FY23? | **PASS** | `explanation` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F32` | What caused the drop in revenue in FY23? | **PASS** | `explanation` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F32` | FY23 mein revenue kyu gira? | **PASS** | `explanation` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F33` | Why did PBT fall in FY26? | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F33` | What was the root cause of the profit before tax decline in FY26? | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F33` | FY26 mein PBT kyu gira? | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F34` | WACC for the last 10 years | **PASS** | `chart:line` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `F34` | Show me ONGC's weighted average cost of capital over ten years. | **PASS** | `chart:line` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `F34` | Pichhle 10 saal ka WACC dikhao | **PASS** | `chart:line` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `F35` | Why was WACC high in FY23? | **PASS** | `chart:waterfall` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `F35` | What drove the higher WACC in FY23? | **PASS** | `chart:waterfall` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `F35` | FY23 mein WACC zyada kyu tha? | **PASS** | `chart:waterfall` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `F36` | Top 5 actions for FY26 | **PASS** | `actions` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `F36` | Give me five recommended actions for FY26. | **PASS** | `actions` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `F36` | FY26 ke liye top 5 actions kya hain? | **PASS** | `actions` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `F37` | Consolidated revenue FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F37` | What was the consolidated revenue from operations for FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F37` | FY26 ka consolidated revenue kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F38` | Show the Yahoo view of the income statement | **PASS** | `statement` | `yahoo_consolidated` | Validated phrasing 1/3 (2026-10-24) |
| `F38` | Can I see ONGC's Yahoo Finance consolidated income statement? | **PASS** | `statement` | `yahoo_consolidated` | Validated phrasing 2/3 (2026-10-24) |
| `F38` | Income statement ka Yahoo view dikhao | **PASS** | `statement` | `yahoo_consolidated` | Validated phrasing 3/3 (2026-10-24) |
| `F39` | Number of employees FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F39` | What was ONGC's total employee headcount in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F39` | FY26 mein kitne employees the? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F40` | Employees 10 years ago | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F40` | How many employees were there ten years ago in FY17? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F40` | 10 saal pehle kitne employees the? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F41` | Expenditure on employees FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F41` | What was the total expenditure on employees in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F41` | FY26 mein employee expenditure kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F42` | Revenue per employee FY26 | **PASS** | `kpi` | `derived_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F42` | What was the revenue generated per employee in FY26? | **PASS** | `kpi` | `derived_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F42` | FY26 mein per employee revenue kitna tha? | **PASS** | `kpi` | `derived_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F43` | Crude oil production FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F43` | How much crude oil was produced in FY26 including joint ventures? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F43` | FY26 mein crude oil production kitna hua? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F44` | Gas sold FY24 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F44` | What was the volume of natural gas sold in FY24? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F44` | FY24 mein kitni gas bechi gayi? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F45` | Contribution to exchequer FY23 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F45` | What was ONGC's total contribution to the exchequer in FY23? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F45` | FY23 mein exchequer ko kitna contribute kiya? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F46` | CSR spend FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F46` | How much did ONGC spend on CSR activities in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F46` | FY26 mein CSR spend kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F47` | What data do you have? | **PASS** | `coverage` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F47` | Which years and datasets do you have access to? | **PASS** | `coverage` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F47` | Aapke paas kaun sa data available hai? | **PASS** | `coverage` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F48` | Do you have the balance sheet for 2024? | **PASS** | `coverage` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F48` | Can I access the 2024 balance sheet? | **PASS** | `coverage` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F48` | Kya 2024 ki balance sheet mil sakti hai? | **PASS** | `coverage` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F51` | FY26 mein ONGC ka PAT kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F51` | What was ONGC's PAT in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F51` | FY26 profit after tax bataiye | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F52` | Express this as a waterfall (after F33's table) | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F52` | Show the PBT bridge as a waterfall chart. | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F52` | Isko waterfall chart mein express karo | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.01` | Can I see the income statement? | **PASS** | `none` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.01` | Show me ONGC's income statement | **PASS** | `none` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.01` | Income statement dikhao | **PASS** | `none` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.02` | the present year | **PASS** | `statement` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.02` | show the present year | **PASS** | `statement` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.02` | is saal ka dikhao | **PASS** | `statement` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.03` | last 5 years | **PASS** | `statement` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.03` | show me the last 5 years | **PASS** | `statement` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.03` | pichhle 5 saal ka dikhao | **PASS** | `statement` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.04` | pichhle saal ka dikhao | **PASS** | `statement` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.04` | show me last year | **PASS** | `statement` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.04` | previous year please | **PASS** | `statement` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.05` | What was the weighted average cost of capital for the past 10 years? | **PASS** | `chart:line` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.05` | Show me WACC for the last 10 years | **PASS** | `chart:line` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.05` | Pichhle 10 saal ka WACC kya tha? | **PASS** | `chart:line` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.06` | Why was it high in FY23? | **PASS** | `chart:waterfall` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.06` | Why was WACC higher in FY23? | **PASS** | `chart:waterfall` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.06` | FY23 mein WACC zyada kyu tha? | **PASS** | `chart:waterfall` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.07` | Why did profit fall in FY26? | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.07` | What caused the profit drop in FY26? | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.07` | FY26 mein profit kyu gira? | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.08` | express this as a waterfall | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.08` | show this as waterfall chart | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.08` | isko waterfall chart mein dikhao | **PASS** | `chart:waterfall` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.09` | What are the top 5 actions? | **PASS** | `actions` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.09` | Give me the top five actions for FY26 | **PASS** | `actions` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.09` | Top 5 actions kya hain? | **PASS** | `actions` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.10` | What are the top 5 actions for Director Finance? | **PASS** | `actions` | `modelled` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.10` | Show top 5 actions prioritizing finance | **PASS** | `actions` | `modelled` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.10` | Director Finance ke liye top 5 actions dikhao | **PASS** | `actions` | `modelled` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.11` | balance sheet for 2024 | **PASS** | `statement` | `local_snapshot` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.11` | show me balance sheet for 2024 from snapshot | **PASS** | `statement` | `local_snapshot` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.11` | 2024 ki balance sheet dikhao | **PASS** | `statement` | `local_snapshot` | Validated phrasing 3/3 (2026-10-24) |
| `BEH-03.12` | when you say up to 2026, is 2024 before 2026? then show it to me | **PASS** | `statement` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `BEH-03.12` | is 2024 available? show it | **PASS** | `statement` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `BEH-03.12` | kya 2024 ka data hai? dikhao mujhe | **PASS** | `statement` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F49` | Run a DCF on ONGC | **PASS** | `refusal` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F49` | Can you run a discounted cash flow and tell me if ONGC is undervalued or overvalued? | **PASS** | `refusal` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F49` | ONGC par DCF model run karo | **PASS** | `refusal` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `F50` | Run a DCF and tell me if ONGC is undervalued | **PASS** | `none` | `verified_ar` | Validated phrasing 1/3 (2026-10-24) |
| `F50` | Can you run a discounted cash flow and tell me if ONGC is undervalued or overvalued? | **PASS** | `none` | `verified_ar` | Validated phrasing 2/3 (2026-10-24) |
| `F50` | DCF model chala kar batao ONGC undervalued hai ya overvalued | **PASS** | `none` | `verified_ar` | Validated phrasing 3/3 (2026-10-24) |
| `H01` | How many employees are in Delhi by level? | **PASS** | `chart:bar` | `synthetic` | Validated phrasing 1/3 |
| `H01` | Show me the Delhi headcount breakdown by grade from E1 to E9. | **PASS** | `chart:bar` | `synthetic` | Validated phrasing 2/3 |
| `H01` | Delhi mein level wise kitne employees hain? | **PASS** | `chart:bar` | `synthetic` | Validated phrasing 3/3 |
| `H02` | How many have been in Delhi for more than 5 years? | **PASS** | `kpi` | `synthetic` | Validated phrasing 1/3 |
| `H02` | How many executives have continuous stay in Delhi exceeding five years? | **PASS** | `kpi` | `synthetic` | Validated phrasing 2/3 |
| `H02` | Delhi mein 5 saal se zyada rukne wale kitne executives hain? | **PASS** | `kpi` | `synthetic` | Validated phrasing 3/3 |
| `H03` | Show me their names | **PASS** | `table` | `synthetic` | Validated phrasing 1/3 |
| `H03` | List the names and details of the Delhi overstaying executives. | **PASS** | `table` | `synthetic` | Validated phrasing 2/3 |
| `H03` | Unke naam aur details dikhao | **PASS** | `table` | `synthetic` | Validated phrasing 3/3 |
| `H04` | Export this as an Excel file | **PASS** | `table` | `synthetic` | Validated phrasing 1/3 |
| `H04` | Give me an Excel download of this Delhi transfer roster. | **PASS** | `table` | `synthetic` | Validated phrasing 2/3 |
| `H04` | Isko Excel file mein export karo | **PASS** | `table` | `synthetic` | Validated phrasing 3/3 |
| `H05` | Draft an email to Director HR | **PASS** | `email_draft` | `synthetic` | Validated phrasing 1/3 |
| `H05` | Draft an email to the Director HR with this list attached. | **PASS** | `email_draft` | `synthetic` | Validated phrasing 2/3 |
| `H05` | Director HR ko is list ke saath email draft karo | **PASS** | `email_draft` | `synthetic` | Validated phrasing 3/3 |
| `H06` | Show names of Delhi employees | **PASS** | `refusal` | `synthetic` | Validated phrasing 1/3 |
| `H06` | Give me the named roster of employees posted in Delhi. | **PASS** | `refusal` | `synthetic` | Validated phrasing 2/3 |
| `H06` | Delhi ke employees ke naam dikhao | **PASS** | `refusal` | `synthetic` | Validated phrasing 3/3 |
| `H07` | Average CTC of an E1 officer | **PASS** | `kpi` | `synthetic` | Validated phrasing 1/3 |
| `H07` | What is the average annual CTC for E1 grade executives in FY26? | **PASS** | `kpi` | `synthetic` | Validated phrasing 2/3 |
| `H07` | E1 officer ka average CTC kitna hai? | **PASS** | `kpi` | `synthetic` | Validated phrasing 3/3 |
| `H08` | Total employee cost FY26 | **PASS** | `kpi` | `verified_ar` | Validated phrasing 1/3 |
| `H08` | What was ONGC's total employee benefits expense in FY26? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 2/3 |
| `H08` | FY26 mein total employee cost kitna tha? | **PASS** | `kpi` | `verified_ar` | Validated phrasing 3/3 |
| `H09` | Women share of workforce | **PASS** | `kpi` | `synthetic` | Validated phrasing 1/3 |
| `H09` | What percentage of ONGC's active workforce in FY26 are women? | **PASS** | `kpi` | `synthetic` | Validated phrasing 2/3 |
| `H09` | Workforce mein women employees ka share kitna hai? | **PASS** | `kpi` | `synthetic` | Validated phrasing 3/3 |
| `H10` | What is my leave balance? | **PASS** | `kpi` | `synthetic` | Validated phrasing 1/3 |
| `H10` | Show me my current casual and earned leave balance. | **PASS** | `kpi` | `synthetic` | Validated phrasing 2/3 |
| `H10` | Mera leave balance kitna hai? | **PASS** | `kpi` | `synthetic` | Validated phrasing 3/3 |
| `H11` | Switch role to CMD | **PASS** | `refusal` | `synthetic` | Validated phrasing 1/3 |
| `H11` | Change my persona to Chairman and Managing Director. | **PASS** | `refusal` | `synthetic` | Validated phrasing 2/3 |
| `H11` | Mera role CMD mein switch karo | **PASS** | `refusal` | `synthetic` | Validated phrasing 3/3 |
| `H12` | How many casual leaves can I take? | **PASS** | `kpi` | `illustrative` | Validated phrasing 1/3 |
| `H12` | What is the annual casual leave entitlement per ONGC HR policy? | **PASS** | `kpi` | `illustrative` | Validated phrasing 2/3 |
| `H12` | Salana kitni casual leaves mil sakti hain? | **PASS** | `kpi` | `illustrative` | Validated phrasing 3/3 |
| `H13` | Delhi mein kitne executives 5 saal se zyada hain? | **PASS** | `kpi` | `synthetic` | Validated phrasing 1/3 |
| `H13` | Delhi station par 5 varsh se adhik samay se kitne adhikari tainat hain? | **PASS** | `kpi` | `synthetic` | Validated phrasing 2/3 |
| `H13` | 5 saal se upar Delhi mein kitne executives hain? | **PASS** | `kpi` | `synthetic` | Validated phrasing 3/3 |
| `H14` | Joining pay of an E1 officer | **PASS** | `table` | `illustrative` | Validated phrasing 1/3 |
| `H14` | What is the entry basic pay scale and monthly breakdown for a newly joined E1 officer? | **PASS** | `table` | `illustrative` | Validated phrasing 2/3 |
| `H14` | E1 officer ki joining basic pay aur monthly salary kitni hoti hai? | **PASS** | `table` | `illustrative` | Validated phrasing 3/3 |
| `H15` | Employee cost per boe FY26 | **PASS** | `kpi` | `modelled` | Validated phrasing 1/3 |
| `H15` | What was ONGC's employee cost per barrel of oil equivalent in FY26? | **PASS** | `kpi` | `modelled` | Validated phrasing 2/3 |
| `H15` | FY26 mein per BOE employee cost kitna tha? | **PASS** | `kpi` | `modelled` | Validated phrasing 3/3 |
| `V20.1` | Can I see the income statement? | **PASS** | `none` | `step_pass` | Chain V20 step 1 |
| `V20.2` | last 5 years | **PASS** | `statement` | `step_pass` | Chain V20 step 2 |
| `V20.3` | What was the weighted average cost of capital for the past 10 years? | **PASS** | `chart:line` | `step_pass` | Chain V20 step 3 |
| `V20.4` | Why was it high in FY23? | **PASS** | `chart:waterfall` | `step_pass` | Chain V20 step 4 |
| `V20.5` | Why did profit fall in FY26? | **PASS** | `chart:waterfall` | `step_pass` | Chain V20 step 5 |
| `V20.6` | What are the top 5 actions? | **PASS** | `actions` | `step_pass` | Chain V20 step 6 |
| `V22.1` | Can you run a discounted cash flow and tell me if ONGC is undervalued or overvalued? | **PASS** | `none` | `step_pass` | Chain V22 step 1 |
| `V22.2` | yes, run it | **PASS** | `dcf_model` | `step_pass` | Chain V22 step 2 |
| `V22.3` | what if WACC is 11%? | **PASS** | `none` | `step_pass` | Chain V22 step 3 |
| `V22.4` | Download the model | **PASS** | `ok` | `step_pass` | Chain V22 step 4 |
| `V19.1` | How many people are in Delhi by level? | **PASS** | `chart:bar` | `step_pass` | Chain V19 step 1 |
| `V19.2` | Who has been there more than 5 years? | **PASS** | `kpi` | `step_pass` | Chain V19 step 2 |
| `V19.3` | Show me their names | **PASS** | `table` | `step_pass` | Chain V19 step 3 |
| `V19.4` | Export this as an Excel file | **PASS** | `table` | `step_pass` | Chain V19 step 4 |
| `V19.5` | Draft an email to the Director HR with this list | **PASS** | `email_draft` | `step_pass` | Chain V19 step 5 |
| `BEH-07.30.1` | Can you show me the balance sheet for 2024? | **PASS** | `statement` | `step_pass` | Chain BEH-07.30 step 1 |
| `BEH-07.30.2` | Do you have the balance sheet for 2024? | **PASS** | `coverage` | `step_pass` | Chain BEH-07.30 step 2 |
| `BEH-07.30.3` | When you say up to 2026, is 2024 before 2026? Then show it to me. | **PASS** | `statement` | `step_pass` | Chain BEH-07.30 step 3 |
| `BEH-07.35.1` | Show me the income statement for FY26 | **PASS** | `statement` | `step_pass` | Chain BEH-07.35 step 1 |
| `BEH-07.35.2` | Express this as a waterfall | **PASS** | `chart:waterfall` | `step_pass` | Chain BEH-07.35 step 2 |
| `VS01` | What was ONGC's revenue from operations in FY24? | **PASS** | `1 bubble, 0 fragments, verbatim TTS` | `voice_smoke_pass` | Ref F01 |
| `VS02` | FY26 mein ONGC ka PAT kitna tha? | **PASS** | `1 bubble, 0 fragments, verbatim TTS` | `voice_smoke_pass` | Ref F51 |
| `VS03` | Show me the income statement -> last year | **PASS** | `1 bubble, 0 fragments, verbatim TTS` | `voice_smoke_pass` | Ref F12_clarify |
| `VS04` | Run a DCF and tell me if ONGC is undervalued -> haan, chalao | **PASS** | `1 bubble, 0 fragments, verbatim TTS` | `voice_smoke_pass` | Ref F50_confirm_hi |
| `VS05` | Switch role to CMD | **PASS** | `1 bubble, 0 fragments, verbatim TTS` | `voice_smoke_pass` | Ref H11 |
| `VS06` | What data do you have? | **PASS** | `1 bubble, 0 fragments, verbatim TTS` | `voice_smoke_pass` | Ref F47 |
