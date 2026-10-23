# Yukti v3 — Progress Dashboard (`PROGRESS.md`)

> **Generated — do not edit by hand.** Source of truth: [`UPGRADE_CHECKLIST.md`](UPGRADE_CHECKLIST.md), [`BUG_REGISTER.md`](BUG_REGISTER.md), [feature list](feature_list_and_verbatims/feature_list/feature_list.md), packet indexes, `docs/reviews/`, git. Regenerate: `python3 scripts/progress/build_progress.py` · Generated 23-Oct-2026 09:30 UTC · branch `v3/P0-stabilise` @ `3f5e4b3`

> [!IMPORTANT]
> **Overall: 17% complete (weighted)** — 10/61 steps ✅ done, 1 in flight, 50 to do, 0 blocked. **12 blocker bugs open.** Integrity: 0 error(s), 0 warning(s).

## 1. Phase progress

| Phase | Name | Progress | ✅ | 🔍 | 🔨 | 🔄 | ⬜ | ⛔ | Steps |
|---|---|---|---|---|---|---|---|---|---|
| **P0** | Stabilise | `████████████████████` 100% | 10 | 0 | 0 | 0 | 0 | 0 | 10 |
| **P1** | Real finance SSOT | `░░░░░░░░░░░░░░░░░░░░` 2% | 0 | 0 | 0 | 1 | 11 | 0 | 12 |
| **P2H** | HR: personas, V19, Employee-360 | `░░░░░░░░░░░░░░░░░░░░` 0% | 0 | 0 | 0 | 0 | 8 | 0 | 8 |
| **P2F** | Finance diagnostics (V20) | `░░░░░░░░░░░░░░░░░░░░` 0% | 0 | 0 | 0 | 0 | 6 | 0 | 6 |
| **P3** | Agents + DCF (V22) | `░░░░░░░░░░░░░░░░░░░░` 0% | 0 | 0 | 0 | 0 | 10 | 0 | 10 |
| **P4** | Visual 9/10 + exports (V21) | `░░░░░░░░░░░░░░░░░░░░` 0% | 0 | 0 | 0 | 0 | 9 | 0 | 9 |
| **P5** | One brain, eval, redeploy | `░░░░░░░░░░░░░░░░░░░░` 0% | 0 | 0 | 0 | 0 | 6 | 0 | 6 |

## 2. Next actionable steps (all dependencies ✅)

**In flight — finish these first:**

| Step | Status | Task | Owner | Next action |
|---|---|---|---|---|
| P1.1 | 🔄 In progress | Acquire ARs FY16–FY20, NSE XBRL, Yahoo, RBI, Damodaran; manifest with sha256 | FL→O | Complete build + evidence |

**Ready to start:**

| Step | Task | Owner | Unblocked by |
|---|---|---|---|
| P1.2 | AR 10-yr table parser (FY13–FY26) | F | phase gates met |
| P1.8 | AR text chunks + embeddings + VECTOR_SEARCH retriever | F / O | phase gates met |
| P2H.1 | 11 personas + `dim_app_user` + function dimension + `self` scope + `@self_emp_id` + aggregate pay | O (tests F) | phase gates met |
| P4.1 | Signed bridge helper (py + ts), re-plot fix, no EBITDA fabrication, explicit-kind precedence, honest single-va | O→F | phase gates met |
| P4.9 | Orb visible in docked mode + optional edge aura (low priority, V21) | F | phase gates met |

## 3. Sponsor action items

| ID | Action | Needed by | Status |
|---|---|---|---|
| SA-1 | Re-authenticate ADC (`gcloud auth application-default login`) | P0.1 | ✅ Done 23-Oct |
| SA-2 | Approve v3 doc set + OD-7…OD-18 | P0.8 | ✅ Done 23-Oct (D-43…D-54) |
| SA-3 | Download RBI Handbook Table 178 (month-end G-sec yields) XLSX → `knowledge/public_sources/market_data/rbi/` | P1.9 | ⬜ Pending |
| SA-4 | Download Damodaran Jan-2025 `ctryprem` → `knowledge/public_sources/market_data/damodaran/` | P1.9 | ⬜ Pending |
| SA-5 | Review the 10 finance action levers + assumption % (SPEC-08 §7, D-50) | P2F.6 | ⬜ Pending |
| SA-6 | G5 sign-off at the end of each phase (P0 … P5) | each phase | ⬜ **P0 ready for sign-off** |
| SA-7 | Go-ahead for the Cloud Run redeploy | P5.6 | ⬜ Pending |

## 4. Requirement coverage by verbatim (V1–V23)

| Verbatim | Features | Feature status | Open steps | Coverage |
|---|---|---|---|---|
| V2 | FEAT-027 | 🟡 | P2H.4, P3.5, P4.6, P4.7 | 🟡 |
| V3 | FEAT-010, FEAT-031 | 🔴 🔴 | P2H.1 | 🔴 |
| V6 | FEAT-013 | 🔴 | P5.2 | 🔴 |
| V7 | FEAT-003, FEAT-015, FEAT-026, FEAT-027 | ✅ 🟡 🔴 🟡 | P2H.4, P3.5, P4.1, P4.4, P4.5, P4.6, P4.7, P4.8 | 🟡 |
| V8 | FEAT-001, FEAT-013 | ✅ 🔴 | P5.2 | 🟡 |
| V11 | FEAT-001, FEAT-002, FEAT-003, FEAT-009 | ✅ 🟡 ✅ 🔴 | P5.1 | 🟡 |
| V12 | FEAT-004, FEAT-005 | 🟡 ✅ | P4.9 | 🟡 |
| V13 | FEAT-006, FEAT-009, FEAT-010, FEAT-011, FEAT-021 | 🟡 🔴 🔴 🟡 🟡 | P1.7, P2H.3, P2H.5, P2H.6, P2H.8, P2F.5, P5.1 | 🟡 |
| V14 | FEAT-007, FEAT-010, FEAT-011, FEAT-014 | 🟡 🔴 🟡 🔴 | P2F.5, P3.1, P5.4, P5.5, P5.6 | 🟡 |
| V15 | FEAT-015, FEAT-026 | 🟡 🔴 | P4.1, P4.4, P4.5, P4.8 | 🟡 |
| V16 | FEAT-016 | 🟡 | P4.9 | 🟡 |
| V17 | FEAT-017, FEAT-031 | 🔴 🔴 | P2H.1, P2H.2 | 🔴 |
| V18 | FEAT-018, FEAT-019, FEAT-020, FEAT-022, FEAT-032 | 🔴 ⛔ 🔴 🔴 🔴 | P1.1, P1.2, P1.3, P1.4, P1.5, P1.6, P1.7, P1.8 … | 🔴 |
| V19 | FEAT-021, FEAT-023 | 🟡 🔴 | P1.7, P2H.3, P2H.4, P2H.5, P2H.6, P2H.8 | 🟡 |
| V20 | FEAT-019, FEAT-020, FEAT-024 | ⛔ 🔴 ⛔ | P1.1, P1.5, P1.8, P1.9, P2F.1, P2F.2, P2F.3, P2F.4 … | 🔴 |
| V21 | FEAT-025, FEAT-026, FEAT-027 | 🟡 🔴 🟡 | P2H.4, P2F.2, P3.5, P4.1, P4.2, P4.3, P4.4, P4.5 … | 🟡 |
| V22 | FEAT-019, FEAT-028, FEAT-029 | ⛔ ⛔ ⛔ | P1.1, P1.5, P1.9, P3.1, P3.2, P3.3, P3.4, P3.4b … | ⛔ |
| V23 | FEAT-021, FEAT-022, FEAT-032 | 🟡 🔴 🔴 | P1.7, P1.10a, P2H.5, P2H.6, P2H.7, P2H.8 | 🟡 |

_Not mapped to a feature (process / question-bank / naming verbatims, tracked in UPGRADE_CHECKLIST Part A and docs/question_bank.md): V1, V4, V5, V9, V10._

## 5. Features (v3 status from the feature list)

✅ 3 · 🟡 12 · 🔴 12 · ⛔ 5 = 32

| Feature | Status | Steps done / total |
|---|---|---|
| FEAT-001 Scrollable conversation feed (history) | ✅ | 0/0 |
| FEAT-002 Multi-turn context & entity carry-over | 🟡 | 0/0 |
| FEAT-003 Visual presentation audit | ✅ | 0/0 |
| FEAT-004 Voice orb (Aurora wave) | 🟡 | 0/1 |
| FEAT-005 Executive UI modernisation | ✅ | 0/0 |
| FEAT-006 CMD named employee roster | 🟡 | 0/1 |
| FEAT-007 Answer contract v2 | 🟡 | 0/1 |
| FEAT-008 Generated semantic layer | 🟡 | 0/1 |
| FEAT-009 QuerySpec planner & compiler (replaces fast-paths) | 🔴 | 0/1 |
| FEAT-010 Granular-data RBAC (row/column masking) | 🔴 | 0/0 |
| FEAT-011 Insight engine & drill-down chips | 🟡 | 0/1 |
| FEAT-012 Reliability, safety, performance | 🟡 | 0/0 |
| FEAT-013 Voice pipeline quality (no duplicate turns) | 🔴 | 0/1 |
| FEAT-014 Eval-gated release & Cloud Run redeploy | 🔴 | 2/5 |
| FEAT-015 Any-chart re-presentation & chart excellence | 🟡 | 0/0 |
| FEAT-016 AI aura visual language | 🟡 | 0/1 |
| FEAT-017 Eleven-persona matrix + function split + `self` scope | 🔴 | 0/2 |
| FEAT-018 Real financial SSOT with page lineage + verification gates | 🔴 | 0/8 |
| FEAT-019 Yahoo Finance ingestion (consolidated view) + market data | ⛔ | 0/2 |
| FEAT-020 Knowledge RAG over real AR text | 🔴 | 0/1 |
| FEAT-021 Employee-360 enterprise table (realistic, reconciled) | 🟡 | 0/4 |
| FEAT-022 Field economics-360 reconciled to company AR totals | 🔴 | 0/3 |
| FEAT-023 V19 transfer workflow: Excel intent + Email agent | 🔴 | 0/2 |
| FEAT-024 V20 finance diagnostics (year-clarify, multi-year statement, WACC, why | ⛔ | 0/7 |
| FEAT-025 Financial statement table visual | 🟡 | 0/4 |
| FEAT-026 Chart portfolio completion + correct waterfall | 🔴 | 0/4 |
| FEAT-027 Export suite | 🟡 | 0/4 |
| FEAT-028 Coordinator + agent registry + jobs + permission UX | ⛔ | 0/6 |
| FEAT-029 DCF valuation agent | ⛔ | 0/4 |
| FEAT-030 One-brain consolidation + numeric golden eval | ⛔ | 1/8 |
| FEAT-031 Identity & security hardening | 🔴 | 2/3 |
| FEAT-032 Provenance honesty & degraded-mode transparency | 🔴 | 3/4 |

## 6. Bugs

- **Blockers:** 14 total — 🔴 open 10 · 🟠 in progress 2 · ↩ regressed 0 · ✅ closed 2
- **Important:** 22 total — 🔴 open 17 · 🟠 in progress 1 · ↩ regressed 0 · ✅ closed 4
- **Cosmetic:** 1 total — 🔴 open 1 · 🟠 in progress 0 · ↩ regressed 0 · ✅ closed 0

**Open blockers:**

| Bug | Status | Symptom | Closing step(s) | Step status |
|---|---|---|---|---|
| BUG-02 | open | BS/CF/ratios wrong (FY24 total assets 4,22,820 vs AR 4,46,021; FY25 CFO 63,180 vs 73,010;  | P0.3, P1.10b, P1.2 | P0.3:✅ P1.10b:⬜ P1.2:⬜ |
| BUG-03 | open | Same metric, three values (FY17 royalty 7,635 / 8,548 / AR 11,575) | P1.10b, P1.6 | P1.10b:⬜ P1.6:⬜ |
| BUG-05 | in_progress | feedback4: "data only up to 2026… balance sheet for 2024 not available" → apology/flip loo | P1.10a, P1.11, P5.1, P5.3 | P1.10a:⬜ P1.11:⬜ P5.1:⬜ P5.3:⬜ |
| BUG-06 | in_progress | E2_HR says "switch role to CMD" → becomes CMD (verified by curl) | P0.4, P2H.2 | P0.4:✅ P2H.2:⬜ |
| BUG-07 | open | Every junior sees Pooja Verma's (EMP-102451) leave/transfer data | P2H.1 | P2H.1:⬜ |
| BUG-08 | open | "Express this as a waterfall" → Total ≈ 3× revenue | P4.1 | P4.1:⬜ |
| BUG-09 | open | Waterfall invents EBITDA (`rev*0.68`, `(rev+pbt)/2`) | P4.1 | P4.1:⬜ |
| BUG-10 | open | "Can you export this as an Excel file" not understood | P2H.4 | P2H.4:⬜ |
| BUG-11 | open | "Draft an email to Director HR" → canned AGT proposal ("401 net recommendations" vs "146 r | P2H.4 | P2H.4:⬜ |
| BUG-12 | open | Hard-coded answers/numbers (Parliament "143 vacancies", Champang EBITDA-negative, `or 3310 | P2H.4, P5.1 | P2H.4:⬜ P5.1:⬜ |
| BUG-13 | open | Cloud Run = baseline rev `00001`; `financial_build/` not in the image | P0.9, P5.6 | P0.9:✅ P5.6:⬜ |
| BUG-35 | open | Container image cannot build: Dockerfile `lint:tokens` gate fails on raw colours | P4.9, P5.6 | P4.9:⬜ P5.6:⬜ |

## 7. Recent step commits

| Commit | Date | Message |
|---|---|---|
| `3f5e4b3` | 2026-10-23 | P0.9 (G4 r2 fixes): end-to-end degraded-run evidence (with/without snapshot, broken ADC), Dockerfile fail-closed + demo-mode notes |
| `4945902` | 2026-10-23 | P0.5 (G4 r2 fixes): prod with no YUKTI_ALLOWED_ORIGINS allows no cross-origin callers (minor) |
| `6467e8f` | 2026-10-23 | P0.3 (G4 r2 fixes): insight context no longer labelled 'Annual Report' (unverified snapshot) + guard test |
| `b0f2b44` | 2026-10-23 | P0.4 (G4 r2 fixes): JWT charset + bytes compare (no 500), prod fail-closed signing key, trusted dev key file (O_NOFOLLOW+fstat), L |
| `927f434` | 2026-10-23 | P0.3 (G4 r2 fixes): remove remaining 'audited' claims (turn_runner, agent prompt, draft_document, access_control, fixture) + AST g |
| `8ee9991` | 2026-10-23 | P0.1 (G4 r2 fixes): Live voice-tool errors use safe copy + error code (no str(e)); /health auth_mode via auth.auth_mode() |
| `19df56e` | 2026-10-23 | P0.9 (pre-G4): runtime financial snapshot + manifest in image, prod env defaults, dockerignore hygiene; packet + layout smoke (BUG |
| `825d356` | 2026-10-23 | P0.6 (pre-G4): true test baseline (backend 416P/8F/0E vs 321P/9F/13E; ADC-caused failures 0); test_31 schema accepts P0.7 provenan |
| `911fa3b` | 2026-10-23 | P0.5 (pre-G4): CORS allow-list (no * with credentials), /admin/* behind YUKTI_ENABLE_ADMIN + admin token, docs off in prod (BUG-32 |
| `640b185` | 2026-10-23 | P0.4 (pre-G4): signed persona session token, /api/auth routes, role-switch refusal (R-ROLE) + audit, no persona from body/contract |
| `b55fc80` | 2026-10-23 | P0.7 (pre-G4): clause provenance (all 68 rulebook clauses illustrative), Illustrative badge, no hard-coded JRTP footer (BUG-31, D- |
| `68a5e46` | 2026-10-23 | P0.3 (pre-G4): remove false Audited/Yahoo/Compiled labels; explicit local_snapshot status, provenance, caveat and badge (BUG-02 la |
| `5872529` | 2026-10-23 | P0.2 (pre-G4): resolve_fy treats YYYY-YY / FY YYYY-YY as one FY; tenure 'over N years' not a range (BUG-20) |
| `85f476b` | 2026-10-23 | P0.1 (pre-G4): /health auth_ok + auth_mode, AuthBanner, safe E-AUTH/generic error copy (BUG-01, BUG-33) |

## 8. Integrity checks

✅ No inconsistencies between checklist, bug register, feature list, packets, reviews and git.

---
**How this stays current:** every step completion = (1) update the step's Status in `UPGRADE_CHECKLIST.md` (⬜ → 🔨 Built → 🔍 In review → ✅ Done only with a `docs/reviews/<step>.md` APPROVE), (2) close the linked bugs in `BUG_REGISTER.md`, (3) run `python3 scripts/progress/build_progress.py` (regenerate) and `--check` (validate), (4) commit all three files together. The optional git hook (`scripts/progress/install_hook.sh`) blocks commits when `--check` fails.
