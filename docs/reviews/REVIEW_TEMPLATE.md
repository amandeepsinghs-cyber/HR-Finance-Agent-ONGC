# Review: `<STEP-ID>` <Step title>

**Reviewer:** <independent reviewer agent / human> · **Date:** YYYY-MM-DD · **Branch / diff:** `upgrade/<phase>` @ `<sha>`
**Spec:** [`UPGRADE_CHECKLIST.md`](../../UPGRADE_CHECKLIST.md), row `<step-id>` · **Features:** FEAT-0xx
**Executor model:** O (Opus) | F (`flash`) | FL (`flash_lite`) · **Reviewer model:** Opus (`inherit`, fresh context, read-only). It must differ from the executor's context, and is never a Flash model.
**Task packet:** [`docs/delegation/packets/<step-id>.md`](../delegation/packets/) (F/FL steps) · **Strike count:** 0 | 1 | 2 (2 → step moves to Opus, per `DELEGATION.md` §3)

## Verdict
**APPROVE** | **CHANGES REQUESTED** | **BLOCKED (needs decision)**. One-line reason.

## 1. Acceptance criteria
| # | Criterion (copied from spec) | Met? | Evidence (command output / screenshot / file:line) |
|---|---|---|---|
| 1 | | ✅ / ❌ | |

## 2. Verification evidence (G3)
```text
<commands run and their summarised results: tsc, next build, pytest, eval subset, playwright, bq spot checks>
```
Screenshots (light + dark if UI): `docs/reviews/assets/<step-id>_*.png`

## 3. Review checklist (BUILD.md §4.1)
- [ ] All acceptance criteria met with evidence
- [ ] No regressions (tests, eval, build)
- [ ] RBAC respected; text and visual agree
- [ ] No hardcoded data or codes that belong in data/config
- [ ] No secrets, generated artefacts or unrelated changes
- [ ] Light/dark and accessibility OK
- [ ] Performance OK (no blocking calls; ~60 fps animations)
- [ ] Docs updated (feature status, checklist, decisions)
- [ ] *(F/FL steps)* Only files listed in the packet changed; packet's do-not-touch list respected
- [ ] *(F/FL steps)* Consistency: design tokens, naming, contract fields and patterns match neighbouring code

## 4. Findings
| Severity | File:line | Finding | Required change |
|---|---|---|---|
| Blocking / Important / Minor | | | |

## 5. Sponsor confirmation (G5, phase-end only)
- [ ] Confirmed by sponsor on YYYY-MM-DD. Notes:
