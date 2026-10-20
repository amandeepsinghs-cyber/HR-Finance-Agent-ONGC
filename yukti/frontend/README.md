# Yukti AI — Executive Voice-First Front-End Shell

> **High-Fidelity Voice-First HR & Finance Intelligence Agent for ONGC Leadership (CMD, Director HR, Director Finance)**
> Designed and implemented following the **Google DeepMind / AlphaEvolve** aesthetic deck language, approved **UX Spec v1.0**, and the strict **Answer Contract** schema.
> Fully functional end-to-end with the **FastAPI + Google ADK** backend.

---

## 1. Quick Start (Live Backend + Front-End)

### Step 1: Start the Backend Server (Port 8095)
```bash
cd "o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend"
export PATH="$HOME/.local/bin:$PATH"

# Run FastAPI backend on port 8095 (Track C eval sweep runs on 8080)
PORT=8095 uv run python run.py
```
*Health Check: `http://localhost:8095/health`*

### Step 2: Start the Front-End Client (Port 3200)
```bash
cd "o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/frontend"
export PATH="$HOME/.local/bin:$PATH"

# Development server
npm run dev

# Or production build & start
npm run build
npm run start
```
Open **[http://localhost:3200](http://localhost:3200)** in Google Chrome.

### Operational Modes
- **Live ADK Mode (Default)**: Directly connects to `ws://localhost:8095/ws/live` and `http://localhost:8095/api/turn`. Live BigQuery queries, Vertex AI Live `gemini-3.8-live` audio streaming, and Leda speech synthesis.
- **Mock Demo Mode**: Toggle via TopBar pill or open `http://localhost:3200?mock=1`. Allows reviewing all 12 Gate G5 scenarios completely offline.

### Keyboard Shortcuts
- **Spacebar**: Advance through the 12 scripted executive scenarios
- **M**: Toggle hands-free microphone input (connects live Web Audio Analyser)
- **T**: Toggle Light / Dark Mode (defaults to Light Mode)
- **F**: Toggle Full-Screen Conversation Panel (for document drafting & long reviews)
- **Escape**: Restore Docked view from Full-Screen mode

---

## 2. Manual Voice Testing Script (Real Microphone)

Follow these steps to test the voice-first executive loop with a real microphone in Google Chrome:

1. **Start Services**: Ensure the backend is running on port 8095 and frontend on port 3200.
2. **Open Chrome**: Navigate to `http://localhost:3200`. Verify the green `🟢 Live ADK` pill is visible in the top bar.
3. **Verify Opening State**: Confirm the canvas displays the clean opening state (*"Hello, I am Yukti. Your voice-first HR & Finance agent."*) with the 3 executive starter cards.
4. **Grant Microphone Permission**:
   - Click the blue microphone icon in the bottom-right conversation panel (or press `M`).
   - Click "Allow" when Chrome prompts for microphone access.
   - Verify the Voice Orb expands into energetic cyan-blue listening mode, reacting dynamically to ambient voice volume.
5. **Ask Query 1 (Speech Input)**:
   - Speak clearly into your microphone:  
     *"How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline."*
   - Verify:
     - Voice status transitions from `listening` to `thinking` (*"Querying BigQuery hrfin_gold in asia-south1..."*).
     - Streaming 24 kHz audio returns with Leda's voice.
     - The Voice Orb ripples in sync with the spoken output audio graph.
     - Canvas renders the C1 Donut chart (419 total / 17 retiring / 401 due).
     - Caveat chip appears: *"Tenure lower bound: most current stays start at 1-Jul-2020..."*
6. **Test Barge-In (Interruption)**:
   - While Leda is speaking, speak into your mic or click the mic button:  
     *"Stop, show only E5 and above."*
   - Verify: Audio playback stops immediately (gapless audio graph stops without delay), and the view refines in place to the E5–E7 senior management bar chart.
7. **Test Role-Based Refusal (Pooja Verma, E2 HR)**:
   - Click the Role dropdown in the top bar and select **"E2 · HR (Pooja Verma)"**.
   - Verify the blue notification banner appears: *"Now speaking as Pooja Verma (Assistant Manager, E2 · HR)"*.
   - Speak or type: *"Show me the draft transfer list for Mumbai."*
   - Verify: The agent politely refuses under JRTP Clause 11.0 & RTI Act Section 8(1)(i). The canvas renders the high-visibility Refusal Card with the permitted alternative aggregate data.
8. **Test Document Generation & Export**:
   - Switch persona back to **"CMD"**.
   - Speak or type: *"Draft a reply to Parliament question on North East vacancies."*
   - Verify: The X7 official document preview renders with the official ONGC logo, "Draft v1" badge, and clean category-wise Markdown table.
   - Click **"Download .docx"** in the action bar: verify the Word document downloads to your computer.
   - Click **"Open in Google Docs"**: verify the Google Workspace simulation notice modal explains the OAuth configuration status.

---

## 3. Design System Tokens (AlphaEvolve & ONGC Visual Language)

| Category | Light Mode (Default) | Dark Mode | Usage |
|---|---|---|---|
| **Canvas Background** | `#FFFFFF` | `#121316` | Clean full-width document canvas |
| **Card / Surface** | `#F8F9FA` | `#1E2024` | Primary visual containers, cards, floating panel |
| **Borders** | `#E0E3E7` | `#2D3139` | Subtle structural lines, table borders |
| **Text Primary** | `#1F1F1F` | `#F1F3F4` | High-contrast readable typography (≥18px on 1080p) |
| **Text Secondary** | `#5F6368` | `#9AA0A6` | Metadata, timestamps, captions, axis labels |
| **Accent Primary** | `#3186FF` | `#3186FF` | AlphaEvolve bright interaction blue (buttons, pins, active states) |
| **Accent Secondary** | `#76BBFF` | `#76BBFF` | Depth highlights, glowing orb particles, pills |
| **ONGC Maroon** | `#8E000C` | `#8E000C` | Official sampled maroon from ONGC logo, top bar badge, document header |
| **Chart Palette** | `#1A56DB` → `#76BBFF` | Same | AlphaEvolve blue ramp with `#8E000C` for emphasis & loss fields |
| **Typography** | `Inter`, `Google Sans`, `Noto Sans Devanagari` | Same | Clean sans-serif with full Devanagari Unicode support |

---

## 4. Live Backend E2E Test Results

Automated Playwright test script: `npm run test:live` (`node scripts/live_e2e_test.js`)

```
================================================================
       GENUINE LIVE BACKEND E2E TEST SCORECARD SUMMARY          
================================================================
┌─────────┬─────────────────────────────┬───────────────────────────────┬───────────┬───────────────────────────────────────────┐
│ (index) │ turn                        │ turnId                        │ latencyMs │ canvasTitle                               │
├─────────┼─────────────────────────────┼───────────────────────────────┼───────────┼───────────────────────────────────────────┤
│ 0       │ 'C1 Root Turn'              │ 'turn-sess-1792484502310-...' │ 9520      │ "Delhi Executives with ≥5 Years' Cont..." │
│ 1       │ 'C1 Follow-up (Refine)'     │ 'turn-sess-1792484502310-...' │ 6895      │ 'Only e5 and above...'                    │
│ 2       │ 'P1 Policy Clause'          │ 'turn-sess-1792484502310-...' │ 9521      │ 'DOC-RB-JRTP-SCAN Clause 4.0...'          │
│ 3       │ 'D2 Role Refusal (E2 · HR)' │ 'turn-sess-1792484502310-...' │ 1796      │ 'Access Restricted (D2)...'               │
│ 4       │ 'X7 Document Draft'         │ 'turn-sess-1792484502310-...' │ 15743     │ 'Parliament Question Reply: Executive...' │
└─────────┴─────────────────────────────┴───────────────────────────────┴───────────┴───────────────────────────────────────────┘
================================================================
```

- **Live Visual Latency (Send → Response → Render)**:
  - C1 Root Turn: **9.52 s** (Live BigQuery execution + Gemini model generation; verified count 419)
  - C1 Follow-up: **6.90 s** (Stateful in-place refinement to E5 senior management)
  - P1 Policy Clause: **9.52 s** (Vertex AI document search; verified JRTP Clause 4.0 card)
  - D2 Role Refusal: **1.80 s** (Access control hook + CDA Rule 11 evaluation; verified refusal card)
  - X7 Document Draft: **15.74 s** (Multi-table Parliament reply generation; verified 143 vacancies; Word .docx download tested via `GET /api/export/{export_id}`)
- **User Decision on Sources & Citations**:
  - Sources sit strictly at the end of each response, collapsed by default (`Sources (N) ▸`), expanding on click.
  - Citation markers (`[1]`, `[2]`) are stripped from display and spoken text; sources are never read aloud.
  - Data caveats are kept clean and contained strictly inside the expanded Sources section, keeping the presentation view pristine.
- **Audio TTFB Instrumentation**:
  - Live audio TTFB cannot be synthesized in headless Playwright without an active physical microphone. Client-side VAD instrumentation measures speech-end → first audio chunk and exposes live telemetry via the `?debug=1` overlay for real mic testing.
- **Screenshots Captured (Post-Render)**:
  - `screenshots/live_turn_c1.png`
  - `screenshots/live_turn_sources_expanded.png` (Collapsed sources expanded on canvas showing citations + caveat)
  - `screenshots/live_turn_c1_followup.png`
  - `screenshots/live_turn_p1.png`
  - `screenshots/live_turn_d2_refusal.png`
  - `screenshots/live_turn_x7_export.png`

---

## 5. Third-Party Licenses & Attribution

- **Official ONGC Corporate Logo**:
  - Source URL: `https://ongcindia.com/documents/77751/1767704/2203_logopng.png/9c8ae834-3067-b310-e32f-6dd0703b8720` (Official ONGC Corporate Portal Media Center)
  - Retrieved: 20-October-2026
  - Saved Path: `public/brand/ongc_logo.png` (1499x1499 master PNG)
  - Trademark Notice: Trademark of Oil and Natural Gas Corporation Limited (ONGC); used strictly for executive demo presentation.
  - Sampled Official Brand Maroon: `#8E000C` (RGB 142, 0, 12).

- **Official Survey of India Boundary GeoJSON**:
  - Depiction: Official Survey of India boundary including full Jammu & Kashmir, Ladakh, and Arunachal Pradesh.
  - Source: DataMeet Maps Project (`datameet/maps - Country/india-composite.geojson`)
  - Licence: Creative Commons Attribution 2.5 India (CC BY 2.5 IN) / Open Data
  - Attribution: © DataMeet Community Maps Contributors & Survey of India
  - Included in: `src/data/indiaGeoJson.ts`

---

## 6. Feedback & Backend Coordination Notes with Track C

1. **Direct Binary Download Endpoint (Resolved)**:
   - Track C implemented `GET /api/export/{export_id}` returning binary `FileResponse` with content headers. Front-end `CanvasView` and `DocumentRenderer` directly download from this endpoint without local filesystem access.
2. **Contract Event Emission in `/ws/live` (Future Enhancement)**:
   - Currently, `/ws/live` emits audio, transcripts, status, and tool calls. Full visual Answer Contracts are fetched via REST `/api/turn`. Emitting the full composed `{"type": "contract", "contract": ...}` payload directly over `/ws/live` on turn completion would streamline websocket-only clients.
