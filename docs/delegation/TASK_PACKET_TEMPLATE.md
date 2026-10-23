# Task Packet: `<STEP-ID>` <title>

**Executor:** F (`flash`) | FL (`flash_lite`) · **Author:** O (Opus) · **Date:** YYYY-MM-DD
**Branch:** `v3/<phase-id>` (BUILD.md §8 names) · **Base SHA:** `<sha>` · **Max files changed:** N · **Budget:** ~N tool calls / stop after 2 failed self-checks · **Features:** FEAT-0xx · **Checklist:** [`UPGRADE_CHECKLIST.md`](../../UPGRADE_CHECKLIST.md) (from a packet in `packets/v3/`, use `../../../../UPGRADE_CHECKLIST.md`), row `<step-id>`
**App root (quote it, the path has spaces and `&`):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal (one sentence)

## 2. Context you need (read these first, nothing else)
- `path/to/file` — why it matters

## 3. Files you may change
- `path/to/file`

## 4. Do NOT touch
- Contract schema / `answerContract.ts` (unless listed above), RBAC/access control, SQL safety, `.env`, lockfiles, generated files
- Any file not in §3. If you need one, **stop and report**.
- **No** `git commit` / `push` / `reset` / `checkout` / `stash`, no deploys, no `bq` writes (DDL/DML), and no destructive commands (`rm -rf`, dropping data). Leave changes uncommitted in the working tree.

## 5. Exact requirements
1.
2.

## 6. Examples / reference patterns
```
<input → expected output, or a snippet of the pattern to follow>
```

## 7. Acceptance criteria (copied into the review)
- [ ]
- [ ]

## 8. Self-check commands (run before reporting)
```bash
cd "<app root>/yukti/frontend" && npx tsc --noEmit
```

## 9. Stop-and-ask triggers
- Spec ambiguous or contradicts the code
- Need a file outside §3, or a type/contract change
- A self-check fails twice

## 10. Report format (reply exactly in this structure)
- **Files changed:** list with 1-line summary each
- **Self-check output:** pass/fail per command (paste the summary)
- **Acceptance criteria:** each ✅/❌ with evidence
- **Open questions / deviations:**
