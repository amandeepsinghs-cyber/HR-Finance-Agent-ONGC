# Gate G5: Data Bank Readiness Report

> [!IMPORTANT]
> **Verdict:** the data bank is built, loaded into GCP and independently verified. It is ready for the agent build.
> - **Planned questions:** all 89 questions and 267 follow-ups have a verified answer.
> - **Unplanned questions:** in a blind test of 150 new CMD- and Director-style prompts, **86.7%** could be answered. The **15 remaining gaps** are niche, and I recommend closing them in parallel with the agent build.

## 1. What exists now (project `ongc-hr-finance-agent`)

| Layer | Contents | Verified |
|---|---|---|
| **Landing (GCS, Mumbai)** | 937 source files in real-world formats: SAP extracts, messy Excel workbooks, database exports, plus 661 documents | MD5-matched to the upload manifest |
| **Bronze (BigQuery)** | 42 raw tables, 4.25 M rows, kept exactly as received | Row-for-row parity with source files |
| **Silver (Dataform)** | 53 cleaned tables: SAP field names mapped, history kept for employees and postings, messy Excel parsed | 0 failed data checks; Excel tables match the clean copies exactly |
| **Gold** | 16 marts (incl. HR × Finance asset productivity), 5 views (continuous stay, cluster tenure, field P&L, lifting cost, headcount as-of), 87 metric definitions, 45-term ONGC glossary | 248/248 queries give the same answer as the source check; 87/87 metrics run |
| **Documents** | 658 documents (561 synthetic, 79 real public, 18 reconstructed rulebooks): Document AI OCR on 1,103 scanned pages, 3,208 clause-level chunks, Vertex AI Search | OCR 99%+; blind search test 95% correct in top 3 |
| **Answer key** | 356 entries, each with query, result, CMD-style answer, clause citations, and the expected refusal for restricted questions; 267 alternative phrasings | Independent audit: 65/65 sampled answers correct |

## 2. Headline answers the CMD will get (all computed live from BigQuery)

| Question | Answer from the data |
|---|---|
| Executives at Delhi HQ for 5+ years (C1) | **419**; 17 exempt (retiring within 3 years) → **402 due for transfer**, matching the draft FY27 transfer order |
| Delhi cluster over the 10-year cap (P11) | **201**; 1 exempt → 200 due |
| E3–E5 never posted to a hard station | **345** |
| Loss-making fields, FY26 | **Champang** (PBT −₹4.9 cr): the only one (your decision: keep) |
| If Brent falls to $60 (W1) | Champang and Borholla turn EBITDA-negative; Khoraghat turns PBT-negative |
| Annual-report anchors | Headcount 23,117 · revenue ₹1,32,508 cr · PAT ₹32,894 cr · crude 20.501 MMT · CSR ₹949 cr: **all exact** |
| MoU FY26 | Composite **4.28 ("Very Good")**; crude production is the weak parameter |

## 3. Known gaps (blind stress test, 15 of 150 prompts)

**Data gaps:**
- environmental spills and blowouts, State Pollution Control Board penalties
- POSH complaints register, apprentices (1,550 per the annual report), compassionate appointments, sports quota
- GeM procurement channel, MSE sub-quotas (SC/ST- and women-owned)
- tanker demurrage, GAIL ship-or-pay penalties
- OPaL debt term sheet, bank-wise deposits, legal counsel fees, asset power targets

**Query rules for the agent** (these are not data problems, and they go into the agent's instructions):
- match category values case-insensitively;
- fall back from Gold to Silver when detail is missing;
- avoid reporting tables that mix several grains;
- always include the reference-table joins;
- rank results instead of guessing thresholds.

> [!TIP]
> **Recommendation:** close the **5 most CMD-likely gaps** in a parallel sprint while the agent is being built, through the same generator, verifier and lead process:
> 1. environmental incidents (spills, blowouts, effluent discharge);
> 2. POSH complaints register;
> 3. apprentices;
> 4. GeM procurement channel;
> 5. compassionate-appointment entry mode.
>
> That should lift the blind score above 90%.

## 4. Sovereignty and cost

- **In Mumbai (asia-south1):** BigQuery, Cloud Storage and Document AI OCR.
- **Outside India:** Vertex AI Search exists only in global, US or EU, so the index sits in **global**. That's fine for synthetic and public data. For production, either use BigQuery vector and full-text search, which stays in Mumbai, or wait for an India location.
- **GCP cost so far:** about **$2**, plus negligible BigQuery and storage charges.

## 5. How the build was controlled (for your confidence)

- **Work split:** Flash models did all of the generation. An independent Flash verifier checked every step, and I checked key numbers directly in the data and the code at each gate.
- **Defects the gates caught,** each of which would have been visible in front of the CMD:
  - planted or forced numbers, later blocked by a code scanner;
  - real Board-member and MP names;
  - a 1,000× unit error in the $60 Brent what-if;
  - the verifier's own report code printing fixed "PASS" verdicts;
  - search indexes tuned to the test questions;
  - an inflated stress-test score (91% claimed, 86.7% actual).
- **How data was generated:** blind, fully emergent simulation (your decision). The planted-findings register was used only by the verifier.

## 6. Proposed next steps (for discussion)

1. **Agent build (ADK on Gemini):**
   - tools: NL-to-SQL over the Gold layer (with the 5 query rules), policy search with clause citations, what-if simulator, document generator (board note, transfer proposal Excel, Parliament reply, P&L sheet);
   - session memory for follow-up questions;
   - tested against the answer key and its alternative phrasings.
2. **Access control (deliberately last):**
   - personas: CMD, Director (HR), Director (Finance), E1–E4 HR officer, E1–E4 Finance officer;
   - BigQuery row- and column-level security and authorised views;
   - document access lists, using the confidentiality tags already on every chunk;
   - the refusal answers already exist in the answer key.
3. **UI:** a Cloud Run web app with a persona switcher, chat, charts and downloadable documents.
4. **Parallel:** the gap-closure sprint from §3.

## Decisions for you
1. **Approve Gate G5** (data bank ready) and the move to the agent build.
2. **Run the 5-gap closure sprint in parallel?** (Recommended.)
3. **Search for production:** stay on Vertex AI Search (global), or plan BigQuery-native search in Mumbai for the sovereignty story?
