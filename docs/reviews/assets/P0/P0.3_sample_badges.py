"""P0.3 evidence: sample 20 answers (10 live BigQuery on :8095, 10 forced-BQ-failure on :8096) and check badges."""
import json
import re
import sys
import urllib.request

FALSE = re.compile(r"Audited|Yahoo|ONGC\.NS")
COMPILED = re.compile(r"Compiled .* SQL|dry-run")

QS = [
    "Show the income statement for FY24",
    "Show the balance sheet for FY 2024-25",
    "Show the cash flow statement for FY23",
    "What are ONGC's key financial ratios for FY25?",
    "Profit and loss trend over the last 5 years",
    "Balance sheet trend from FY20 to FY25",
    "How many executives are posted in Delhi?",
    "Headcount by discipline",
    "Which fields made losses in FY26?",
    "Show the cash flow trend over the last 5 years",
]


def turn(port, q, i):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/turn",
        data=json.dumps({"query": q, "persona": "CMD", "session_id": f"p03-sample-{port}-{i}"}).encode(),
        headers={"content-type": "application/json", "authorization": f"Bearer {TOKENS.get(port, '')}"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def visible(c):
    vis = dict(c.get("visual") or {})
    if isinstance(vis.get("table"), dict):
        vis["table"] = {k: v for k, v in vis["table"].items() if k != "rows"}
    if isinstance(vis.get("chart"), dict):
        vis["chart"] = {k: v for k, v in vis["chart"].items() if k != "data"}
    keep = {k: c.get(k) for k in ("display_text", "spoken_summary", "insights", "sources", "caveat", "status_events")}
    keep["visual"] = vis
    return json.dumps(keep, ensure_ascii=False)


TOKENS = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
TOKENS = {int(k): v for k, v in TOKENS.items()}
rows, bad = [], 0
for port in (8095, 8096):
    for i, q in enumerate(QS):
        try:
            c = turn(port, q, i)
        except Exception as e:  # noqa: BLE001
            rows.append((port, q, "ERROR", type(e).__name__, "", "")); bad += 1
            continue
        src = (c.get("status") or {}).get("source") or ("legacy" if not c.get("query_spec") else "?")
        txt = visible(c)
        false_hits = sorted(set(FALSE.findall(txt)))
        compiled_hit = bool(COMPILED.search(txt))
        ok = not false_hits and (src != "local_snapshot" or (not compiled_hit and "local snapshot" in (c.get("caveat") or "").lower()))
        if port == 8096 and src not in ("local_snapshot",) and c.get("query_spec"):
            ok = False  # forced failure: a planner answer must be local_snapshot
        bad += 0 if ok else 1
        rows.append((port, q, src, ",".join(false_hits) or "-", "yes" if compiled_hit else "no", "OK" if ok else "BAD"))
print("| port | question | status.source | false labels | 'Compiled/dry-run' text | verdict |")
print("|---|---|---|---|---|---|")
for r in rows:
    print("| " + " | ".join(str(x) for x in r) + " |")
print(f"\nBAD = {bad} / {len(rows)}")
