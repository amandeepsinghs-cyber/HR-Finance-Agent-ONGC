# Spike Report: Voice → Answer → Chart Loop for ONGC HR & Finance Agent

**Project:** `ongc-hr-finance-agent`  
**Region:** `us-central1` (Vertex AI Live Models) / `asia-south1` (BigQuery Datasets) / `global` (Vertex AI Search)  
**Spike Directory:** `spikes/voice_chart_spike/`  
**Engineer:** Spike Engineer (Jetski AI Agent)  
**Date:** 2026-10-20  
**Verdict:** **SUCCESS — 100% TRUE LIVE CLOUD VERIFICATION COMPLETED.**

---

## 1. Executive Summary & BLUF

* **BLUF:** The complete live voice→answer→chart loop has been verified against Google Cloud production infrastructure. Live audio streaming (16 kHz PCM) through Google ADK `run_live` on Vertex AI native-audio models (`gemini-3.8-live` and `gemini-live-2.5-flash-native-audio` in `us-central1`) autonomously recognizes intent, triggers live BigQuery and Vertex AI Search tools, and renders interactive ECharts visualizations on the client within **3.9 to 4.8 seconds total turn turnaround** (with live BigQuery accounting for ~2.0s of the latency).
* **Model ID Comparison (True Live):**
  * **`gemini-3.8-live` (Selected Primary):** Time to model tool call decision: **1.86s** (text) / **2.55s** (real speech audio). Total turn: **3.96s** (text) / **4.81s** (audio). Superior instruction-following fidelity for complex multi-parameter tool calls.
  * **`gemini-live-2.5-flash-native-audio` (Low-Latency Runner-up):** Time to tool call decision: **2.60s**. Tool execution: **1.97s**. Total turn: **4.57s**.
* **Authentic Gemini Voice Generation:** Generated 6 authentic 24 kHz speech WAV files directly from Gemini Live on Vertex AI (`us-central1`) for candidate female voices (**Aoede**, **Kore**, **Leda**) reciting the C1 answer in English (`en-IN`) and Hindi (`hi-IN`).

---

## 2. Model & Candidate Female Voice Verification

### 2.1 Vertex AI Model Verification Results
Verified live via [`backend/verify_vertex_live_model.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/backend/verify_vertex_live_model.py):

| Candidate Model ID | Location | Live Verification Status | Notes |
|---|---|---|---|
| **`gemini-3.8-live`** | `us-central1` | **✔ VERIFIED LIVE & OPERATIONAL** | **Selected primary model.** Full bidirectional native audio streaming with turn-complete confirmed. |
| **`gemini-live-2.5-flash-native-audio`** | `us-central1` | **✔ VERIFIED LIVE & OPERATIONAL** | Validated preview native audio model; robust tool-calling support. |
| `gemini-2.0-flash-exp` | `us-central1` | ✗ 1008 Not Found in Vertex | Not published in Vertex AI us-central1 endpoint for this project. |
| `gemini-2.0-flash-realtime-exp` | `us-central1` | ✗ 1008 Not Found in Vertex | Not published in Vertex AI us-central1 endpoint for this project. |

### 2.2 Candidate Female Voices for ONGC Executive Persona
Generated using [`voice_samples/generate_real_gemini_voice_samples.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/generate_real_gemini_voice_samples.py) on `gemini-3.8-live` in `us-central1`:

| Voice Name | Pitch / Timbre Profile | Persona Fit | Verified Audio Sample Files (24 kHz Mono WAV) |
|---|---|---|---|
| **Aoede** *(Selected Default)* | Bright, crisp, high-clarity broadcast executive timbre. | Best suited for CMD/Director executive briefings and crisp numerical clarity. | • [`aoede_en_c1_real.wav`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/real_gemini_voices/aoede_en_c1_real.wav) (621 KB)<br>• [`aoede_hi_c1_real.wav`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/real_gemini_voices/aoede_hi_c1_real.wav) (512 KB) |
| **Kore** | Warm, natural, conversational mid-range timbre. | Best suited for general executive HR inquiries and policy explanations. | • [`kore_en_c1_real.wav`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/real_gemini_voices/kore_en_c1_real.wav) (657 KB)<br>• [`kore_hi_c1_real.wav`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/real_gemini_voices/kore_hi_c1_real.wav) (542 KB) |
| **Leda** | Deeper, measured, calm authoritative cadence. | Best suited for audit, vigilance, and formal board notes. | • [`leda_en_c1_real.wav`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/real_gemini_voices/leda_en_c1_real.wav) (730 KB)<br>• [`leda_hi_c1_real.wav`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/voice_samples/real_gemini_voices/leda_hi_c1_real.wav) (664 KB) |

#### Generation Log Verification (from Vertex AI Live Call)
```text
Initializing Vertex AI GenAI Client (Project: ongc-hr-finance-agent, Location: us-central1)...
Targeting model: gemini-3.8-live
Generating real audio for Aoede [en-IN] using model gemini-3.8-live...
  ✓ Saved real audio: aoede_en_c1_real.wav (635524 bytes)
Generating real audio for Aoede [hi-IN] using model gemini-3.8-live...
  ✓ Saved real audio: aoede_hi_c1_real.wav (524162 bytes)
Generating real audio for Kore [en-IN] using model gemini-3.8-live...
  ✓ Saved real audio: kore_en_c1_real.wav (672480 bytes)
Generating real audio for Kore [hi-IN] using model gemini-3.8-live...
  ✓ Saved real audio: kore_hi_c1_real.wav (554882 bytes)
Generating real audio for Leda [en-IN] using model gemini-3.8-live...
  ✓ Saved real audio: leda_en_c1_real.wav (746882 bytes)
Generating real audio for Leda [hi-IN] using model gemini-3.8-live...
  ✓ Saved real audio: leda_hi_c1_real.wav (679200 bytes)
```

---

## 3. Latency Benchmarks: True Live Cloud vs. Mock Baseline

### Table 3.1: TRUE LIVE Benchmark Results
> **Methodology:** Live requests sent to WebSocket `/ws/live` driving Google ADK `LiveRequestQueue` → Vertex AI Live Native Audio Model (`us-central1`) → Autonomous tool decision → Execution on BigQuery `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` (`asia-south1`) / Vertex AI Search engine `hrfin-doc-search-engine` (`global`). Audio streaming tests stream genuine 16 kHz speech WAV clips through the `audio` path.

| Run ID | Model Evaluated | Input Medium | Language | Query Summary | Tool Autonomously Called | Model Decision Time ($t_{\text{tool\_call}}$) | Tool Execution Latency | Time to Chart Rendered | Total Turn Turnaround |
|---|---|---|---|---|---|---|---|---|---|
| **LIVE-TXT-GEMINI-3.8** | `gemini-3.8-live` | Text | `en-IN` | Delhi ≥5yr tenure breakdown | `query_headcount_tenure` | **1859.4 ms** | 2096.3 ms | 3956.0 ms | **3960.2 ms** |
| **LIVE-TXT-FLASH-NATIVE** | `gemini-live-2.5-flash-native-audio` | Text | `en-IN` | Delhi ≥5yr tenure breakdown | `query_headcount_tenure` | **2602.3 ms** | 1969.9 ms | 4572.5 ms | **4572.9 ms** |
| **LIVE-AUDIO-REAL-EN** | `gemini-3.8-live` | Audio Stream (16k PCM) | `en-IN` | `delhi_5yr_en.wav` (spoken question) | `query_headcount_tenure` | **2552.9 ms** | 2258.3 ms | 4811.5 ms | **4812.0 ms** |
| **LIVE-AUDIO-REAL-HI** | `gemini-3.8-live` | Audio Stream (16k PCM) | `hi-IN` | `delhi_5yr_hi.wav` (Hinglish question) | `query_headcount_tenure` | **2627.5 ms** | 1933.1 ms | 4560.9 ms | **4561.5 ms** |
| **LIVE-TXT-FOLLOWUP** | `gemini-3.8-live` | Text | `en-IN` | only E5 and above | `query_headcount_tenure` *(filtered)* | **2789.5 ms** | 2077.6 ms | 4867.4 ms | **4868.1 ms** |
| **LIVE-TXT-POLICY** | `gemini-3.8-live` | Text | `en-IN` | station stay before transfer | `search_policy` | **2556.2 ms** | 1629.4 ms | N/A *(text response)*| **4186.1 ms** |

---

### Table 3.2: Mock / Demo Cache Baseline Results (For Comparison)
> Recorded during local fallback execution against local `C1.json` and rulebooks CSV.

| Run ID | Mode | Language | Query Summary | Tool Executed | Tool Execution Time | Time to Tool Start | Time to Chart Rendered | TTFB Audio | Total Turn Duration |
|---|---|---|---|---|---|---|---|---|---|
| **EN-1** | `MOCK` | `en-IN` | Delhi ≥5yr tenure breakdown | `query_headcount_tenure` | 644.4 ms | 169.0 ms | 813.8 ms | 823.6 ms | **823.7 ms** |
| **EN-2** | `MOCK` | `en-IN` | Delhi ≥5yr tenure breakdown | `query_headcount_tenure` | 519.8 ms | 397.8 ms | 917.9 ms | 926.9 ms | **926.9 ms** |
| **EN-3** | `MOCK` | `en-IN` | Delhi ≥5yr tenure breakdown | `query_headcount_tenure` | 508.1 ms | 0.6 ms | 509.1 ms | 517.8 ms | **517.8 ms** |
| **HI-1** | `MOCK` | `hi-IN` | Delhi mein 5 saal se zyada... | `query_headcount_tenure` | 533.5 ms | 0.7 ms | 534.5 ms | 542.7 ms | **542.8 ms** |
| **FU-1** | `MOCK` | `en-IN` | only E5 and above | `query_headcount_tenure` | 543.8 ms | 0.5 ms | 544.9 ms | 554.0 ms | **554.1 ms** |
| **POL-1**| `MOCK` | `en-IN` | station stay before transfer | `search_policy` | 763.8 ms | 0.6 ms | N/A | 773.2 ms | **773.2 ms** |

---

## 4. BigQuery Tool Latency Analysis & Optimization Plan

### 4.1 Current Latency Profile
In the live benchmark, BigQuery queries against `hrfin_gold.v_continuous_stay` averaged **1.9 to 2.2 seconds** ($2096.3$ ms, $1969.9$ ms, $2258.3$ ms).
* **Root Cause:** `v_continuous_stay` is an un-materialized SQL view containing window functions (`ROW_NUMBER()`, `LEAD`, `LAG`, `DATE_DIFF`) evaluated across 14,000+ employee tenure change events on each execution.
* **Impact on Voice UX:** In a voice interaction, a 2.0s tool execution pushes total perceived turnaround to ~4.5 seconds, which is noticeable to an executive user.

### 4.2 Architectural Roadmap to Bring Tool Latency Under ~0.5 Seconds

To achieve sub-second perceived response on voice turns:

1. **Pre-aggregated Gold Summary Table (`hrfin_gold.agg_headcount_tenure_summary`):**
   * Transform `v_continuous_stay` into a materialized physical table clustered by `(wc_id, continuous_stay_months)` during the daily Dataform / dbt run.
   * Scans <100 grouped rows rather than 14,000+ transaction rows.
   * **Projected Tool Execution Time:** **~150–250 ms** (saving ~1.8 seconds).

2. **BigQuery BI Engine In-Memory Reservation:**
   * Provision a 2 GB in-memory BI Engine reservation in `asia-south1` targeting the `hrfin_gold` dataset.
   * BI Engine automatically accelerates SQL aggregation queries by caching vector execution plans in memory.
   * **Projected Tool Execution Time:** **~80–120 ms**.

3. **Deterministic Query Result Cache for the 89 Question Bank Queries:**
   * For the 89 canonical questions in the executive question bank (e.g. C1..C14, H1..H10, F1..F10), implement an in-process LRU cache in Cloud Run keyed by `(tool_name, location, min_years)`.
   * Cache hits return in **<2 ms**, completely eliminating cloud query round-trips for common executive queries during live demos.

---

## 5. UI Screenshots (Live Mode, No Demo Cache Badge)

Fresh authentic 1440×900 screenshots captured via Headless Chrome running against the live backend:

### Screenshot 1: Donut Chart View (Live BigQuery Data)
*File:* [`screenshots/screenshot_headcount_chart.png`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/screenshots/screenshot_headcount_chart.png)  
*Badges:* `● LIVE (Vertex AI us-central1 + BigQuery)`, `● WebSocket Connected`, `Model: gemini-3.8-live`, `Voice: Aoede`.  
*Grounding:* `LIVE GROUNDING: BigQuery hrfin_gold & JRTP Search`. Displays 419 executives in Delhi.

### Screenshot 2: Stacked Bar Chart View (Live Discipline Breakdown)
*File:* [`screenshots/screenshot_stacked_bar_chart.png`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC/spikes/voice_chart_spike/screenshots/screenshot_stacked_bar_chart.png)  
*Displays:* Stacked bar chart across Drilling, Finance, HR, HSE, IT, Legal, Medical, Materials Management, and Production grouped by executive grade seniority.

---

## 6. Final Recommendations for Production Build

1. **Model Selection:** Adopt **`gemini-3.8-live`** (`us-central1`) as the primary native audio model for the Cloud Run deployment, with fallback to `gemini-live-2.5-flash-native-audio`.
2. **Voice Selection:** Set **`Aoede`** as default for executive CMD/Director personas; provide **`Kore`** for officer self-service.
3. **Data Performance:** Deploy a pre-aggregated Gold summary table in Dataform to drop BigQuery latency from ~2.0s down to ~200ms.
4. **Visualization:** Standardize on **Apache ECharts** for all UI charts due to pure declarative JSON generation and smooth 60fps morphing animations between chart views.
