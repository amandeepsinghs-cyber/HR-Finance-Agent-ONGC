# v3 Packet Index: P2H.5–P2H.8 (Employee-360, Field Economics, Reconciliation)

**Author:** O · **Date:** 2026-10-23 · **Base:** `wip/pre-v3-snapshot` @ `e7de82f` (O re-stamps the Base SHA at delegation) · Template: [`TASK_PACKET_TEMPLATE.md`](../../TASK_PACKET_TEMPLATE.md) · Rules: [`DELEGATION.md`](../../../../DELEGATION.md) §3 · Step IDs follow [`UPGRADE_CHECKLIST.md`](../../../../UPGRADE_CHECKLIST.md) · Other indexes: [`_INDEX_P0_P2H1-4_P4.md`](_INDEX_P0_P2H1-4_P4.md) (20), [`_INDEX_P1_P2F_P3.md`](_INDEX_P1_P2F_P3.md) (27).

> **BLUF.** 4 packets (total across the three indexes: **51 packets**). Generator calibration, allocation maths and reconciliation rules/SQL stay with Opus (`O`); Flash (`F`) does Dataform wiring and tests. Order: P2H.5 → P2H.6 → P2H.7 → P2H.8, strictly sequential (each Base SHA is the previous step's G4-approved tip). Reconciliation (`recon_checks`) blocks publication (D-40).

| Step | Title | Owner | Features | Spec | Bugs | Depends on | Packet |
|---|---|---|---|---|---|---|---|
| P2H.5 | Employee-360 generator regeneration (realistic pyramid, names, pay + benefits + insurance + CTC, calibrated to AR/BRSR) | `O` (unit tests may go to `F`) | FEAT-021 | SPEC-04 §5–§7 | BUG-26, BUG-29, BUG-30 | P0; P2H.1 (persona/`self` scope) | [P2H.5](P2H.5_employee360_generator.md) |
| P2H.6 | Employee-360 Dataform build, semantic model (pay components, KPIs, entry pay), certified queries | `O→F` (O: certified SQL + KPI SQL; F: Dataform wiring, YAML, tests) | FEAT-021, FEAT-008 | SPEC-04 §3, §4, §8, §9; BEH-06 | BUG-26 | P2H.5 | [P2H.6](P2H.6_employee360_dataform.md) |
| P2H.7 | Field Economics-360: production recalibration, RAS allocation engine, Dataform | `O` (F may do Dataform files after the engine is approved) | FEAT-022 | SPEC-05 | — | P2H.6 | [P2H.7](P2H.7_field_economics_recon.md) |
| P2H.8 | Reconciliation gates: `recon_checks` (30 EMP-R + 17 FLD-R), BLOCK assertion, offline tests, golden eval | `O→F` (O: recon rules/SQL + assertion; F: tests, fixtures, golden YAML) | FEAT-021, FEAT-022, FEAT-030 | SPEC-04 §7, SPEC-05 §7 | — | P2H.7 | [P2H.8](P2H.8_reconciliation_tests.md) |

**Universal rules** (repeated in each packet §4): no `git commit/push/reset/checkout/stash`, no deploys, no `bq` DDL/DML by F/FL, no destructive commands; stop and ask on ambiguity, out-of-scope files or two failed self-checks. Every step gets an R-O review (`docs/reviews/<step>.md`).
