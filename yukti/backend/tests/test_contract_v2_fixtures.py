"""Pytest suite validating Yukti Contract-v2 fixtures and legacy v1 fixtures.
Ensures schema compliance (Draft 2020-12) and strict domain/numeric consistency.
"""

from datetime import datetime, date
import json
from pathlib import Path
import pytest
import jsonschema

# Locate schema and fixture directories relative to this file
# parents[0] = tests, [1] = backend, [2] = yukti, [3] = app root
BASE_DIR = Path(__file__).resolve().parents[3]
SCHEMA_PATH = BASE_DIR / "yukti" / "contracts" / "answer_contract.schema.json"
FIXTURES_V1_DIR = BASE_DIR / "yukti" / "frontend" / "src" / "fixtures"
FIXTURES_V2_DIR = FIXTURES_V1_DIR / "v2"

# Load schema once
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)

V1_FILES = sorted([p for p in FIXTURES_V1_DIR.glob("*.json") if p.is_file()])
V2_FILES = sorted([p for p in FIXTURES_V2_DIR.glob("*.json") if p.is_file()])


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("fixture_path", V1_FILES, ids=lambda p: p.name)
def test_v1_fixture_validates_schema(fixture_path: Path):
    """Every v1 fixture must validate cleanly against the answer contract schema."""
    data = load_json(fixture_path)
    errors = list(VALIDATOR.iter_errors(data))
    assert not errors, f"{fixture_path.name} schema errors: {[e.message for e in errors]}"


@pytest.mark.parametrize("fixture_path", V2_FILES, ids=lambda p: p.name)
def test_v2_fixture_validates_schema(fixture_path: Path):
    """Every v2 fixture must validate cleanly against Draft 2020-12 schema."""
    data = load_json(fixture_path)
    errors = list(VALIDATOR.iter_errors(data))
    assert not errors, f"{fixture_path.name} schema errors: {[e.message for e in errors]}"


def test_v2_roster_row_counts_and_total_rows():
    """419 and 2000 roster row counts and total_rows must match exactly."""
    r419 = load_json(FIXTURES_V2_DIR / "v2_roster_419.json")
    rows_419 = r419["visual"]["table"]["rows"]
    total_419 = r419["visual"]["table"]["total_rows"]
    assert len(rows_419) == 419, f"Expected 419 rows, got {len(rows_419)}"
    assert total_419 == 419, f"Expected total_rows=419, got {total_419}"

    r2000 = load_json(FIXTURES_V2_DIR / "v2_roster_2000.json")
    rows_2000 = r2000["visual"]["table"]["rows"]
    total_2000 = r2000["visual"]["table"]["total_rows"]
    assert len(rows_2000) == 2000, f"Expected 2000 rows, got {len(rows_2000)}"
    assert total_2000 == 2000, f"Expected total_rows=2000, got {total_2000}"


def test_v2_roster_no_duplicate_emp_ids():
    """Emp_ids in 419 and 2000 rosters must be unique (no duplicates)."""
    r419 = load_json(FIXTURES_V2_DIR / "v2_roster_419.json")
    emp_ids_419 = [r["emp_id"] for r in r419["visual"]["table"]["rows"]]
    assert len(emp_ids_419) == len(set(emp_ids_419)), "Duplicate emp_id found in v2_roster_419.json"

    r2000 = load_json(FIXTURES_V2_DIR / "v2_roster_2000.json")
    emp_ids_2000 = [r["emp_id"] for r in r2000["visual"]["table"]["rows"]]
    assert len(emp_ids_2000) == len(set(emp_ids_2000)), "Duplicate emp_id found in v2_roster_2000.json"


def test_v2_roster_partial_masking():
    """Partial fixture (DIR_FIN) must mask emp_id, posted_since, AND continuous_stay_years."""
    rpart = load_json(FIXTURES_V2_DIR / "v2_roster_partial_dirfin.json")
    masking = rpart["visual"]["table"]["masking"]
    assert masking["level"] == "partial"
    assert "emp_id" in masking["masked_columns"]
    assert "posted_since" in masking["masked_columns"]
    assert "continuous_stay_years" in masking["masked_columns"]

    rows = rpart["visual"]["table"]["rows"]
    assert len(rows) == 60, f"Expected 60 partial rows, got {len(rows)}"
    for idx, row in enumerate(rows):
        assert row["emp_id"] == "••••", f"Row {idx} emp_id is not '••••': {row['emp_id']}"
        assert row["posted_since"] == "••••", f"Row {idx} posted_since is not '••••': {row['posted_since']}"
        assert row["continuous_stay_years"] == "••••", (
            f"Row {idx} continuous_stay_years is not '••••': {row['continuous_stay_years']}"
        )


def test_v2_roster_aggregate_counts_sum():
    """Aggregate fixture (E2_HR) executive counts across grades must sum to 419."""
    raggr = load_json(FIXTURES_V2_DIR / "v2_roster_aggregate_e2.json")
    masking = raggr["visual"]["table"]["masking"]
    assert masking["level"] == "aggregate"

    rows = raggr["visual"]["table"]["rows"]
    total_executives = sum(r["executives"] for r in rows)
    assert total_executives == 419, f"Aggregate sum {total_executives} != 419"

    # KPI total must also match
    kpis = raggr["visual"]["kpis"]
    total_kpi = next(k for k in kpis if "Total" in k["label"])
    assert total_kpi["value"] == 419


def test_v2_roster_419_seniority_and_numeric_claims():
    """v2_roster_419: seniority correlation, posted_since consistency, and KPI/insight checks."""
    r419 = load_json(FIXTURES_V2_DIR / "v2_roster_419.json")
    rows = r419["visual"]["table"]["rows"]

    # 1. Seniority correlation: senior officers (E7-E9) have significantly higher stay than junior (E1-E3)
    senior_stays = [r["continuous_stay_years"] for r in rows if r["grade"] in ["E7", "E8", "E9"]]
    junior_stays = [r["continuous_stay_years"] for r in rows if r["grade"] in ["E1", "E2", "E3"]]
    avg_senior = sum(senior_stays) / len(senior_stays)
    avg_junior = sum(junior_stays) / len(junior_stays)
    assert avg_senior > avg_junior, f"Expected senior stays ({avg_senior:.1f}) > junior ({avg_junior:.1f})"

    # 2. Table sorted descending
    for i in range(len(rows) - 1):
        assert rows[i]["continuous_stay_years"] >= rows[i + 1]["continuous_stay_years"], (
            f"Rows not sorted descending at index {i}"
        )

    # 3. posted_since consistent with continuous_stay_years (reference 2026-10-22)
    ref_date = date(2026, 10, 22)
    for r in rows:
        p_date = datetime.strptime(r["posted_since"], "%Y-%m-%d").date()
        diff_days = (ref_date - p_date).days
        expected_days = round(r["continuous_stay_years"] * 365.25)
        assert abs(diff_days - expected_days) <= 1, (
            f"posted_since {r['posted_since']} inconsistent with stay {r['continuous_stay_years']}"
        )

    # 4. KPI numeric claims match rows
    kpis = {k["label"]: k["value"] for k in r419["visual"]["kpis"]}
    assert kpis["Total Delhi 5+ Yr"] == 419

    sorted_stays = sorted([r["continuous_stay_years"] for r in rows], reverse=True)
    expected_median = sorted_stays[len(sorted_stays) // 2]
    assert kpis["Median Stay"] == expected_median

    actual_e7_count = len([r for r in rows if r["grade"] in ["E7", "E8", "E9"]])
    assert kpis["E7+ Senior Count"] == actual_e7_count

    # 5. Insights numeric claims match rows
    insights = r419["insights_v2"]
    outlier = next(ins for ins in insights if ins.get("kind") == "outlier")
    assert outlier["value"] == rows[0]["continuous_stay_years"]
    assert outlier["ref"] == rows[0]["discipline"]

    risk = next(ins for ins in insights if ins.get("kind") == "risk")
    assert risk["value"] == actual_e7_count


def test_v2_roster_2000_weights_and_numeric_claims():
    """v2_roster_2000: weighted distributions, clusters, and KPI/insight checks."""
    r2000 = load_json(FIXTURES_V2_DIR / "v2_roster_2000.json")
    rows = r2000["visual"]["table"]["rows"]

    # 1. Work centres distribution: Mumbai and Delhi must be the 2 largest clusters
    wc_counts = {}
    for r in rows:
        wc_counts[r["work_centre"]] = wc_counts.get(r["work_centre"], 0) + 1

    sorted_wcs = sorted(wc_counts.items(), key=lambda x: x[1], reverse=True)
    assert sorted_wcs[0][0] == "Mumbai (Western Offshore)", (
        f"Expected Mumbai as #1 cluster, got {sorted_wcs[0]}"
    )
    assert sorted_wcs[1][0] == "Delhi (Corporate HQ)", (
        f"Expected Delhi as #2 cluster, got {sorted_wcs[1]}"
    )
    assert len(wc_counts) == 15, f"Expected 15 work centres, got {len(wc_counts)}"

    # 2. Disciplines distribution: Production + Drilling must exceed 40%
    prod_drill_count = len([r for r in rows if r["discipline"] in ["Production", "Drilling"]])
    prod_drill_pct = round((prod_drill_count / len(rows)) * 100, 1)
    assert prod_drill_pct > 40.0, f"Expected Prod+Drill > 40%, got {prod_drill_pct}%"

    # 3. KPI numeric claims match rows
    kpis = {k["label"]: k["value"] for k in r2000["visual"]["kpis"]}
    assert kpis["Long-Stay Executives"] == 2000

    sorted_stays = sorted([r["continuous_stay_years"] for r in rows], reverse=True)
    expected_median = sorted_stays[len(sorted_stays) // 2]
    assert kpis["Median Stay"] == expected_median
    assert kpis["Work Centres"] == 15
    assert kpis["Prod & Drilling Share"] == prod_drill_pct

    # 4. Insights numeric claims match rows
    insights = r2000["insights_v2"]
    trend = next(ins for ins in insights if ins.get("kind") == "trend")
    assert trend["value"] == wc_counts["Mumbai (Western Offshore)"]
    assert trend["ref"] == "Mumbai (Western Offshore)"

    risk = next(ins for ins in insights if ins.get("kind") == "risk")
    assert risk["value"] == prod_drill_pct
    assert risk["ref"] == "Production"


def test_v2_compare_delhi_mumbai_consistency_and_types():
    """Compare fixture: per-grade values equal grouped_bar, and KPI shares are numbers."""
    rcomp = load_json(FIXTURES_V2_DIR / "v2_compare_delhi_mumbai.json")
    gb_data = rcomp["visual"]["chart"]["data"]
    items = rcomp["visual"]["compare"]["items"]
    assert len(items) == 2, f"Expected 2 compare items, got {len(items)}"

    delhi_item = next(it for it in items if "Delhi" in it["label"])
    mumbai_item = next(it for it in items if "Mumbai" in it["label"])

    delhi_chart_data = delhi_item["chart"]["data"]
    mumbai_chart_data = mumbai_item["chart"]["data"]

    delhi_by_grade = {r["grade"]: r["headcount"] for r in delhi_chart_data}
    mumbai_by_grade = {r["grade"]: r["headcount"] for r in mumbai_chart_data}

    for row in gb_data:
        grade = row["grade"]
        assert row["Delhi"] == delhi_by_grade[grade], (
            f"Delhi count mismatch for grade {grade}: {row['Delhi']} vs {delhi_by_grade[grade]}"
        )
        assert row["Mumbai"] == mumbai_by_grade[grade], (
            f"Mumbai count mismatch for grade {grade}: {row['Mumbai']} vs {mumbai_by_grade[grade]}"
        )

    # Verify KPI numeric claims and types (MUST BE NUMBER, NOT "12.0%")
    delhi_kpis = {k["label"]: k for k in delhi_item["kpis"]}
    delhi_share_kpi = delhi_kpis["E7+ Share"]
    assert isinstance(delhi_share_kpi["value"], (int, float)), (
        f"delhi E7+ Share value must be numeric, got {type(delhi_share_kpi['value'])}: {delhi_share_kpi['value']}"
    )
    assert delhi_share_kpi["unit"] == "%"
    assert delhi_share_kpi["value"] == 12.0

    mumbai_kpis = {k["label"]: k for k in mumbai_item["kpis"]}
    mumbai_share_kpi = mumbai_kpis["E7+ Share"]
    assert isinstance(mumbai_share_kpi["value"], (int, float)), (
        f"mumbai E7+ Share value must be numeric, got {type(mumbai_share_kpi['value'])}: {mumbai_share_kpi['value']}"
    )
    assert mumbai_share_kpi["unit"] == "%"
    assert mumbai_share_kpi["value"] == 6.2


def test_v2_insights_drilldowns_numeric_claims():
    """Insights drilldowns: all numbers in chart, KPIs, and insights match."""
    rins = load_json(FIXTURES_V2_DIR / "v2_insights_drilldowns.json")
    chart_data = rins["visual"]["chart"]["data"]

    total_headcount = sum(r["headcount"] for r in chart_data)
    assert total_headcount == 22890

    kpis = {k["label"]: k["value"] for k in rins["visual"]["kpis"]}
    assert kpis["Total Headcount"] == total_headcount
    assert kpis["Work Centres"] == len(chart_data)

    insights = rins["insights_v2"]
    headline = next(ins for ins in insights if ins.get("kind") == "headline")
    assert headline["value"] == total_headcount

    outlier = next(ins for ins in insights if ins.get("kind") == "outlier")
    mumbai_data = next(r for r in chart_data if "Mumbai" in r["work_centre"])
    assert outlier["value"] == mumbai_data["headcount"]

    trend = next(ins for ins in insights if ins.get("kind") == "trend")
    sivasagar = next(r["headcount"] for r in chart_data if "Sivasagar" in r["work_centre"])
    jorhat = next(r["headcount"] for r in chart_data if "Jorhat" in r["work_centre"])
    assert trend["value"] == sivasagar + jorhat


def test_v2_finance_pnl_numeric_claims():
    """Finance PnL: all net profit, loss counts, and top asset KPIs match chart data."""
    rpnl = load_json(FIXTURES_V2_DIR / "v2_finance_pnl.json")
    chart_data = rpnl["visual"]["chart"]["data"]

    net_profit = sum(r["profit_cr"] for r in chart_data)
    loss_fields = [r for r in chart_data if r["profit_cr"] < 0]
    total_loss = sum(r["profit_cr"] for r in loss_fields)
    top_asset = max(r["profit_cr"] for r in chart_data)

    assert net_profit == 36150
    assert len(loss_fields) == 4
    assert total_loss == -3870
    assert top_asset == 22450

    kpis = {k["label"]: k["value"] for k in rpnl["visual"]["kpis"]}
    assert kpis["Net Profit"] == net_profit
    assert kpis["Loss-Making Fields"] == 4
    assert kpis["Top Asset (Mumbai High)"] == top_asset

    insights = rpnl["insights_v2"]
    headline = next(ins for ins in insights if ins.get("kind") == "headline")
    assert headline["value"] == net_profit

    outlier = next(ins for ins in insights if ins.get("kind") == "outlier")
    assert outlier["value"] == top_asset

    risk = next(ins for ins in insights if ins.get("kind") == "risk")
    assert risk["value"] == total_loss


@pytest.mark.parametrize("fixture_path", V2_FILES, ids=lambda p: p.name)
def test_v2_contract_version_and_display_text(fixture_path: Path):
    """Every v2 fixture must have contract_version == 2 and display_text <= 600 characters."""
    data = load_json(fixture_path)
    assert data.get("contract_version") == 2, (
        f"{fixture_path.name} missing or invalid contract_version: {data.get('contract_version')}"
    )
    display_text = data.get("display_text", "")
    assert len(display_text) <= 600, (
        f"{fixture_path.name} display_text exceeds 600 chars: {len(display_text)}"
    )
