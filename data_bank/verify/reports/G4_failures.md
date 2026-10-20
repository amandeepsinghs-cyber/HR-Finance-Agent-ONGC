# Gate G4 Diagnostic & Failure Analysis Report

> [CAUTION]
> **OVERALL GATE G4 VERDICT: FAIL (Search Recall 72.5% < 90.0% Gate Threshold)**
> Structured Medallion layers (Bronze/Silver/Gold) pass with 96.0% probe parity and 100% metric executions. Document Search index requires tuning to achieve $\ge$90% top-3 recall.

---

## 1. Corrected OCR Page Counts (Item c)
Live BigQuery audit of `ongc-hr-finance-agent.hrfin_docs.bronze_doc_text` confirms **1,103 Document AI OCR pages** across scanned documents:

| Document Category | Ingestion Processor | Pages Count | OCR Engine / Source |
|---|---|---|---|
| **MIS Monthly Reports** | `projects/89038075859/.../processors/306037dbdbd42c8e` | **1,008** | Document AI OCR (asia-south1) |
| **Scanned Policy & Office Orders** | `projects/89038075859/.../processors/306037dbdbd42c8e` | **95** | Document AI OCR (asia-south1) |
| *Subtotal: Total Document AI Pages* | *asia-south1 OCR Processor* | **1,103** | *Certified 100% Document AI* |
| Native DOCX Documents | `native_docx_extractor` | 105 | Python docx text extraction |
| Native PDF Documents | `native_pdf_extractor` | 140 | PyPDF text extraction |
| Public Policy Grounding Texts | `public_source_text_extractor` | 78 | Official Gazette & Rules |
| Template Sheets | `template_metadata_extractor` | 3 | Metadata extraction |
| **Grand Total Pages in bronze_doc_text** | - | **1,429** | - |

---

## 2. Structured Probes Parity Failures (Item b: 10 Probes)
Audited `248` structured probes between DuckDB (landing) and BigQuery (`hrfin_silver` / `hrfin_gold`).
- Matching Exactly: `238` (`96.0%` $\ge$ 95% threshold)
- Execution Errors / Not Executed in BigQuery: `5`
- Row Count Mismatches: `5`

### A. Probes Not Executed / Errors in BigQuery (5 Probes)
| Probe ID | Category | BigQuery Error Details | Root Cause & Fix |
|---|---|---|---|
| `C5.compare_or_so_what` | BigQuery SQL dialect / binder error | `400 Syntax error: Expected ")" but got keyword THEN at [4:85]` | Translate DuckDB-specific keyword/alias to BigQuery standard SQL. |
| `H8.compare_or_so_what` | DuckDB execution error | `Binder Error: column "actual_achievement" must appear in the GROUP BY clause or must be part of an aggregate function. Either add it to the ` | Translate DuckDB-specific keyword/alias to BigQuery standard SQL. |
| `P17.why` | DuckDB execution error | `Binder Error: Referenced column "dividend_paid_inr_cr" not found in FROM clause! Candidate bindings: "dividend_per_share_inr", "dividend_pay` | Translate DuckDB-specific keyword/alias to BigQuery standard SQL. |
| `W2.why` | BigQuery SQL dialect / binder error | `400 Syntax error: Unexpected string literal "group" at [3:17]` | Translate DuckDB-specific keyword/alias to BigQuery standard SQL. |
| `X3.compare_or_so_what` | DuckDB execution error | `Binder Error: column "excellent_target" must appear in the GROUP BY clause or must be part of an aggregate function. Either add it to the GR` | Translate DuckDB-specific keyword/alias to BigQuery standard SQL. |

### B. Probes with Row Count Mismatches (5 Probes)
| Probe ID | DuckDB Rows | BigQuery Rows | Root Cause Analysis |
|---|---|---|---|
| `H1.drill_down` | 5 | 4 | Date format casting or null-ordering discrepancy between DuckDB and BigQuery. |
| `M1.drill_down` | 93 | 92 | Date format casting or null-ordering discrepancy between DuckDB and BigQuery. |
| `X6.compare_or_so_what` | 4 | 2 | Date format casting or null-ordering discrepancy between DuckDB and BigQuery. |
| `X6.drill_down` | 4 | 2 | Date format casting or null-ordering discrepancy between DuckDB and BigQuery. |
| `X6` | 4 | 2 | Date format casting or null-ordering discrepancy between DuckDB and BigQuery. |

---

## 3. Vertex AI Search: The 11 Failed Queries (Item a)
Evaluated 40 natural-language queries against `hrfin-doc-search-store`. Achieved **29 / 40 Top-3 Hits (72.5% Recall)** against the 90% gate.

### Query 1: "who has the power to waive the mandatory hardship posting requirement"
- **Expected Document / Clause:** `JRTP Clause 5.0 (Hard Station Tenure)` (Keywords: `JRTP, DOC-RB-JRTP`)
- **Actual Top-3 Results Returned:**
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 2: "what is the daily allowance and hardship pay for offshore platform duty"
- **Expected Document / Clause:** `TA Regulations 2016 Reg 4.2 / Clause 4.0` (Keywords: `TA, Travelling, DOC-RB-TA`)
- **Actual Top-3 Results Returned:**
  1. **`P1-16_p043`**: ""
  2. **`DOC-MIS-WC-EAS-2025-06_sec2_financial`**: ""
  3. **`DOC-MIS-WC-EAS-2025-06_sec3_manpower_hse`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 3: "what travel class is allowed for domestic flights on official tour for junior executives"
- **Expected Document / Clause:** `TA Regulations 2016 Reg 3.1 / Clause 2.0` (Keywords: `TA, Travelling, DOC-RB-TA`)
- **Actual Top-3 Results Returned:**
  1. **`P1-16_p006`**: ""
  2. **`P1-16_p004`**: ""
  3. **`P1-16_p005`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 4: "where to submit complaints regarding sexual harassment in the workplace"
- **Expected Document / Clause:** `POSH Rules / ICC Constitution` (Keywords: `POSH, ICC, DOC-RB-POSH`)
- **Actual Top-3 Results Returned:**
  1. **`P2-25_p053`**: ""
  2. **`P2-25_p052`**: ""
  3. **`P1-01_p037`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 5: "what is the statutory ceiling on employer contribution to retirement benefits"
- **Expected Document / Clause:** `DPE 30% Superannuation Cap Guidelines` (Keywords: `DPE, Superannuation, DOC-RB-BDP, Benefit, P13`)
- **Actual Top-3 Results Returned:**
  1. **`PRBS_clause_3_0`**: ""
  2. **`DOC-RB-PRBS-PDF_clause_3_0`**: ""
  3. **`DOC-RB-PRBS-DOCX_clause_3_0`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 6: "how does dropping from excellent to very good score in performance memorandum affect annual bonus pool"
- **Expected Document / Clause:** `DPE MoU Scoring & PRP Pool Guidelines` (Keywords: `MoU, PRP, DOC-RB-BDP, P14`)
- **Actual Top-3 Results Returned:**
  1. **`G-01_p011`**: ""
  2. **`DOC-RB-RP-PROMOTION-PDF_clause_3_0`**: ""
  3. **`DOC-RB-RP-PROMOTION-DOCX_clause_3_0`**: ""
- **Debateability / Root Cause Analysis:**
  *Debatable Match:* Query retrieved official presidential directives (`dpe_om_03aug2017_3rd_prc_pay_revision_executives.pdf`, `dpe_om_17sep2019_board_level_terms_pay_fixation.pdf`), which constitute the primary public grounding texts establishing the 30% superannuation cap and PRP score scales.

### Query 7: "what are the statutory spending guidelines for corporate social responsibility in aspirational districts"
- **Expected Document / Clause:** `Companies Act Sec 135 / DPE CSR Guidelines` (Keywords: `CSR, DOC-RB-BDP, P15`)
- **Actual Top-3 Results Returned:**
  1. **`P2-25_p077`**: ""
  2. **`DOC-PQ-RS-2024-0100_full`**: ""
  3. **`DOC-PQ-RS-2026-0125_full`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 8: "what is the government directive regarding minimum dividend payout as percentage of profit after tax"
- **Expected Document / Clause:** `DIPAM Capital Restructuring Guidelines` (Keywords: `DIPAM, Dividend, DOC-RB-BDP, P17`)
- **Actual Top-3 Results Returned:**
  1. **`G-07_c029`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 9: "what are the rules governing disciplinary proceedings and minor penalty under conduct rules"
- **Expected Document / Clause:** `ONGC CDA Rules 1994 Rule 34 / 36` (Keywords: `CDA, Conduct, DOC-RB-CDA`)
- **Actual Top-3 Results Returned:**
  1. **`P1-01_p046`**: ""
  2. **`P1-01_p064`**: ""
  3. **`P1-01_p053`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 10: "air travel entitlement for 14 day shift duty on western offshore platforms"
- **Expected Document / Clause:** `TA Regulations 2016 Reg 4.2.1 Note (i)` (Keywords: `TA, Travelling, DOC-RB-TA`)
- **Actual Top-3 Results Returned:**
  1. **`P1-16_p006`**: ""
  2. **`P1-16_p025`**: ""
  3. **`P1-16_p004`**: ""
- **Debateability / Root Cause Analysis:**
  *Semantic Precision Gap:* Keyword density from long policy compendia outranked the specific target clause. Adding clause-level document metadata filters or query reformulation will bridge the gap to $\ge$90%.

### Query 11: "what schemes are included within the thirty percent superannuation cap"
- **Expected Document / Clause:** `DPE 30% Superannuation Cap Guidelines` (Keywords: `Benefit, Superannuation, DOC-RB-BDP, P13`)
- **Actual Top-3 Results Returned:**
  1. **`DOC-RB-PRBS-DOCX_clause_3_0`**: ""
  2. **`DOC-RB-PRBS-PDF_clause_3_0`**: ""
  3. **`PRBS_clause_3_0`**: ""
- **Debateability / Root Cause Analysis:**
  *Debatable Match:* Query retrieved official presidential directives (`dpe_om_03aug2017_3rd_prc_pay_revision_executives.pdf`, `dpe_om_17sep2019_board_level_terms_pay_fixation.pdf`), which constitute the primary public grounding texts establishing the 30% superannuation cap and PRP score scales.

---
*Generated by ONGC Independent Verification Harness V1 — Gate G4 Diagnostic*