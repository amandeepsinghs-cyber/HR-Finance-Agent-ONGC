import asyncio
import yaml
import time
import os
import json
import subprocess
import argparse
import httpx
from app.auth import issue_token

def check_expectation(contract, expect):
    if not contract:
        return False, "No contract", "None"
        
    if "proposed_action" in expect:
        exp_agent = expect["proposed_action"].get("agent")
        has_override = expect["proposed_action"].get("has_override", False)
        
        got_pa = contract.get("proposed_action")
        if not got_pa:
            return False, "No proposed_action found", "None"
        if exp_agent and got_pa.get("agent") != exp_agent:
            return False, f"Agent mismatch {got_pa.get('agent')} != {exp_agent}", got_pa.get("agent")
        
        if has_override:
            # check if editable_inputs has WACC or something?
            # Or just check if there is an editable_inputs that is populated.
            ed = got_pa.get("editable_inputs", {})
            if not ed:
                return False, "Expected override, found none", str(ed)
        return True, "Pass", "proposed_action matched"

    if "job" in expect:
        exp_job = expect["job"]
        if exp_job is None:
            if contract.get("job") is not None:
                return False, "Expected no job, but found one", str(contract.get("job"))
            return True, "Pass", "No job as expected"
        else:
            got_job = contract.get("job")
            if not got_job:
                return False, "Expected job, found none", "None"
            if exp_job.get("status") and got_job.get("status") != exp_job["status"]:
                return False, f"Job status mismatch {got_job.get('status')} != {exp_job['status']}", got_job.get("status")
            return True, "Pass", "Job matched"

    if "access" in expect:
        exp_status = expect["access"].get("status")
        got_status = contract.get("access", {}).get("status")
        if exp_status and got_status != exp_status:
            return False, f"Access mismatch {got_status} != {exp_status}", got_status
        return True, "Pass", "Access matched"
        
    return True, "Pass (fallback)", "Ok"

async def poll_job(client, base_url, token, job_id, timeout_sec=20):
    start = time.time()
    while time.time() - start < timeout_sec:
        resp = await client.get(f"{base_url}/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            data = resp.json()
            job = data.get("job") if "job" in data else data
            if job and job.get("status") in ("succeeded", "failed", "cancelled"):
                return job
        await asyncio.sleep(1)
    return None

async def process_phrasing(case, phrasing, run_id, base_url):
    case_id = case["id"]
    persona = case.get("persona", "hr_manager")
    expect = case.get("expect", {})
    
    sess_id = f"{run_id}-{case_id}-{time.time_ns()}"
    token = issue_token(persona, False)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{base_url}/api/turn", json={
                "query": phrasing,
                "session_id": sess_id,
                "persona": persona,
                "language": "en"
            }, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
            
            if resp.status_code != 200:
                return {
                    "case": case_id,
                    "phrasing": phrasing,
                    "status": "FAIL",
                    "got": f"HTTP {resp.status_code}",
                    "expected": "",
                    "note": resp.text[:50]
                }
                
            contract = resp.json()
            
            if contract and "job" in contract and contract["job"] and contract["job"].get("status") == "queued":
                job_id = contract["job"].get("id")
                if job_id:
                    polled_job = await poll_job(client, base_url, token, job_id, timeout_sec=20)
                    if polled_job:
                        contract["job"] = polled_job

            ok, note, got = check_expectation(contract, expect)
            status = "PASS" if ok else "FAIL"
            
    except Exception as e:
        status = "ERROR"
        note = str(e)
        got = "Exception"
        
    return {
        "case": case_id,
        "phrasing": phrasing,
        "status": status,
        "got": got,
        "expected": "",
        "note": note
    }

async def process_chain(chain, run_id, base_url):
    chain_id = chain["id"]
    persona = chain.get("persona", "CMD")
    sess_id = f"{run_id}-{chain_id}-{time.time_ns()}"
    token = issue_token(persona, False)
    
    results = []
    for step_def in chain.get("steps", []):
        phrasing = step_def["phrasing"]
        expect = step_def.get("expect", {})
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{base_url}/api/turn", json={
                    "query": phrasing,
                    "session_id": sess_id,
                    "persona": persona,
                    "language": "en"
                }, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
                
                if resp.status_code != 200:
                    status = "FAIL"
                    note = f"HTTP {resp.status_code}"
                    got = resp.text[:50]
                else:
                    contract = resp.json()
                    
                    if contract and "job" in contract and contract["job"] and contract["job"].get("status") == "queued":
                        job_id = contract["job"].get("id")
                        if job_id:
                            polled_job = await poll_job(client, base_url, token, job_id, timeout_sec=20)
                            if polled_job:
                                contract["job"] = polled_job

                    ok, note, got = check_expectation(contract, expect)
                    status = "PASS" if ok else "FAIL"
        except Exception as e:
            status = "ERROR"
            note = str(e)
            got = "Exception"
            
        results.append({
            "case": f"{chain_id}.{step_def['step']}",
            "phrasing": phrasing,
            "status": status,
            "got": got,
            "expected": "",
            "note": note
        })
    return results

async def run_cases(cases_path, chains_path, out_md, base_url, only_filter=None):
    cases = []
    if cases_path and os.path.exists(cases_path):
        with open(cases_path, "r") as f:
            cases = yaml.safe_load(f)
        
    chains = []
    if chains_path and os.path.exists(chains_path):
        with open(chains_path, "r") as f:
            chains = yaml.safe_load(f)
    
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
    chain_tasks = []
    
    for case in cases:
        if only_filter and case["id"] != only_filter:
            continue
        if not only_filter and case.get("gate") != "P1":
            continue
        for phrasing in case.get("phrasings", []):
            tasks.append(process_phrasing(case, phrasing, run_id, base_url))
            
    for chain in chains:
        if only_filter and chain["id"] != only_filter:
            continue
        if not only_filter and chain.get("gate") not in ["P1", "P3.4b", "P2F"]:
            continue
        chain_tasks.append(process_chain(chain, run_id, base_url))
            
    print(f"Running {len(tasks)} independent tasks concurrently...")
    results = []
    if tasks:
        results.extend(await asyncio.gather(*tasks))
        
    print(f"Running {len(chain_tasks)} chains sequentially...")
    if chain_tasks:
        for ct in chain_tasks:
            cr = await ct
            results.extend(cr)
    
    passes = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    
    for r in results:
        with open(out_md, "a") as f:
            f.write(f"| {r['case']} | {r['phrasing']} | {r['status']} | {r['got']} | {r['expected']} | {r['note']} |\n")
            
    print(f"Run complete: {passes}/{total}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, help="Run only specific case or chain by ID")
    parser.add_argument("--chains", type=str, help="Path to chains yaml (optional)")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8095")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--report", type=str, default="report.md")
    args = parser.parse_args()
    
    base = os.path.dirname(__file__)
    cases_p = os.path.join(base, "cases_finance.yaml")
    chains_p = args.chains
    
    asyncio.run(run_cases(cases_p, chains_p, args.report, args.base_url, args.only))
