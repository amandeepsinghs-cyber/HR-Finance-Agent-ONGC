# Yukti AI — HR & Finance Agent for ONGC (demo) · v0.1

Voice-first HR & Finance agent for ONGC leadership (CMD, Director (HR), Director (Finance), E1–E4 officers). Questions can be asked in English, Hindi or Hinglish, by voice or text. It answers in 2–4 sentences (Leda voice), shows a live chart, table or document on a canvas, can draft documents (board notes, Parliament replies, applications) and exports to Word, PDF and Excel. It refuses on a per-persona basis, citing the relevant policy.

> **Demo only.** All employee-level and financial detail is **synthetic** ("fully emergent" simulation calibrated to public ONGC facts, e.g. headcount 23,117 and revenue ₹1,32,508 cr in FY26). Rulebooks are marked *DEMO RECONSTRUCTION — not an official ONGC document*. Board personas are role-only; no real individuals are represented.

## Repository layout
| Path | What |
|---|---|
| `verbatims/` | User requirements (verbatim) |
| `docs/` | Question bank, data requirements, **UX spec** (`ux_spec.md`), gate reviews, **`TODO_BACKLOG.md`** (deferred work) |
| `data_bank/world_bible/` | Locked reference world: schema, calibration targets, questions (89 + 267 follow-ups) |
| `data_bank/generators/` | Synthetic data generators (HR, ops, finance, governance, documents, gaps) |
| `data_bank/medallion/` | GCS upload, Bronze loader, Dataform Silver/Gold, document pipeline (Document AI OCR → chunks → Vertex AI Search) |
| `data_bank/answer_key/` | Verified SQL, expected results and narratives for all 356 entries, plus the semantic audit (`AUDIT_SEMANTIC_2026-10-20.md`) |
| `data_bank/verify/`, `data_bank/tests/` | Independent verification harness and tests |
| `yukti/contracts/` | Agent→UI answer contract (JSON Schema) |
| `yukti/backend/` | FastAPI + Google ADK agent (Gemini Live `gemini-3.8-live`, voice Leda; text `gemini-2.5-flash`), tools: query_data, search_policy, what_if, draft_document, export, access_check; eval harness |
| `yukti/frontend/` | Next.js + Tailwind + Framer Motion + ECharts UI (AlphaEvolve-style particle orb, floating chat, canvas, Survey of India map) |
| `spikes/voice_chart_spike/` | Early voice→chart latency spike |

## GCP (project `ongc-hr-finance-agent`)
BigQuery `hrfin_bronze/silver/gold/docs` (asia-south1), GCS `gs://ongc-hr-finance-agent-landing` and `-docs`, Document AI OCR (asia-south1), Vertex AI Search `hrfin-doc-search-engine` (global), and Gemini on Vertex AI (us-central1/global).

## Run locally
```bash
# backend
cd yukti/backend && uv sync && PORT=8095 uv run python run.py
# frontend
cd yukti/frontend && npm install && npm run dev   # http://localhost:3000  (?mock=1 for offline fixtures, ?debug=1 for latency overlay)
```
Requires `gcloud auth application-default login` with access to the project.

## Not in git (heavy or regenerable)
- `data_bank/landing/**` data files (~750 MB): regenerate with `data_bank/generators/*` in the order of `data_bank/DATA_GENERATION_CHECKLIST.md`, or copy from `gs://ongc-hr-finance-agent-landing/`.
- `knowledge/public_sources/**/raw/` PDFs: re-download using the links in `knowledge/public_sources/policies/MANIFEST.md` and `grounding_data/FACTS.md`.
- Local DuckDB files, `node_modules`, `.venv`, `.next`, and exports.

## Status (v0.1)
- Data bank, medallion pipeline, answer key (re-audited), UI and live agent integration: working end-to-end.
- Agent accuracy (cache OFF, `yukti/backend/eval/report.md`): **35% overall** (roots 55%, follow-ups 22%, paraphrases 37%, held-out 44%). Improvement in progress.
- Deferred: data repair sprint, RBAC and Cloud Run deployment (see `docs/TODO_BACKLOG.md`).
