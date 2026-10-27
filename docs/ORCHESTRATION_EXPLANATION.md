# How Yukti orchestrates a question

**In one sentence:** every question goes down a fixed ladder of checks, written in code, and the first check that matches answers it. Only two places use a language model: the data planner (Gemini 2.5 Flash writes a structured plan, never SQL or numbers) and the small-talk fallback (no data, no figures).

- Code: [`yukti/backend/app/turn_runner.py`](../yukti/backend/app/turn_runner.py), `AgentTurnRunner._execute_turn_inner`.
- Also see [ARCHITECTURE.md](ARCHITECTURE.md) and the in-app page `/architecture`.

---

## 1. Who calls the orchestrator

| Entry point | When | What happens |
|---|---|---|
| **Gemini Live → `ask_yukti(question)`** | Voice | Gemini Live (`app/live_session.py`) does not answer data questions itself. It calls the `ask_yukti` tool, waits for the result and reads it aloud. The other two tools, `ui_control` and `control_screen`, change the screen without going through the ladder. |
| **`POST /api/turn`** | Typed questions, suggestion chips, follow-up buttons | Calls the same `execute_turn`. |

The result is always an **answer contract**: spoken summary, display text, visual (chart, table, KPI, document), sources, suggestions, access status and export options. The frontend renders it and Gemini Live speaks it.

## 2. Preparation, on every turn

1. **Clean the words:** `normalize_asr_query` fixes common speech-to-text errors.
2. **Resolve the role:** the persona comes from the signed cookie (`normalize_persona`). It cannot be changed by what the user says.
3. **Detect the language:** English, Hindi or Hinglish.
4. **Load the session:** previous turns, the last plan, the rows on screen, the active cohort, pending confirmations and the last DCF run. The session is hydrated with what the browser is currently showing, so "make it a pie chart" knows what "it" is.
5. **Give the turn an id:** `turn-<session>-<n>`, used for audit and export.

## 3. The ladder: first match wins

| # | Band | Check | Example | What answers it |
|---|---|---|---|---|
| 1 | Control | **Role switch** | "Sign in as Director HR" | Role-switch contract; the actual switch is signed by the server |
| 2 | Control | **Screen-command probe** | "Open the roster", "export this" | `detect_screen_control_intent`. It is disambiguated first: "plot Brent" or "what drives the valuation" are new questions, not re-plots |
| 3 | Control | **Pending year question** | Yukti asked "which year?" and the user says "last year" | Fills the year into the saved plan and re-runs the planner |
| 4 | Control | **Chart and UI change** | "Make it a waterfall" | `handle_ui_control`; re-draws on-screen data with no new query |
| 5 | **Safety** | **Access check** | A junior asks for named salaries | `check_access` returns a refusal with a rule reference and a safe alternative. It runs before any data handler |
| 6 | Simple | **Greeting** | "Good morning" | `handle_greeting` |
| 7 | Simple | **Coverage** | "Which years do you have?" | `handle_coverage` |
| 8 | Simple | **HR policy** | "What is the transfer policy?" | `handle_policy`, from the policy corpus |
| 9 | Simple | **Transfer note** | "Draft a transfer note for these" | `transfer_note_contract`, built from the selected cohort |
| 10 | Specialist | **DCF follow-up** | "What drives the valuation?", "What if WACC is 12%?" | `app/finance/dcf/followup.py`. Only runs if a DCF already ran in this chat and nothing is waiting for confirmation |
| 11 | Specialist | **Coordinator** | "Run a DCF", "Draft a board note" | `app/agents/coordinator.py`, see §4 |
| 12 | Specialist | **Revenue drivers and mix** | "Why did revenue hold up while oil fell?" | `app/market/revenue_drivers.py`: price, volume, rupee and product mix |
| 13 | Specialist | **Oil and rupee plot** | "Plot Brent for 5 years" | `app/market/oil_intent.py`, using cached Yahoo history plus today's price. If the feed is down, the question falls through |
| 14 | General | **Planner pipeline** | "Headcount by grade in FY25" | `app/brain/pipeline.py`, see §5 |
| 15 | General | **Small talk** | "Thanks!", "Who built you?" | `app/brain/smalltalk.py`: one Gemini call, no tools, no data, no digits |

**Why this order**
- **Safety before data:** the access check (5) runs before every data, policy or specialist handler.
- **Specific before general:** a DCF follow-up (10) is caught before the coordinator, which would otherwise treat any "valuation" question as a request for a new DCF.
- **Cheap before expensive:** checks 1–13 are pattern matches that take microseconds to milliseconds. The LLM planner (14) runs only when nothing else matches.
- **Fail soft:** each specialist is wrapped in `try/except`. If it fails, the question falls through to the next check instead of erroring.

## 4. Inside the coordinator (check 11)

1. **Pending confirmation?** "Yes, proceed", "cancel" or a voice edit ("make WACC 11%") resolves the waiting proposal. A confirmed DCF runs as a **background job** with progress steps (load inputs → WACC → forecast → valuation → sensitivity → tornado → XLSX → publish).
2. **Pattern match against [`registry.yaml`](../yukti/backend/app/agents/registry.yaml).** The first trigger regex that matches selects a module; otherwise it is `analyst`.
3. **Role gate:** each module lists `requires_role`. For example, DCF is CMD and Director Finance only. A disallowed role gets a refusal and an alternative.
4. **Branch:**
   - `dcf_agent` → **proposal** with editable assumptions. Nothing runs until the user confirms.
   - Board note, memo or parliament reply → policy check, then `DocumentDraftingEngine`, using the data on screen.
   - **Everything else**, including `fin_diagnostics_agent`, `hr_transfer_agent` and `analyst`, returns `delegate_to` and **continues down the ladder** to checks 12–14. For example, "why did PBT drop" is answered by the planner's *why* branch.

> In short, the registry is the place where specialists are declared. Today only DCF and document drafting have their own branch; the rest share the planner. A future LLM sub-agent would plug in here.

## 5. Inside the planner pipeline (check 14)

1. **Shortcuts:** export requests and email/letter drafting are handled first.
2. **Plan:** Gemini 2.5 Flash turns the question, plus the previous plan and recent history, into a JSON **QuerySpec**: metric, dimensions, filters, period and chart. It may also return a **patch** to the previous plan ("only Mumbai", "as a bar chart").
3. **Branches by intent:**
   - presentation-only patch → re-draw the rows already on screen;
   - **why** → variance or bridge analysis;
   - **what-if** → simulation from field economics, finance roles only;
   - **data** → continue.
4. **Office-holder safeguard:** APAR and medical records of the top office holders are refused for every role.
5. **Year clarification:** if the period is ambiguous, Yukti asks "which year?". This is the pending question that check 3 picks up on the next turn.
6. **Compile:** a deterministic compiler turns the spec into **certified SQL** against the semantic model. The model never writes SQL.
7. **Pre-query policy:** checks the data classes the compiled query would touch. It may refuse, or narrow the query to aggregates.
8. **Execute:** BigQuery dry run (bytes checked), then the run against `hrfin_*_v3`.
9. **Privacy:** for junior roles, small aggregate cells are suppressed.
10. **Present:** code builds the chart, table, KPI cards and context chips.
11. **Narrate:** the explanation may only use **allowed numbers**, taken from the result rows. Any other figure is rejected and a deterministic sentence is used instead.

## 6. After every answer, whichever check produced it

1. **`enforce_contract`:** role-based masking of rows and text for the signed role.
2. **Session memory keeps the masked version**, so later turns (drafts, re-plots, exports) cannot resurface data the role may not see.
3. **Export registration:** the turn is registered so PDF, Excel or Word exports use exactly what was shown.
4. **Contract validation:** the answer must match the contract schema before it is returned.

## 7. Worked examples

| Question | Path |
|---|---|
| "Headcount by grade in FY25" | 1–13 no match → **14 planner**: Flash spec → SQL → BigQuery → bar chart → narration |
| "Make it a pie chart" | **2/4 UI change**: re-draw on-screen rows; no query, no LLM |
| "Run a DCF" (CMD) | 11 coordinator → `dcf_agent` → **proposal** → "Yes" → background job → valuation, sensitivity, tornado |
| "What drives the valuation?" (after a DCF) | **10 DCF follow-up**: drivers from the saved run |
| "Why did revenue hold up while oil fell?" | 11 coordinator: no own branch → `delegate_to` → **12 revenue drivers**: price, volume, rupee, mix |
| "Plot Brent for 5 years" | **13 oil plot**: Yahoo history |
| A junior asks "salaries of named officers" | **5 access check**: refusal with a rule reference and an aggregate alternative |
| "Thanks!" | **15 small talk** |

## 8. Single agent or multi-agent?

- **Single agent:** Gemini Live is the only component that reasons freely. The orchestrator is code.
- **Agent-ready:** a registry entry is `id + class + triggers + requires_role (+ steps)`. Replacing a `delegate_to` module with an LLM sub-agent (e.g. one that explains an on-screen chart) needs no change to the ladder, the access check, masking or export.
