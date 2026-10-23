# v3 Packet Index: P0 (Stabilise), P2H.1–P2H.4 (Personas + V19), P4 (Visual & Export)

**Author:** O · **Date:** 2026-10-23 · **Base:** branch `wip/pre-v3-snapshot` @ `e7de82f` (O re-stamps Base SHA at delegation time) · Template: [`TASK_PACKET_TEMPLATE.md`](../../TASK_PACKET_TEMPLATE.md) · Rules: [`DELEGATION.md`](../../../../DELEGATION.md) §3 · Other v3 packets: P1/P2F/P3 in [`_INDEX_P1_P2F_P3.md`](_INDEX_P1_P2F_P3.md), P2H.5–P2H.8 in [`_INDEX_P2H5-8.md`](_INDEX_P2H5-8.md); P5 packets are written at P5 start. **Total: 51 packets** (20 + 27 + 4).

> **BLUF.** 20 steps. Security/RBAC/contract cores stay with Opus (`O`); Flash (`F`) builds renderers, intents, writers and tests from fixed fixtures; Flash-lite (`FL`) produces the baseline evidence. Order: P0 (all) → P2H.1 → P2H.2/P2H.3 → P2H.4; P4.1 can start right after P0; P4.2/P4.3 need SPEC-01 verified lines for final acceptance but can build on the labelled synthetic fixture.

| Step | Title | Owner | Features | Spec | Bugs | Depends on | Packet |
|---|---|---|---|---|---|---|---|
| P0.1 | ADC restore, `/health.auth_ok`, auth banner, safe error copy | `O + S` → `F` | FEAT-032 | SPEC-11, BEH-07 | BUG-01, BUG-33 | sponsor re-auth | [P0.1](P0.1.md) |
| P0.2 | Fix `resolve_fy("FY 2024-25")` regression | `F` | FEAT-030 | SPEC-11 | BUG-20 | — | [P0.2](P0.2.md) |
| P0.3 | Remove false "Audited/Yahoo/Compiled SQL" labels; explicit `local_snapshot` | `F` | FEAT-032 | SPEC-11 | BUG-02 (labels), BUG-04 | — | [P0.3](P0.3.md) |
| P0.4 | Server-side persona token; block role switching; audit | `O` | FEAT-031 | SPEC-06 §4.4 | BUG-06 | — | [P0.4](P0.4.md) |
| P0.5 | CORS allow-list + admin route lock | `O→F` | FEAT-031 | SPEC-06 §4.7 | BUG-32 | P0.4 (admin claim) | [P0.5](P0.5.md) |
| P0.6 | True test baseline + evidence pack | `FL` | FEAT-014 | BUILD G3 | — | P0.1 | [P0.6](P0.6.md) |
| P0.7 | "Illustrative" labels on synthetic clauses (JRTP Rev 4, R16) | `F` | FEAT-032 | SPEC-07 §4.2, SPEC-11 | BUG-31 | — | [P0.7](P0.7.md) |
| P2H.1 | 11 personas + `dim_app_user` + function dimension + `self` scope + `@self_emp_id` + aggregate pay | `O` (tests `F`) | FEAT-017, FEAT-031 | SPEC-06 | BUG-07, BUG-27, BUG-28 | P0.4 | [P2H.1](P2H.1.md) |
| P2H.2 | Persona picker, `/api/auth/me` banner, refusal UX copy EN/HI | `O→F` | FEAT-017 | SPEC-06 §4.4, §4.6 | BUG-06 (UI) | P2H.1 | [P2H.2](P2H.2.md) |
| P2H.3 | V19 turns 1–3: ordered levels, `DELHI_GT5_CONT_V1`, roster columns, cohort store | `O→F` | FEAT-023 | SPEC-07 §4.1–4.3, §4.6 | BUG-34 | P2H.1 | [P2H.3](P2H.3.md) |
| P2H.4 | V19 turns 4–5: export intent + columns + xlsx link; email agent (.eml/.docx/mailto); delete canned proposal | `O→F` | FEAT-023, FEAT-027 | SPEC-07 §4.4–4.5, SPEC-10 §4.1, §4.6 | BUG-10, BUG-11, BUG-12 | P2H.3 | [P2H.4](P2H.4.md) |
| P4.1 | Signed bridge helper (py+ts), re-plot fix, no EBITDA fabrication, explicit-kind precedence, false-success | `O→F` | FEAT-026 | SPEC-09 §4.3–4.4 | BUG-08, BUG-09, BUG-22 | P0 | [P4.1](P4.1.md) |
| P4.2 | `visual.type=statement` contract + presenter emit (multi-FY) | `O` | FEAT-025 | SPEC-09 §4.1 | — | P4.1; SPEC-01 for final data | [P4.2](P4.2.md) |
| P4.3 | `StatementTable` renderer | `F` | FEAT-025 | SPEC-09 §4.2 | — | P4.2 | [P4.3](P4.3.md) |
| P4.4 | Portfolio batch A: combo dual-axis, 100% stacked, heatmap, box, gauge, scatter fix; compat matrix | `F` | FEAT-026 | SPEC-09 §4.5–4.6 | BUG-23 | P4.1 | [P4.4](P4.4.md) |
| P4.5 | Portfolio batch B: sensitivity grid, tornado, bubble, sunburst, sankey, India choropleth, `dcf_model`/`actions` composites | `F` | FEAT-026 | SPEC-09 §4.5, §5 | — | P4.4 | [P4.5](P4.5.md) |
| P4.6 | Export backend: xlsx formats, CSV, PDF (WeasyPrint + Noto), docx, honest Sheets/Docs, audit, naming | `O→F` | FEAT-027 | SPEC-10 | BUG-24, BUG-25 | P2H.4 (artifact shape) | [P4.6](P4.6.md) |
| P4.7 | Export frontend: menu, PNG/SVG, intents for all formats EN/HI, toasts | `F` | FEAT-027 | SPEC-10 §4.4, §4.7–4.8 | BUG-25 (UI) | P4.6 | [P4.7](P4.7.md) |
| P4.8 | Finance rubric F1–F14 + scorecards | `F→O` | FEAT-025, FEAT-026 | SPEC-09 §4.7 | — | P4.3–P4.5 | [P4.8](P4.8.md) |
| P4.9 | Orb visible in docked mode + optional edge aura (low priority) | `F` | FEAT-004, FEAT-016 (V21 low) | SPEC-09 §4.9 | — | — | [P4.9](P4.9.md) |

**Universal rules for every packet** (repeated in each §4): no `git commit/push/reset/checkout/stash`, no deploys, no `bq` DDL/DML, no destructive commands; leave changes uncommitted; stop and ask on ambiguity, out-of-scope files or two failed self-checks. Every step gets an R-O review (`docs/reviews/<step>.md`).
