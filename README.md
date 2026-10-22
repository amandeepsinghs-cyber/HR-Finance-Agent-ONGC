# Yukti AI — Voice-First HR & Finance Agent for ONGC Leadership · v1.0 (`upgrade-H1`)

Voice-first HR & Finance executive agent for ONGC leadership (**CMD**, **Director (HR)**, **Director (Finance)**) and officers (**E1–E4**). Questions can be asked in English, Hindi, or Hinglish by voice or text. Yukti responds in 2–4 grounded sentences (Leda voice), renders interactive visualizations in a scrollable conversation feed (`AnswerCard` v2), supports instant any-chart re-presentation (`< 300 ms`), drills down from aggregate metrics to actionable employee rosters, drafts formal documents (Board notes, Transfer proposals, Parliament replies), and exports to Word (`.docx`), PDF (`.pdf`), Excel (`.xlsx`), Google Docs, and Google Sheets. Role-based access control (`rbac_policy.yaml`) is enforced pre- and post-query with small-cell suppression (`< 5`).

> **Demo only.** All employee-level and financial detail is **synthetic** ("fully emergent" simulation calibrated to public ONGC facts, e.g. headcount 23,117 and revenue ₹1,32,508 Cr in FY26). Rulebooks are marked *DEMO RECONSTRUCTION — not an official ONGC document*. Board personas are role-only; no real individuals are represented.

---

## Repository Layout

| Path | What |
|---|---|
| `BUILD.md` | Build charter, 5-gate governance (`G1`–`G5`), architecture, and quality metrics |
| `UPGRADE_CHECKLIST.md` | Step-by-step upgrade checklist (`U0`–`U5`, `B1`–`B4`, `H1`) with links to G3 evidence and G4 reviews |
| `DELEGATION.md` | Multi-agent delegation protocol (`Opus` / `Flash` / `Flash-lite`) and task packets (`docs/delegation/packets/`) |
| `docs/DECISIONS.md` | Complete decision log (`D-1` … `D-33`) |
| `docs/demo_script.md` | End-to-end executive demo script (Voice orb, 7-turn HR chain, Any-chart re-plot, 5-turn Finance chain, RBAC) |
| `docs/reviews/` | Independent G4 review reports and rubric scorecards (`U0.2` through `H1`) |
| `feature_list_and_verbatims/` | Feature specification (`FEAT-001` … `FEAT-016`) and sponsor verbatims (`V1` … `V16`) |
| `data_bank/` | Locked reference world, synthetic generators, medallion pipeline, and 356-entry verified answer key |
| `yukti/contracts/` | Agent ↔ UI Answer Contract v2 JSON Schema (`answer_contract.schema.json`) |
| `yukti/backend/` | FastAPI + Google ADK + QuerySpec brain (`app/brain/`: planner, compiler, RBAC, insights, drilldowns, narrator) + Gemini Live (`gemini-3.8-live`, voice Leda) + BigQuery semantic layer (`app/semantic/`) |
| `yukti/frontend/` | Next.js + Tailwind + ECharts UI (`src/design/` tokens, `primitives.tsx`, `VoiceOrb.tsx` borderless Aurora wave, `ConversationFeed.tsx`, `AnswerCard.tsx`, `RosterTable.tsx`, `CompareRenderer.tsx`, `src/charts/compat.ts`) |

---

## GCP Architecture (Project `ongc-hr-finance-agent`)

- **BigQuery (`asia-south1`):** `hrfin_bronze`, `hrfin_silver`, `hrfin_gold` (`ssot_workforce_employee`, `ssot_work_centre_360`, `ssot_field_economics_360`, `ssot_corporate_annual_360`), `hrfin_docs`
- **Cloud Storage:** `gs://ongc-hr-finance-agent-landing` and `gs://ongc-hr-finance-agent-docs`
- **Vertex AI Search (`global`):** `hrfin-doc-search-engine`
- **Gemini on Vertex AI:** `gemini-2.5-flash` (structured-output QuerySpec planner & ADK text runner), `gemini-3.8-live` (bi-directional voice with Leda voice & server/client barge-in)

---

## Run Locally

Requires `gcloud auth application-default login` with access to `ongc-hr-finance-agent`.

```bash
# 1. Start Backend (FastAPI + QuerySpec Planner on :8095)
cd yukti/backend
YUKTI_PLANNER=1 GOOGLE_CLOUD_PROJECT=ongc-hr-finance-agent GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8095

# 2. Start Frontend Single-Origin Server (Next.js + HTTP/WS Proxy on :3300)
cd yukti/frontend
npm install && npm run build
NODE_ENV=production PORT=3300 HOST=0.0.0.0 YUKTI_BACKEND_URL=http://127.0.0.1:8095 node server.js
```

Open [http://localhost:3300](http://localhost:3300) (or [http://localhost:3300/design-system](http://localhost:3300/design-system) for the design system & chart showcase).

---

## Verification & Quality Summary (`v1.0` / `upgrade-H1`)

- **UI & Visual System (`U1`–`U5`):**
  - Tokenised design system (`0` hardcoded hex in components; `58/58` WCAG contrast pairs pass in Light & Dark).
  - Borderless **Aurora wave** voice orb (`D-29`) verified at `60 fps` at 1440p and 4K.
  - Scrollable conversation feed (`AnswerCard` v2), virtualised `RosterTable` (`60 fps` on 2,000 rows), `CompareRenderer`, and `20/20` chart gallery views scoring `≥ 4/5` on all 8 rubric criteria (`C1`–`C8`).
- **Brain, Governance & Hardening (`B1`–`B4`, `H1`):**
  - 86-table profiled `semantic_catalog.json` + unified entity dictionary (`0` catalog/data mismatches).
  - Structured-output `QuerySpec` planner + deterministic SQL compiler (`37/37` golden specs, `100%` BigQuery dry-run, flagship 7-turn HR chain `7/7`, flagship 5-turn Finance chain `5/5`).
  - Granular RBAC (`25/25` persona × data-class matrix cells pass, `120/120` gate refusal governance, `< 5` small-cell suppression).
  - Deterministic insight engine & grounded narrator (`0` ungrounded numbers across all 120 gate turns).
  - Gate accuracy (`cache OFF`, `YUKTI_PLANNER=1`): **87.5% lenient (`105/120`) / 71.7% strict (`86/120`)**, up from **35.0%** pre-fix baseline (`52.5%` strict at `U0`), with median latency reduced from `14.6 s` (`U0`) to **`2.9 s`** (`H1`).
