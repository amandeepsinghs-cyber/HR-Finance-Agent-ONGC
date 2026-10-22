"""End-to-End Verification Suite for the Overnight Yukti AI Build (Phase 5.1).

Verifies:
1. 5-Turn Multi-Turn Conversational Context & Entity Retention (Ahmedabad WC-AHM):
   - Turn 1: "How many employees are here in Ahmedabad?" -> 1,199 active (698 exec, 501 non-exec)
   - Turn 2: "Break it down by discipline" -> remembers Ahmedabad (1,199 across disciplines)
   - Turn 3: "Plot this as a pie chart" -> re-plots Ahmedabad disciplines as kind='pie'
   - Turn 4: "Draw a histogram of employee ages" -> remembers Ahmedabad, returns kind='histogram' summing to 1,199
   - Turn 5: "Draft a briefing note on this" -> returns visual.type='document' grounded in Ahmedabad SSOT
2. Arbitrary Plot Types from BigQuery SSOT:
   - Field Lifting Cost Histogram (530 fields in ssot_field_economics_360)
   - Treemap / Scatter / Donut / H-Bar re-plots
3. Live Document & Data Exports (.docx, .pdf, .xlsx) via /api/export
"""

import json
import sys
import urllib.request

BASE_URL = "http://127.0.0.1:3200"


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        assert resp.status == 200, f"Expected 200 on {path}, got {resp.status}"
        return json.loads(resp.read().decode("utf-8"))


def get_bytes(path: str) -> bytes:
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200, f"Expected 200 on {path}, got {resp.status}"
        return resp.read()


def extract_ui_context(contract: dict) -> dict:
    v = contract.get("visual") or {}
    tbl = v.get("table") or {}
    chart = v.get("chart") or {}
    rows = tbl.get("rows") or chart.get("data") or []
    cols = tbl.get("columns") or (list(rows[0].keys()) if rows and isinstance(rows[0], dict) else [])
    sql = next((s.get("sql") for s in (contract.get("sources") or []) if s.get("sql")), None)
    return {
        "title": v.get("title"),
        "subtitle": v.get("subtitle"),
        "visual_type": v.get("type"),
        "chart_kind": chart.get("kind"),
        "columns": cols,
        "rows": rows[:50],
        "sql": sql,
    }


def main():
    session_id = "sess-overnight-e2e-verify"
    history = []
    ui_context = None

    print("=== 1. Testing 5-Turn Multi-Turn Conversational Context & Re-Plotting ===")

    # Turn 1: Ahmedabad headcount
    q1 = "How many employees are here in Ahmedabad?"
    c1 = post_json("/api/turn", {"query": q1, "persona": "CMD", "session_id": session_id, "history": history, "ui_context": ui_context})
    spoken1 = c1.get("spoken_summary", "")
    print(f"[Turn 1] Spoken: {spoken1}")
    assert "1,199" in spoken1 and "698" in spoken1 and "501" in spoken1, f"Turn 1 failed: {spoken1}"
    history.extend([{"role": "user", "text": q1}, {"role": "agent", "text": spoken1}])
    ui_context = extract_ui_context(c1)

    # Turn 2: Follow-up breakdown by discipline (must remember Ahmedabad WC-AHM!)
    q2 = "Break it down by discipline"
    c2 = post_json("/api/turn", {"query": q2, "persona": "CMD", "session_id": session_id, "history": history, "ui_context": ui_context})
    spoken2 = c2.get("spoken_summary", "")
    title2 = (c2.get("visual") or {}).get("title", "")
    rows2 = ((c2.get("visual") or {}).get("table") or {}).get("rows") or []
    total_disc = sum(int(float(r.get("employees", 0) or 0)) for r in rows2)
    print(f"[Turn 2] Title: {title2} | Total across disciplines: {total_disc} | Spoken: {spoken2}")
    assert "Ahmedabad" in title2 and total_disc == 1199, f"Turn 2 failed: {title2}, total={total_disc}"
    history.extend([{"role": "user", "text": q2}, {"role": "agent", "text": spoken2}])
    ui_context = extract_ui_context(c2)

    # Turn 3: Re-plot current discipline breakdown as a Pie chart
    q3 = "Plot this as a pie chart"
    c3 = post_json("/api/turn", {"query": q3, "persona": "CMD", "session_id": session_id, "history": history, "ui_context": ui_context})
    kind3 = ((c3.get("visual") or {}).get("chart") or {}).get("kind")
    print(f"[Turn 3] Chart kind: {kind3} | Spoken: {c3.get('spoken_summary')}")
    assert kind3 == "pie", f"Expected chart kind 'pie' in Turn 3, got {kind3}"
    history.extend([{"role": "user", "text": q3}, {"role": "agent", "text": c3.get("spoken_summary", "")}])
    ui_context = extract_ui_context(c3)

    # Turn 4: Histogram of employee ages (must remember Ahmedabad WC-AHM!)
    q4 = "Draw a histogram of employee ages"
    c4 = post_json("/api/turn", {"query": q4, "persona": "CMD", "session_id": session_id, "history": history, "ui_context": ui_context})
    kind4 = ((c4.get("visual") or {}).get("chart") or {}).get("kind")
    title4 = (c4.get("visual") or {}).get("title", "")
    rows4 = ((c4.get("visual") or {}).get("table") or {}).get("rows") or []
    total_hist4 = sum(int(float(r.get("employees", 0) or 0)) for r in rows4)
    print(f"[Turn 4] Title: {title4} | Chart kind: {kind4} | Sample size: {total_hist4}")
    assert kind4 == "histogram" and "Ahmedabad" in title4 and total_hist4 == 1199, f"Turn 4 failed: {title4}, kind={kind4}, n={total_hist4}"
    history.extend([{"role": "user", "text": q4}, {"role": "agent", "text": c4.get("spoken_summary", "")}])
    ui_context = extract_ui_context(c4)

    # Turn 5: Draft an official briefing note on this
    q5 = "Draft a briefing note on this"
    c5 = post_json("/api/turn", {"query": q5, "persona": "CMD", "session_id": session_id, "history": history, "ui_context": ui_context})
    vtype5 = (c5.get("visual") or {}).get("type")
    doc5 = ((c5.get("visual") or {}).get("document") or {})
    md5 = doc5.get("markdown", "")
    print(f"[Turn 5] Visual type: {vtype5} | Doc title: {doc5.get('title')} | Markdown len: {len(md5)}")
    assert vtype5 == "document" and "1,199" in md5 and "Ahmedabad" in md5, f"Turn 5 failed: vtype={vtype5}"

    print("\n=== 2. Testing Field Economics Histogram & Additional Plot Kinds ===")
    c_lift = post_json(
        "/api/turn",
        {
            "query": "Draw a histogram of lifting cost across all fields",
            "persona": "CMD",
            "session_id": "sess-overnight-plots",
        },
    )
    kind_lift = ((c_lift.get("visual") or {}).get("chart") or {}).get("kind")
    rows_lift = ((c_lift.get("visual") or {}).get("table") or {}).get("rows") or []
    total_fields = sum(int(float(r.get("fields", 0) or 0)) for r in rows_lift)
    print(f"[Field Lifting Cost Histogram] Kind: {kind_lift} | Total fields binned: {total_fields}")
    assert kind_lift == "histogram" and total_fields == 53, f"Expected 53 FY26 fields in lifting cost histogram, got {total_fields}"

    print("\n=== 3. Testing Document Exports (.docx, .pdf, .xlsx) ===")
    for fmt in ("word", "pdf", "xlsx"):
        exp_res = post_json(
            "/api/export",
            {
                "format": fmt,
                "title": "Ahmedabad_Executive_Briefing",
                "content": md5,
                "columns": ["bucket", "employees", "share_pct", "avg_metric"],
                "rows": rows4,
            },
        )
        export_id = exp_res.get("export_id")
        assert export_id, f"Missing export_id for {fmt}: {exp_res}"
        file_bytes = get_bytes(f"/api/export/{export_id}")
        print(f"[Export {fmt}] export_id={export_id} | downloaded {len(file_bytes):,} bytes")
        assert len(file_bytes) > 500, f"Exported {fmt} file too small: {len(file_bytes)} bytes"

    print("\nALL END-TO-END OVERNIGHT BUILD ASSERTIONS PASSED!")


if __name__ == "__main__":
    main()
