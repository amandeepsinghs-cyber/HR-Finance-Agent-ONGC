# ONGC HR & Finance Data Bank: Generation Checklist

**Project root:** `HR and Finance_ONGC/` · **GCP project:** `ongc-hr-finance-agent` · **Region:** `asia-south1` (Mumbai)
**Specs:** [`docs/data_requirements_spec.md`](../docs/data_requirements_spec.md) · [`docs/question_bank.md`](../docs/question_bank.md) · [`knowledge/public_sources/grounding_data/FACTS.md`](../knowledge/public_sources/grounding_data/FACTS.md) · [`knowledge/public_sources/policies/MANIFEST.md`](../knowledge/public_sources/policies/MANIFEST.md)

> [!IMPORTANT]
> **Execution model:** every step is done by a **Gemini Flash** agent. The agent must run the step's automated test and report the result. The **lead agent** then re-runs the test independently and reviews the output (gate) before the next step starts. A step is only `[x]` when its test passes **and** the gate has signed off.

## Legend
`[ ]` not started · `[/]` in progress · `[x]` done and gated · **Owner:** F = Flash agent, L = lead agent, U = user

---

## ★ North Star: the questions (read this before every step)

> [!IMPORTANT]
> **The data exists only to answer the questions in [`docs/question_bank.md`](../docs/question_bank.md) and their follow-ups.** The question bank is copied into the World Bible as `world_bible/reference/questions.yaml` (step 1.0). It is the **first reference file** every Flash agent reads.
> - Every step lists the question IDs it serves (table below). Its test must prove those questions are answerable from its output.
> - Nothing is generated that no question or follow-up needs. Nothing a question needs may be missing.
> - The question set is **89 questions + 267 follow-ups** (3 per question: drill-down · why · compare/so-what).

| Question group (IDs) | Persona | Served by steps |
|---|---|---|
| C1–C5 CMD people and transfers | CMD | 2.1, 2.2, 3.3 |
| C6–C10 CMD money and assets | CMD | 2.3, 2.4, 2.5, 3.3 |
| C11–C14 CMD cross-silo HR × Finance | CMD | 2.1–2.4, 3.4, 3.7 |
| H1–H10 Director HR | Dir HR | 2.1, 2.2, 3.1, 3.7 |
| F1–F10 Director Finance | Dir Finance | 2.3, 2.4, 2.5, 3.7 |
| E1–E7 officer self-service | E1–E4 | 2.2, 2.5, 3.1 |
| D1–D6 officer refusals | E1–E4 | 2.1, 2.2, 3.3 |
| P1–P20 policies (look-up, policy+data, refusals) | All | 3.1, 1.6 (78 real policies), 2.1, 2.2, 2.4, 2.5, 3.3 |
| T1–T3 follow-up chains | CMD | 2.1–2.4, 3.3, 3.7 |
| W1–W4 what-if | CMD / Directors | 2.1, 2.3, 2.4 |
| M1–M5 HR vs Finance officer split | E1–E4, CMD | 2.1, 2.4, 4.4 (audit log) |
| X1–X10 extra themes | CMD / Directors | 2.2, 2.4, 2.5, 3.6, 3.7 |

---

## ★ Flash hand-off protocol (how the generation is delegated)

1. **One Flash agent per step** (model: Gemini Flash), launched by the lead with this brief: *"Execute step `<id>` of `data_bank/DATA_GENERATION_CHECKLIST.md`. Read, in order: `world_bible/reference/questions.yaml`, `world_bible/question_coverage.yaml` (once it exists), `docs/data_requirements_spec.md`, `knowledge/public_sources/grounding_data/FACTS.md`, then the World Bible. Produce only the outputs listed for the step. Write and run the step's pytest. Write `reports/step_reports/<id>.md`. Report the question IDs your output serves and prove each one with a sample query."*
2. **Steps with no dependencies between them may run in parallel** (e.g. 2.3 alongside 2.1; Phase 3 documents once Phase 2 passes G2).
3. **The lead verifies:** re-runs the pytest, spot-checks 5 questions from the step's question list against the output, then marks the step `[x]`. On failure, the same Flash agent gets the failing test output and fixes it.
4. **You see a one-line status per step** (`PASS/FAIL · questions served · calibration deltas`) and full review at gates G1–G5.

---

## Global rules (every step)

1. **Medallion layers:** Landing (source-format files) → **Bronze** (raw, as-loaded) → **Silver** (conformed, typed, deduplicated, keyed) → **Gold** (business marts, semantic views, glossary, answer key). Nothing skips a layer.
2. **Source-native formats in Landing:** SAP-style CSV extracts (SAP table/field names, e.g. `PERNR`, `BEGDA`, `ENDDA`, `ORGEH`), messy Excel (merged headers, multiple sheets), DB-export CSV, scanned image-PDFs, native PDF/DOCX.
3. **Determinism:** all structured data comes from seeded Python generators (`SEED=20261019`). Re-running gives byte-identical output (checked by hashing). **No numbers typed by the LLM** in structured data.
4. **Single source of truth:** every generator reads `data_bank/world_bible/*.yaml`. Nothing is hard-coded that the Bible defines.
5. **Calibration:** public totals within **±2%** of `calibration_targets.yaml`.
5a. **Answers are derived from the tables, never hard-coded** (user decision, G1):
   - Generators simulate **individual records**: every employee, every posting/transfer, every monthly production and cost line. They do **not** write summary numbers.
   - Story numbers in `story_register.yaml` are **target ranges** used to tune the simulation (e.g. Delhi ≥5-year executives ≈ 380–450). They are not answers.
   - The **answer key (Phase 5)** is computed by SQL on the BigQuery tables **after** generation. Whatever the data says is the answer, and the agent computes it live the same way.
   - Tests check that each story *emerges* from the record-level data within its range. No summary table may contain a story number that cannot be recomputed from the underlying records.
   - Core HR truth lives in BigQuery `hrfin_silver.employee_master` (current posting) and `hrfin_silver.posting_history` (full transfer history, SCD2). Every HR answer (Delhi tenure, transfers due, North East gap, retirements) is a query over these.
6. **Follow-up readiness:** every fact table carries the standard **drill dimensions** (below). Every story has **driver columns** that answer "why".
7. **Consistency:** every employee, date, amount or field named in a document must exist in the structured data.
8. **No secrets or real personal data.** Employee, vendor and person names are fictional. Real names are allowed only for organisation, Board roles, work centres, fields, subsidiaries and public figures.
9. **Python env:** `uv` venv at `data_bank/.venv`; dependencies pinned in `data_bank/pyproject.toml`. No global pip.
10. **No git commits** by any agent.

### Standard drill dimensions (follow-up contract)
| Domain | Must be sliceable by |
|---|---|
| HR facts | FY / month · work centre → asset → sector/cluster · grade (E0–E9, non-exec groups) · discipline · gender · category (Gen/SC/ST/OBC/EWS) · PwD · age band · tenure band · hard-station flag |
| Finance facts | FY / month · field → asset → basin → onshore/offshore · cost head / cost element · project · vendor / customer · BE / RE / Actual |
| Every story | **who** (named list) · **why** (driver columns) · **compared to what** (YoY, vs. company average, vs. target, vs. peer asset) · **so what** (policy link or document output) |

---

## Folder layout (created in step 0.1)
```
data_bank/
  world_bible/        reference + calibration + stories + coverage (YAML)
  generators/         hr/, ops/, finance/, governance/, documents/  (Python)
  landing/            sap/, db_exports/, excel/, documents/{native,scanned}/   <- source-format output
  medallion/          bronze/, silver/, gold/  (BigQuery SQL / Dataform SQLX)
  answer_key/         questions.yaml, followups.yaml, sql/, expected/
  tests/              pytest suites per step
  reports/            step_reports/*.md, validation_report.md
```

---

## Phase 0: Setup
| # | Step | Owner | Output | Automated test |
|---|---|---|---|---|
| [x] 0.1 | Scaffold folders, `pyproject.toml` (pandas, numpy, faker[en_IN], pyyaml, openpyxl, python-docx, reportlab, pillow, pdf2image, pytest, google-cloud-bigquery, google-cloud-storage), `uv sync` | F | Folder tree, `.venv` | `uv run pytest tests/test_00_env.py` (imports, folders exist) |
| [x] 0.2 | `gcloud auth login` + `gcloud auth application-default login`; set project | **U** | Authenticated CLI | `gcloud config get-value project` = `ongc-hr-finance-agent` |
| [x] 0.3 | Enable APIs: bigquery, storage, documentai, discoveryengine, aiplatform, dataform, run, cloudbuild | L (needs your OK) | APIs enabled | `gcloud services list --enabled` contains all |
| [x] 0.4 | Create buckets `gs://ongc-hr-finance-agent-landing` (versioned), `gs://ongc-hr-finance-agent-docs`; datasets `hrfin_bronze`, `hrfin_silver`, `hrfin_gold`, `hrfin_docs` (asia-south1) | L | Buckets + datasets | `bq ls`, `gcloud storage ls` |

## Phase 1: World Bible (the contract for everything else)
| # | Step | Owner | Output | Automated test |
|---|---|---|---|---|
| [x] 1.0 | **Questions as reference:** convert `docs/question_bank.md` into `world_bible/reference/questions.yaml`. Each entry has id, persona(s), question text, decision it drives, type (data / policy / policy+data / refusal / chain / what-if / document), expected output (number/table/list/chart/doc), and 3 follow-ups (drill-down, why, compare/so-what) | F | `world_bible/reference/questions.yaml` | `test_10a_questions.py`: all 89 IDs present (C1–C14, H1–H10, F1–F10, E1–E7, D1–D6, P1–P20, T1–T3, W1–W4, M1–M5, X1–X10 + chains); 3 follow-ups each; text matches question_bank.md |
| [x] 1.1 | Reference data R1–R10: ~45 work centres (from organogram, with cluster, sector, hard-station category, director owner); grades E0–E9 + non-exec groups with pay scales; ~30 disciplines; ~45 real fields mapped to asset/basin; ~60 projects; ~400 SAP cost and profit centres; customers; ~2,000 vendors; states/districts; monthly price/FX FY17–FY27 | F | `world_bible/reference/*.yaml` | `test_10_reference.py`: unique IDs, valid FKs, every asset in organogram present, 41 locations in 12 states |
| [x] 1.2 | Calibration targets from FACTS.md, each with value, tolerance and citation | F | `world_bible/calibration_targets.yaml` | `test_11_calibration_spec.py`: ≥40 targets, each cited |
| [x] 1.3 | Story Register S1–S15: exact numbers, tables involved, driver columns, expected answer text | F | `world_bible/story_register.yaml` | `test_12_stories_spec.py`: every story → ≥1 question, has who/why/compare/so-what |
| [x] 1.4 | **Question coverage map:** all 89 questions + **3 follow-ups each (267)** → required tables, columns, documents, filters, expected output type (number/table/list/chart/doc) | F | `world_bible/question_coverage.yaml` | `test_13_coverage.py`: 89/89 questions, 267 follow-ups, every referenced table/column exists in the spec |
| [x] 1.5 | Silver schema contract: column name, type, nullability, PK/FK, drill dimensions per table (H1–H20, F1–F17, G1–G5) | F | `world_bible/schema_silver.yaml` | `test_14_schema.py`: drill-dimension contract satisfied for every fact table |
| [x] 1.6 | **Real policy registry:** index the 78 collected public documents (`knowledge/public_sources/policies/`). For each policy question (P1–P20, E2, E4, E5, H10…), record which real document and clause answers it, or flag "needs reconstruction" for step 3.1 | F | `world_bible/policy_question_map.yaml` | `test_16_policy_map.py`: every policy-type question → real clause or reconstruction flag |
| [x] **G1** | **Gate: lead reviews the Bible; user approves the story numbers** | L+U | Sign-off in `reports/step_reports/G1.md` | n/a |

## Phase 2: Structured generation (writes to `landing/`, source formats)
| # | Step | Owner | Output (Landing) | Automated test |
|---|---|---|---|---|
| [x] 2.1 | **HR lifecycle simulator** FY2001→Oct-2026: hiring, postings (following JRTP-style rotation and clusters), promotions (time-bound E1–E4, merit E5+), separations (superannuation at 60, VRS, resignation). Outputs H1–H5. | F | `sap/PA0002.csv`, `PA0001.csv`, `PA0000.csv`, `excel/DPC_tracker.xlsx` | `test_21_hr_core.py`: headcount FY13–FY26 ±2%; 13,781 exec / 9,336 non-exec; women 8.2%; SC/ST %; PwD 523; age bands; Assam 3,561; FY26 hires 167, separations ~1,400; S1–S5 exact; no overlapping postings; determinism hash |
| [x] 2.2 | HR satellites H6–H20 (sanctioned posts, payroll, APAR, succession, training, leave, medical, grievances, contract workforce, HSE, travel, POSH committees, vigilance) | F | `sap/` payroll, PA2001/PA2006, `excel/` manpower plan, succession, legal register; `db_exports/` HSE, LMS, medical | `test_22_hr_sat.py`: payroll total ₹10,211 cr FY26 ±2%; median pay (exec M ₹43.3L / F ₹37.5L); FKs to H1; S11–S14 exact |
| [x] 2.3 | Production and subsurface F1–F4 (fields monthly, reserves, wells, prices/FX) | F | `db_exports/production_monthly.csv`, `excel/reserves.xlsx`, `db_exports/wells.csv`, `excel/price_fx.xlsx` | `test_23_ops.py`: 20.501 MMT, 19.966 BCM FY26; 501 wells (100 exploratory); 2P 709.32 MMTOE; RRR 1.17; S7 production leg |
| [x] 2.4 | Field economics and spend F5–F11 (CO-PA P&L, FI-CO cost ledger, BE/RE capex, project progress, POs, receivables, hedges). Manpower cost **pulled from 2.2 payroll** by work centre. | F | `sap/CO_PA.csv`, `COSP.csv`, `EKKO.csv`/`EKPO.csv`, `BSID.csv`, `PS_PRPS.csv`; `excel/BE_RE_<asset>.xlsx` | `test_24_fin.py`: revenue ₹1,32,508 cr; Offshore/Onshore split; royalty ₹12,965 cr; cess ₹13,034 cr; capex ₹35,878 cr; receivables ₹13,168 cr; S6, S8, S9, S15 exact; payroll↔P&L manpower reconcile |
| [x] 2.5 | Corporate and governance F12–F17, G1–G4 (CSR, MoU, liabilities, subsidiaries, energy transition, corporate financials, Parliament Qs, CAG paras, RTI, board agenda index) | F | `excel/` CSR, MoU, actuarial; `db_exports/` RTI; `landing/governance/` | `test_25_corp.py`: CSR ₹949 cr + state totals; liabilities; PAT ₹32,894 cr; dividend ₹13.25/share; S10 exact |
| [x] **G2** | **Gate: full cross-table validation** (FKs across domains, calibration, all 15 stories, determinism) | L | `reports/validation_report.md` | `uv run pytest tests/ -k "2"` all green |

## Phase 3: Unstructured generation (writes to `landing/documents/`)
| # | Step | Owner | Output | Automated test |
|---|---|---|---|---|
| [x] 3.1 | **Demo reconstructions** of rulebooks not available publicly: JRTP, Book of Delegated Powers (summary), Leave Rules, R&P/Promotion, HR Manual, PRBS. ONGC-style, clause-numbered, consistent with the real excerpts in `policies/text/`. Watermark: "Demo reconstruction". 3 of them rendered as **scanned image-PDFs**. | F | `documents/native/`, `documents/scanned/` | `test_31_rulebooks.py`: clause numbering; rules used by generators (tenure 3y min, 10y cap, clusters, NE, retirement exemption) match world_bible; scanned PDFs have no text layer |
| [x] 3.2 | Office orders and circulars (~150) **rendered from H2/H3**: transfer orders, promotion notifications, DA circulars | F | Scanned PDF + DOCX | `test_32_orders.py`: 100% of named employees, dates and work centres match postings/promotions |
| [x] 3.3 | Confidential documents (~12): Draft FY27 Transfer Order (from S1/S2), Board notes (field divestment from S6, FY27 capex), DPC results, vigilance summary | F | DOCX/PDF + `confidentiality` metadata | `test_33_conf.py`: every number traces to gold queries |
| [x] 3.4 | Monthly asset MIS reports (~400 = 17 assets × 24 months) with tables and charts, rendered as scanned PDFs | F | `documents/scanned/mis/` | `test_34_mis.py`: sampled values = production/P&L/headcount tables |
| [x] 3.5 | Messy Excel source workbooks (BE/RE, MoU, CSR, manpower plan, succession), if not already produced in Phase 2 | F | `excel/` | `test_35_excel.py`: parser recovers values = silver |
| [x] 3.6 | Synthetic Parliament replies (~30) + CAG para texts (~30) consistent with G1/G2 | F | PDF | `test_36_gov_docs.py` |
| [x] 3.7 | Output templates: board note, transfer proposal sheet, Parliament reply format, P&L sheet | F | `documents/templates/` | Files open; placeholders present |
| [x] 3.8 | Document metadata manifest: doc_id, title, type, issuer, effective date, confidentiality, source (real/reconstruction/synthetic), linked entities | F | `landing/documents/DOC_MANIFEST.csv` | `test_38_doc_manifest.py`: every file listed; includes the 78 real policies |
| [x] **G3** | **Gate: document↔data consistency audit** | L | `reports/step_reports/G3.md` | All Phase 3 tests green |

## Phase 4: Medallion load on GCP
| # | Step | Owner | Output | Automated test |
|---|---|---|---|---|
| [x] 4.1 | Upload `landing/` to `gs://…-landing/{source}/{yyyymmdd}/` (immutable) | F | GCS objects | Object count and MD5 = local |
| [x] 4.2 | **Bronze:** load every landing file into `hrfin_bronze.<source>_<table>`, all columns STRING, plus `_source_file`, `_ingest_ts`, `_batch_id` | F | Bronze tables | Row counts = landing files |
| [x] 4.3 | **Silver (Dataform):** SAP field rename map, typing, dedupe, SCD2 for employee/posting, Excel unpivot, conformed dims; **assertions** (not null, unique, FK, accepted values) | F | `hrfin_silver.*` + Dataform repo in `medallion/` | All Dataform assertions pass; schema = `schema_silver.yaml` |
| [x] 4.4 | **Gold:** star-schema marts (`mart_workforce`, `mart_postings`, `mart_field_economics`, `mart_capex`, `mart_corporate`, `mart_governance`), semantic views, `glossary` and `metric_definitions` tables | F | `hrfin_gold.*` | Gold reconciles to calibration targets; stories queryable |
| [x] 4.5 | **Unstructured medallion:** Bronze = Document AI OCR/Layout output (`hrfin_docs.bronze_doc_text`); Silver = clause/section chunks with metadata and linked entity IDs (`silver_chunks`); Gold = Vertex AI Search data store (+ `gold_doc_index`) | F | Docs tables + search data store | 40 probe queries return the correct clause or document in the top 3 |
| [x] **G4** | **Gate: medallion integrity** (landing = bronze counts; silver assertions; gold = calibration; search probes) | L | `reports/step_reports/G4.md` | All green |

## Phase 5: Answer key and follow-up readiness
| # | Step | Owner | Output | Automated test |
|---|---|---|---|---|
| [x] 5.1 | Gold SQL + expected result for all 89 questions | F | `answer_key/sql/Qxx.sql`, `expected/Qxx.json` | Every query runs on gold and returns non-empty results; story answers = register |
| [x] 5.2 | 267 follow-ups (3 per question: drill-down, why, compare / so-what) with SQL or document reference | F | `answer_key/followups.yaml` | 100% executable; 0 "data not available" |
| [x] 5.3 | 3 phrasings per question (formal, casual, Hindi-English mix) for the later agent eval | F | `answer_key/paraphrases.yaml` | 267 paraphrases |
| [x] 5.4 | **Free-question stress test:** a Flash agent role-plays the CMD and invents 50 new questions plus follow-ups; each is checked for whether the gold data *could* answer it | F + L | `reports/stress_test.md` | ≥90% answerable; gaps fed back to Phase 2 |
| [ ] **G5** | **Gate: data bank ready for agent build** | L+U | `reports/step_reports/G5.md` | All tests green |

---

## Step report template (each Flash agent writes `reports/step_reports/<step>.md`)
```
Step: <id>   Status: PASS/FAIL   Runtime: <m>
Outputs: <paths + row counts / file counts>
Test command + result: <pytest summary>
Calibration deltas: <metric: target vs actual>
Stories verified: <ids>
Known issues / assumptions:
```
