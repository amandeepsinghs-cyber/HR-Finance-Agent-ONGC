"""Test ensuring that agent application code never imports or opens files from answer_key.
Guarantees clean separation: answer_key is strictly the evaluation oracle.
Only certified/ may derive from answer_key roots, through scripts/build_certified.py committed with provenance.
"""

from pathlib import Path
import yaml
import re

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BACKEND_DIR / "app"
CERTIFIED_DIR = BACKEND_DIR / "certified"
CERTIFIED_FILE = CERTIFIED_DIR / "library.yaml"
SCRIPTS_DIR = BACKEND_DIR / "scripts"


def test_no_answer_key_imports_in_app():
    """Asserts that no file in app/** imports or references answer_key (except optional cache.py)."""
    violations = []
    for p in APP_DIR.rglob("*.py"):
        if p.name == "cache.py":
            continue  # Optional demo cache module
        text = p.read_text(encoding="utf-8")
        if "answer_key" in text:
            violations.append(str(p))

    assert not violations, f"Found references to answer_key in application code: {violations}"


def test_certified_library_provenance_and_integrity():
    """Asserts that certified/library.yaml contains the 89 answer_key root queries with provenance
    plus the 12 P2H.6 employee_360 synthetic queries referencing only catalog tables.

    Follow-ups and paraphrases must be strictly absent.
    """
    import json

    assert CERTIFIED_FILE.exists(), f"Missing certified library file: {CERTIFIED_FILE}"
    with open(CERTIFIED_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    catalog_file = APP_DIR / "semantic" / "semantic_catalog.json"
    assert catalog_file.exists(), f"Missing semantic catalog: {catalog_file}"
    catalog_tables = set(json.loads(catalog_file.read_text(encoding="utf-8")).get("tables", {}).keys())

    queries = data.get("queries", [])
    ak_queries = [
        q for q in queries
        if isinstance(q.get("provenance"), dict)
        and str(q["provenance"].get("source_file", "")).startswith("data_bank/answer_key/")
    ]
    e360_queries = [q for q in queries if q.get("group") == "employee_360"]

    assert len(ak_queries) == 89, (
        f"Certified library must contain exactly 89 answer-key root queries, got {len(ak_queries)}"
    )
    assert len(e360_queries) == 12, (
        f"Certified library must contain exactly 12 employee_360 queries, got {len(e360_queries)}"
    )
    assert len(ak_queries) + len(e360_queries) == len(queries), (
        f"Unclassified queries in certified library: total={len(queries)}, "
        f"ak={len(ak_queries)}, e360={len(e360_queries)}"
    )

    for q in ak_queries:
        qid = q["id"]
        # Ensure only roots are present
        assert "__" not in qid, f"Certified library contains non-root follow-up: {qid}"

        # Ensure provenance exists
        prov = q.get("provenance", {})
        assert "source_file" in prov, f"Missing source_file in provenance for {qid}"
        assert prov["source_file"].endswith(f"{qid}.sql"), f"Invalid source_file in provenance: {prov['source_file']}"
        assert "sha256" in prov and len(prov["sha256"]) == 64, f"Missing or invalid sha256 in provenance for {qid}"

        # Ensure parameterized SQL and visual kind exist
        assert "parameterized_sql" in q and len(q["parameterized_sql"]) > 10
        assert "visual_kind" in q and q["visual_kind"] in {"table", "bar_chart", "kpi_card", "refusal", "document"}

    for q in e360_queries:
        qid = q["id"]
        assert "__" not in qid, f"employee_360 query contains non-root follow-up: {qid}"
        assert qid.startswith("HR_E360_"), f"Unexpected employee_360 query id: {qid}"
        sql = q.get("parameterized_sql", "")
        assert len(sql) > 10, f"Missing parameterized_sql for {qid}"
        ref_tables = set(re.findall(r"\bhrfin_(?:gold|silver)\.[a-z0-9_]+\b", sql, flags=re.I))
        assert ref_tables, f"employee_360 query {qid} does not reference any hrfin_* table"
        unknown_tables = ref_tables - catalog_tables
        assert not unknown_tables, (
            f"employee_360 query {qid} references tables not in semantic_catalog.json: {unknown_tables}"
        )


def test_build_certified_script_present():
    """Asserts that scripts/build_certified.py is committed and valid."""
    build_script = SCRIPTS_DIR / "build_certified.py"
    assert build_script.exists(), "Missing scripts/build_certified.py"
    text = build_script.read_text(encoding="utf-8")
    assert "provenance" in text
    assert "hashlib.sha256" in text
