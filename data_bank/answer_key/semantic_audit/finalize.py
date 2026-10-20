"""Rebuild answer_key/INDEX.md from the current SQL/JSON/MD and assemble
answer_key/AUDIT_SEMANTIC_2026-10-20.md from semantic_audit/changes_*.yaml + data_defects_*.yaml.

Usage (from data_bank/answer_key):  uv run python -m semantic_audit.finalize
"""

from __future__ import annotations

import datetime
import json
import re
from collections import Counter, defaultdict

import yaml

from semantic_audit import common as C

INDEX_PATH = C.AK_DIR / "INDEX.md"
AUDIT_PATH = C.AK_DIR / "AUDIT_SEMANTIC_2026-10-20.md"
REFUSAL_ROOTS = {"D1", "D2", "D3", "D4", "D5", "D6"}  # overwritten from build_answer_key.REFUSAL_MAP below


def _refusal_roots():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bak", C.AK_DIR / "build_answer_key.py")
    bak = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bak)
    return set(bak.REFUSAL_MAP)


def _old_index_rows():
    rows = {}
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \| \*\*(\w+)\*\* \| `(\d+)` \| `([^`]*)` \| (.*?) \| (.*) \|$", line)
        if m:
            rows[m.group(1)] = {"gold": m.group(7), "assumptions": m.group(8), "headline": m.group(9)}
    return rows


def load_yaml_lists(prefix):
    out = []
    for p in sorted(C.AUDIT_DIR.glob(f"{prefix}_*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or []
        for d in data:
            d["_slice"] = p.stem.split("_", 1)[1] if prefix == "changes" else p.stem.split("_", 2)[2]
        out.extend(data)
    return out


def build_index(changes):
    qm = C.question_map()
    refusal_roots = _refusal_roots()
    old = _old_index_rows()
    gap_ids = {c["id"] for c in changes if "GAP" in (c.get("defect_class") or []) and c.get("status_gap")}
    changed_ids = {c["id"] for c in changes}
    order = []
    data = yaml.safe_load(C.QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]
    for q in data:
        order.append(q["id"])
        order.extend(f"{q['id']}__{fu['kind']}" for fu in q.get("followups", []))

    answered = refusals = gaps = 0
    total_bytes = 0
    lines = []
    for eid in order:
        meta = qm[eid]
        res = C.load_json(eid)
        total_bytes += res.get("total_bytes_processed", 0)
        root = eid.split("__")[0]
        if root in refusal_roots and (meta["parent"] is None or meta["kind"] == "why"):
            status = "refusal"; refusals += 1
        elif res["row_count"] == 0 or eid in gap_ids:
            status = "gap"; gaps += 1
        else:
            status = "answered"; answered += 1
        md = C.md_path(eid).read_text(encoding="utf-8")
        headline = C.headline_from_md(md) or old.get(eid, {}).get("headline", "")
        if status == "refusal":
            headline = old.get(eid, {}).get("headline", headline)
        o = old.get(eid, {"gold": "hrfin_silver, hrfin_gold", "assumptions": ""})
        note = o["assumptions"].replace(" — semantic-audit 2026-10-20 corrected", "")
        if eid in changed_ids:
            note = (note + " — semantic-audit 2026-10-20 corrected").strip(" —")
            g = next((c.get("gold_objects") for c in changes if c["id"] == eid and c.get("gold_objects")), None)
            if g:
                o = dict(o, gold=g)
        lines.append(f"| `{eid}` | `{meta['parent'] or '-'}` | `{meta['kind'] or 'root'}` | `{meta['type']}` | **{status.upper()}** | "
                     f"`{res['row_count']}` | `{o['gold']}` | {note} | {headline.replace('|', '/')} |")

    n = len(order)
    head = [
        "# ONGC Data Bank — Answer Key & Follow-Up Verification Index",
        "",
        f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} (semantic audit 2026-10-20 applied — see `AUDIT_SEMANTIC_2026-10-20.md`)",
        f"**GCP Project:** `{C.PROJECT_ID}` | **Datasets:** `hrfin_gold`, `hrfin_silver`, `hrfin_docs`",
        f"**Total Entries:** `{n}` (`89` Root Questions + `{n - 89}` Follow-ups)",
        f"**Audit Status:** `{answered}` Answered, `{refusals}` Refusals, `{gaps}` Gaps",
        f"**Total BigQuery Bytes Processed:** `{total_bytes:,}` bytes ({round(total_bytes / (1024 * 1024), 2)} MB)",
        "",
        "## Summary Statistics",
        "| Category | Count | Percentage |",
        "|---|---|---|",
        f"| **Answered (Data & Policy)** | {answered} | {round(answered / n * 100, 1)}% |",
        f"| **Documented Refusals** | {refusals} | {round(refusals / n * 100, 1)}% |",
        f"| **Data Gaps** | {gaps} | {round(gaps / n * 100, 1)}% |",
        f"| **Total Evaluated** | {n} | 100.0% |",
        "",
        "## Complete Answer Key Ledger",
        "| Entry ID | Parent | Kind | Type | Status | Rows | Gold Objects Used | Key Assumptions / Notes | Headline Answer / Citation |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    INDEX_PATH.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    return answered, refusals, gaps


def build_audit(changes, defects, sanity_md):
    cls = Counter()
    sev = Counter()
    for c in changes:
        for k in c.get("defect_class") or []:
            cls[k] += 1
        sev[c.get("severity", "n/a")] += 1
    semantic = [c for c in changes if set(c.get("defect_class") or []) - {"GENERIC_TEXT", "CASE_HYGIENE"}]
    out = [
        "# Semantic Audit of the Answer Key — 2026-10-20",
        "",
        f"**Scope:** 89 root + 267 follow-up SQLs, expected JSONs and answer MDs. **Entries changed:** {len(changes)} "
        f"({len(semantic)} with a semantic/SQL defect; {len(changes) - len(semantic)} narrative-only).",
        "",
        "Tooling: `semantic_audit/` (`run_entry.py` re-executes + renders, `narratives_*.py` render answers from result rows, "
        "`sanity_checks.py` automated checks, `finalize.py` rebuilds this file and INDEX.md). Pre-change snapshot kept outside the repo.",
        "",
        "## Counts by defect class (an entry can carry several classes)",
        "| Defect class | Entries |",
        "|---|---|",
    ]
    out += [f"| `{k}` | {v} |" for k, v in cls.most_common()]
    out += ["", "| Severity | Entries |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sev.most_common()]
    out += ["", "## Change log", "| id | defect class | severity | old headline | new headline | why |", "|---|---|---|---|---|---|"]

    def key(c):
        rank = {"blocking": 0, "important": 1, "cosmetic": 2}.get(str(c.get("severity", "")).lower(), 3)
        return (rank, c["id"])

    for c in sorted(changes, key=key):
        esc = lambda s: str(s or "").replace("|", "/").replace("\n", " ")
        out.append(f"| `{c['id']}` | {', '.join(c.get('defect_class') or [])} | {esc(c.get('severity'))} | {esc(c.get('old_headline'))} | "
                   f"{esc(c.get('new_headline'))} | {esc(c.get('why'))} |")
    out += ["", "## Data defects found in silver/gold (reported, NOT fixed)", "| table | issue | evidence | impacted ids |", "|---|---|---|---|"]
    for d in defects:
        esc = lambda s: str(s or "").replace("|", "/").replace("\n", " ")
        ids = d.get("impact_on_ids") or []
        out.append(f"| `{esc(d.get('table'))}` | {esc(d.get('issue'))} | {esc(d.get('evidence'))} | {esc(', '.join(map(str, ids)) if isinstance(ids, list) else ids)} |")
    out += ["", "## Automated sanity checks (post-fix)", sanity_md]
    AUDIT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    import io
    import contextlib
    from semantic_audit import sanity_checks as S
    changes = load_yaml_lists("changes")
    defects = load_yaml_lists("data_defects")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            S.main([])
        except SystemExit:
            pass
    sanity = buf.getvalue()
    a, r, g = build_index(changes)
    build_audit(changes, defects, sanity)
    print(f"INDEX: answered={a} refusals={r} gaps={g}; changes={len(changes)} defects={len(defects)}")


if __name__ == "__main__":
    main()
