"""P4.4 Backend–Frontend Chart Compatibility Parity Suite (SPEC-09 §4.5–4.6).

Verifies that `yukti/backend/app/brain/chart_rules.py` (`ALL_KINDS`, `profile`, `compatibility`,
`kinds_for`, `select_chart_kind`) is 100% parity-identical to `yukti/frontend/src/charts/compat.ts`
across all 14 canonical data shapes (9 core shapes from `scripts/test_compat.ts` + 5 portfolio-A
fixtures from `src/fixtures/charts/portfolioA/*.json`) × all 20 chart kinds (280 cells).
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List
import pytest

from app.brain.chart_rules import (
    ALL_KINDS,
    build_chart_spec,
    compatibility,
    kinds_for,
    profile,
    select_chart_kind,
)

BASE_DIR = Path(__file__).resolve().parents[3]
FRONTEND_DIR = BASE_DIR / "yukti" / "frontend"
FIXTURES_V1_DIR = FRONTEND_DIR / "src" / "fixtures"
FIXTURES_V2_DIR = FIXTURES_V1_DIR / "v2"
PORTFOLIO_A_DIR = FIXTURES_V1_DIR / "charts" / "portfolioA"


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_canonical_visuals() -> Dict[str, Dict[str, Any]]:
    """Builds the 14 canonical visuals (9 from `scripts/test_compat.ts` + 5 from `portfolioA`)."""
    roster = _load_json(FIXTURES_V2_DIR / "v2_roster_419.json")
    pnl = _load_json(FIXTURES_V2_DIR / "v2_finance_pnl.json")
    hc = _load_json(FIXTURES_V2_DIR / "v2_insights_drilldowns.json")
    grades = _load_json(FIXTURES_V1_DIR / "c1_donut_by_grade.json")
    combo_v1 = _load_json(FIXTURES_V1_DIR / "c11_combo_headcount_prod.json")

    combo_pa = _load_json(PORTFOLIO_A_DIR / "combo_revenue_margin.json")
    stacked100_pa = _load_json(PORTFOLIO_A_DIR / "stacked100_grade_mix.json")
    heatmap_pa = _load_json(PORTFOLIO_A_DIR / "heatmap_overtime.json")
    box_pa = _load_json(PORTFOLIO_A_DIR / "box_tenure.json")
    gauge_pa = _load_json(PORTFOLIO_A_DIR / "gauge_mou.json")

    return {
        "records": roster["visual"],
        "categorical_neg": pnl["visual"],
        "categorical": hc["visual"],
        "ordinal_multi": grades["visual"],
        "multi_neg": combo_v1["visual"],
        "time": {
            "type": "chart",
            "mode": "replace",
            "title": "Revenue trend",
            "chart": {
                "kind": "line",
                "x": "fy",
                "y": "revenue_cr",
                "unit": "₹ Cr",
                "data": [
                    {"fy": fy, "revenue_cr": 100000 + i * 7000}
                    for i, fy in enumerate(["FY22", "FY23", "FY24", "FY25", "FY26"])
                ],
            },
        },
        "distribution": {
            "type": "chart",
            "mode": "replace",
            "title": "Age distribution",
            "chart": {
                "kind": "histogram",
                "x": "bin",
                "y": "count",
                "data": [
                    {"bin": b, "count": c}
                    for b, c in zip(["21–30", "31–40", "41–50", "51–60"], [120, 340, 280, 90])
                ],
            },
        },
        "single": {
            "type": "chart",
            "mode": "replace",
            "title": "PAT",
            "chart": {
                "kind": "bar",
                "x": "metric",
                "y": "value",
                "data": [{"metric": "PAT", "value": 38329}],
            },
        },
        "table_arrays": {
            "type": "table",
            "mode": "replace",
            "title": "Arrays",
            "table": {
                "columns": ["work_centre", "headcount"],
                "rows": [
                    ["Delhi", 4120],
                    ["Mumbai", 3880],
                    ["Dehradun", 2100],
                    ["Vadodara", 1600],
                ],
            },
        },
        "portfolio_combo": {"type": "chart", "mode": "replace", "chart": combo_pa},
        "portfolio_stacked100": {"type": "chart", "mode": "replace", "chart": stacked100_pa},
        "portfolio_heatmap": {"type": "chart", "mode": "replace", "chart": heatmap_pa},
        "portfolio_box": {"type": "chart", "mode": "replace", "chart": box_pa},
        "portfolio_gauge": {"type": "chart", "mode": "replace", "chart": gauge_pa},
    }


CANONICAL_VISUALS = build_canonical_visuals()


def _run_ts_compat_dump(visuals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Executes `yukti/frontend/src/charts/compat.ts` in Node to dump TS profiles + compatibility."""
    node_script = r"""
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const ts = require('typescript');

const root = process.cwd();
const cache = {};
const classes = JSON.parse(readFileSync(join(root, 'src/contracts/generated/statement_line_classes.json'), 'utf8'));

function load(rel) {
  if (cache[rel]) return cache[rel];
  const js = ts.transpileModule(readFileSync(join(root, rel), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  }).outputText;
  const mod = { exports: {} };
  cache[rel] = mod.exports;
  const req = (name) => {
    if (name === 'echarts') return require('echarts');
    if (name === '@/contracts/generated/statement_line_classes.json') return classes;
    if (name === '@/design/tokens.json') return JSON.parse(readFileSync(join(root, 'src/design/tokens.json'), 'utf8'));
    if (name.startsWith('../')) return load(`src/${name.slice(3)}.ts`);
    if (name.startsWith('@/contracts/')) return {};
    if (name.startsWith('./')) return load(`src/charts/${name.slice(2)}.ts`);
    if (name.startsWith('@/charts/')) return load(`src/charts/${name.slice('@/charts/'.length)}.ts`);
    throw new Error(`unexpected import ${name} in ${rel}`);
  };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, req);
  cache[rel] = mod.exports;
  return mod.exports;
}

const { ALL_KINDS, profile, compatibility } = load('src/charts/compat.ts');
const input = JSON.parse(readFileSync(0, 'utf8'));
const out = { all_kinds: ALL_KINDS, shapes: {} };
for (const [key, vis] of Object.entries(input)) {
  const p = profile(vis);
  const compatMap = {};
  for (const k of ALL_KINDS) {
    compatMap[k] = compatibility(p, k);
  }
  out.shapes[key] = {
    profile: {
      columns: p.columns,
      dimKey: p.dimKey,
      measures: p.measures,
      primary: p.primary,
      shape: p.shape,
      hasNegative: p.hasNegative,
      hasTarget: p.hasTarget,
      ordinal: p.ordinal,
      people: p.people,
      groupable: p.groupable,
      n: p.n,
    },
    compat: compatMap,
  };
}
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", node_script],
        input=json.dumps(visuals),
        capture_output=True,
        text=True,
        cwd=str(FRONTEND_DIR),
        check=True,
    )
    return json.loads(proc.stdout)


TS_DUMP = _run_ts_compat_dump(CANONICAL_VISUALS)


def test_all_kinds_exact_parity_with_frontend():
    """`ALL_KINDS` in Python matches `ALL_KINDS` in `compat.ts` in exact order and membership."""
    assert list(ALL_KINDS) == TS_DUMP["all_kinds"]
    for required in ("stacked_100", "combo", "heatmap", "box", "gauge", "bullet", "scatter", "histogram", "waterfall", "table"):
        assert required in ALL_KINDS


@pytest.mark.parametrize("shape_key", list(CANONICAL_VISUALS.keys()))
def test_profile_exact_parity_with_frontend(shape_key: str):
    """Python `profile(vis)` returns identical DataProfile fields as TypeScript `profile(vis)`."""
    vis = CANONICAL_VISUALS[shape_key]
    py_p = profile(vis)
    ts_p = TS_DUMP["shapes"][shape_key]["profile"]

    assert py_p.shape == ts_p["shape"], f"{shape_key} shape mismatch: {py_p.shape} vs {ts_p['shape']}"
    assert py_p.dim_key == ts_p["dimKey"], f"{shape_key} dimKey mismatch: {py_p.dim_key} vs {ts_p['dimKey']}"
    assert py_p.measures == ts_p["measures"], f"{shape_key} measures mismatch: {py_p.measures} vs {ts_p['measures']}"
    assert py_p.primary == ts_p["primary"], f"{shape_key} primary mismatch: {py_p.primary} vs {ts_p['primary']}"
    assert py_p.has_negative == ts_p["hasNegative"]
    assert py_p.has_target == ts_p["hasTarget"]
    assert py_p.ordinal == ts_p["ordinal"]
    assert py_p.people == ts_p["people"]
    assert py_p.groupable == ts_p["groupable"]
    assert py_p.n == ts_p["n"]


@pytest.mark.parametrize("shape_key", list(CANONICAL_VISUALS.keys()))
@pytest.mark.parametrize("kind", list(ALL_KINDS))
def test_compatibility_matrix_280_cells_exact_parity(shape_key: str, kind: str):
    """Every `(shape_key, kind)` cell in Python `compatibility(p, kind)` matches TypeScript `compat.ts`."""
    vis = CANONICAL_VISUALS[shape_key]
    py_p = profile(vis)
    py_c = compatibility(py_p, kind)
    ts_c = TS_DUMP["shapes"][shape_key]["compat"][kind]

    assert py_c == ts_c, f"{shape_key} × {kind} mismatch: py={py_c} vs ts={ts_c}"


def test_p44_specific_gating_rules_and_defaults():
    """Explicit assertions for every P4.4 gating rule in SPEC-09 §4.5–4.6."""
    # 1. combo: native on multi-measure time series (`portfolio_combo`), alternative on 1-measure time series
    p_combo = profile(CANONICAL_VISUALS["portfolio_combo"])
    assert compatibility(p_combo, "combo") == {"status": "native"}
    p_time1 = profile(CANONICAL_VISUALS["time"])
    assert compatibility(p_time1, "combo")["status"] == "alternative"
    assert compatibility(p_time1, "combo")["alternative"] == "line"

    # Default chart kind for value + % time series is `combo`
    combo_rows = CANONICAL_VISUALS["portfolio_combo"]["chart"]["data"]
    assert select_chart_kind(list(combo_rows[0].keys()), combo_rows) == "combo"

    # 2. stacked_100: native on positive multi-measure (`portfolio_stacked100`), rejected on negative or 1-measure
    p_s100 = profile(CANONICAL_VISUALS["portfolio_stacked100"])
    assert compatibility(p_s100, "stacked_100") == {"status": "native"}
    p_mneg = profile(CANONICAL_VISUALS["multi_neg"])
    assert compatibility(p_mneg, "stacked_100") == {
        "status": "alternative",
        "alternative": "bar",
        "note": "A 100% stacked bar cannot show negative values.",
    }
    assert compatibility(p_time1, "stacked_100")["status"] == "alternative"

    # 3. heatmap: native on 2-category + measure (`portfolio_heatmap`) and records with >= 2 groupable cols
    p_heat = profile(CANONICAL_VISUALS["portfolio_heatmap"])
    assert compatibility(p_heat, "heatmap") == {"status": "native"}
    assert compatibility(profile(CANONICAL_VISUALS["records"]), "heatmap") == {"status": "native"}
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "heatmap") == {
        "status": "alternative",
        "alternative": "bar",
        "note": "A heatmap needs two categories and a measure (e.g. work centre × month).",
    }

    # 4. box: native on repeated group records (`portfolio_box`) and `records`, rejected on 1-row-per-category summary
    p_box = profile(CANONICAL_VISUALS["portfolio_box"])
    assert compatibility(p_box, "box") == {"status": "native"}
    assert compatibility(profile(CANONICAL_VISUALS["records"]), "box") == {"status": "native"}
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "box") == {
        "status": "alternative",
        "alternative": "bar",
        "note": "A box plot needs individual records per group; showing the summary instead.",
    }

    # 5. gauge: native only on single value with target (`portfolio_gauge`), alternative without target
    p_gauge = profile(CANONICAL_VISUALS["portfolio_gauge"])
    assert compatibility(p_gauge, "gauge") == {"status": "native"}
    p_single_no_target = profile(CANONICAL_VISUALS["single"])
    assert compatibility(p_single_no_target, "gauge") == {
        "status": "alternative",
        "alternative": "table",
        "note": "A gauge shows one value against a target.",
    }
    gauge_rows = CANONICAL_VISUALS["portfolio_gauge"]["chart"]["data"]
    assert select_chart_kind(list(gauge_rows[0].keys()), gauge_rows) == "gauge"
    # P4.4 S1: build_chart_spec("gauge", ...) keeps the 1-row target intact instead of pivoting measures
    gauge_spec = build_chart_spec("gauge", list(gauge_rows[0].keys()), gauge_rows)
    assert gauge_spec["kind"] == "gauge"
    assert len(gauge_spec["data"]) == 1
    assert "target" in gauge_spec["data"][0]

    # 6. scatter: requires 2 measures (never fabricates a rank axis)
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "scatter") == {
        "status": "alternative",
        "alternative": "bar",
        "note": "A scatter plot needs two measures per item; showing the closest view.",
    }
    assert compatibility(p_combo, "scatter") == {"status": "native"}

    # 7. histogram: never on time (-> line) and never on categorical with < 30 values (-> hbar)
    assert compatibility(p_time1, "histogram") == {
        "status": "alternative",
        "alternative": "line",
        "note": "A histogram is for distributions; this time series is shown as a line.",
    }
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "histogram") == {
        "status": "alternative",
        "alternative": "hbar",
        "note": "Too few values for a distribution; showing them ranked.",
    }

    # 8. pie/donut: never on time (-> bar) and never on negatives (-> hbar)
    assert compatibility(p_time1, "pie") == {
        "status": "alternative",
        "alternative": "bar",
        "note": "A pie cannot show change over time; showing columns over time.",
    }
    assert compatibility(profile(CANONICAL_VISUALS["categorical_neg"]), "pie") == {
        "status": "alternative",
        "alternative": "hbar",
        "note": "Shares cannot show losses; showing gains and losses as bars.",
    }

    # 9. line/area on nominal categorical -> bar; funnel/waterfall on nominal positive categorical -> hbar
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "line") == {
        "status": "alternative",
        "alternative": "bar",
        "note": "A line implies an order; these categories are shown as bars.",
    }
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "funnel")["alternative"] == "hbar"
    assert compatibility(profile(CANONICAL_VISUALS["categorical"]), "waterfall")["alternative"] == "hbar"

    # 10. kinds_for lists all 20 kinds
    kf = kinds_for(CANONICAL_VISUALS["categorical_neg"])
    assert [item["kind"] for item in kf] == list(ALL_KINDS)
