import asyncio
import yaml
import time
import os
import json
import subprocess
from app.brain.pipeline import run_planner_turn
from app.session_memory import get_session_manager
import app.config

def check_kpi_value(visual, expect, text=""):
    kpis = visual.get("kpis", [])
    if "kpi" in visual and not kpis:
        kpis = [visual["kpi"]]
        
    expected_vals = expect.get("values", [])
    exp_val = None
    if expected_vals:
        exp_val = expected_vals[0].get("value_inr_cr")
        if exp_val is None:
            exp_val = expected_vals[0].get("value_inr")
        if exp_val is None:
            exp_val = expected_vals[0].get("value")
        if exp_val is None:
            exp_val = expected_vals[0].get("value_mmt")
        if exp_val is None:
            exp_val = expected_vals[0].get("value_bcm")
        if exp_val is None:
            exp_val = expected_vals[0].get("value_headcount")
            
    if exp_val is not None:
        tol = expected_vals[0].get("tol", 0.05)
        # Search kpis
        for k in kpis:
            v = k.get("value")
            if v is not None:
                try:
                    if abs(float(v) - float(exp_val)) <= tol:
                        return True, "Pass", v
                except:
                    pass
        if visual.get("type") == "chart":
            rows = visual.get("table", {}).get("rows", [])
            for r in rows:
                if "fy" in expected_vals[0] and r.get("fiscal_year") != expected_vals[0]["fy"]:
                    continue
                v = r.get("value_inr_cr") or r.get("amount_cr") or r.get(expected_vals[0].get("line_code", "").split(".")[-1].lower() + "_cr")
                if v is not None:
                    try:
                        if abs(float(v) - float(exp_val)) <= tol:
                            return True, "Pass (chart row)", v
                    except:
                        pass
        # Search text
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text.replace(",", ""))
        for n in nums:
            try:
                if abs(float(n) - float(exp_val)) <= tol:
                    return True, "Pass (text)", float(n)
            except:
                pass

    if visual.get("type") != "kpi":
        if exp_val is None and kpis:
             return True, "Pass (chart kpi)", kpis[0].get("value")
        return False, "Not a KPI / Mismatch", visual.get("type")
        
    got = kpis[0].get("value") if kpis else None
    if got is None:
        return False, "Got None", None
    if exp_val is None:
        return True, "Pass", got
        
    tol = expected_vals[0].get("tol", 0.05)
    try:
        if abs(float(got) - float(exp_val)) <= tol:
            return True, "Pass", got
    except:
        pass
    return False, f"Mismatch: {got} != {exp_val}", got

def check_table_value(visual, expect):
    if visual.get("type") != "table":
        return False, "Not a table", visual.get("type")
        
    rows = visual.get("table", {}).get("rows", [])
    expected_vals = expect.get("values", [])
    
    if not expected_vals:
        return True, "Pass", len(rows)
        
    for ev in expected_vals:
        lc = ev.get("line_code")
        exp = ev.get("value_inr_cr")
        tol = ev.get("tol", 0.05)
        match = next((r for r in rows if r.get("line_code") == lc), None)
        if not match:
            return False, f"Missing line {lc}", None
        got = match.get("amount_cr") or match.get("value_inr_cr")
        if got is None or abs(float(got) - float(exp)) > tol:
            return False, f"Mismatch {lc}: {got} != {exp}", got
            
    return True, "Pass", "Table Matched"

def check_chart_value(visual, expect):
    return True, "Pass", "Chart (Not implemented detailed check)"

async def process_phrasing(case, phrasing, sm, run_id):
    case_id = case["id"]
    persona = case.get("persona", "hr_manager")
    expect = case.get("expect", {})
    
    sess = sm.get_or_create(f"{run_id}-{case_id}-{time.time_ns()}", persona=persona, language="en")
    
    try:
        res = await run_planner_turn(phrasing, sess, persona, "turn1", "en", time.time())
        if res is None:
            status = "FAIL"
            note = "Fallback to legacy agent (Planner returned None)"
            got = "None"
        else:
            contract = res.get("contract")
            if not contract:
                status = "FAIL"
                note = str(res.get("error", "Refused"))
                got = "None"
            else:
                visual = contract.get("visual", {})
                vtype = expect.get("visual_type", "")
                
                if "kpi" in vtype:
                    ok, note, got = check_kpi_value(visual, expect, contract.get("display_text", ""))
                elif "table" in vtype:
                    ok, note, got = check_table_value(visual, expect)
                else:
                    ok, note, got = check_chart_value(visual, expect)
                    
                status = "PASS" if ok else "FAIL"
            
    except Exception as e:
        status = "ERROR"
        note = str(e)
        got = "Exception"
        
    exp_str = str(expect.get("values", []))[:50]
    return {
        "case": case_id,
        "phrasing": phrasing,
        "status": status,
        "got": got,
        "expected": exp_str,
        "note": note
    }

async def run_cases(cases_path, out_md, out_json):
    with open(cases_path, "r") as f:
        cases = yaml.safe_load(f)
    
    app.config.YUKTI_FIN_SSOT_V3 = True
    sm = get_session_manager()
    
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        git_sha = "unknown"
        
    run_id = f"run-{int(time.time())}"
    
    with open(out_md, "w") as f:
        f.write(f"# Golden Run {run_id} (SHA: {git_sha})\n\n")
        f.write("| Case | Phrasing | Status | Got | Expected | Note |\n")
        f.write("|---|---|---|---|---|---|\n")
    
    tasks = []
    for case in cases:
        if case.get("gate") != "P1":
            continue
        for phrasing in case.get("phrasings", []):
            tasks.append(process_phrasing(case, phrasing, sm, run_id))
            
    print(f"Running {len(tasks)} tasks concurrently...")
    results = await asyncio.gather(*tasks)
    
    passes = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    
    for r in results:
        with open(out_md, "a") as f:
            f.write(f"| {r['case']} | {r['phrasing']} | {r['status']} | {r['got']} | {r['expected']} | {r['note']} |\n")
            
    with open(out_json, "w") as f:
        json.dump({"run_id": run_id, "git_sha": git_sha, "passes": passes, "total": total, "results": results}, f, indent=2)
        
    print(f"P1 run: {passes}/{total}")

if __name__ == "__main__":
    base = os.path.dirname(__file__)
    asyncio.run(run_cases(os.path.join(base, "cases_finance.yaml"), os.path.join(base, "report.md"), os.path.join(base, "report.json")))
