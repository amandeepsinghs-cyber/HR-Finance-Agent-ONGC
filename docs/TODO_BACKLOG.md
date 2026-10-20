# Yukti AI — Deferred Backlog

Owner: lead. Status legend: ⏸ deferred · ▶ active · ✅ done.
Order agreed with user (2026-10-20): **finish and finalise the front end (working end-to-end with the agent) first → then data repair → then access control (RBAC) → deployment.**

---

## ⏸ DR — Data Repair Sprint (start ONLY after the front end is built, finalised and functional)

Decision (user, 2026-10-20 07:29): defer. Current data stays as-is for front-end work; answer key is frozen and consistent with it.

### Why
The semantic audit (answer_key/AUDIT_SEMANTIC_2026-10-20.md, auditor `ee3ffc4e-1366-47ae-9683-f25a82a4f930`) found data defects. They are internally consistent (agent, answer key and UI agree), but some are implausible to a careful reviewer.

### Defects to fix (priority order)
| # | Defect | Root cause / where | Fix instruction |
|---|---|---|---|
| DR-1 | 9,236 of 13,453 current executive stays (69%) start on **2020-07-01**; 350 of 419 Delhi C1 cases. Max stay ≈ 8.4 years, so P11 (10-year cap) = 0. | `data_bank/generators/hr/gen_21_hr_core.py` ~L1562–1660: annual wcs are simulated only for 31-Mar-2021…2026; the first segment opens on 1-Jul-(start_yr−1); back-filled earlier stints end 30-Jun-2020 at a different wc, so everyone moves at once. | Rewrite mobility as a forward career simulation from DOJ (stint-length hazard by wc type/grade/cadre; min ~3y, rising hazard 3–5y; cluster cumulative cap 10y; exemption within 3y of superannuation; staggered transfer dates around the AGT season, not one date). Tests: no single date > 5% of current stay starts; median exec stint 3–5y; some execs with cluster cumulative ≥ 10y exist (emergent). Blind generator per DELEGATION_PLAYBOOK. |
| DR-2 | project_progress: every project overruns exactly 15%; project value repeated on all 6 milestone rows. | gen 2.4 (finance) | Overrun emerges from a class-based distribution (project type, complexity, contractor class); value stored once (project grain), milestones carry their own % only. |
| DR-3 | receivables: only FY26 invoices carry balances; FY27 invoices (future-dated) are fully paid; FY22–25 billing ≠ revenue. | gen 2.4 | Invoice stream FY22→Sep-2026 tied to revenue by customer; payment-delay hazard; balances at each FY end; nothing dated after 2026-10-19. |
| DR-4 | capex_budget FY17–24 doesn't reconcile with corporate_financials; FY22 PAT > PBT. | gen 2.4 / 2.5 | Reconcile to calibration_targets; tax ≥ 0. |
| DR-5 | Implausible ratios: ROCE 42–89%; offshore allowance 160% of basic; PRBS assets equal liability to the rupee every year. | gen 2.2 / 2.5 | Bound via PARAMS; funded status emerges. |
| DR-6 | mart_employee_relations POSH counts inflated by fan-out (FY22: 26 vs 8). | Dataform gold SQLX | Aggregate posh_cases at case grain before joining. |
| DR-7 | Literal string 'None' in exemption_tag / exemption_reason_code. | gen 2.1 output / silver casts | Emit NULL; silver NULLIF(x,'None'). |
| DR-8 | 100% NULL medical_claims.turnaround_days, rti_applications.turnaround_days; DPC benchmark constant 85; one placeholder ICC presiding officer. | gen 2.2 / 2.5 | Generate from processes. |
| DR-9 | headcount_snapshot only March for FY13–21 (12 months for FY22+); mart_asset_productivity.regular_headcount = 0 FY17–21, 18,033 FY26. | design + gold | Keep the design, but document it in glossary/semantic layer; fix the mart to use period-end snapshot. |
| DR-10 | silver_chunks: header/glossary false keyword hits; P1-01 mis-chunked; questions_served routes D6 to confidential docs. | docs pipeline 4.5 | Re-chunk; strip boilerplate; fix routing metadata. |
| DR-11 | Reconstructed rulebook text contains technical jargon (e.g. JRTP 4.2 'historical postings (SCD2 records)'). | step 3.1 rulebooks | Rewrite clause text in formal HR-policy language; no data-engineering terms; re-render DOCX/PDF/scans; re-OCR + re-chunk. |

### Cascade (after the DR-1…DR-8 generator fixes)
1. Regenerate 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → gap sprint (RNG isolation) → documents 3.2/3.3/3.6 (orders are rendered from postings) → 3.4 MIS → Excel mess post-processor (last).
2. Re-upload landing to GCS (new batch_date), Bronze, Dataform Silver/Gold, docs OCR/chunks/Vertex AI Search re-import (~$2–5).
3. `cd data_bank/answer_key && uv run python -m semantic_audit.run_entry <all ids> && uv run python -m semantic_audit.sanity_checks && uv run python -m semantic_audit.finalize && uv run pytest tests/test_51_53_answer_key.py` (guard: never run build_answer_key.py without `--force-overwrite-semantic-audit`).
4. Refresh the materialized tables: `yukti/backend/scripts/refresh_materialized.sh` + reconciliation test.
5. `yukti/frontend`: `python3 scripts/build_fixtures.py && python3 scripts/check_fixtures.py`; remove caveat chips that no longer apply.
6. Re-run the agent eval (cache OFF) and the 150-prompt stress test; independent verifier checks.
7. Lead re-baselines world_bible manifest only if schema changes; update LEAD_NOTES.

### Interim handling (until DR is done)
- UI shows amber caveat chips on tenure/rotation answers (C1, H10, …). Decide before the demo whether to hide chips in "presentation mode" (lead recommends: hide on canvas, keep in the source card).
- Agent must never invent arrival dates; if asked "when did they arrive", answer from data as-is.

---

## ⏸ RBAC — Access control (after DR)
BigQuery row/column security or authorized views per persona; document ACLs from DOC_MANIFEST `audience_roles`; replace the access_check hook's static matrix with policy-driven checks.

## ⏸ DEPLOY — Cloud Run + demo rehearsal (after RBAC)
- Cloud Run in asia-south1 (next to BigQuery/GCS), `--min-instances=1` (no cold starts mid-demo), small max instances, WebSocket support (request timeout ≥ 3600 s, session affinity on).
- Demo: in-memory result cache + run `scripts/warmup.py` before the session.
- Production/pilot (many users / several instances): add **Memorystore (Redis)** for a shared result cache + conversation/session memory (needs Serverless VPC Access / Direct VPC egress; ~US$40–50/month for the smallest Mumbai instance — confirm current pricing).
- Gemini Live has no India region (us-central1); BigQuery/GCS/Document AI stay in asia-south1.
