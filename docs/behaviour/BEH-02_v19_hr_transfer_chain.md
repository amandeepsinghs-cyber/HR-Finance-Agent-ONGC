# BEH-02: V19 HR Transfer Chain (5 turns)

**Features:** FEAT-023 (+ FEAT-017, FEAT-027) · **Spec:** [SPEC-07](../specs/SPEC-07_v19_transfer_workflow_email.md), [SPEC-10](../specs/SPEC-10_export_suite.md), [SPEC-06](../specs/SPEC-06_personas_identity_rbac_v3.md) · **Steps:** P2H.3, P2H.4 · **Verbatim:** V19

> **BLUF.** The sponsor's five sentences must run end-to-end in one session, by text or voice, in English or Hindi: ordered level chart → canonical ">5 years" count (executives default, all-cadres toggle) → named roster → xlsx with exactly the requested columns → editable email to Director (HR) with the xlsx attached. CMD and DIR_HR get names; DIR_FIN and juniors get aggregates; Finance juniors can't raise the email. No canned numbers anywhere.

**Placeholders** (`{…}`) are evaluated from the SPEC-07 reference SQL at test time: `{n_delhi}`, `{n_gt5_exec}`, `{n_gt5_all}`, `{by_level}`, `{n_exempt}`, `{as_of}`. Today's landing-CSV values (for orientation only, will change after SPEC-04 regeneration): 943 / 419 / 645 as of 19-Oct-2026.

---

## A. Golden chain — CMD (text, English)

| ID | Given | When | Then |
|---|---|---|---|
| BEH-02.01 | CMD signed in; new session | "How many employees are there in the Delhi office across levels? Show it as a histogram." | `chart.kind=column`; x = `E1…E9, GRP-B, GRP-C, GRP-D` in that order; note "Levels are categories, so this is a column chart in level order."; footnote "Also in Delhi: CMD 1, Directors 2"; title contains `{n_delhi}`; cohort C0 active; chips incl. "More than 5 years in Delhi" |
| BEH-02.02 | after .01 | "How many of these employees are here in Delhi for more than five years?" | KPI "**{n_gt5_exec} executives** (`{n_gt5_all}` including non-executive staff)"; column chart by level E1→E9; rule line "Continuous stay at the current station, more than 5.0 years, as of {as_of}"; clause line "JRTP Rev 4 cl. 3.2 — rotation after 3–5 years (**Illustrative**)" + "Delhi High Court (2018), ONGC v. B.V. Srihari Rao" (real); chips "Show the names", "Include all cadres", "Export to Excel", "Draft email to Director (HR)"; cohort C1 ⊂ C0 |
| BEH-02.03 | after .02 | "Include all cadres" | Same chart + GRP-B/C/D; KPI `{n_gt5_all}`; cohort C1′ (definition same, population all) |
| BEH-02.04 | after .02 | "Can you give me the name of those employees and their tenure in Delhi?" | Roster, `row_count={n_gt5_exec}`; columns `Name, Designation, Level, ONGC service (yrs), Tenure in Delhi (yrs), Years to retirement, Exemption`; sorted Tenure in Delhi desc; caveat if designation is the generic fallback |
| BEH-02.05 | after .04 | "Can you export this as an Excel file? Their names, their designations, their ranks from E1 to whatever level, and then ultimately their tenure in Delhi." | Export intent detected (no data query); `artifacts[0].kind=xlsx`; header exactly `Name | Designation | Level | Tenure in Delhi (yrs)`; rows = `{n_gt5_exec}`; frozen header, title rows, sheet "Definition"; filename `yukti_delhi_gt5y_roster_…_cmd_….xlsx`; spoken "Your Excel file with {n_gt5_exec} executives is ready…"; download link visible on the card |
| BEH-02.06 | after .05 | "Can you draft an email to the Director HR highlighting these employees and requesting review?" | `visual.type=email_draft`; To = Director (HR) `<director.hr@ongc.example>`; CC empty; Subject "Review requested: {n_gt5_exec} executives at Delhi beyond 5 years' continuous stay (as of {as_of})"; body: counts by level summing to `{n_gt5_exec}`, "of which {n_exempt} carry a recorded exemption", JRTP 3.2 (Illustrative) + J-03 sentences, Transfer Board ask with date as_of+30d, attachment = the .05 xlsx; buttons "Download .eml", "Download .docx", "Open in mail app"; draft label "please review before sending" |
| BEH-02.07 | after .06 | edit Subject inline, click "Download .eml" | .eml has the edited subject, `X-Unsent: 1`, 1 xlsx attachment |
| BEH-02.08 | after .06 | click "Open in mail app" | `mailto:` opens with subject + body (≤ 1,800 chars); toast "Attach the downloaded Excel file manually" |

## B. Variants

| ID | Given | When | Then |
|---|---|---|---|
| BEH-02.10 | CMD, after .02 (no names turn) | "Export this to Excel" | xlsx of the **counts by level** (the active visual), not the roster; caveat "Say 'export the names' for the full list" |
| BEH-02.11 | CMD, after .04 | "Draft an email to Director HR" without an export first | Agent first creates the xlsx with default V19 columns, says "I've also prepared the Excel list to attach", then the draft |
| BEH-02.12 | CMD, fresh session | "Draft an email to Director HR about overdue transfers" | Clarify: "Which group should the email cover?" + chips ("Delhi, more than 5 years", "Another station…"); **no canned proposal** |
| BEH-02.13 | CMD | 🎙 voice for all five turns | Same contracts as A; voice speaks each `spoken_summary` verbatim once; no duplicate bubbles (BEH-07.10) |
| BEH-02.14 | CMD | Hindi: "दिल्ली ऑफिस में स्तर-वार कितने कर्मचारी हैं?" → "इनमें से कितने पाँच साल से ज़्यादा दिल्ली में हैं?" → "उनके नाम और दिल्ली में कार्यकाल बताओ" → "इसे एक्सेल में डाउनलोड करो" → "निदेशक (मानव संसाधन) को ईमेल ड्राफ्ट करो" | Same visuals and numbers as A; narration in Hindi; email body in Hindi with English subject + table headers (SPEC-07 Q4) |
| BEH-02.15 | CMD | Hinglish: "excel mein export karo, sirf naam aur Delhi tenure" | xlsx with `Name | Tenure in Delhi (yrs)` |
| BEH-02.16 | CMD, after .04 | "go back to all Delhi staff" then "export this" | C0 re-activated; xlsx = counts by level for all Delhi |
| BEH-02.17 | CMD | "How many have been in Mumbai for more than 5 years?" | Same definition on `WC-MUM` (STATION_GT5_CONT_V1); column label "Tenure at Mumbai (yrs)" in roster |
| BEH-02.18 | CMD | "Export with their home town" (unknown column) | xlsx with matched columns; caveat "I couldn't match 'home town'; exported the rest" |
| BEH-02.19 | after .01 | "show crude oil exports for FY25" | Not an export intent (negative guard) → data question |

## C. RBAC per persona (SPEC-07 §4.7)

| ID | Persona | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|
| BEH-02.20 | CMD | allow | allow | names | named xlsx | email + named attachment |
| BEH-02.21 | DIR_HR | allow | allow | names | named xlsx | "Who should this go to?" chips (CMD / Transfer Board), then draft |
| BEH-02.22 | DIR_FIN | allow | allow | counts by level (+ DISC-FIN names, pending OD-7) | aggregate xlsx `_aggregate` | aggregate email, no named attachment |
| BEH-02.23 | E1–E4_HR | allow (k≥5) | allow (k≥5) | R-NAMED + counts by level | aggregate xlsx, no `Name` column | aggregate email: "Counts only; the named list is available to Director (HR)." |
| BEH-02.24 | E1–E4_FIN | aggregate (k≥5) | aggregate (k≥5) | R-NAMED + counts | aggregate xlsx | R-FUNC: "Transfer reviews are raised by HR. I can prepare the counts table for you to share with HR." + chip |

**Exact copy for BEH-02.23 T3:** "I can't share individual names at your access level. Here is the same group as counts by grade (groups under 5 shown as '<5')."

## D. Regressions guarded

| ID | Old behaviour | Then (must not recur) |
|---|---|---|
| BEH-02.30 | "histogram" → age distribution (legacy default branch) | Always ordered level column chart |
| BEH-02.31 | Level axis ordered by headcount (BUG-34) | E1→E9 order |
| BEH-02.32 | T2 numbers differ by path (645 vs 419; `>` vs `>=`) | One definition id `DELHI_GT5_CONT_V1` on every path |
| BEH-02.33 | "export this as an Excel file" → treated as a data query (BUG-10) | Export intent, artifact link |
| BEH-02.34 | "draft an email…" → canned "AGT Proposal FY27" with 401 vs 146 (BUG-11/12) | email_draft from cohort; no literals |
| BEH-02.35 | Juniors' names leaked via export | Export built from masked contract only |
