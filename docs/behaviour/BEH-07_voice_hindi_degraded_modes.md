# BEH-07: Voice, Hindi & Degraded Modes (incl. feedback 1–4 regressions)

**Features:** FEAT-030 (one brain, voice reads contract), FEAT-032 (provenance & degraded-mode transparency), FEAT-017, FEAT-026 · **Specs:** [SPEC-11](../specs/SPEC-11_one_brain_provenance_eval.md) (one brain/provenance), [SPEC-06](../specs/SPEC-06_personas_identity_rbac_v3.md), [SPEC-09](../specs/SPEC-09_statement_visual_chart_portfolio.md), [SPEC-10](../specs/SPEC-10_export_suite.md) · **Steps:** P0.1, P0.3, P4.1, P5 (one brain) · **Verbatims:** V6, V8, V11, V18 · **Bugs:** BUG-01, 04, 05, 17, 18, 19, 26, 33 + fb1–fb4

> **BLUF.** Voice and text give the **same answer** (voice speaks the contract's `spoken_summary` verbatim, once); Hindi questions get Hindi narration, not English + Hindi concatenated; outages are stated honestly ("data service unreachable", "local snapshot") instead of generic errors or false provenance. Six feedback regressions are pinned as scenarios BEH-07.30–.35 and must stay green in the P5 golden eval.

---

## A. Voice parity

| ID | Given | When | Then |
|---|---|---|---|
| BEH-07.01 | CMD, Live voice on | 🎙 "Show the balance sheet for FY24" | One user bubble, one agent bubble with Sources; contract identical to the text turn; Leda speaks `spoken_summary` verbatim |
| BEH-07.02 | Live on, typed turn | type "headcount in Delhi by level" | REST answer bubble + spoken once; no second agent bubble from the Live transcript |
| BEH-07.03 | speaking | user says "stop" (real barge-in) | Speech stops within 300 ms; no fragment bubble; next turn normal |
| BEH-07.04 | speaking, speaker echo at mic level > 0.5 | (no user speech) | No `interrupt` sent during speak-only playback; no fake user bubble |

## B. Hindi

| ID | Given | When | Then |
|---|---|---|---|
| BEH-07.10 | CMD | 🎙 "Yukti, tumhe Hindi bolni aati hai kya?" | "जी हाँ, मैं हिंदी बोल सकती हूँ। मैं आपकी किस प्रकार सहायता कर सकती हूँ?" (single bubble) |
| BEH-07.11 | CMD | "दिल्ली में कितने कर्मचारी हैं?" | Visual as English; `display_text` and `spoken_summary` in Hindi; numbers in Indian grouping; one language per bubble |
| BEH-07.12 | CMD | Hinglish "Delhi mein E3 kitne hain?" | Hindi (Devanagari) or Hinglish per `det_lang` policy (SPEC-11); never English + Hindi concatenated |
| BEH-07.13 | E2_HR | "मेरी वेतन पर्ची दिखाओ" | `self` payslip; Hindi labels on the card headers where available |
| BEH-07.14 | any | Hindi refusal case | Hindi refusal copy from SPEC-06 §4.6 |

## C. Degraded modes (honest status)

| ID | Given | When | Then |
|---|---|---|---|
| BEH-07.20 | ADC expired (BUG-01) | open app | Banner "Data service not authorised — answers limited" (from `/health.auth_ok=false`); orb shows idle-warning |
| BEH-07.21 | ADC expired | "Headcount in Delhi" | E-AUTH copy: "I can't reach the data service right now. Nothing is wrong with your question; please try again in a minute." No "Reauthentication…" text (BUG-33) |
| BEH-07.22 | BigQuery unreachable, local snapshot available | "Balance sheet FY24" | Answer from the local snapshot with caveat "Shown from a local snapshot ({snapshot_date}); live data service unavailable" and `source=local_snapshot` (BUG-04); never "Compiled SQL / BigQuery" or "Audited + Yahoo" labels |
| BEH-07.23 | Gemini unavailable, deterministic path possible | "Show income statement FY25" | Deterministic statement answer; narration from template; caveat "Summary generated without AI narration" |
| BEH-07.24 | Synthetic clause cited | any policy answer from JRTP Rev 4 / R16 clauses | "Illustrative" badge + tooltip "Synthetic clause for demo; ONGC's text is not public" (BUG-31) |
| BEH-07.25 | Live WebSocket drops | mid-conversation | Toast "Voice disconnected — you can keep typing"; text path unaffected; auto-reconnect ≤ 3 tries |
| BEH-07.26 | Coverage question | "What years of financial data do you have?" | Deterministic coverage card from the SSOT manifest (standalone FY17–FY26, consolidated FY22–FY26, Yahoo view FY23–FY26); LLM never asserts coverage on its own (BUG-05) |

## D. Feedback regressions (must stay green)

| ID | Source | Given | When | Then (exact) | Root cause fixed by |
|---|---|---|---|---|---|
| **BEH-07.30** | feedback4 L15-40 | CMD, Live on | "can you show me the balance sheet for 2024?" → "when you say upto 2026, 2024 is before 2026?" → "then show it to me" → "give me income statement" | T1: FY24 **balance sheet statement table** (FY 2023-24, "2024" resolved to FY24 with a one-line note "Taking 2024 as FY 2023-24; say FY25 for 2024-25"). T2: deterministic coverage answer, no apology loop. T3: "it" = FY24 balance sheet (re-shown). T4: year-clarify chips (FY26/FY25/FY24/5-yr) — no "I do not have a pre-compiled income statement". **0 occurrences** of "not available", "my apologies", "I can only access data up to" | one brain + coverage manifest (BUG-05), SPEC-08 clarify |
| **BEH-07.31** | feedback4 L46-86 | Live on, voice reading the BS answer, speaker echo | (Yukti speaking) | Exactly 1 user bubble and 1 agent bubble per turn in both the feed and the panel thread; no fragment "revenue, EBITDA, PAT, or total"; no duplicate full-length agent bubble | per-speak `speak_id`, no `_is_speak_only` reset on interrupt, barge-in suppressed during speak (BUG-17); one text source per turn (BUG-18) |
| **BEH-07.32** | feedback3 | E2_HR | "How many casual leaves do I get in a year?" | Casual Leave 12 days per calendar year (Leave Rules cl. 2A.0) — **not study leave**; no "0.0%" chart; no JRTP footer on a leave clause | topic guards + no cache serve without clause match (diag_D B05/B06) |
| **BEH-07.33** | feedback1 | CMD | "What is the average salary in NYC?" → "pay of an E1 officer who is joining?" → "divide this pay into perks, base salary and other components" → "do the math" | T1: note "I heard 'NYC' as ONGC" + avg gross pay. T2: entry pay from `dim_grade` (E1 scale minimum, DPE 3rd PRC) + DA/HRA rates — explicitly not the incumbents' average. T3: per-employee monthly components table (basic, DA, HRA, cafeteria, field/offshore, PRP, gross) where components **sum to the shown gross** (no fudge factor), unit "₹ per month"; **no ₹ crore pool totals** unless asked. T4: computes per-officer figures from pool ÷ headcount if a pool was shown, else restates T3. No self-contradiction ("cannot provide… total basic ₹140.47 Crore"); units never "years" | BUG-26 fix (remove scale factor, entry pay), semantic component metrics |
| **BEH-07.34** | fedback2 L331-341 | CMD, single-asset revenue KPI (Ankleshwar) on screen | "show this as a waterfall" ×3 | BridgeError copy (EN, or HI if asked in Hindi) once per request; **0** "I've switched the screen view to a waterfall" without a rendered waterfall; offer "Show the Ankleshwar revenue trend instead?" chip | SPEC-09 §4.3 false-success rule |
| **BEH-07.35** | fedback2 L277-283 + B12 | CMD | 🎙 Hindi question about revenue (e.g. "पिछले पाँच साल का रेवेन्यू दिखाओ") | Narration only in Hindi (translated `spoken_summary`), displayed once; not "English summary + Hindi re-voicing" concatenated in one bubble | narrator translates `spoken_summary` per `det_lang`; voice reads verbatim (BUG-19) |

## E. Acceptance

- BEH-07.30–.35 are encoded in the P5 golden eval (multi-turn), text and voice (voice: 3 runs each), **6/6 pass on 3 consecutive runs**.
- BEH-07.20–.22 run offline with forced failures (`YUKTI_FORCE_ADC_FAIL=1`, `YUKTI_FORCE_BQ_FAIL=1` test flags), 100% pass; scan of all responses for `Reauthentication|RefreshError|Traceback` = 0.
