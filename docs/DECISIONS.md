# Yukti AI: Decision Log (`DECISIONS.md`)

Every decision that changes scope, behaviour, policy or process is recorded here with its source. **Open decisions block the steps listed against them.**

---

## Confirmed decisions

| ID | Date | Decision | Source | Affects |
|---|---|---|---|---|
| D-1 | 2026-10-22 | Approve the brain re-architecture: QuerySpec planner, generated semantic layer, deterministic insight engine | Verbatim 14 | B1–B4 |
| D-2 | 2026-10-22 | `BUILD.md`, the feature list and `UPGRADE_CHECKLIST.md` must exist and be confirmed **before** any upgrade code | Verbatim 14 | U0 gate |
| D-3 | 2026-10-22 | Five-gate process (Spec → Build → Verify → Review → Confirm) with an independent reviewer and sponsor sign-off | Verbatim 14 | All steps |
| D-4 | 2026-10-22 | **UI first** (U1–U5), then the brain (B1–B4), then hardening (H1). UI defines contract v2 so it is forward-compatible with the brain | Verbatim 14 | Phase order |
| D-5 | 2026-10-22 | **Granular data policy:** CMD and Directors see granular, individual-level data (names, designation, grade, tenure, posting). E1–E4 see an aggregated summary or a refusal | Verbatim 14 | FEAT-010, B3 |
| D-6 | 2026-10-22 | Current version committed as the baseline build: `fbe3594`, tag `baseline-v0.2`, not pushed | Verbatim 14 | Rollback point |
| D-7 | 2026-10-22 | Previous `BUILD.md` (overnight plan) archived to `docs/archive/`; its completion claims are superseded by the 2026-10-22 audit | Agent, per D-2 | Docs |
| D-8 | 2026-10-22 | **Delegation model:** Opus leads design, high-risk code and reviews; Flash implements from task packets; Flash-lite runs evidence; every Flash output is separately reviewed by an Opus reviewer (`DELEGATION.md`) | Sponsor chat 05:26 | All steps |
| D-9 | 2026-10-22 | **Apache ECharts is the visualisation engine** in place of Plotly Dash (V7). It gives the same interactive dashboard behaviour (chart switching, zoom, tooltips, export) inside the Next.js app with no second runtime | Agent proposal; **confirmed by sponsor** (V15) | U5 |

| D-10 | 2026-10-22 | **CMD and Directors (DIR_HR, DIR_FIN) see everything**, including individual pay and APAR. This replaces the current refusals D1/M3/APAR for these personas (implemented in B3) | V15 (OD-2) | FEAT-010, B3 |
| D-11 | 2026-10-22 | **E1–E4:** aggregate by default (no names; cells < 5 suppressed); **refusal** for sensitive personal topics (pay, APAR, vigilance, POSH, medical) | V15 (OD-3) | FEAT-010, B3, U5 |
| D-12 | 2026-10-22 | **Commit cadence:** local commits on `upgrade/*` after each G4-approved step; never push; merge to `main` and tag only at G5 | V15 (OD-4) | All steps |
| D-13 | 2026-10-22 | **Colour system (confirmed for UI/data, see D-16 for the AI layer):** Aurora tokens for the UI system, with ONGC saffron/petroleum blue as brand accents (orb glow, logo, highlights). This is the recommended OD-1 option, adopted on "go ahead"; **the sponsor confirms visually at the U1 gate** | V15 ("go ahead"), agent recommendation | U1, U3 |
| D-14 | 2026-10-22 | **Any-chart re-presentation + chart excellence** become an explicit feature (FEAT-015), with a chart design system in U1 and a compatibility/transform engine in U5 | V15 | FEAT-003, FEAT-015, U1.5, U5.7–U5.9 |
| D-15 | 2026-10-22 | **U1.3 adoption scope:** primitives are built and showcased in U1; legacy `CanvasView`/`FloatingConversationPanel`/`TopBar` migrate in U4 (they are rebuilt there), and new components (TurnCard, U2.3) use primitives from day one. This avoids migrating code that U2/U4 replace. The `/_design` route is renamed `/design-system` (Next.js treats `_`-prefixed folders as private) | Agent (change control, BUILD §4); sponsor sees it at the U1 gate | U1.3, U2.3, U4 |
| D-16 | 2026-10-22 | **AI Aura approved** (Verbatim 16, prototype v3): Google brand hues (#EA4335/#FBBC04/#34A853/#4285F4 + Gemini violet) rendered as feathery pastel light: a thin rotating arc with an outside-only halo on the ask bar and orb, and a pale bloom behind the greeting. **Scope (resolves OD-6): AI-presence elements only**; never data, page backgrounds or text. Supersedes D-13's "ONGC accents" for the AI layer; the UI/data palette from U1 is unchanged and confirmed | Sponsor "yes" 06:57 | U3, U4, FEAT-016 |
| D-17 | 2026-10-22 | **Phase order changed to visual-first:** U4 → U3 → U2 → U5, then B1–B4, H1 (none of these UI phases depends on another's output) | Sponsor 06:45 | Checklist order |
| D-18 | 2026-10-22 | **U1 accepted** (design-system foundation + aura). Merged to `main`, tag `upgrade-U1` | Sponsor (order + aura approval) | U1 |
| D-19 | 2026-10-22 | **U4 scope approved** (docs/design/U4_spec.md) | Sponsor "go ahead" 06:59 | U4 |
| D-20 | 2026-10-22 | **KPI deltas coloured by meaning** (green = good, maroon = bad, per metric polarity; e.g. falling vacancy rate = green) | Recommended default, approved with U4 go-ahead | U4.3 |
| D-21 | 2026-10-22 | **Greeting copy:** time-aware, persona-aware "Good morning, Chairman. I'm Yukti, your HR & Finance agent." | Recommended default, approved with U4 go-ahead | U4.5 |
| D-22 | 2026-10-22 | **Top bar height criterion restated in rem:** `--topbar-h: 3.5rem` on the fluid root scale (≈56 px on laptops, larger on big screens for 5 m legibility) instead of a fixed 56 px (G4 U4 recommendation) | Agent per reviewer; sponsor sees at U4 gate | U4.1 |
| D-23 | 2026-10-22 | **U4.8 legacy-migration deferred to U2:** `CanvasView` is restructured into the conversation feed (TurnCard) in U2, so migrating its remaining ad-hoc classes now would be redone. TopBar and ask bar already use the primitives | Agent (change control); sponsor sees at U4 gate | U4.8, U2 |
---

## Open decisions (need sponsor input)

| ID | Question | Options | Agent recommendation | Blocks |
|---|---|---|---|---|
| ~~**OD-1**~~ → D-13 (provisional) | **Colour system:** the design recommendations use ONGC saffron `#E85D04` and petroleum blue `#0077B6`; the brand guide mandates Google "Aurora" tokens (`#3186FF`, `#4B31E3`, …) | (a) Aurora only (b) ONGC palette only (c) **Aurora for the UI system, ONGC saffron/blue as brand accents (orb glow, logo, highlights)** (d) AlphaEvolve theme (V9; `style_guide/AlphaEvolve Grab & Go Slides.pptx`) as the visual language, with Aurora tokens | **(c)**: respects the brand guide while keeping the ONGC identity | U1, U3 (orb palette) |
| ~~**OD-2**~~ → D-10 | Does D-5 extend to **individual compensation and APAR ratings**? Today these are refused even for Directors, and for the CMD on individual salary (CDA Rules; refusals D1/M3) | (a) **Keep statutory-confidential fields (individual pay, APAR, vigilance, POSH) refused below CMD; CMD sees them** (b) CMD and Directors see everything (c) Keep current rules | **(a)**: honours D-5 for names/postings/tenure and keeps a demonstrable privacy boundary | B3 |
| ~~**OD-3**~~ → D-11 | **E1–E4: when an aggregate, when a refusal?** | (a) **Aggregate by default (no names; cells < 5 suppressed); refuse personal-sensitive topics (pay, APAR, vigilance, POSH, medical)** (b) Always refuse granular asks (c) Always aggregate | **(a)**: shows RBAC both ways in the demo (Verbatim 3) | B3, U5 (masking/aggregate UI states) |
| ~~**OD-4**~~ → D-12 | **Commit cadence within a phase** (your rule: never auto-commit) | (a) Commit only at G5 phase sign-off (b) **Local commits on the `upgrade/*` branch after each G4-approved step; never push; merge to `main` only at G5** | **(b)**: gives a rollback point per step without touching `main` | All steps |
| **OD-5** | **Persona coverage for E1–E4:** today only `E2_HR` and `E3_FIN` exist | (a) Keep both, apply the "junior" policy class to them (b) Add `E1` and `E4` generic personas | **(a)** for now; the policy is defined by class, so adding personas later is trivial | B3 |
