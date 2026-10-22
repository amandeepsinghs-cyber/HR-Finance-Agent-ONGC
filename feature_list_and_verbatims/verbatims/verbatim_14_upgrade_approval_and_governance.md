# Verbatim 14: Upgrade Approval, Governance, UI-First Order & Granular-Data RBAC Policy

**Date Captured**: October 22, 2026, 05:21 UTC  
**Source**: User Chat Directive  
**Persona**: Product Sponsor / CMD Interaction Lead  
**Tags**: `#governance` `#build-process` `#ui-first` `#rbac` `#granular-data` `#baseline`

---

## 1. Verbatim Transcript

> "1. yes I approve the build but we should have a build.md file, a feature list and a step by step upgrade checklist.md before doing anything. We should have a robust documentation and confirmation mechanism and review mechanism so that we have a robust build. I will go with the UI first as it changes the feel and UI is ultimately tied to the brain as you said. See with names or any other data my idea is to show and expose the granular data on the CMD and Director level. On the E1-E4 level it can be aggregated summary or rejection. yes commit the current version first and say it as a baseline build."

---

## 2. Decisions Extracted

| # | Decision | Effect |
|---|---|---|
| D-1 | **Approve the brain re-architecture** (QuerySpec planner, governed semantic layer, insight engine) | Brain phases B1–B4 in `UPGRADE_CHECKLIST.md` |
| D-2 | **Documentation before code**: `BUILD.md`, feature list, and a step-by-step `UPGRADE_CHECKLIST.md` must exist before any upgrade work | No code changes until docs are confirmed |
| D-3 | **Robust confirmation + review mechanism** for every step | Gate process defined in `BUILD.md` §4 |
| D-4 | **UI first**, then the brain (the UI is tied to the brain, so UI contracts must be forward-compatible) | Phase order U0 → U5, then B1 → B4, then H1 |
| D-5 | **Granular data policy**: CMD and Director personas see granular data (names and other individual-level fields). E1–E4 personas get an **aggregated summary or a rejection** | RBAC policy in `feature_list.md` FEAT-010 |
| D-6 | **Commit the current version as the baseline build** | Commit `fbe3594`, tag `baseline-v0.2` (local, not pushed) |
