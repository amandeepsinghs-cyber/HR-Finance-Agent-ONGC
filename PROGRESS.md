# Yukti v3 — Progress Dashboard (`PROGRESS.md`)

> **Generated — do not edit by hand.** Source of truth: [`UPGRADE_CHECKLIST.md`](UPGRADE_CHECKLIST.md), [`BUG_REGISTER.md`](BUG_REGISTER.md), [feature list](feature_list_and_verbatims/feature_list/feature_list.md), packet indexes, `docs/reviews/`, git. Regenerate: `python3 scripts/progress/build_progress.py` · Generated 25-Oct-2026 13:51 UTC · branch `v3/P0-stabilise` @ `a5f91bb`

> [!IMPORTANT]
> **Overall: 97% complete (weighted)** — 60/62 steps ✅ done, 1 in flight, 1 to do, 0 blocked. **2 blocker bugs open.** Integrity: 0 error(s), 1 warning(s).

## 1. Phase progress

| Phase | Name | Progress | ✅ | 🔍 | 🔨 | 🔄 | ⬜ | ⛔ | Steps |
|---|---|---|---|---|---|---|---|---|---|
| **P0** | Stabilise | `████████████████████` 100% | 11 | 0 | 0 | 0 | 0 | 0 | 11 |
| **P1** | Real finance SSOT | `███████████████████░` 94% | 11 | 0 | 0 | 1 | 0 | 0 | 12 |
| **P2H** | HR: personas, V19, Employee-360 | `████████████████████` 100% | 8 | 0 | 0 | 0 | 0 | 0 | 8 |
| **P2F** | Finance diagnostics (V20) | `████████████████████` 100% | 6 | 0 | 0 | 0 | 0 | 0 | 6 |
| **P3** | Agents + DCF (V22) | `████████████████████` 100% | 10 | 0 | 0 | 0 | 0 | 0 | 10 |
| **P4** | Visual 9/10 + exports (V21) | `████████████████████` 100% | 9 | 0 | 0 | 0 | 0 | 0 | 9 |
| **P5** | One brain, eval, redeploy | `█████████████████░░░` 83% | 5 | 0 | 0 | 0 | 1 | 0 | 6 |

## 2. Next actionable steps (all dependencies ✅)

**In flight — finish these first:**

| Step | Status | Task | Owner | Next action |
|---|---|---|---|---|
| P1.1 | 🔄 In progress | Acquire ARs FY16–FY20, NSE XBRL, Yahoo, RBI, Damodaran; manifest with sha256 | FL→O | Complete build + evidence |

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
| V2 | FEAT-027 | ✅ |  | ✅ |
| V3 | FEAT-010, FEAT-031 | ✅ ✅ |  | ✅ |
| V6 | FEAT-013 | 🟡 |  | 🟡 |
| V7 | FEAT-003, FEAT-015, FEAT-026, FEAT-027 | ✅ ✅ ✅ ✅ |  | ✅ |
| V8 | FEAT-001, FEAT-013 | ✅ 🟡 |  | 🟡 |
| V11 | FEAT-001, FEAT-002, FEAT-003, FEAT-009 | ✅ ✅ ✅ ✅ |  | ✅ |
| V12 | FEAT-004, FEAT-005 | ✅ ✅ |  | ✅ |
| V13 | FEAT-006, FEAT-009, FEAT-010, FEAT-011, FEAT-021 | ✅ ✅ ✅ ✅ ✅ |  | ✅ |
| V14 | FEAT-007, FEAT-010, FEAT-011, FEAT-014 | ✅ ✅ ✅ 🟡 | P5.6 | 🟡 |
| V15 | FEAT-015, FEAT-026 | ✅ ✅ |  | ✅ |
| V16 | FEAT-016 | ✅ |  | ✅ |
| V17 | FEAT-017, FEAT-031 | ✅ ✅ |  | ✅ |
| V18 | FEAT-018, FEAT-019, FEAT-020, FEAT-022, FEAT-032 | ✅ 🟡 ✅ ✅ ✅ | P1.1 | 🟡 |
| V19 | FEAT-021, FEAT-023 | ✅ ✅ |  | ✅ |
| V20 | FEAT-019, FEAT-020, FEAT-024 | 🟡 ✅ 🟡 | P1.1 | 🟡 |
| V21 | FEAT-025, FEAT-026, FEAT-027 | ✅ ✅ ✅ |  | ✅ |
| V22 | FEAT-019, FEAT-028, FEAT-029 | 🟡 ✅ 🟡 | P1.1 | 🟡 |
| V23 | FEAT-021, FEAT-022, FEAT-032 | ✅ ✅ ✅ |  | ✅ |

_Not mapped to a feature (process / question-bank / naming verbatims, tracked in UPGRADE_CHECKLIST Part A and docs/question_bank.md): V1, V4, V5, V9, V10._

## 5. Features (v3 status from the feature list)

✅ 27 · 🟡 5 · 🔴 0 · ⛔ 0 = 32

| Feature | Status | Steps done / total |
|---|---|---|
| FEAT-001 Scrollable conversation feed (history) | ✅ | 0/0 |
| FEAT-002 Multi-turn context & entity carry-over | ✅ | 0/0 |
| FEAT-003 Visual presentation audit | ✅ | 0/0 |
| FEAT-004 Voice orb (Aurora wave) | ✅ | 1/1 |
| FEAT-005 Executive UI modernisation | ✅ | 0/0 |
| FEAT-006 CMD named employee roster | ✅ | 1/1 |
| FEAT-007 Answer contract v2 | ✅ | 1/1 |
| FEAT-008 Generated semantic layer | ✅ | 1/1 |
| FEAT-009 QuerySpec planner & compiler (replaces fast-paths) | ✅ | 1/1 |
| FEAT-010 Granular-data RBAC (row/column masking) | ✅ | 0/0 |
| FEAT-011 Insight engine & drill-down chips | ✅ | 1/1 |
| FEAT-012 Reliability, safety, performance | ✅ | 0/0 |
| FEAT-013 Voice pipeline quality (no duplicate turns) | 🟡 | 2/2 |
| FEAT-014 Eval-gated release & Cloud Run redeploy | 🟡 | 4/5 |
| FEAT-015 Any-chart re-presentation & chart excellence | ✅ | 0/0 |
| FEAT-016 AI aura visual language | ✅ | 1/1 |
| FEAT-017 Eleven-persona matrix + function split + `self` scope | ✅ | 2/2 |
| FEAT-018 Real financial SSOT with page lineage + verification gates | ✅ | 7/8 |
| FEAT-019 Yahoo Finance ingestion (consolidated view) + market data | 🟡 | 1/2 |
| FEAT-020 Knowledge RAG over real AR text | ✅ | 1/1 |
| FEAT-021 Employee-360 enterprise table (realistic, reconciled) | ✅ | 4/4 |
| FEAT-022 Field economics-360 reconciled to company AR totals | ✅ | 3/3 |
| FEAT-023 V19 transfer workflow: Excel intent + Email agent | ✅ | 2/2 |
| FEAT-024 V20 finance diagnostics (year-clarify, multi-year statement, WACC, why | 🟡 | 7/7 |
| FEAT-025 Financial statement table visual | ✅ | 4/4 |
| FEAT-026 Chart portfolio completion + correct waterfall | ✅ | 4/4 |
| FEAT-027 Export suite | ✅ | 4/4 |
| FEAT-028 Coordinator + agent registry + jobs + permission UX | ✅ | 6/6 |
| FEAT-029 DCF valuation agent | 🟡 | 4/4 |
| FEAT-030 One-brain consolidation + numeric golden eval | ✅ | 8/8 |
| FEAT-031 Identity & security hardening | ✅ | 3/3 |
| FEAT-032 Provenance honesty & degraded-mode transparency | ✅ | 4/4 |

## 6. Bugs

- **Blockers:** 14 total — 🔴 open 1 · 🟠 in progress 1 · ↩ regressed 0 · ✅ closed 12
- **Important:** 33 total — 🔴 open 1 · 🟠 in progress 0 · ↩ regressed 0 · ✅ closed 32
- **Cosmetic:** 1 total — 🔴 open 0 · 🟠 in progress 0 · ↩ regressed 0 · ✅ closed 1

**Open blockers:**

| Bug | Status | Symptom | Closing step(s) | Step status |
|---|---|---|---|---|
| BUG-13 | open | Cloud Run = baseline rev `00001`; `financial_build/` not in the image | P0.9, P5.6 | P0.9:✅ P5.6:⬜ |
| BUG-35 | in_progress | Container image cannot build: Dockerfile `lint:tokens` gate fails on raw colours | P4.9, P5.6 | P4.9:✅ P5.6:⬜ |

## 7. Recent step commits

| Commit | Date | Message |
|---|---|---|
| `9884eb6` | 2026-10-24 | P5.1–P5.3: One Brain & Fast-Path Dispositions, Voice Verbatim & Hindi/Hinglish Narration, Deterministic Coverage Manifest (SPEC-11 |
| `ed631b2` | 2026-10-24 | P2H.1–P2H.4 G4 reviews: all 4 V19 + RBAC steps approved |
| `901464f` | 2026-10-24 | P2H.4 (G4 r1 fixes): resolve P2H4-B1..B4 |
| `4a7844b` | 2026-10-24 | P3.1 (pre-G4): Answer contract v3 consolidation (proposed_action, job, provenance, dcf_model, 11 personas, contract_version 3, 23/ |
| `a1a5952` | 2026-10-24 | P3.4 (G4 r2 fixes + G4 approval): full DCFResult, SSOT line codes, 8-driver tornado, WACC & SOTP holdco discount |
| `1c1ee11` | 2026-10-24 | P3.4 (pre-G4): DCF engine core (assumptions, inputs, wacc, fcff, valuation, sensitivity, run) + P3.2 G4 review |
| `7effbaf` | 2026-10-24 | P3.2 (pre-G4): Jobs API, in-process asyncio executor, Firestore/in-memory store, SSE & RBAC double-check |
| `979b3d1` | 2026-10-24 | P2F.3 (pre-G4): WACC metrics, chart routing, and 5-factor Shapley attribution (SPEC-02 §5, 21/21 tests) |
| `73274fb` | 2026-10-24 | P2H.4 (pre-G4): V19 turns 4-5 export intent + columns + xlsx link, email_draft agent + EmailDraftRenderer, delete canned proposal  |
| `aba36a5` | 2026-10-24 | P1.6 (pre-G4): Add P1.6_evidence.md for verified SSOT load |
| `f9f6e29` | 2026-10-24 | P1.9 (G4 r1 fixes): resolve P19-B1..P19-B3 in build_wacc.py and inputs.py (9/9 tests) |
| `7b53be0` | 2026-10-24 | P2F.4 + P2F.6 (G4 r1 fixes) + P2F.1 frontend: resolve P2F4-B1..B3 & P2F6-B1..B3 (24/24 tests) and port ClarifySpec UI |
| `5ce3b16` | 2026-10-24 | P2F.1 + P2F.2: multi-year statement payload and BUG-42 fix |
| `0655f18` | 2026-10-24 | P2H.5 (pre-G4 r4): Fix objective scaling and remove residual pools, report gap |
| `6d645f2` | 2026-10-24 | P2F.6 (pre-G4): Top-5 action generator, safe AST expr evaluator, and delegation table (SPEC-08 §7, 12/12 tests) |

## 8. Integrity checks

- ⚠️ FEAT-018 is ✅ in the feature list but has unfinished steps: P1.1.

---
**How this stays current:** every step completion = (1) update the step's Status in `UPGRADE_CHECKLIST.md` (⬜ → 🔨 Built → 🔍 In review → ✅ Done only with a `docs/reviews/<step>.md` APPROVE), (2) close the linked bugs in `BUG_REGISTER.md`, (3) run `python3 scripts/progress/build_progress.py` (regenerate) and `--check` (validate), (4) commit all three files together. The optional git hook (`scripts/progress/install_hook.sh`) blocks commits when `--check` fails.
