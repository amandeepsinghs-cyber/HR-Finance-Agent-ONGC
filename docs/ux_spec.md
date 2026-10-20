# UX Spec v1.0 (approved): Yukti AI, voice-first HR & Finance agent

> [!NOTE]
> **Scope:** this covers **behaviour (UX)** only. The visual design (UI: Gemini Enterprise patterns, Material 3 Expressive and ONGC brand) comes in Track B once this is approved. Inputs: verbatims 1–8 and the Gate G5 data bank.

## 1. Experience goals (from your verbatims)
1. **Hands-off and voice-first, with typing allowed.** Hindi, English and Hindi-English mixed, in **one running conversation**.
2. **Brief spoken answers, rich visuals:** 2–4 spoken sentences, with the screen carrying charts, tables and sources.
3. **Asks, instructs and drafts:** answers questions, builds dashboards, **writes documents** (board notes, letters, applications, Parliament replies, transfer proposals), and exports them to Google Sheets, Google Docs, Word or PDF.
4. **Same question, different answer by role:** a persona dropdown, with refusals shown plainly and politely.
5. **Big-screen presence:** readable from 5 metres away, run from your laptop.

## 2. Personas on the dropdown
| Persona | Shown as | Can see |
|---|---|---|
| Chairman & CEO | "CMD" | Everything |
| Director (HR) | "Dir HR" | All HR; Finance summaries |
| Director (Finance) | "Dir Fin" | All Finance; HR summaries |
| Pooja Verma, E2 HR officer | "E2 · HR" | Own records; published policy; HR aggregates |
| Rajesh Kulkarni, E3 Finance officer | "E3 · Fin" | Own records; published policy; Finance aggregates |

## 3. Screen zones (one screen, big-screen 16:9). *Revised per verbatim 9*
```
┌───────────────────────────────────────────────────────────────────────────┐
│ Yukti AI   [Persona ▼ CMD]                         ☀/☾   EN|हि         │  ← slim top bar
├───────────────────────────────────────────────────────────────────────────┤
│                                                   ┌──────────────────────┐│
│   CANVAS (full width, behind the panel)           │ FLOATING CONVERSATION││
│   ┌──────────────────────────────┐ ┌──────────┐   │ PANEL (right)        ││
│   │ Primary visual / document /  │ │ Insight  │   │ ─  ⤢  (minimise /    ││
│   │ clause card / map            │ │ card     │   │        full screen)  ││
│   └──────────────────────────────┘ └──────────┘   │ running thread +     ││
│   [Source chips]  [Export ▼]                      │ citations + chips    ││
│   ── history strip ▢ ▢ ▢ ──                       │ ◉ particle voice orb ││
│                                                   │ [Type…]        🎤    ││
│                                                   └──────────────────────┘│
└───────────────────────────────────────────────────────────────────────────┘
```
- **All actions happen in the floating panel** on the right: asking, instructing, drafting and exporting. The canvas only displays results.
- **Panel modes:**
  - **Docked:** about 30% width, floating over the canvas edge.
  - **Minimised:** collapses to the **voice orb** only. It keeps listening, and the canvas becomes full width.
  - **Full screen:** the conversation takes over the screen, for drafting long documents or reading.
- **Siri-like voice orb (AlphaEvolve particle sphere):** a sphere of dots that reacts live to the microphone.
  - **Idle:** slow drift.
  - **Listening:** dots pulse with voice amplitude.
  - **Thinking:** a swirl.
  - **Speaking:** dots ripple with Leda's audio.
  - It shows the room that audio is going in, and that the agent is answering.
- **Light mode is the default** (document-centric: policy, HR and finance), with a dark-mode toggle (☀/☾).

## 4. Conversation and canvas behaviour
| Situation | Conversation | Canvas |
|---|---|---|
| New topic ("Which fields lost money?") | New agent turn | **Replaces** the primary visual; the old one moves to the history strip |
| Follow-up refining the topic ("only E5 and above", "show it by discipline") | Agent turn references the previous one | **Refines** the current visual in place (animated transition) |
| Comparison ("compare with Dehradun") | Turn | Side-by-side or grouped visual |
| "Go back to the transfer chart" | Turn | Restores from the history strip |
| Drafting ("Draft a board note on…") | Turn: "Here's the draft…" | **Document preview** replaces the visual; editable by voice |
| Policy question | Turn with a clause citation | **Clause card**: rule text highlighted plus the source document |

- **Memory:** one session for the whole demo. The agent understands "that", "those officers", "the same for Mumbai".
- **Suggestion chips:** after each answer, 2–3 natural follow-ups, e.g. "Why?", "Show by grade", "Draft transfer proposal".
- **Sources placement & visibility (User Decision):** Sources appear visually ONLY at the end of the canvas response (source chips at the bottom). Spoken answers NEVER recite dataset names, tables, documents or clause numbers by default.

## 5. The answer contract (what the agent returns each turn; it drives the UI)
```json
{
  "spoken_summary": "2–4 sentences, same language as the user (hi/en/mixed)",
  "display_text": "brief text for the thread (≤ 60 words) with inline citations",
  "visual": {"type": "chart|table|kpi|clause|document|map", "spec": {...declarative...}, "mode": "replace|refine|compare"},
  "insights": ["fact 1", "fact 2", "so-what"],
  "sources": [{"kind": "data", "object": "hrfin_gold.v_continuous_stay", "query_id": "..."}, {"kind": "policy", "doc_id": "JRTP", "clause": "3.0"}],
  "suggestions": ["…", "…"],
  "access": {"status": "allowed|partial|refused", "reason": "rule + clause", "alternative": "what this persona CAN see"},
  "export_options": ["sheets", "docs", "word", "pdf"]
}
```

## 6. Chart-selection rules (the agent chooses; the presenter can override by voice)
| Data shape | Default visual | Voice overrides |
|---|---|---|
| One measure split by ≤ 7 categories (e.g. C1 by grade) | Donut | "as bars", "as a table" |
| Categories × sub-categories (grade × discipline) | Stacked bar / treemap | "as heatmap" |
| Time series (headcount FY13–FY26, production) | Line / area with annotations | "yearly bars" |
| Ranking (top loss-making fields, top vendors) | Horizontal bar, sorted | "top 5 only" |
| Distribution (tenure, age, lifting cost) | Histogram / box | — |
| Actual vs target (MoU, capex BE/RE/actual) | Bullet / gauge / waterfall | — |
| Assets or regions (headcount by work centre) | **Map of India** with asset markers | — |
| Single number (402 due for transfer) | KPI tile with delta | — |
| What-if (Brent $60) | Before/after waterfall + slider | "try $55" |
| List of people or records | Table (paged), with names only where the role allows | "export to Sheets" |

## 7. Document drafting flow
1. **Ask:** "Draft a board note on loss-making fields" / "Write an application for study leave for Pooja Verma" / "Prepare the Parliament reply on North East vacancies".
2. **Draft:** the agent fills the matching template (board note, transfer proposal, Parliament reply, P&L sheet) or writes free-form (letters, applications). Data is pulled live and policy clauses are cited. A preview appears on the canvas.
3. **Revise by voice or text:** "make it shorter", "add the Brent $60 scenario", "translate to Hindi", "change the recommendation to PEC".
4. **Export:** "send to Google Docs" (your account) or "download as Word/PDF". A link appears in the thread.
5. **Guardrail:** drafting obeys the persona. An E2 officer can draft their own leave application, but not a board note containing restricted figures.

## 8. Persona and refusal flow (the "same question, two presenters" moment)
1. As CMD: "Show me the draft transfer list for Mumbai." → full roster plus chart.
2. The presenter switches the dropdown to **E2 · HR**; a visible banner reads "Now speaking as Pooja Verma (E2, HR)".
3. Same question → the agent says, politely and briefly: *"I can't share the draft transfer list. Pre-decision transfer records are confidential under the transfer policy, Clause 11. I can tell you when you're due for transfer and what the rotation rules are."* The canvas shows a **refusal card** (rule and clause) and the permitted alternative.
4. The refusal is logged (the audit log the CMD can query: "Who tried to access confidential data this week?").

## 9. Voice and language
- **Voice: Leda** (chosen, verbatim 9). Calm and authoritative, Indian-accent instruction, Hindi and English.
- **Language:** the agent replies in the language of the question, and mixed Hindi-English is fine. Numbers are spoken the Indian way ("1.32 lakh crore").
- **Spoken sources rule (User Decision):** Spoken answers NEVER mention sources, tables, documents or clause numbers by default. Plain business answers only. Exception: policy questions may naturally mention the policy name ("Under the transfer policy, …") but NOT clause numbers unless asked. When the user explicitly asks ("what's the source?", "where is this from?", "kiska data hai?"), Yukti speaks the source in plain business language ("This comes from the HR posting records as of today, and the JRTP policy, clause 3"). Never speak dataset or table names even then.
- **Interruption:** the presenter can interrupt mid-sentence ("stop — show by grade instead").
- **Hands-free:** one tap starts a hands-free session. An optional wake phrase can be added later.

## 10. Interaction states (always visible in the top bar)
Idle → **Listening** (live waveform and transcript) → **Thinking** (shows the step: "querying postings…", "reading JRTP…") → **Speaking** (voice plus the visual animating in) → back to Listening. Error states: "Didn't catch that", "Data not available: here's the closest I have", "Not permitted for this role".

## 11. Fallbacks for a live demo
- The typed input always works, even if the room audio fails.
- **Demo mode:** results for the 89 planned questions are pre-warmed (cached query results), so they answer in under 2 seconds.
- If voice drops, the session continues in text without losing history.
- A "show me how you got this" toggle reveals the query and sources, which helps build trust in the room.

## 12. Latency budget (target, end of speech to visual)
| Step | Target | Spike (live, measured) |
|---|---|---|
| Speech recognised, intent understood, tool chosen | ≤ 0.8 s | **1.9 s (text) / 2.6 s (voice)** |
| Tool (BigQuery Gold view / cached) | ≤ 1.5 s (cached ≤ 0.3 s) | **~2.0 s** BigQuery, **~1.6 s** search |
| Chart rendered / turn complete | ≤ 2.5–3 s total | **4.0–4.8 s** |

**Plan to close the gap:**
1. Pre-computed summary tables and a result cache for the 89 planned questions, bringing the tool step to ≤ 0.3 s.
2. Optionally, BigQuery's in-memory engine (BI Engine).
3. A **spoken holding phrase plus live status** while tools run, so it never feels silent ("Checking the posting records…"). The model's non-blocking tools support this.
4. Model: `gemini-3.8-live` was about 0.7 s faster than `gemini-live-2.5-flash-native-audio` at choosing the tool.

**Expected after these changes:** about 2.5–3 s to the chart, with voice starting within about 1 s.

## 13. Platform notes from research ([research_ux_inputs.md](file:///usr/local/google/home/amandeepsinghs/.gemini/jetski/brain/fd024626-b38e-48a5-ae39-8b4b562295c0/research_ux_inputs.md))
- **Voice model:** `gemini-live-2.5-flash-native-audio` on Vertex AI.
  - Hindi (hi-IN) and Indian English (en-IN), with automatic code-switching.
  - Female voice shortlist: **Kore, Aoede, Leda** (accent steered by instruction). You'll pick by ear from the spike.
  - Interruption is handled on the server.
  - Live transcription on both sides feeds the conversation thread and captions.
  - Tools don't block the conversation, so the agent can say "checking postings…" while the query runs.
- **Region:** US or EU only (no India). Accepted by you for the demo; adds about 200–250 ms network latency.
- **Long sessions:** audio sessions last about 15 minutes and each connection about 10 minutes. Session resumption plus context compression keep one running conversation through a long demo without losing history.
- **Front end:** Next.js + Tailwind + Framer Motion + **Apache ECharts** (best animation and streaming updates).
  - The agent emits a small validated chart spec; the UI renders it, and no AI-generated code runs in the browser.
  - Plotly Dash is dropped.
- **Exports:** Google Docs and Sheets APIs (your account), python-docx for Word, PDF via a headless browser.
- **Design inputs for Track B:**
  - Gemini Enterprise patterns: thread, citation chips, follow-up chips, editable canvas, one-click export.
  - **Material 3 Expressive:** spring motion, a mic button that changes shape across listening, thinking and speaking, large emphasised KPI numbers.
  - **ONGC brand:** the "Vasudhara" mark, maroon-red and white (exact colour to be checked against the official logo), Devanagari wordmark, tagline "Making Tomorrow Brighter".
- **"AlphaEvolve" theme:** the user means the **AlphaEvolve pitch deck's visual language** (Google DeepMind template, file in ~/Downloads). Extracted:
  - **Look:** clean white canvas, near-black text `#1F1F1F` / `#202124`, light surfaces `#F8F9FA`.
  - **Accent blue:** one bright blue `#3186FF`, secondary `#76BBFF`, with Google `#4285F4` sparingly.
  - **Type:** Google Sans Flex / Google Sans Text / Roboto (fallback Inter or Roboto Flex if licensing requires).
  - **Signature visual:** an **animated particle-dot sphere** (white and light-blue dots on black). Reference saved in `docs/design_refs/alphaevolve_particle_orb.gif`.
  - **It can be brought alive:** the particle sphere becomes the **voice orb**. It's a WebGL/canvas particle system driven by the Web Audio analyser for the microphone and by Leda's output for speaking. Blue dots on white in light mode; white and blue on black in dark mode.
  - The deck's blue becomes the interaction colour (buttons, highlights, chart primary). **ONGC maroon** (Vasudhara mark) is used sparingly for brand: logo, header accent, the persona chip.

## 14. Decisions (closed, verbatim 10)
1. **Name:** **Yukti AI**. The agent introduces itself as "Yukti".
2. **Opening:** a basic spoken intro on session start: *"Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help."* (Hindi equivalent if the session language is Hindi). A morning briefing is available on request ("give me today's briefing"), not automatic.
3. **Wake phrase:** none. One tap on the orb or mic starts a hands-free session; tap again to pause.
4. **"How did you get this":** off by default, shown on request ("how did you get this?") or via a small "Sources" chip. Source chips are always visible.
5. **Script:** the thread mirrors the user's language. A Hindi question gets Devanagari text plus Hindi speech; mixed Hindi-English gets Roman-script mixed text. Numbers use the Indian system (lakh/crore).

## 15. Amendment 2026-10-20 (user decision): sources
- Spoken answers never mention sources, tables, documents or clause numbers by default. The policy name may be said naturally ("Under the transfer policy…").
- Sources are shown visually only, at the END of each response: a collapsed "Sources (n) ▸" row at the bottom of the chat message and of the canvas card.
- When the user asks "what's the source?" or "kiska data hai?", Yukti states the source of the previous answer in plain business language. Never dataset or table names.
- Data-caveat notes (amber chips) are hidden in the default view and appear only inside the expanded Sources section.
