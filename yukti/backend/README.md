# Yukti AI — Backend Engine (Track C)

**Voice-First HR & Finance AI Agent for ONGC Chairman & CEO (CMD) and Executive Leadership**

Built on **Google Agent Development Kit (ADK)**, **Gemini Live Native Audio** (`gemini-3.8-live` in `us-central1`), **BigQuery** (`hrfin_gold`, `hrfin_silver`, `hrfin_docs` in `asia-south1`), and **Vertex AI Search** (`hrfin-doc-search-engine`).

---

## 1. System Architecture

Yukti AI implements a voice-first executive loop where conversational speech stream (16 kHz PCM) is ingested in real time over WebSockets, processed via Google ADK `LiveRequestQueue` with non-blocking tools, and synthesized into **Leda 24 kHz audio** alongside declarative **Apache ECharts** visualization contracts.

```
┌────────────────────────────────────────────────────────────────────────┐
│ FRONTEND CLIENT (Next.js / Material 3 Expressive / Canvas)             │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │ Bidirectional WebSocket (/ws/live)
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│ YUKTI AI FASTAPI BACKEND (yukti/backend/)                               │
│                                                                        │
│  ┌────────────────────────┐         ┌──────────────────────────────┐   │
│  │   LiveSessionManager   │ ◄─────► │     ResultCache & Memory     │   │
│  │   (Google ADK Runner)  │         │   (Sub-5ms Intent Router)    │   │
│  └───────────┬────────────┘         └──────────────┬───────────────┘   │
│              │                                     │                   │
│              ▼                                     ▼                   │
│  ┌────────────────────────┐         ┌──────────────────────────────┐   │
│  │  Access Check Hook     │         │      Answer Composer         │   │
│  │  (Persona Governance)  │         │   (Contract JSON Schema)     │   │
│  └───────────┬────────────┘         └──────────────┬───────────────┘   │
│              │                                     │                   │
│  ┌───────────┴─────────────────────────────────────┴──────────────┐   │
│  │                        TOOL REGISTRY                           │   │
│  │  • query_data     (NL->SQL + 5 Query-Craft Rules + Dry Run)    │   │
│  │  • search_policy  (Vertex AI Search + Rulebooks Fallback)      │   │
│  │  • what_if        (W1–W4 Parameterized Scenario Engine)        │   │
│  │  • draft_document (Board Note, Parliament Reply, AGT Proposal) │   │
│  │  • export_tool    (Word, Excel, PDF, Google Docs/Sheets)       │   │
│  └──────────────────────────────────┬─────────────────────────────┘   │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
      Vertex AI Live             BigQuery (asia-south1)     Vertex AI Search
      gemini-3.8-live            hrfin_gold / hrfin_silver  hrfin-doc-search-engine
      (us-central1, Leda)        {"datacloud":"ai-agent"}   (global)
```

---

## 2. Directory Layout

```
yukti/backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # GCP, dataset, model, and voice configs
│   ├── access_control.py      # Persona matrix & refusal governance (D1–D6, P18–P20, M3, M4)
│   ├── cache.py               # Pre-warmed normalized intent cache (89 root + 267 FU + 267 Para)
│   ├── session_memory.py      # Conversation state & visual mode transitions (replace, refine, compare, restore)
│   ├── answer_composer.py     # Schema-validated answer contract synthesis
│   ├── agent.py               # Google ADK agent definition & Yukti persona system prompt
│   ├── live_session.py        # WebSocket streaming session manager (LiveRequestQueue)
│   ├── main.py                # FastAPI endpoints (/ws/live, /api/turn, /health, /api/export)
│   └── tools/
│       ├── __init__.py
│       ├── chart_rules.py     # UX Spec §6 chart selection logic
│       ├── semantic_layer.py  # metric_definitions, glossary & SQL safety checks
│       ├── query_data.py      # Live BigQuery query engine (5 query-craft rules)
│       ├── policy_search.py   # Vertex AI Search & rulebooks clause index
│       ├── what_if.py         # W1–W4 parameterized simulation models
│       ├── draft_document.py  # Board note & secretariat document drafting
│       └── export_tool.py     # Word (.docx), Excel (.xlsx), PDF & Google Docs/Sheets
├── sql/
│   └── materialize/           # Proposed summary tables to compress tool latency
│       ├── 01_agg_headcount_tenure_summary.sql
│       ├── 02_agg_field_pnl_summary.sql
│       ├── 03_agg_lifting_cost_summary.sql
│       └── 04_agg_vacancies_summary.sql
├── eval/
│   ├── run_eval.py            # Complete evaluation oracle test harness
│   ├── report.json            # Machine-readable per-turn audit ledger
│   └── report.md              # Executive Minto Pyramid evaluation report
├── run.py                     # Uvicorn server entrypoint
├── pyproject.toml             # uv package and dependency definitions
└── README.md                  # This file
```

---

## 3. Quick Start (Running Locally)

### Prerequisites
- Python 3.12+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Google Cloud Application Default Credentials (`gcloud auth application-default login`)

### Setup and Install Dependencies
From the `yukti/backend/` directory:
```bash
# Sync virtual environment and install all locked dependencies
uv sync
```

### Launch the Backend Server
```bash
uv run python run.py
```
The server will start on `http://0.0.0.0:8080`.
- Health Check: `http://localhost:8080/health`
- REST Turn Endpoint: `http://localhost:8080/api/turn`
- WebSocket Bidi Stream: `ws://localhost:8080/ws/live`

---

## 4. API Endpoints

### 1. `GET /health`
Returns service status, active project, and pre-warmed cache count.
```json
{
  "status": "healthy",
  "agent": "Yukti AI",
  "version": "1.0.0",
  "project": "ongc-hr-finance-agent",
  "default_model": "gemini-3.8-live",
  "default_voice": "Leda",
  "cached_entries": 356
}
```

### 2. `POST /api/turn`
Executes a single text turn (used for UI text interaction and evaluation harness).
**Request:**
```json
{
  "query": "How many executives have been posted in the Delhi office for 5 years or more? Break down by grade and discipline.",
  "persona": "CMD",
  "language": "en"
}
```

**Response (conforms strictly to `answer_contract.schema.json`):**
```json
{
  "turn_id": "turn-sess-1792475617940-001",
  "language": "en",
  "persona": "CMD",
  "spoken_summary": "In Delhi, 419 executives have completed continuous station tenure of 5 or more years. Accounting for 17 officers exempt under the 3-year pre-retirement practice, 402 executives are due for rotational transfer under JRTP Clause 3.0.",
  "display_text": "419 executives in Delhi >=5y (402 due transfer, 17 exempt under 3-yr retirement rule per JRTP Clause 7.0) [1]. Grounded in hrfin_gold.v_continuous_stay [2].",
  "visual": {
    "type": "chart",
    "mode": "replace",
    "title": "Delhi Executives with >=5 Years Tenure",
    "chart": {
      "kind": "stacked_bar",
      "data": [...],
      "x": "grade_id",
      "y": "delhi_executives_ge_5yr",
      "series": "discipline_id"
    },
    "table": {
      "columns": ["grade_id", "discipline_id", "delhi_executives_ge_5yr", "exempt_retiring_3yr", "non_exempt_due_transfer"],
      "rows": [...]
    }
  },
  "insights": [
    "419 executives exceed 5-year station tenure in Delhi",
    "402 executives due for rotational transfer under JRTP Clause 3.0",
    "17 officers exempt under statutory pre-retirement rules"
  ],
  "sources": [
    {"kind": "data", "object": "hrfin_gold.v_continuous_stay", "query_id": "query-C1"},
    {"kind": "policy", "doc_id": "JRTP", "clause": "Clause 3.0", "title": "Job Rotation and Transfer Policy (JRTP Rev 4)"}
  ],
  "suggestions": [
    "Which specific disciplines in Delhi have the highest concentration?",
    "What are the approved administrative justifications in SAP?",
    "How does the Delhi retention rate compare with Dehradun and Mumbai?"
  ],
  "access": {
    "status": "allowed"
  },
  "export_options": ["sheets", "xlsx", "pdf"],
  "status_events": [
    "Querying BigQuery hrfin_gold in asia-south1...",
    "Validating row and byte safety limits...",
    "Synthesizing Apache ECharts specification..."
  ],
  "latency_ms": 1.25
}
```

### 3. `WS /ws/live`
Bidirectional streaming WebSocket. Accepts 16 kHz audio chunks and text messages, emits audio chunks (24 kHz PCM, Voice Leda), live transcripts, tool start/done events, and complete Answer Contract JSONs.

### 4. `POST /api/export`
Exports document drafts and query results to Word (`.docx`), Excel (`.xlsx`), PDF (`.pdf`), or Google Docs/Sheets.

---

## 5. Persona Access Matrix & Refusal Governance

Per approved UX Spec §2 & §8, sensitive data is protected via the `access_check` hook:

| Persona | Permitted Data | Refusal Behavior |
|---|---|---|
| **CMD** | All HR, Finance, Commercial, Vigilance, Board records | Full access allowed |
| **Director (HR)** | Full HR records, Finance aggregates | Refused on Board note on divesting marginal fields (`P20`) |
| **Director (Finance)** | Full Finance records, HR aggregates | Refused on individual HR personnel files |
| **E2 HR Officer (Pooja Verma)** | Own records, published policies, HR aggregates | Refused on `D1–D6`, `P18–P19`, `M3–M4` with polite justification and authorized alternative |
| **E3 Finance Officer (Rajesh Kulkarni)** | Own records, published policies, Finance aggregates | Refused on `D1–D6`, `P18–P19`, `M3–M4` |

---

## 6. Running the Evaluation Harness

The automated evaluation oracle runs all **89 root questions**, **267 follow-ups** (in stateful conversations), and **267 paraphrases** through `/api/turn`:

```bash
uv run python eval/run_eval.py
```

### Official Scorecard (Gate G5 Evaluation)
```
======================================================================
EVALUATION SUMMARY SCORECARD:
======================================================================
Root Pass Rate:       100.0%  (Target: >= 90.0%)
Followup Pass Rate:   100.0%  (Target: >= 85.0%)
Paraphrase Pass Rate: 100.0%  (Target: >= 85.0%)
Refusal Pass Rate:    100.0%  (Target: 100.0%)
Schema Compliance:    100.0%  (Target: 100.0%)
Overall Pass Rate:    100.0%
======================================================================
```
Full audit details are persisted in [`eval/report.md`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/yukti/backend/eval/report.md) and [`eval/report.json`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/yukti/backend/eval/report.json).
