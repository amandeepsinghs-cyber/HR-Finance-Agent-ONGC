"""Golden tests for QuerySpec planner (Task Packet B2.2b).

Runs the planner on 35 golden cases (HR + finance flagship chains, paraphrases,
Hinglish, non-data intents) and asserts produced QuerySpecs against expected specs.
"""

import asyncio
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import pytest
import yaml

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.planner import Plan, Planner
from app.brain.query_spec import Filter, QuerySpec


GOLDEN_YAML_PATH = Path(__file__).resolve().parent / "golden" / "planner_golden.yaml"


def load_cases() -> List[Dict[str, Any]]:
    with open(GOLDEN_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cases = data if isinstance(data, list) else data.get("cases", [])
    return cases


CASES = load_cases()
CASES_BY_ID = {c["id"]: c for c in CASES}


def norm_filter(f: Any) -> Tuple[str, str, Any]:
    """Normalize filter into a hashable (field, op, value) tuple (§6)."""
    if hasattr(f, "field"):
        field = f.field
        op = f.op
        val = f.value
    elif isinstance(f, dict):
        field = f["field"]
        op = f.get("op", "=")
        val = f.get("value")
    else:
        raise TypeError(f"Unexpected filter type: {type(f)}")

    if isinstance(val, list):
        v = tuple(sorted(str(x) for x in val))
    elif isinstance(val, (int, float)) and not isinstance(val, bool):
        v = float(val)
    else:
        v = str(val)
    return (field, op, v)


def compare_case(plan: Plan, expect: Dict[str, Any]) -> List[str]:
    """Compares a Plan against the expect dictionary. Returns list of mismatch messages."""
    mismatches: List[str] = []

    if "intent" in expect:
        if plan.intent != expect["intent"]:
            mismatches.append(f"intent: expected {expect['intent']!r}, got {plan.intent!r}")

    if "is_followup" in expect:
        if plan.is_followup != expect["is_followup"]:
            mismatches.append(f"is_followup: expected {expect['is_followup']!r}, got {plan.is_followup!r}")

    spec = plan.spec

    if "metric" in expect:
        got_metric = spec.metric if spec else None
        if got_metric != expect["metric"]:
            mismatches.append(f"metric: expected {expect['metric']!r}, got {got_metric!r}")

    if "metric_in" in expect:
        got_metric = spec.metric if spec else None
        if got_metric not in expect["metric_in"]:
            mismatches.append(f"metric_in: expected in {expect['metric_in']!r}, got {got_metric!r}")

    if "grain" in expect:
        got_grain = spec.grain if spec else None
        if got_grain != expect["grain"]:
            mismatches.append(f"grain: expected {expect['grain']!r}, got {got_grain!r}")

    if "dimensions" in expect:
        got_dims = set(spec.dimensions) if spec else set()
        exp_dims = set(expect["dimensions"])
        if got_dims != exp_dims:
            mismatches.append(f"dimensions: expected {sorted(exp_dims)}, got {sorted(got_dims)}")

    if "dimensions_include" in expect:
        got_dims = set(spec.dimensions) if spec else set()
        exp_subset = set(expect["dimensions_include"])
        if not exp_subset.issubset(got_dims):
            mismatches.append(f"dimensions_include: expected subset {sorted(exp_subset)}, got {sorted(got_dims)}")

    if "filters" in expect:
        got_filters = set(map(norm_filter, spec.filters)) if spec else set()
        exp_filters = set(map(norm_filter, expect["filters"]))
        if got_filters != exp_filters:
            mismatches.append(f"filters: expected {sorted(exp_filters)}, got {sorted(got_filters)}")

    if "filters_include" in expect:
        got_filters = set(map(norm_filter, spec.filters)) if spec else set()
        exp_subset = set(map(norm_filter, expect["filters_include"]))
        if not exp_subset.issubset(got_filters):
            mismatches.append(f"filters_include: expected subset {sorted(exp_subset)}, got {sorted(got_filters)}")

    if "filter_fields_any" in expect:
        got_fields = {f.field for f in spec.filters} if spec else set()
        exp_any = set(expect["filter_fields_any"])
        if not (got_fields & exp_any):
            mismatches.append(f"filter_fields_any: expected any of {sorted(exp_any)}, got {sorted(got_fields)}")

    if "period" in expect:
        if not spec or not spec.period:
            got_period = {}
        else:
            p_dict = spec.period.model_dump(by_alias=True, exclude_none=True)
            got_period = {k: v for k, v in p_dict.items() if k in ("fy", "from", "to")}
        exp_period = {k: v for k, v in expect["period"].items() if k in ("fy", "from", "to")}
        if got_period != exp_period:
            mismatches.append(f"period: expected {exp_period}, got {got_period}")

    return mismatches


_PLANS_CACHE: Dict[str, Plan] = {}


async def _plan_one(planner: Planner, case: Dict[str, Any], cases_by_id: Dict[str, Any], sem: asyncio.Semaphore) -> Tuple[str, Plan]:
    prev_spec = None
    prior_id = case.get("prior")
    if prior_id:
        prior_case = cases_by_id.get(prior_id)
        if prior_case and prior_case.get("spec"):
            prev_spec = QuerySpec.from_contract(prior_case["spec"])
        else:
            raise ValueError(f"Case {case['id']} references prior {prior_id} which has no spec")

    async with sem:
        try:
            plan = await planner.plan(question=case["question"], prev=prev_spec)
        except Exception as exc:
            plan = Plan(intent="error", notes=[f"Exception in plan: {exc}"])
        return case["id"], plan


async def _run_all_cases(cases: List[Dict[str, Any]], cases_by_id: Dict[str, Any]) -> Dict[str, Plan]:
    planner = Planner()
    sem = asyncio.Semaphore(6)
    tasks = [_plan_one(planner, c, cases_by_id, sem) for c in cases]
    results = await asyncio.gather(*tasks)
    return dict(results)


def get_planner_results() -> Dict[str, Plan]:
    global _PLANS_CACHE
    if not _PLANS_CACHE:
        _PLANS_CACHE = asyncio.run(_run_all_cases(CASES, CASES_BY_ID))
    return _PLANS_CACHE


@pytest.fixture(scope="module")
def planner_results() -> Dict[str, Plan]:
    return get_planner_results()


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_planner_case(case: Dict[str, Any], planner_results: Dict[str, Plan]):
    cid = case["id"]
    plan = planner_results[cid]
    mismatches = compare_case(plan, case.get("expect", {}))
    details = "; ".join(mismatches)
    assert not mismatches, f"Case {cid} mismatches: {details}"


def test_golden_summary(planner_results: Dict[str, Plan]):
    passed = 0
    total = len(CASES)
    table_lines: List[str] = []

    for case in CASES:
        cid = case["id"]
        plan = planner_results[cid]
        mismatches = compare_case(plan, case.get("expect", {}))
        ok = len(mismatches) == 0
        if ok:
            passed += 1
            table_lines.append(f"{cid:<5} | PASS")
        else:
            table_lines.append(f"{cid:<5} | FAIL | {'; '.join(mismatches)}")

    print(f"\n=== PLANNER GOLDEN TEST SUMMARY: {passed}/{total} PASSED ===")
    for line in table_lines:
        print(line)

    assert passed >= 30, f"Expected >= 30 of {total} golden specs to pass, but got {passed}/{total}"
