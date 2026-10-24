# P2H.2 End-to-End Test Report

| Scenario | Persona | Question | Observed Visual Type / Refusal Code | PASS/FAIL | Screenshot |
|---|---|---|---|---|---|
| (a) Persona Picker (Light) | All | N/A | Persona picker opened with 11 personas | **PASS** | [`persona_picker.png`](assets/P2H.2/persona_picker.png) |
| (b) Refusal Card (E2_HR) | E2_HR | pay of Ramesh Kumar | Refusal card with copy line, alternative chips, and Why? disclosure | **PASS** | [`refusal_e2_hr.png`](assets/P2H.2/refusal_e2_hr.png) |
| (b) Refusal Card (Dark) | E2_HR | pay of Ramesh Kumar | Refusal card in dark theme | **PASS** | [`refusal_e2_hr_dark.png`](assets/P2H.2/refusal_e2_hr_dark.png) |
| (c) Permitted Answer | E2_HR | Alternative chip click | Permitted answer displayed | **PASS** | [`permitted_answer_e2_hr.png`](assets/P2H.2/permitted_answer_e2_hr.png) |
| (d) Allowed Aggregate Answer | E3_FIN | average salary of E1 officers | Allowed aggregate answer displayed | **PASS** | [`aggregate_e3_fin.png`](assets/P2H.2/aggregate_e3_fin.png) |
| (e) Function-Scope Refusal (D-43) | DIR_FIN | show Delhi transfer list | Function-scope refusal (D-43) | **PASS** | [`refusal_dir_fin_delhi.png`](assets/P2H.2/refusal_dir_fin_delhi.png) |
| (f) TopBar/Banner CMD | CMD | N/A | TopBar showing CMD persona | **PASS** | [`topbar_cmd.png`](assets/P2H.2/topbar_cmd.png) |

### Console Errors
```
Failed to load resource: the server responded with a status of 401 (Unauthorized)
Failed to load resource: the server responded with a status of 401 (Unauthorized)
```

## Lead verification (24-Oct 05:35)
- **Bug found and fixed:** the persona picker was cut off at the top (Leadership group and title invisible), because the TopBar's `backdrop-blur` made the header the containing block for the `fixed` modal. Fix: the modal is portalled to `<body>` (PersonaPicker.tsx). `persona_picker.png` was re-shot: all 11 personas are visible and the dialog box is at y=111, h=677 in a 1440×900 viewport. The stale dark shot was removed.
- Scenario (e) is mislabelled by the runner. DIR_FIN asking for the Delhi transfer list gets the **aggregate fallback** (counts by grade, with "I can't share individual names at your access level"), not a refusal. This matches SPEC-07 §4.3 (DIR_FIN: names only for DISC-FIN rows, the rest collapsed to counts) and D-43.
- The 401s in the console are the pre-sign-in `/api/auth/session` probe (expected).

## G4 r1 frontend fixes (lead, 24-Oct 05:51)
- **M2 (BEH-01.01): verified live** on :3401 against the P2H backend (:8195).
  - A first visit with no cookie shows the **blocking** picker: no close button, and Escape does nothing.
  - The TopBar reads "Sign in as…".
  - **0** calls to /api/turn, /api/auth/session or /ws/live before a pick.
  - Picking Asha Mishra → `POST /api/auth/session` → TopBar "E3 · Finance · Asha Mishra"; the picker closes.
  - Evidence: [`first_visit_signin.png`](assets/P2H.2/first_visit_signin.png), [`after_signin_e3_fin.png`](assets/P2H.2/after_signin_e3_fin.png).
- **M3:** no CMD fallback anywhere in the frontend.
  - TopBar shows a "Sign in as…" state.
  - CanvasView gives no starters and no name for an unknown persona.
  - The AnswerCard role chip is empty, not "CMD".
  - websocketClient defaults are `''`.
  - `grep "'CMD'"` now finds only the persona enum and directory.
- **M4 (frontend part):** RefusalRenderer de-duplicates chips by label and question, and in Hindi asks `question_hi` (and shows `label_hi`). The backend `question_hi` comes with rbac's fix.
- The broken dark-picker link was removed. Scenario (c) and the Hindi refusal shot are re-shot after the backend M1/M4 fixes land.
