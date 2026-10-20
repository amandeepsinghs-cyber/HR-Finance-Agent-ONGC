"""Automated semantic sanity checks over every answer-key entry (SQL + expected JSON + MD).

Usage (from data_bank/answer_key):  uv run python -m semantic_audit.sanity_checks [--md OUT.md]
Exit code 1 if any BLOCKING finding remains.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict

from semantic_audit import common as C

HC_COL = re.compile(r"(^|_)(headcount|hc|employees?|staff|staff_count|emp_count|regular_headcount|in_position)(_|$)", re.I)
PCT_COL = re.compile(r"(pct|percent|rate_pct|share|ratio_pct)$", re.I)
PCT_OK_OVER_100 = re.compile(r"growth|change|variance|overrun|delta|yoy|vs_|increase|decline|diff|utilisation|achievement|escalation|roce|margin|cagr|slippage|dev|funded", re.I)
# Company-level March period-end headcount (headcount_snapshot) FY13..FY26 - legitimate values > 23,117
COMPANY_HC_BY_FY = {32923, 33911, 33185, 33927, 33660, 32265, 31065, 30105, 28479, 27165, 25993, 25847, 24368, 23117}
CATEGORICAL_COLS = ("status", "gender", "category", "cadre", "type", "severity", "mode", "stage", "decision",
                    "forum", "theme", "channel", "bucket", "rating", "readiness", "tier", "outcome", "class",
                    "line_type", "employment_status", "separation_type", "posting_type", "incident_type")


def entries():
    qm = C.question_map()
    return sorted(qm)


def check_entry(eid, findings):
    sql_raw = C.sql_path(eid).read_text(encoding="utf-8")
    sql = C.clean_sql(sql_raw)
    sql_l = sql.lower()
    res = C.load_json(eid)
    md = C.md_path(eid).read_text(encoding="utf-8")
    rows = res.get("rows", [])

    def add(sev, cls, msg):
        findings.append({"id": eid, "severity": sev, "class": cls, "msg": msg})

    # ---- static SQL checks
    if "headcount_snapshot" in sql_l and not re.search(r"\bmonth\b\s*(=|in\b|>=|<=|between)|max\(month\)|month\s*=\s*\(", sql_l):
        if re.search(r"sum\s*\([^;]{0,120}?\b(\w+\.)?(headcount|active_headcount)\b", sql_l):
            add("BLOCKING", "STOCK_SUMMED", "SUM(headcount) over headcount_snapshot without a single-month filter")
    if re.search(r"sum\s*\(\s*\w*\.?contractor_headcount", sql_l) and not re.search(r"\bmonth\b\s*(=|in\b)|max\(month\)|avg\(|/\s*12|count\(distinct\s+\w*\.?month", sql_l):
        add("WARN", "STOCK_SUMMED", "SUM(contractor_headcount) without month restriction/average (person-months?)")
    if re.search(r"oil_production_mt[^,;\n]*[+][^,;\n]*gas_production_mmscm|gas_production_mmscm[^,;\n]*[+][^,;\n]*oil_production_mt", sql_l):
        add("BLOCKING", "UNIT_MIXING", "adds oil (MT) and gas (MMSCM) in one expression")
    if re.search(r"sum\s*\(\s*\w*\.?(outstanding_amount_inr_cr|net_liability_inr_cr|actuarial_liability_inr_cr|reserves_2p_total_mmtoe|active_producing_wells)", sql_l) \
            and not re.search(r"fiscal_year\s*(=|in\s*\(\s*'fy\d\d'\s*\))|month\s*=|group by[^;]*fiscal_year|outstanding_amount_inr_cr\s*>\s*0", sql_l):
        add("WARN", "STOCK_SUMMED", "SUM of a balance/stock measure without a single-period filter")
    if "mart_corporate_performance" in sql_l:
        add("WARN", "JOIN_FANOUT", "uses multi-grain mart_corporate_performance")
    for col in CATEGORICAL_COLS:
        for m in re.finditer(rf"(?<!lower\()\b(\w+\.)?{col}\s*(=|in)\s*\(?\s*'([^']*)'", sql_l):
            pass
    raw_cat = [m.group(0) for m in re.finditer(r"(?<!lower\()\b(?:\w+\.)?(" + "|".join(CATEGORICAL_COLS) + r")\s*=\s*'[^']*'", sql, re.I)]
    if raw_cat:
        add("INFO", "CASE_HYGIENE", f"categorical literal filter without LOWER(): {raw_cat[:3]}")

    # ---- result checks
    if res.get("row_count", 0) == 0:
        add("BLOCKING", "EMPTY", "0 rows")
    for r in rows:
        for k, v in r.items():
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if HC_COL.search(k) and "per_" not in k.lower() and v > C.COMPANY_HC_FY26_END and int(v) not in COMPANY_HC_BY_FY and not re.search(r"sanction|strength|month|person|cum|total_|sum_|fy2[2-5]|fy1|fy20|fy21|2021|2013", k, re.I):
                add("BLOCKING", "SANITY_BOUND", f"{k}={v} exceeds company headcount {C.COMPANY_HC_FY26_END}")
            if PCT_COL.search(k) and (v > 100.0001 or v < -100.0001) and not PCT_OK_OVER_100.search(k):
                add("WARN", "PCT_DENOM", f"{k}={v} outside [-100,100]")
        fy = str(r.get("fiscal_year", ""))
        if fy == "FY26" and "gross_revenue_inr_cr" in r and len([c for c in r if c.endswith("_id") or c.endswith("name")]) == 0:
            if abs(float(r["gross_revenue_inr_cr"] or 0) - C.REVENUE_FY26_CR) > 1:
                add("BLOCKING", "SANITY_BOUND", f"company FY26 revenue {r['gross_revenue_inr_cr']} != {C.REVENUE_FY26_CR}")

    # ---- follow-up vs parent
    q = C.question_map()[eid]
    if q["parent"]:
        if C.load_json(q["parent"])["rows"] == rows:
            add("BLOCKING", "IDENTICAL_TO_PARENT", f"same rows as {q['parent']}")

    # ---- MD
    if C.GENERIC_MARKER in md:
        add("BLOCKING", "GENERIC_TEXT", "generic template narrative")


def main(argv):
    if "--base" in argv:  # audit a snapshot copy (same layout) instead of the live answer key
        from pathlib import Path
        b = Path(argv[argv.index("--base") + 1])
        C.SQL_DIR, C.EXPECTED_DIR, C.ANSWERS_DIR, C.FOLLOWUPS_DIR = b / "sql", b / "expected", b / "answers", b / "followups"
    findings = []
    for eid in entries():
        check_entry(eid, findings)
    by = defaultdict(int)
    for x in findings:
        by[(x["severity"], x["class"])] += 1
    lines = ["| Severity | Class | Count |", "|---|---|---|"]
    for (s, c), n in sorted(by.items()):
        lines.append(f"| {s} | {c} | {n} |")
    detail = ["", "| id | severity | class | detail |", "|---|---|---|---|"]
    for x in findings:
        if x["severity"] != "INFO":
            detail.append(f"| `{x['id']}` | {x['severity']} | {x['class']} | {x['msg'].replace('|', '/')} |")
    out = "\n".join(lines + detail)
    print(out)
    if "--md" in argv:
        p = argv[argv.index("--md") + 1]
        open(p, "w", encoding="utf-8").write(out)
    if "--json" in argv:
        p = argv[argv.index("--json") + 1]
        open(p, "w", encoding="utf-8").write(json.dumps(findings, indent=1))
    blocking = [x for x in findings if x["severity"] == "BLOCKING"]
    print(f"\nBLOCKING={len(blocking)} WARN={sum(1 for x in findings if x['severity']=='WARN')} INFO={sum(1 for x in findings if x['severity']=='INFO')}")
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
