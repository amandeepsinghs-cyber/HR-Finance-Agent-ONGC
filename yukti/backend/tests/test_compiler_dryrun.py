"""B2.3: every QuerySpec the planner produces on the golden set compiles to SQL that passes
the safety validator and a BigQuery dry-run (no bytes billed), plus every metric in the
semantic model compiles and dry-runs with its default spec. Live (Gemini + BigQuery dry-run)."""

import asyncio
from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.compiler import CompileError, Compiler
from app.brain.planner import Planner
from app.brain.query_spec import Filter, Period, QuerySpec
from app.brain.semantic_model import get_semantic_model

GOLDEN = yaml.safe_load((Path(__file__).resolve().parent / "golden" / "planner_golden.yaml").read_text(encoding="utf-8"))
CASES = GOLDEN if isinstance(GOLDEN, list) else GOLDEN.get("cases", [])
BY_ID = {c["id"]: c for c in CASES}


def _default_specs():
    m = get_semantic_model()
    specs = []
    for s in m.subjects.values():
        for mn in s.metrics:
            dims = [] if s.row_only else ([d for d in ("wc", "asset", "field", "fy") if d in s.fields][:1])
            specs.append(QuerySpec(domain=s.domain, metric=mn, dimensions=dims))
        if s.row_columns:
            specs.append(QuerySpec(domain=s.domain, metric=next(iter(s.metrics)), grain="row", limit=5))
    for t in m.templates:
        specs.append(QuerySpec(metric=t))
    # time-shift (as-of) variant used by "last year" on the workforce subject
    specs.append(QuerySpec(domain="hr", metric="headcount", dimensions=["wc"], period=Period(fy="FY26"),
                           filters=[Filter(field="station_tenure_years", op=">=", value=5),
                                    Filter(field="wc", op="in", value=["WC-DEL", "WC-MUM"])]))
    return specs


@pytest.fixture(scope="module")
def dry_runs():
    async def run():
        planner, compiler = Planner(), Compiler()
        sem = asyncio.Semaphore(6)
        out = {}

        async def one(case):
            prev = QuerySpec.from_contract(BY_ID[case["prior"]]["spec"]) if case.get("prior") else None
            async with sem:
                plan = await planner.plan(case["question"], prev, [])
            if plan.intent != "data" or plan.spec is None:
                return
            try:
                cq = compiler.compile(plan.spec)
                b = await asyncio.to_thread(compiler.dry_run, cq.sql)
                out[case["id"]] = ("ok", b, cq.sql)
            except CompileError as e:
                out[case["id"]] = ("compile_error", str(e), None)
            except Exception as e:
                out[case["id"]] = ("dry_run_error", str(e)[:300], cq.sql)

        await asyncio.gather(*[one(c) for c in CASES])
        for i, spec in enumerate(_default_specs()):
            key = f"metric:{spec.metric}:{spec.grain}:{i}"
            try:
                cq = compiler.compile(spec)
                b = await asyncio.to_thread(compiler.dry_run, cq.sql)
                out[key] = ("ok", b, cq.sql)
            except Exception as e:
                out[key] = ("error", str(e)[:300], None)
        return out

    return asyncio.run(run())


def test_golden_specs_dry_run_100pct(dry_runs):
    golden = {k: v for k, v in dry_runs.items() if not k.startswith("metric:")}
    bad = {k: v for k, v in golden.items() if v[0] != "ok"}
    print(f"golden data specs compiled + dry-run OK: {len(golden) - len(bad)}/{len(golden)}")
    assert len(golden) >= 25
    assert not bad, bad


def test_every_metric_compiles_and_dry_runs(dry_runs):
    metrics = {k: v for k, v in dry_runs.items() if k.startswith("metric:")}
    bad = {k: v for k, v in metrics.items() if v[0] != "ok"}
    print(f"semantic-model metrics dry-run OK: {len(metrics) - len(bad)}/{len(metrics)}")
    assert not bad, bad
