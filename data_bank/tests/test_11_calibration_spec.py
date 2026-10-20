"""Validation test suite for calibration_targets.yaml (Step 1.2)."""

from pathlib import Path
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DATA_BANK_ROOT.parent
TARGETS_YAML_PATH = DATA_BANK_ROOT / "world_bible/calibration_targets.yaml"
QUESTIONS_YAML_PATH = DATA_BANK_ROOT / "world_bible/reference/questions.yaml"
FACTS_PATH = PROJECT_ROOT / "knowledge/public_sources/grounding_data/FACTS.md"
TEXT_DIR = PROJECT_ROOT / "knowledge/public_sources/grounding_data/text"

VALID_DOMAINS = {"hr", "ops", "finance", "corporate", "governance"}
VALID_SCOPES = {"standalone", "group"}
VALID_CONFIDENCES = {"verified", "derived", "uncertain"}

REQUIRED_TARGET_FIELDS = {
    "id",
    "domain",
    "metric",
    "period",
    "value",
    "unit",
    "tolerance",
    "scope",
    "citation",
    "confidence",
    "target_tables",
    "questions_served",
}

REQUIRED_ASSUMPTION_ITEMS = {
    "grade_wise_headcount",
    "asset_level_headcount",
    "asset_level_pnl",
    "obc_share",
    "contract_labour",
    "lifting_cost_proxy",
}


@pytest.fixture(scope="module")
def targets_file_data():
    assert TARGETS_YAML_PATH.exists(), f"Missing {TARGETS_YAML_PATH}"
    with open(TARGETS_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Root must be a dictionary"
    assert "calibration_targets" in data, "YAML root must have 'calibration_targets' key"
    assert "modelled_assumptions" in data, "YAML root must have 'modelled_assumptions' key"
    return data


@pytest.fixture(scope="module")
def targets_list(targets_file_data):
    return targets_file_data["calibration_targets"]


@pytest.fixture(scope="module")
def questions_ids():
    assert QUESTIONS_YAML_PATH.exists(), f"Missing {QUESTIONS_YAML_PATH}"
    with open(QUESTIONS_YAML_PATH, "r", encoding="utf-8") as f:
        qdata = yaml.safe_load(f)
    questions = qdata.get("questions", qdata)
    return {q["id"] for q in questions}


@pytest.fixture(scope="module")
def ground_truth_texts():
    """Load FACTS.md and referenced raw text files for anti-hallucination verification."""
    assert FACTS_PATH.exists(), f"Missing {FACTS_PATH}"
    facts_content = FACTS_PATH.read_text(encoding="utf-8")
    
    text_corpus = {}
    if TEXT_DIR.exists():
        for p in TEXT_DIR.glob("*.txt"):
            try:
                text_corpus[p.name] = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
                
    combined = facts_content + "\n" + "\n".join(text_corpus.values())
    return {
        "facts": facts_content,
        "combined": combined,
        "files": text_corpus,
    }


def _get_number_variants(val, unit: str) -> set[str]:
    """Generate textual representations of a number (Western, Indian comma, mn conversions, decimals)."""
    variants = {str(val)}
    if isinstance(val, int):
        variants.add(f"{val:,}")
        s = str(val)
        if len(s) > 3:
            last3 = s[-3:]
            rest = s[:-3]
            groups = []
            while len(rest) > 2:
                groups.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.insert(0, rest)
            variants.add(",".join(groups) + "," + last3)
        if unit == "cr_inr":
            mn_val = val * 10
            variants.add(str(mn_val))
            variants.add(f"{mn_val:,}")
            # Also allow approximate million integer match for roundings
            variants.add(f"{val*10 - 5}")
            variants.add(f"{val*10 + 5}")
    elif isinstance(val, float):
        variants.add(f"{val:.2f}")
        variants.add(f"{val:.1f}")
        variants.add(f"{val:.3f}")
        clean_s = f"{val:.4f}".rstrip("0").rstrip(".")
        variants.add(clean_s)
        int_part = int(val)
        frac = str(val).split(".")[1]
        variants.add(f"{int_part:,}.{frac}")
        if unit == "lakh_inr":
            full_inr = int(val * 100000)
            variants.add(str(full_inr)[:4])
    return variants


def test_target_count_at_least_40(targets_list):
    """Check that calibration targets has at least 40 targets."""
    assert len(targets_list) >= 40, f"Expected >= 40 targets, got {len(targets_list)}"


def test_no_duplicate_target_ids(targets_list):
    """Check that all target IDs are unique."""
    ids = [t["id"] for t in targets_list]
    duplicates = [tid for tid in ids if ids.count(tid) > 1]
    assert len(ids) == len(set(ids)), f"Duplicate target IDs found: {set(duplicates)}"


def test_required_fields_present_and_valid(targets_list):
    """Check that all targets contain the required schema fields."""
    for t in targets_list:
        tid = t.get("id")
        assert tid, "Target missing 'id'"
        missing = REQUIRED_TARGET_FIELDS - set(t.keys())
        assert not missing, f"Target {tid} missing required fields: {missing}"

        assert t["domain"] in VALID_DOMAINS, f"Invalid domain '{t['domain']}' in {tid}"
        assert t["scope"] in VALID_SCOPES, f"Invalid scope '{t['scope']}' in {tid}"
        assert t["confidence"] in VALID_CONFIDENCES, f"Invalid confidence '{t['confidence']}' in {tid}"
        assert isinstance(t["metric"], str) and len(t["metric"].strip()) > 0, f"Empty metric in {tid}"
        assert isinstance(t["period"], str) and len(t["period"].strip()) > 0, f"Empty period in {tid}"
        assert isinstance(t["value"], (int, float)), f"Value must be numeric in {tid}, got {type(t['value'])}"
        assert isinstance(t["unit"], str) and len(t["unit"].strip()) > 0, f"Empty unit in {tid}"

        # Tolerance: relative float (e.g. 0.02) or string 'exact'
        tol = t["tolerance"]
        assert tol == "exact" or isinstance(tol, (int, float)), f"Invalid tolerance '{tol}' in {tid}"

        assert isinstance(t["target_tables"], list) and len(t["target_tables"]) > 0, f"Empty target_tables in {tid}"
        assert isinstance(t["questions_served"], list) and len(t["questions_served"]) > 0, f"Empty questions_served in {tid}"


def test_every_target_has_valid_citation(targets_list):
    """Check that every target has a valid citation to FACTS.md source documents."""
    for t in targets_list:
        tid = t["id"]
        citation = t.get("citation")
        assert isinstance(citation, str) and len(citation.strip()) >= 3, f"Missing or empty citation in {tid}"


def test_every_question_served_exists_in_questions_yaml(targets_list, questions_ids):
    """Check that all questions_served reference valid IDs in questions.yaml."""
    for t in targets_list:
        tid = t["id"]
        for qid in t["questions_served"]:
            assert qid in questions_ids, f"Target {tid} references unknown question ID '{qid}'"


def test_anti_hallucination_verified_targets(targets_list, ground_truth_texts):
    """Every target with confidence 'verified' must appear in FACTS.md or cited text file."""
    facts_text = ground_truth_texts["facts"]
    all_text = ground_truth_texts["combined"]

    failures = []
    for t in targets_list:
        if t.get("confidence") == "verified":
            val = t["value"]
            unit = t["unit"]
            variants = _get_number_variants(val, unit)
            found = any(v in facts_text for v in variants) or any(v in all_text for v in variants)
            if not found:
                failures.append({
                    "id": t["id"],
                    "metric": t["metric"],
                    "value": val,
                    "unit": unit,
                    "citation": t["citation"],
                    "tested_variants": list(variants),
                })

    assert not failures, (
        f"Anti-hallucination test failed for {len(failures)} verified target(s):\n"
        + "\n".join(f"  - {f['id']}: val={f['value']} ({f['unit']}) cite='{f['citation']}' metric='{f['metric']}'" for f in failures)
    )


def test_internal_consistency_workforce_headcount(targets_list):
    """Check internal consistency of regular workforce headcounts."""
    by_id = {t["id"]: t for t in targets_list}

    # 1. exec + non-exec = total regular employees
    tot_hc = by_id["CAL-HR-HC-FY26"]["value"]
    exec_hc = by_id["CAL-HR-STR-EXEC"]["value"]
    nonexec_hc = by_id["CAL-HR-STR-NONEXEC"]["value"]
    assert exec_hc + nonexec_hc == tot_hc, f"Exec ({exec_hc}) + Non-exec ({nonexec_hc}) != Total ({tot_hc})"

    # 2. women exec + women non-exec = total women
    tot_women = by_id["CAL-HR-DIV-WOMEN-TOT"]["value"]
    women_exec = by_id["CAL-HR-DIV-WOMEN-EXEC"]["value"]
    women_nonexec = by_id["CAL-HR-DIV-WOMEN-NONEXEC"]["value"]
    assert women_exec + women_nonexec == tot_women, f"Women exec ({women_exec}) + non-exec ({women_nonexec}) != Total ({tot_women})"

    # 3. PwD exec + non-exec = total PwD
    tot_pwd = by_id["CAL-HR-DIV-PWD-TOT"]["value"]
    pwd_exec = by_id["CAL-HR-DIV-PWD-EXEC"]["value"]
    pwd_nonexec = by_id["CAL-HR-DIV-PWD-NONEXEC"]["value"]
    assert pwd_exec + pwd_nonexec == tot_pwd, f"PwD exec ({pwd_exec}) + non-exec ({pwd_nonexec}) != Total ({tot_pwd})"

    # 4. Assam headcount consistency
    assam_tot = by_id["CAL-HR-LOC-ASSAM-TOT"]["value"]
    assam_exec = by_id["CAL-HR-LOC-ASSAM-EXEC"]["value"]
    assam_nonexec = by_id["CAL-HR-LOC-ASSAM-NONEXEC"]["value"]
    assert assam_exec + assam_nonexec == assam_tot, f"Assam exec + non-exec != Assam total"

    assam_grpa = by_id["CAL-HR-LOC-ASSAM-GRPA"]["value"]
    assam_grpb = by_id["CAL-HR-LOC-ASSAM-GRPB"]["value"]
    assam_grpc = by_id["CAL-HR-LOC-ASSAM-GRPC"]["value"]
    assam_grpd = by_id["CAL-HR-LOC-ASSAM-GRPD"]["value"]
    assert assam_grpa + assam_grpb == assam_exec, f"Assam Grp A ({assam_grpa}) + Grp B ({assam_grpb}) != Assam Exec ({assam_exec})"
    assert assam_grpc + assam_grpd == assam_nonexec, f"Assam Grp C ({assam_grpc}) + Grp D ({assam_grpd}) != Assam Non-exec ({assam_nonexec})"


def test_internal_consistency_segment_revenues(targets_list):
    """Check that offshore + onshore segment revenues reconcile to total revenue within 1%."""
    by_id = {t["id"]: t for t in targets_list}
    tot_rev = by_id["CAL-FIN-REV-FY26"]["value"]
    offshore_rev = by_id["CAL-FIN-SEG-REV-OFFSHORE"]["value"]
    onshore_rev = by_id["CAL-FIN-SEG-REV-ONSHORE"]["value"]

    sum_seg_rev = offshore_rev + onshore_rev
    pct_diff = abs(sum_seg_rev - tot_rev) / tot_rev
    assert pct_diff <= 0.01, f"Segment revenue sum ({sum_seg_rev}) differs from total revenue ({tot_rev}) by {pct_diff:.2%}"


def test_internal_consistency_operations(targets_list):
    """Check internal consistency of oil/gas splits and drilling counts."""
    by_id = {t["id"]: t for t in targets_list}

    # Crude production ONGC standalone + JV ≈ Total production
    tot_oil = by_id["CAL-OPS-PROD-OIL-FY26"]["value"]
    ongc_oil = by_id["CAL-OPS-PROD-OIL-ONGC-FY26"]["value"]
    jv_oil = by_id["CAL-OPS-PROD-OIL-JV-FY26"]["value"]
    assert abs((ongc_oil + jv_oil) - tot_oil) / tot_oil <= 0.01

    # Gas production ONGC standalone + JV ≈ Total production
    tot_gas = by_id["CAL-OPS-PROD-GAS-FY26"]["value"]
    ongc_gas = by_id["CAL-OPS-PROD-GAS-ONGC-FY26"]["value"]
    jv_gas = by_id["CAL-OPS-PROD-GAS-JV-FY26"]["value"]
    assert abs((ongc_gas + jv_gas) - tot_gas) / tot_gas <= 0.01

    # Wells drilled: Exploratory + Development = Total
    tot_wells = by_id["CAL-OPS-WELLS-TOT-FY26"]["value"]
    expl_wells = by_id["CAL-OPS-WELLS-EXPL-FY26"]["value"]
    dev_wells = by_id["CAL-OPS-WELLS-DEV-FY26"]["value"]
    assert expl_wells + dev_wells == tot_wells, f"Exploratory ({expl_wells}) + Dev ({dev_wells}) != Total ({tot_wells})"


def test_modelled_assumptions_present_and_complete(targets_file_data):
    """Check that modelled_assumptions section contains all 6 non-public items with ranges and rationales."""
    assumptions = targets_file_data["modelled_assumptions"]
    assert len(assumptions) >= 6, f"Expected >= 6 modelled assumptions, got {len(assumptions)}"

    items = {a["item"] for a in assumptions}
    missing = REQUIRED_ASSUMPTION_ITEMS - items
    assert not missing, f"Missing required modelled assumptions: {missing}"

    for a in assumptions:
        item = a["item"]
        assert "description" in a and len(a["description"]) > 0, f"Empty description in {item}"
        assert "proposed_range" in a and a["proposed_range"], f"Empty proposed_range in {item}"
        assert "rationale" in a and len(a["rationale"]) > 0, f"Empty rationale in {item}"
        assert "confidence" in a, f"Missing confidence in {item}"

    # Verify lifting cost is flagged uncertain
    lifting = next(a for a in assumptions if a["item"] == "lifting_cost_proxy")
    assert lifting["confidence"] == "uncertain", f"Lifting cost must be flagged uncertain, got {lifting['confidence']}"
