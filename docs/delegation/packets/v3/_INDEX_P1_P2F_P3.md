# v3 Packet Index: P1 (Real Finance SSOT), P2F (V20 diagnostics), P3 (Coordinator, jobs, DCF)

**Author:** O · **Date:** 2026-10-23 · **Base:** `wip/pre-v3-snapshot` @ `e7de82f` (O re-stamps the Base SHA at delegation) · Template: [`TASK_PACKET_TEMPLATE.md`](../../TASK_PACKET_TEMPLATE.md) · Rules: [`DELEGATION.md`](../../../../DELEGATION.md) §3 · Step IDs follow [`UPGRADE_CHECKLIST.md`](../../../../UPGRADE_CHECKLIST.md). P2H.5–P2H.8 are indexed in [`_INDEX_P2H5-8.md`](_INDEX_P2H5-8.md); P0/P2H.1–4/P4 in [`_INDEX_P0_P2H1-4_P4.md`](_INDEX_P0_P2H1-4_P4.md). **Total: 51 packets.** An `a`/`b` suffix means one checklist row split into an O part and an F part.

> **BLUF.** 27 packets. Schema, contract, RBAC, BigQuery writes, planner/compiler and voice stay with Opus (`O`). Flash (`F`) builds the deterministic extractors, gate library, variance engine, DCF engine, xlsx writer and UI cards from fixed fixtures taken from real AR pages. Flash-lite (`FL`) runs evidence. Critical path: P1.2 → P1.3 → P1.6 → P1.10a → P2F → P3. Yahoo (P1.5) is **off** the critical path (HTTP 429). WACC (P1.9) needs the manual RBI seed CSV.

| Step | Title | Owner | Spec | Depends on | Packet |
|---|---|---|---|---|---|
| P1.2 | AR 10-yr table parser (FY13–FY26) | F | SPEC-01 §4.2 | — | [P1.2](P1.2_ar_10yr_table_parser.md) |
| P1.3 | Full statements + notes (S + C) | F (+O Gemini fallback) | SPEC-01 §4.3 | P1.2 | [P1.3](P1.3_ar_full_statement_extraction.md) |
| P1.4 | NSE XBRL parser | F | SPEC-01 §4.4 | P1.2 | [P1.4](P1.4_xbrl_parser.md) |
| P1.5 | Yahoo loader + market provider chain (optional, retryable) | F | SPEC-01 §9.1 | P1.2 | [P1.5](P1.5_yahoo_loader.md) |
| P1.6 | Mapping, gates V01–V12, gold + snapshot, BQ load | O (+F gates, FL evidence) | SPEC-01 §5–§6 | P1.2–P1.4 | [P1.6](P1.6_fact_tables_bq_load_and_gates.md) |
| P1.7 | Anchor tables (segment, production, reserves, HR aggregates, realisation) | O→F | SPEC-01 §10 | P1.3 | [P1.7](P1.7_anchor_tables.md) |
| P1.8 | AR text chunks + embeddings + VECTOR_SEARCH | F chunker / O load + retriever | SPEC-01 §8 | — | [P1.8](P1.8_ar_text_chunks_vector.md) |
| P1.9 | WACC inputs + `fact_wacc_annual` | F (+O load, human RBI seed) | SPEC-02 §3 | P1.3, P1.5, P1.6 | [P1.9](P1.9_wacc_inputs.md) |
| P1.10a | Compiler on verified rows + honest provenance | O | SPEC-01 §7 | P1.6 | [P1.10a](P1.10a_compiler_switch_verified_rows.md) |
| P1.10b | Retire LLM-authored artefacts | F | SPEC-01 §11 | P1.10a | [P1.10b](P1.10b_retire_legacy_financials.md) |
| P1.11 | Finance golden set (P1 gate) + V20 chain (P2F gate) | F + FL | SPEC-11 §8 | P1.10a | [P1.11](P1.11_finance_golden_set_and_v20_chain.md) |
| P2F.1 | Year clarification (chips + voice) | O | SPEC-08 §3 | P1, P0.2 | [P2F.1](P2F.1_year_clarification.md) |
| P2F.2 | Multi-year statement payload | O | SPEC-08 §4 | P1.10a | [P2F.2](P2F.2_multiyear_statement.md) |
| P2F.3 | WACC metric + chart + Shapley | O (Shapley → F optional) | SPEC-02 §5 | P1.9 | [P2F.3](P2F.3_wacc_metric_chart.md) |
| P2F.4 | Variance-attribution engine | F | SPEC-08 §6.1 | P1 | [P2F.4](P2F.4_variance_attribution_engine.md) |
| P2F.5 | Grounded "why" + non-circular grounding | O | SPEC-08 §6.2–6.3 | P1.8, P2F.4 | [P2F.5](P2F.5_grounded_why.md) |
| P2F.6 | Top-5 actions + delegation table | O→F | SPEC-08 §7 | P2F.4 | [P2F.6](P2F.6_top5_action_generator.md) |
| P3.1 | Contract v3 consolidation + `contract_version` bump (SPEC-03 §5.1 ledger) | O | SPEC-03 §5 | ledger rows from P2F.1, P2F.6, P2H.4, P4.2 | [P3.1](P3.1_contract_v3.md) |
| P3.2 | Jobs API + executor + Firestore + SSE | O | SPEC-03 §7 | P3.1 | [P3.2](P3.2_jobs_api_executor.md) |
| P3.3 | Coordinator + router + registry | O | SPEC-03 §3–4 | P3.1, P3.2 | [P3.3](P3.3_coordinator_registry.md) |
| P3.4 | DCF engine core | F (O reviews API first) | SPEC-02 §6–8 | P1, P1.9 | [P3.4](P3.4_dcf_engine_core.md) |
| P3.4b | dcf_agent wiring + result contract | O | SPEC-03 §7.3–7.4 | P3.2–P3.5 | [P3.4b](P3.4b_dcf_agent_wiring.md) |
| P3.5 | DCF xlsx with live formulas | F (+FL parity) | SPEC-02 §9.2 | P3.4 | [P3.5](P3.5_dcf_xlsx_live_formulas.md) |
| P3.6a | Permission UX frontend | F | SPEC-03 §6 | P3.1, P3.2 | [P3.6a](P3.6a_permission_ux_frontend.md) |
| P3.6b | Voice confirm + completion announcement | O | SPEC-03 §6.2, §9 | P3.3, P3.4b | [P3.6b](P3.6b_voice_confirm_and_announce.md) |
| P3.7 | Wrap specialist agents | O→F | SPEC-03 §4 | P3.3, P2F, P2H.4 | [P3.7](P3.7_wrap_specialist_agents.md) |
| P3.8 | V22 golden chain + E2E evidence | F + FL | SPEC-11 §8.4 | P3.1–P3.7 | [P3.8](P3.8_v22_golden_chain_e2e.md) |

**Universal rules** (repeated in each packet §4): no `git commit/push/reset/checkout/stash`, no deploys, no `bq` DDL/DML by F/FL, no destructive commands; stop and ask on ambiguity, out-of-scope files or two failed self-checks. Every step gets an R-O review (`docs/reviews/<step>.md`).
