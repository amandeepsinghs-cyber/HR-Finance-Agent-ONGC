# Yukti v3 — Progress Dashboard (`PROGRESS.md`)

> **Generated — do not edit by hand.** Source of truth: [`UPGRADE_CHECKLIST.md`](UPGRADE_CHECKLIST.md), [`BUG_REGISTER.md`](BUG_REGISTER.md), [feature list](feature_list_and_verbatims/feature_list/feature_list.md), packet indexes, `docs/reviews/`, git. Regenerate: `python3 scripts/progress/build_progress.py` · Generated 24-Oct-2026 09:34 UTC · branch `v3/P0-stabilise` @ `59784c8`

> [!IMPORTANT]
> **Overall: 65% complete (weighted)** — 36/62 steps ✅ done, 10 in flight, 16 to do, 0 blocked. **12 blocker bugs open.** Integrity: 0 error(s), 23 warning(s).

## 1. Phase progress

| Phase | Name | Progress | ✅ | 🔍 | 🔨 | 🔄 | ⬜ | ⛔ | Steps |
|---|---|---|---|---|---|---|---|---|---|
| **P0** | Stabilise | `████████████████████` 100% | 11 | 0 | 0 | 0 | 0 | 0 | 11 |
| **P1** | Real finance SSOT | `███████████████████░` 94% | 11 | 0 | 0 | 1 | 0 | 0 | 12 |
| **P2H** | HR: personas, V19, Employee-360 | `██████████░░░░░░░░░░` 50% | 3 | 1 | 0 | 1 | 3 | 0 | 8 |
| **P2F** | Finance diagnostics (V20) | `███████████████░░░░░` 75% | 2 | 3 | 0 | 1 | 0 | 0 | 6 |
| **P3** | Agents + DCF (V22) | `██░░░░░░░░░░░░░░░░░░` 8% | 0 | 0 | 0 | 3 | 7 | 0 | 10 |
| **P4** | Visual 9/10 + exports (V21) | `████████████████████` 100% | 9 | 0 | 0 | 0 | 0 | 0 | 9 |
| **P5** | One brain, eval, redeploy | `░░░░░░░░░░░░░░░░░░░░` 0% | 0 | 0 | 0 | 0 | 6 | 0 | 6 |

## 2. Next actionable steps (all dependencies ✅)

**In flight — finish these first:**

| Step | Status | Task | Owner | Next action |
|---|---|---|---|---|
| P1.1 | 🔄 In progress | Acquire ARs FY16–FY20, NSE XBRL, Yahoo, RBI, Damodaran; manifest with sha256 | FL→O | Complete build + evidence |
| P2H.4 | 🔍 In review | V19 turns 4–5: export intent + columns + xlsx link; email agent (.eml/.docx/mailto); delete canned proposal | O→F | Apply review findings / approve |
| P2H.5 | 🔄 In progress | Employee-360 generator regeneration (realistic pyramid, names, pay + benefits + insurance + CTC, calibrated) | O | Complete build + evidence |
| P2F.1 | 🔍 In review | Year clarification (chips + voice) | O | Apply review findings / approve |
| P2F.2 | 🔍 In review | Multi-year statement payload (4–10 FY columns) | O | Apply review findings / approve |
| P2F.3 | 🔍 In review | WACC metric + chart + driver attribution | O (Shapley → F optional) | Apply review findings / approve |
| P2F.5 | 🔄 In progress | Grounded "why" + non-circular grounding | O | Complete build + evidence |
| P3.1 | 🔄 In progress | Contract v3 consolidation: add `proposed_action`, `job`, `provenance`, `dcf_model`; **owns the `contract_versi | O | Complete build + evidence |
| P3.2 | 🔄 In progress | Jobs API + executor + job state store + SSE | O | Complete build + evidence |
| P3.4 | 🔄 In progress | DCF engine core | F (O reviews API first) | Complete build + evidence |

**Ready to start:**

| Step | Task | Owner | Unblocked by |
|---|---|---|---|
| — | Nothing is unblocked: finish the in-flight steps above (G4 reviews) first. | | |

## 3. Sponsor action items

| ID | Action | Needed by | Status |
|---|---|---|---|
| SA-1 | Re-authenticate ADC (`gcloud auth application-default login`) — expires daily | P0.1, P1.6+ | ⬜ **Expired again 24-Oct** (needed for BigQuery steps + live app) |
| SA-2 | Approve v3 doc set + OD-7…OD-18 | P0.8 | ✅ Done 23-Oct (D-43…D-54) |
| SA-3 | Download RBI Handbook Table 178 (month-end G-sec yields) XLSX → `knowledge/public_sources/market_data/rbi/` | P1.9 | ⬜ Pending |
| SA-4 | Download Damodaran Jan-2025 `ctryprem` → `knowledge/public_sources/market_data/damodaran/` | P1.9 | ⬜ Pending |
| SA-5 | Review the 10 finance action levers + assumption % (SPEC-08 §7, D-50) | P2F.6 | ⬜ Pending |
| SA-6 | G5 sign-off at the end of each phase (P0 … P5) | each phase | ✅ P0 signed off 23-Oct 09:52 · ⬜ P1 next |
| SA-7 | Go-ahead for the Cloud Run redeploy (**note:** deploy with `max-instances=1` until exports move to a GCS store; P4.6 G4 r2: the turn registry and export files are per-instance and fail closed with 403 across instances) | P5.6 | ⬜ Pending |

## 4. Requirement coverage by verbatim (V1–V23)

| Verbatim | Features | Feature status | Open steps | Coverage |
|---|---|---|---|---|
| V2 | FEAT-027 | 🟡 | P2H.4, P3.5 | 🟡 |
| V3 | FEAT-010, FEAT-031 | 🔴 🔴 |  | 🔴 |
| V6 | FEAT-013 | 🔴 | P5.2 | 🔴 |
| V7 | FEAT-003, FEAT-015, FEAT-026, FEAT-027 | ✅ 🟡 🔴 🟡 | P2H.4, P3.5 | 🟡 |
| V8 | FEAT-001, FEAT-013 | ✅ 🔴 | P5.2 | 🟡 |
| V11 | FEAT-001, FEAT-002, FEAT-003, FEAT-009 | ✅ 🟡 ✅ 🔴 | P5.1 | 🟡 |
| V12 | FEAT-004, FEAT-005 | 🟡 ✅ |  | 🟡 |
| V13 | FEAT-006, FEAT-009, FEAT-010, FEAT-011, FEAT-021 | 🟡 🔴 🔴 🟡 🟡 | P2H.5, P2H.6, P2H.8, P2F.5, P5.1 | 🟡 |
| V14 | FEAT-007, FEAT-010, FEAT-011, FEAT-014 | 🟡 🔴 🟡 🔴 | P2F.5, P3.1, P5.4, P5.5, P5.6 | 🟡 |
| V15 | FEAT-015, FEAT-026 | 🟡 🔴 |  | 🟡 |
| V16 | FEAT-016 | 🟡 |  | 🟡 |
| V17 | FEAT-017, FEAT-031 | 🔴 🔴 |  | 🔴 |
| V18 | FEAT-018, FEAT-019, FEAT-020, FEAT-022, FEAT-032 | 🔴 ⛔ 🔴 🔴 🔴 | P1.1, P2H.7, P2H.8 | 🔴 |
| V19 | FEAT-021, FEAT-023 | 🟡 🔴 | P2H.4, P2H.5, P2H.6, P2H.8 | 🟡 |
| V20 | FEAT-019, FEAT-020, FEAT-024 | ⛔ 🔴 ⛔ | P1.1, P2F.1, P2F.2, P2F.3, P2F.5 | 🔴 |
| V21 | FEAT-025, FEAT-026, FEAT-027 | 🟡 🔴 🟡 | P2H.4, P2F.2, P3.5 | 🟡 |
| V22 | FEAT-019, FEAT-028, FEAT-029 | ⛔ ⛔ ⛔ | P1.1, P3.1, P3.2, P3.3, P3.4, P3.4b, P3.5, P3.6a … | ⛔ |
| V23 | FEAT-021, FEAT-022, FEAT-032 | 🟡 🔴 🔴 | P2H.5, P2H.6, P2H.7, P2H.8 | 🟡 |

_Not mapped to a feature (process / question-bank / naming verbatims, tracked in UPGRADE_CHECKLIST Part A and docs/question_bank.md): V1, V4, V5, V9, V10._

## 5. Features (v3 status from the feature list)

✅ 3 · 🟡 12 · 🔴 12 · ⛔ 5 = 32

| Feature | Status | Steps done / total |
|---|---|---|
| FEAT-001 Scrollable conversation feed (history) | ✅ | 0/0 |
| FEAT-002 Multi-turn context & entity carry-over | 🟡 | 0/0 |
| FEAT-003 Visual presentation audit | ✅ | 0/0 |
| FEAT-004 Voice orb (Aurora wave) | 🟡 | 1/1 |
| FEAT-005 Executive UI modernisation | ✅ | 0/0 |
| FEAT-006 CMD named employee roster | 🟡 | 1/1 |
| FEAT-007 Answer contract v2 | 🟡 | 0/1 |
| FEAT-008 Generated semantic layer | 🟡 | 0/1 |
| FEAT-009 QuerySpec planner & compiler (replaces fast-paths) | 🔴 | 0/1 |
| FEAT-010 Granular-data RBAC (row/column masking) | 🔴 | 0/0 |
| FEAT-011 Insight engine & drill-down chips | 🟡 | 0/1 |
| FEAT-012 Reliability, safety, performance | 🟡 | 0/0 |
| FEAT-013 Voice pipeline quality (no duplicate turns) | 🔴 | 1/2 |
| FEAT-014 Eval-gated release & Cloud Run redeploy | 🔴 | 2/5 |
| FEAT-015 Any-chart re-presentation & chart excellence | 🟡 | 0/0 |
| FEAT-016 AI aura visual language | 🟡 | 1/1 |
| FEAT-017 Eleven-persona matrix + function split + `self` scope | 🔴 | 2/2 |
| FEAT-018 Real financial SSOT with page lineage + verification gates | 🔴 | 7/8 |
| FEAT-019 Yahoo Finance ingestion (consolidated view) + market data | ⛔ | 1/2 |
| FEAT-020 Knowledge RAG over real AR text | 🔴 | 1/1 |
| FEAT-021 Employee-360 enterprise table (realistic, reconciled) | 🟡 | 1/4 |
| FEAT-022 Field economics-360 reconciled to company AR totals | 🔴 | 1/3 |
| FEAT-023 V19 transfer workflow: Excel intent + Email agent | 🔴 | 1/2 |
| FEAT-024 V20 finance diagnostics (year-clarify, multi-year statement, WACC, why | ⛔ | 3/7 |
| FEAT-025 Financial statement table visual | 🟡 | 3/4 |
| FEAT-026 Chart portfolio completion + correct waterfall | 🔴 | 4/4 |
| FEAT-027 Export suite | 🟡 | 2/4 |
| FEAT-028 Coordinator + agent registry + jobs + permission UX | ⛔ | 0/6 |
| FEAT-029 DCF valuation agent | ⛔ | 1/4 |
| FEAT-030 One-brain consolidation + numeric golden eval | ⛔ | 2/8 |
| FEAT-031 Identity & security hardening | 🔴 | 3/3 |
| FEAT-032 Provenance honesty & degraded-mode transparency | 🔴 | 4/4 |

## 6. Bugs

- **Blockers:** 14 total — 🔴 open 4 · 🟠 in progress 8 · ↩ regressed 0 · ✅ closed 2
- **Important:** 31 total — 🔴 open 12 · 🟠 in progress 13 · ↩ regressed 0 · ✅ closed 6
- **Cosmetic:** 1 total — 🔴 open 0 · 🟠 in progress 1 · ↩ regressed 0 · ✅ closed 0

**Open blockers:**

| Bug | Status | Symptom | Closing step(s) | Step status |
|---|---|---|---|---|
| BUG-02 | in_progress | BS/CF/ratios wrong (FY24 total assets 4,22,820 vs AR 4,46,021; FY25 CFO 63,180 vs 73,010;  | P0.3, P1.10b, P1.2 | P0.3:✅ P1.10b:✅ P1.2:✅ |
| BUG-03 | in_progress | Same metric, three values (FY17 royalty 7,635 / 8,548 / AR 11,575) | P1.10b, P1.6 | P1.10b:✅ P1.6:✅ |
| BUG-05 | in_progress | feedback4: "data only up to 2026… balance sheet for 2024 not available" → apology/flip loo | P1.10a, P1.11, P5.1, P5.3 | P1.10a:✅ P1.11:✅ P5.1:⬜ P5.3:⬜ |
| BUG-06 | in_progress | E2_HR says "switch role to CMD" → becomes CMD (verified by curl) | P0.4, P2H.2 | P0.4:✅ P2H.2:✅ |
| BUG-07 | in_progress | Every junior sees Pooja Verma's (EMP-102451) leave/transfer data | P2H.1 | P2H.1:✅ |
| BUG-08 | in_progress | "Express this as a waterfall" → Total ≈ 3× revenue | P4.1 | P4.1:✅ |
| BUG-09 | in_progress | Waterfall invents EBITDA (`rev*0.68`, `(rev+pbt)/2`) | P4.1 | P4.1:✅ |
| BUG-10 | open | "Can you export this as an Excel file" not understood | P2H.4 | P2H.4:🔍 |
| BUG-11 | open | "Draft an email to Director HR" → canned AGT proposal ("401 net recommendations" vs "146 r | P2H.4 | P2H.4:🔍 |
| BUG-12 | open | Hard-coded answers/numbers (Parliament "143 vacancies", Champang EBITDA-negative, `or 3310 | P2H.4, P5.1 | P2H.4:🔍 P5.1:⬜ |
| BUG-13 | open | Cloud Run = baseline rev `00001`; `financial_build/` not in the image | P0.9, P5.6 | P0.9:✅ P5.6:⬜ |
| BUG-35 | in_progress | Container image cannot build: Dockerfile `lint:tokens` gate fails on raw colours | P4.9, P5.6 | P4.9:✅ P5.6:⬜ |

## 7. Recent step commits

| Commit | Date | Message |
|---|---|---|
| `979b3d1` | 2026-10-24 | P2F.3 (pre-G4): WACC metrics, chart routing, and 5-factor Shapley attribution (SPEC-02 §5, 21/21 tests) |
| `73274fb` | 2026-10-24 | P2H.4 (pre-G4): V19 turns 4-5 export intent + columns + xlsx link, email_draft agent + EmailDraftRenderer, delete canned proposal  |
| `aba36a5` | 2026-10-24 | P1.6 (pre-G4): Add P1.6_evidence.md for verified SSOT load |
| `f9f6e29` | 2026-10-24 | P1.9 (G4 r1 fixes): resolve P19-B1..P19-B3 in build_wacc.py and inputs.py (9/9 tests) |
| `7b53be0` | 2026-10-24 | P2F.4 + P2F.6 (G4 r1 fixes) + P2F.1 frontend: resolve P2F4-B1..B3 & P2F6-B1..B3 (24/24 tests) and port ClarifySpec UI |
| `5ce3b16` | 2026-10-24 | P2F.1 + P2F.2: multi-year statement payload and BUG-42 fix |
| `0655f18` | 2026-10-24 | P2H.5 (pre-G4 r4): Fix objective scaling and remove residual pools, report gap |
| `6d645f2` | 2026-10-24 | P2F.6 (pre-G4): Top-5 action generator, safe AST expr evaluator, and delegation table (SPEC-08 §7, 12/12 tests) |
| `1d0fffa` | 2026-10-24 | P2F.6 (pre-G4): Author SPEC-08 §7.1 lever library (levers.yaml) |
| `0551174` | 2026-10-24 | P2F.4 (pre-G4): Deterministic variance-attribution & PBT bridge engine (SPEC-08 §6.1, 9/9 tests) |
| `f27e188` | 2026-10-24 | P1.6 (pre-G4): Resolve 497 conflict rows and load to BigQuery |
| `0f72640` | 2026-10-24 | P1.9 (pre-G4): WACC input pack and fact_wacc_annual offline build |
| `b2eb34c` | 2026-10-24 | P2H.3 (G4 r2 fixes): Resolve R2-B1..B5 (f-string anchor_date, idempotent k>=5 suppression & raw_total in narrate/insights, remove  |
| `a459f84` | 2026-10-24 | P4.8 (pre-G4): Finance rubric §F (F1–F14), scorecard template, and 10 light/dark screenshots |
| `4cea078` | 2026-10-24 | P4.5 (pre-G4 B3): DcfModelCard tabbed composite, SPEC-02 §10 fixture, and B2 minor polish |

## 8. Integrity checks

- ⚠️ BUG-02 is still in_progress although all its steps (P0.3, P1.10b, P1.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-06 is still in_progress although all its steps (P0.4, P2H.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-02 is still in_progress although all its steps (P0.3, P1.10b, P1.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-02 is still in_progress although all its steps (P0.3, P1.10b, P1.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-03 is still in_progress although all its steps (P1.10b, P1.6) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-02 is still in_progress although all its steps (P0.3, P1.10b, P1.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-02 is still in_progress although all its steps (P0.3, P1.10b, P1.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-03 is still in_progress although all its steps (P1.10b, P1.6) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-07 is still in_progress although all its steps (P2H.1) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-27 is still in_progress although all its steps (P2H.1) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-28 is still in_progress although all its steps (P2H.1) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-06 is still in_progress although all its steps (P0.4, P2H.2) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-34 is still in_progress although all its steps (P2H.3, P4.8) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-08 is still in_progress although all its steps (P4.1) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-09 is still in_progress although all its steps (P4.1) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-22 is still in_progress although all its steps (P4.1) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-38 is still in_progress although all its steps (P4.3) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-39 is still in_progress although all its steps (P1.6, P4.3) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-23 is still in_progress although all its steps (P4.4) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-24 is still in_progress although all its steps (P4.6) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-25 is still in_progress although all its steps (P4.6, P4.7) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-25 is still in_progress although all its steps (P4.6, P4.7) are ✅ — close it in BUG_REGISTER.md.
- ⚠️ BUG-34 is still in_progress although all its steps (P2H.3, P4.8) are ✅ — close it in BUG_REGISTER.md.

---
**How this stays current:** every step completion = (1) update the step's Status in `UPGRADE_CHECKLIST.md` (⬜ → 🔨 Built → 🔍 In review → ✅ Done only with a `docs/reviews/<step>.md` APPROVE), (2) close the linked bugs in `BUG_REGISTER.md`, (3) run `python3 scripts/progress/build_progress.py` (regenerate) and `--check` (validate), (4) commit all three files together. The optional git hook (`scripts/progress/install_hook.sh`) blocks commits when `--check` fails.
