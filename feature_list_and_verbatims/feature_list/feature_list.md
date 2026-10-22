# Yukti AI — Feature List & Requirements Specification

**Location**: `feature_list_and_verbatims/feature_list/`  
**Linked Verbatims**: [`feature_list_and_verbatims/verbatims/`](../verbatims/)  
**Status**: Active / Refinement

---

## Feature Index

| Feature ID | Feature Name | Source Verbatim | Priority | Category | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FEAT-001** | **Scrollable Conversational Feed (History Preservation)** | Verbatim 11 | **P0 (Critical)** | Frontend / UX | Specified |
| **FEAT-002** | **Multi-Turn Context & Entity Carryover** | Verbatim 11 | **P0 (Critical)** | Backend / Agent | Specified |
| **FEAT-003** | **Visual Presentation & Charting Audit** | Verbatim 11, 7 | **P1 (High)** | Visualization / UX | Pending Audit |
| **FEAT-004** | **Luminous Siri / Infinity Loop Voice Orb** | Verbatim 12 | **P1 (High)** | UI / Animation | Specified |
| **FEAT-005** | **Executive UI Modernization & Material Polish** | Verbatim 12 | **P1 (High)** | UI / Design System | Specified |
| **FEAT-006** | **CMD Actionable Employee-Level Roster (Drilldown)** | Verbatim 13 | **P0 (Critical)** | Data / HR Actions | Specified |

> **Design Specifications Reference**: See [`design_recommendations_ui_and_orb.md`](./design_recommendations_ui_and_orb.md) for detailed UI glassmorphism and voice orb wave formulas.

---

## FEAT-001: Scrollable Conversational Feed (History Preservation)

### 1. User Problem Statement
Currently, asking a new question clears or completely replaces the screen. The user cannot see previous questions, tables, or charts, making comparison across queries impossible and feeling disconnected from standard conversational AI experiences (Gemini, Claude, ChatGPT).

### 2. Required Behavior
* **Non-Destructive Append**: When a new question is submitted (by voice or text), the previous turn (question + narrative + visual canvas cards) remains intact and scrolls up.
* **Stream/Feed Layout**: The main viewport functions as an interactive vertical feed:
  * Turn $N-1$: User prompt $\rightarrow$ Yukti verbal summary $\rightarrow$ Generated ECharts/DataTable/Doc card.
  * Turn $N$: User prompt $\rightarrow$ Yukti verbal summary $\rightarrow$ Generated ECharts/DataTable/Doc card.
* **Auto-Scroll with User Control**: The viewport smoothly auto-scrolls down to reveal the latest streaming response, but pauses auto-scrolling if the user scrolls up manually to inspect earlier data.
* **Card Interactivity in History**: Historic charts, tables, and document previews remain fully interactive (hover tooltips, tab switching, export triggers).

### 3. Acceptance Criteria
- [ ] Asking Question B after Question A does not erase Question A's card.
- [ ] The user can scroll up to view Question A's exact visual and tabular outputs.
- [ ] Responsive across full-screen canvas and floating chat modes.

---

## FEAT-002: Multi-Turn Context & Entity Carryover

### 1. User Problem Statement
Every question is currently evaluated in isolation. If a user asks *"How many employees are in New Delhi?"* and follows up with *"Break them down by discipline"*, the system does not remember that "them" refers to Delhi employees, causing failures or irrelevant answers.

### 2. Required Behavior
* **Contextual Entity Resolution**: The agent backend retains the active entity context (e.g. `location: "Delhi"`, `cadre: "Executive"`, `fiscal_year: "FY26"`, `field: "Mumbai High"`) across turns within the same session.
* **Multi-Turn Chat History in Prompts**: The backend passes conversation turn history (user questions, tool outputs, agent summaries) to Gemini so follow-up queries naturally inherit antecedents and filters.
* **Session Reset Option**: A clear "New Session / Clear Context" action allowing the user to start a fresh topic when desired.

### 3. Acceptance Criteria
- [ ] Follow-up questions referencing pronouns or implicit filters ("break them down", "compare this with last year", "show only loss-making ones") correctly resolve context from the immediate prior turn.
- [ ] Session memory persists across voice and text turns within the current browser session.

---

## FEAT-003: Visual Representation & Charting Audit (Next Phase)

### 1. Objective
Conduct an exhaustive audit of all visual representations (charts, KPI metrics, geospatial maps, data tables, and document drafts) across the entire question bank to identify presentation gaps and elevate visual polish.

### 2. Scope of Upcoming Audit
* Map every data question type (categorical, time-series, geospatial, tabular, hierarchical) to its optimal visual format (ECharts, Survey of India map, structured card, rich document).
* Identify gaps where plain text is returned instead of an actionable visual.
* Ensure visual hierarchy, color palette, and responsiveness match ONGC leadership expectations.

---

## FEAT-004: Luminous Siri / Infinity Loop Voice Orb

### 1. User Problem Statement
The existing 3D Fibonacci particle orb feels chaotic, jittery, and overly technical. Leadership expects a serene, organic, and executive voice presence—analogous to Apple's Siri multi-ribbon wave / infinity loop or DeepMind AlphaFold's continuous harmonic ribbons.

### 2. Required Behavior
* **Organic Infinity Ribbon Geometry**: Replace point particles with 3–4 overlapping, luminous cubic Bézier / harmonic sine curves that morph continuously in an infinity / mobius loop configuration.
* **State-Aware Dynamics**:
  * **Idle**: Gentle, slow breathing cycle with soft ambient glow.
  * **Listening**: Responsive audio amplitude modulation where user speech drives ribbon amplitude and thickness organically.
  * **Thinking**: Luminous wave pulse revolving around the loop perimeter at a steady cadence.
  * **Speaking**: Warm vocal resonance frequency pulses matching the agent's synthesized speech playback.
* **Visual Polish**: Smooth gradient blending (ONGC deep saffron `#E85D04` / petroleum blue `#0077B6` / clean gold) with subtle background radial blur, ensuring zero visual noise or harsh edges.

### 3. Acceptance Criteria
- [ ] No scattered or vibrating dots.
- [ ] Smooth 60fps canvas or SVG rendering without CPU spikes.
- [ ] Clear visual distinction between Idle, Listening, Thinking, and Speaking states.

---

## FEAT-005: Executive UI Modernization & Enterprise Material Polish

### 1. User Problem Statement
The current interface is functional but feels somewhat "basic" and flat. It needs an executive-grade aesthetic tailored for ONGC leadership (CMD, Directors) that conveys authority and polish without becoming complex, cluttered, or difficult to use.

### 2. Required Behavior
* **Executive Frame & Card Elevation**:
  * Replace flat borders with subtle frosted glass surfaces (`backdrop-blur-md`, soft layered shadows `shadow-sm` to `shadow-md`).
  * Crisp header badges with metadata: active persona (`CMD`), live query classification, and timestamp.
* **Refined Typography & Hierarchy**:
  * Clean modern sans-serif headings with high-contrast numerical metrics (KPIs prominently styled with contextual trend pills).
  * Executive spacing and breathing room (uncluttered whitespace, generous card padding).
* **Minimalist Canvas Focus**:
  * Keep the UI 90% content-focused: charts, document drafts, and data tables take center stage.
  * Floating voice/chat controls tuck away smoothly when inspecting data.
  * Light-mode default optimized for reading formal documents and board memos.

### 3. Acceptance Criteria
- [ ] Clean, uncluttered layout maintaining single-click access to all actions.
- [ ] Polished executive styling for all rendered tables, charts, and document previews.

---

## FEAT-006: CMD Actionable Employee-Level Roster (Drilldown from Aggregates)

### 1. User Problem Statement
Currently, HR tenure questions (e.g. *Delhi office for 5+ years*) only render an aggregated donut or bar chart showing high-level counts (e.g. 419 executives). A CMD cannot take decisions or initiate transfer actions without seeing the actual names and service histories of the individuals.

### 2. Required Behavior
* **Granular Table Drilldown**: When the CMD asks *"Can you give me a list of all the people who are employed in the Delhi office for more than 5 years? Give me their name, designation, seniority, tenure in ONGC, and time in the Delhi office"*, the system renders an interactive, sortable roster table.
* **Required Column Schema**:
  1. `PERNR` (Employee ID / CPF)
  2. `name` (Full Employee Name)
  3. `designation` (Official ONGC designation, e.g. Chief Manager, DGM)
  4. `grade` (Executive seniority level: E1 to E9)
  5. `discipline` (Domain: Production, Drilling, Finance, HR, IT, Legal)
  6. `total_tenure_years` (Total years of service in ONGC)
  7. `delhi_tenure_years` (Station tenure in Delhi office / WC-DEL)
* **RBAC & Data Privacy Enforcement**:
  * **CMD & Director (HR)**: Full unmasked view with action triggers.
  * **E1–E4 Personas**: Employee names are masked (`******`) or the query is rejected citing ONGC HR Data Privacy Policy Clause 4.2.
* **Direct Transfer Action Triggers**:
  * Row multi-select checkboxes allowing CMD to click individual employees and trigger:
    * *"Draft Transfer Note"* (generates formal transfer proposal document).
    * *"Export to Excel / PDF"* (downloads active filtered list).

### 3. Acceptance Criteria
- [ ] Asking for employee names in Delhi for 5+ years returns individual rows, not just aggregate counts.
- [ ] Columns include Name, Designation, Grade, Total Tenure, and Delhi Station Tenure.
- [ ] Table supports sorting by tenure and filtering by discipline/grade.
- [ ] E1 persona is blocked from seeing individual colleague names.


