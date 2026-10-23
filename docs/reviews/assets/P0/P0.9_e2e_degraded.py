"""P0.9 r2: end-to-end degraded turn in the image layout WITHOUT financial_build/data, real outage.

Run from <layout>/yukti/backend with YUKTI_FORCE_BQ_FAIL=1 and GOOGLE_APPLICATION_CREDENTIALS=<scratch>/invalid.json.
"""
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())
from app.config import ROOT_DIR  # noqa: E402
from app.turn_runner import AgentTurnRunner  # noqa: E402

print("ROOT_DIR =", ROOT_DIR, "| snapshot dir exists:", (ROOT_DIR / "financial_build" / "data").exists())
print("GOOGLE_APPLICATION_CREDENTIALS =", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), "| YUKTI_FORCE_BQ_FAIL =", os.getenv("YUKTI_FORCE_BQ_FAIL"))


async def main():
    r = AgentTurnRunner(model_name="gemini-2.5-flash")
    c = await r.execute_turn_async("Show the balance sheet for FY24", session_id="p09-r2-degraded", persona="CMD")
    vis = c.get("visual") or {}
    rows = (vis.get("table") or {}).get("rows") or []
    chart_rows = ((vis.get("chart") or {}).get("data")) or []
    blob = json.dumps(c, ensure_ascii=False, default=str)
    nums = re.findall(r"\d[\d,]{3,}(?:\.\d+)?", c.get("display_text", "") + " " + c.get("spoken_summary", ""))
    print(json.dumps({
        "display_text": c.get("display_text"),
        "spoken_summary": c.get("spoken_summary"),
        "status": c.get("status"),
        "provenance": c.get("provenance"),
        "visual.type": vis.get("type"),
        "table_rows": len(rows), "chart_points": len(chart_rows),
        "numbers_in_text": nums,
        "status_events": c.get("status_events"),
        "leaks": [m for m in ("Reauthentication", "RefreshError", "Traceback", "invalid.json", "ongc-hr-finance-agent",
                              "DefaultCredentialsError") if m in json.dumps({k: c.get(k) for k in ("display_text", "spoken_summary", "insights", "visual")}, ensure_ascii=False)],
    }, ensure_ascii=False, indent=1))


asyncio.run(main())
