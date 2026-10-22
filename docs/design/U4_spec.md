# U4 Spec (G1): Executive Polish of the main app screens

**Status:** awaiting sponsor confirmation (G1) · **Branch:** `upgrade/U4-polish` · **Features:** FEAT-005, FEAT-016 (aura), D-15 (migrate legacy components to primitives)
**Goal:** the main app *looks* different and executive-grade: calm, premium and simple. It is built from the approved U1 foundation (tokens, primitives, chart system, AI aura).
**Baseline to beat:** [`assets/U0/greeting_1920x1080.png`](../reviews/assets/U0/greeting_1920x1080.png), [`c1_delhi_tenure`](../reviews/assets/U0/c1_delhi_tenure_1920x1080.png), [`c6_loss_fields`](../reviews/assets/U0/c6_loss_fields_1920x1080.png)

---

## Screen-by-screen changes

| # | Area | Today | After U4 | Owner |
|---|---|---|---|---|
| **U4.1** | **Top bar** | 7 separate pills spread across a 74 px white bar ("Speaking as CMD", "Ready", "Live", "English", theme) | One quiet **56 px frosted bar**: ONGC mark + "Yukti" on the left; a **single state pill** in the centre (Ready / Listening / Thinking / Speaking, with an aura dot and the live/offline state merged in); on the right a role selector ("Chairman & CEO ▾"), language and theme as `IconButton`s. ≤ 7 controls. | O→F |
| **U4.5** | **Home / greeting** | A large particle sphere on an empty white page, with suggestion text cut off at the bottom | **Aura bloom hero**: "Good morning, Chairman" + one line of intro, then **4 persona-specific suggestion cards** (2 HR, 1 Finance, 1 Policy) with icons. The orb sits small above the greeting; the ribbon orb arrives in U3. | O |
| **U4.6** | **Ask bar** | A plain pill with a blue mic disc and 3 icon buttons | Primitive-based pill with the **AI aura ring** tied to state (idle drift / listening sweep / thinking fast sweep). Mic and send are integrated, and suggestion chips sit above it (never cut off). | O |
| **U4.2** | **Answer header** | "EXECUTIVE BRIEFING" + title + a spoken-summary box | `CardHeader`: eyebrow, title, then **context chips** (`CMD · Delhi HQ · Executives · FY26 · Source: SSOT`), with export and other actions on the right. The spoken summary becomes a quiet lead paragraph. | F |
| **U4.3** | **KPIs, tables, chart switcher** | KPI tiles basic; 11-pill "PLOT VIEW" bar | KPI cards with tabular numbers and **delta pills coloured by meaning** (see Decision 2); table polish (sticky header, zebra rows, inline bars); chart switcher becomes a **compact segmented `Toolbar`** (top 6 types + "More ▾") | O→F |
| **U4.4** | **Voice pill** | The chat panel always floats | When a chart, table or document is full-screen, the chat **collapses to a glowing aura pill** in the corner; it expands on hover or voice. | F |
| **U4.7** | **Newest-answer glow** | n/a | The newest answer card gets a **faint aura edge** that fades after about 4 s ("Yukti just answered") | O |
| **U4.8** | **Legacy migration** | `CanvasView`, panel and top bar use ad-hoc classes | Migrated to U1 primitives (Card, Chip, Badge, Toolbar, IconButton); `lint:tokens` stays clean | F |

## Acceptance (G3/G5)
- Side-by-side **before/after screenshots of the main app** (greeting, a chart answer, a table answer, a refusal, dark mode) at 1440p and 4K.
- Top bar: one row of 56 px or less, 7 controls or fewer. Suggestions are never truncated. The aura appears only on the AI-presence elements (D-16).
- All existing flows still work: typing and voice turns, export, persona switch, theme, language (the Playwright smoke test passes).
- `tsc`, `next build`, `lint:tokens`, `lint:contrast` all clean. Independent G4 review per step.

## Out of scope for U4 (later phases)
- Conversation feed / no screen-clearing → U2
- Ribbon orb → U3
- Roster table, comparison view, any-chart re-plot → U5
- Answer accuracy and insights → B-phases

---

## Decisions needed (G1)
1. **Approve this U4 scope?**
2. **KPI delta colours:** colour by **meaning** (green = good, maroon = bad, so a *falling* vacancy rate shows green), not by direction. *Recommended.*
3. **Greeting copy:** "Good morning/afternoon/evening, Chairman" (time-aware, persona-aware), or keep "Hello, I am Yukti…" (V10)? *Recommended: time-aware greeting + "I'm Yukti, your HR & Finance agent."*
