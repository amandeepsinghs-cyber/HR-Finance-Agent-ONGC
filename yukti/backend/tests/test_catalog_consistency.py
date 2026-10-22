"""Catalog consistency CI test (Task B1.4 / FEAT-008).

Offline verification ensuring code, prompts, and certified templates do not reference
missing tables, columns, entity codes, or unprofiled categorical values.
"""

import json
from pathlib import Path
import re
from typing import Any, Dict, List
import yaml

from app.semantic.entities import CODE_RE
from app.semantic.normalize import (
    categorical_values,
    normalize_categorical_filters,
    referenced_tables,
)
from app.tools.semantic_layer import SEMANTIC_LAYER_PROMPT

BACKEND = Path(__file__).resolve().parent.parent
CAT_PATH = BACKEND / "app/semantic/semantic_catalog.json"
ENTITIES_PATH = BACKEND / "app/semantic/entities.json"

CAT: Dict[str, Any] = json.loads(CAT_PATH.read_text(encoding="utf-8")) if CAT_PATH.exists() else {}
ENTITIES: Dict[str, Any] = json.loads(ENTITIES_PATH.read_text(encoding="utf-8")) if ENTITIES_PATH.exists() else {}

KNOWN_ENTITY_CODES = (
    set(ENTITIES.get("work_centres", {}).keys())
    | set(ENTITIES.get("disciplines", {}).keys())
    | set(ENTITIES.get("fields", {}).keys())
)

TABLE_RE = re.compile(r"\b(hrfin_(?:gold|silver))\b\.([A-Za-z0-9_]+)", re.IGNORECASE)

_EQ_RE = re.compile(
    r"(?P<lower>LOWER\s*\(\s*)?(?P<col>(?:\b\w+\.)?\b(?P<name>[A-Za-z_]\w*))(?P<close>\s*\))?\s*"
    r"(?P<op>=|!=|<>)\s*'(?P<val>[^']*)'",
    re.IGNORECASE,
)
_IN_RE = re.compile(
    r"(?P<lower>LOWER\s*\(\s*)?(?P<col>(?:\b\w+\.)?\b(?P<name>[A-Za-z_]\w*))(?P<close>\s*\))?\s+"
    r"(?P<not>NOT\s+)?IN\s*\((?P<vals>\s*'[^']*'(?:\s*,\s*'[^']*')*\s*)\)",
    re.IGNORECASE,
)


def get_scan_files() -> List[Path]:
    """Files to scan for entity codes and table references."""
    files = sorted((BACKEND / "app").rglob("*.py"))
    files.append(BACKEND / "certified/library.yaml")
    files.append(BACKEND / "app/semantic/entity_aliases.yaml")
    files.append(BACKEND / "scripts/warmup_answer_cache.py")
    return [f for f in files if f.exists()]


def entity_code_violations(text: str, source: str) -> List[str]:
    """Returns violations for any CODE_RE match not in entities.json."""
    violations: List[str] = []
    for m in CODE_RE.finditer(text or ""):
        code = m.group(1)
        if code not in KNOWN_ENTITY_CODES:
            violations.append(f"{source}: unknown entity code '{code}'")
    return violations


def table_violations(text: str, source: str) -> List[str]:
    """Returns violations for any hrfin_gold.<t> / hrfin_silver.<t> not in catalog."""
    violations: List[str] = []
    catalog_tables = set(CAT.get("tables", {}).keys())
    for m in TABLE_RE.finditer(text or ""):
        dataset = m.group(1).lower()
        tbl = m.group(2).lower()
        if tbl.startswith("information_schema"):
            continue
        key = f"{dataset}.{tbl}"
        if key not in catalog_tables:
            violations.append(f"{source}: unknown table '{key}'")
    return violations


def prompt_column_violations() -> List[str]:
    """Parses SEMANTIC_LAYER_PROMPT bullets and checks columns exist in catalog."""
    violations: List[str] = []
    bullets = re.split(r"\n\s*•\s*", SEMANTIC_LAYER_PROMPT)
    for b in bullets[1:]:
        first_line = b.strip().splitlines()[0]
        header_tables = re.findall(r"`(hrfin_(?:gold|silver)\.[a-z0-9_]+)`", first_line)
        exact_cols_match = re.search(
            r"-\s*Exact Columns:\s*(.+?)(?:\.\s*$|\n\s*-|\n\s*•|\Z)",
            b,
            re.DOTALL,
        )

        target_table = None
        cols_str = None

        if exact_cols_match:
            if len(header_tables) == 1:
                target_table = header_tables[0]
                cols_str = exact_cols_match.group(1).strip().rstrip(".")
        else:
            silver_match = re.match(r"^`(hrfin_silver\.[a-z0-9_]+)`:\s*(.+)$", first_line)
            if silver_match and len(header_tables) == 1:
                target_table = silver_match.group(1)
                cols_str = silver_match.group(2).strip().rstrip(".")

        if not target_table or not cols_str:
            continue

        table_meta = CAT.get("tables", {}).get(target_table, {})
        cat_cols = set(table_meta.get("columns", {}).keys())
        if not cat_cols:
            violations.append(f"{target_table} (table missing from catalog)")
            continue

        # Strip parenthetical hints like ('Active'|'Separated') and (1 if active else 0)
        cleaned = re.sub(r"\([^)]*\)", "", cols_str)
        for raw_col in cleaned.split(","):
            token = raw_col.strip()
            if not token:
                continue
            m = re.match(r"^([a-zA-Z0-9_]+)", token)
            if not m:
                continue
            col_name = m.group(1).lower()
            if col_name not in cat_cols:
                violations.append(f"{target_table}.{col_name}")

    return violations


PARAM_SENTINEL = "__PARAM__"
# Literals that are valid even though no current row holds them: every grade code in dim_grade
# (e.g. 'E0' has no active employee today), plus documented non-filter labels.
KNOWN_CODES = set(ENTITIES.get("grades", {}))
LITERAL_ALLOWLIST = {("F8", "ALL BASINS")}  # certified F8: CTE total-row label in ORDER BY, not a data filter


def _exempt(source: str, col_name: str, val: str) -> bool:
    """Scoped exemptions (G4 B1 r2): grade codes only on *grade_id columns; labels only for their query."""
    if val == PARAM_SENTINEL:
        return True
    if val in KNOWN_CODES and col_name.endswith("grade_id"):
        return True
    return (source.split(":")[-1], val) in LITERAL_ALLOWLIST


def categorical_literal_violations(sql: str, source: str) -> List[str]:
    """Validates categorical literals against catalog spellings and profiled values."""
    violations: List[str] = []
    # (a) normalize_categorical_filters(sql) must return the SQL unchanged
    norm = normalize_categorical_filters(sql, CAT)
    if norm != sql:
        violations.append(f"{source}: normalize_categorical_filters modified SQL (casing mismatch)")

    # (b) each col = 'value' / IN (...) literal on a profiled categorical column must be in catalog
    tables = referenced_tables(sql)
    colvals = categorical_values(tables, CAT)
    for m in _EQ_RE.finditer(sql):
        col_name = m.group("name").lower()
        val = m.group("val")
        if _exempt(source, col_name, val):
            continue
        if col_name in colvals:
            stored = {v.lower() for v in colvals[col_name]}
            if val.lower() not in stored:
                violations.append(
                    f"{source}: column '{col_name}' literal '{val}' not in catalog values"
                )

    for m in _IN_RE.finditer(sql):
        col_name = m.group("name").lower()
        vals = re.findall(r"'([^']*)'", m.group("vals"))
        if col_name in colvals:
            stored = {v.lower() for v in colvals[col_name]}
            for val in vals:
                if not _exempt(source, col_name, val) and val.lower() not in stored:
                    violations.append(
                        f"{source}: column '{col_name}' IN literal '{val}' not in catalog values"
                    )

    return violations


# --------------------------------------------------------------------------- Tests


def test_entity_codes():
    """Scans code and certified library for unknown entity codes."""
    violations: List[str] = []
    for path in get_scan_files():
        rel = path.relative_to(BACKEND)
        text = path.read_text(encoding="utf-8", errors="ignore")
        violations.extend(entity_code_violations(text, str(rel)))
    assert not violations, (
        f"Entity code violations ({len(violations)}):\n" + "\n".join(violations)
    )


def test_tables():
    """Scans code and certified library for unknown table references."""
    violations: List[str] = []
    for path in get_scan_files():
        rel = path.relative_to(BACKEND)
        text = path.read_text(encoding="utf-8", errors="ignore")
        violations.extend(table_violations(text, str(rel)))
    assert not violations, (
        f"Table reference violations ({len(violations)}):\n" + "\n".join(violations)
    )


def test_prompt_columns():
    """Verifies that SEMANTIC_LAYER_PROMPT bullet columns exist in catalog."""
    violations = prompt_column_violations()
    assert not violations, (
        f"Prompt column violations ({len(violations)}):\n" + "\n".join(violations)
    )


def test_certified_categorical_literals():
    """Verifies categorical filters in certified parameterized SQL library."""
    lib_path = BACKEND / "certified/library.yaml"
    assert lib_path.exists(), "certified/library.yaml not found"
    data = yaml.safe_load(lib_path.read_text(encoding="utf-8"))
    queries = data.get("queries", []) if isinstance(data, dict) else []

    violations: List[str] = []
    for q in queries:
        sql = q.get("parameterized_sql", "")
        # Replace @param placeholders with a sentinel literal that the checker ignores
        # (O correction to packet B1.4 §5.4: a literal 'X' was reported as a bad value).
        sql_sub = re.sub(r"@\w+", f"'{PARAM_SENTINEL}'", sql)
        violations.extend(
            categorical_literal_violations(sql_sub, f"certified:{q.get('id', '?')}")
        )
    assert not violations, (
        f"Certified query categorical violations ({len(violations)}):\n"
        + "\n".join(violations)
    )


def test_prompt_example_categorical_literals():
    """Verifies example SQL snippets inside SEMANTIC_LAYER_PROMPT."""
    example_sqls = re.findall(r"`(SELECT\s+[^`]+)`", SEMANTIC_LAYER_PROMPT, re.IGNORECASE)
    violations: List[str] = []
    for i, sql in enumerate(example_sqls, 1):
        violations.extend(categorical_literal_violations(sql, f"prompt:example_{i}"))
    assert not violations, (
        f"Prompt example SQL categorical violations ({len(violations)}):\n"
        + "\n".join(violations)
    )


def test_injected_bad_code_is_caught():
    """Proves the CI test fails on injected bad codes, tables, and categoricals."""
    v_code = entity_code_violations("WHERE wc_id = 'WC-EOA'", "injected")
    assert len(v_code) > 0, "Expected entity_code_violations to catch WC-EOA"

    v_table = table_violations("FROM hrfin_gold.not_a_table", "injected")
    assert len(v_table) > 0, "Expected table_violations to catch hrfin_gold.not_a_table"

    bad_sql = "SELECT 1 FROM hrfin_gold.ssot_workforce_employee WHERE employment_status = 'active'"
    v_cat = categorical_literal_violations(bad_sql, "injected")
    assert len(v_cat) > 0, "Expected categorical_literal_violations to catch lowercase 'active'"


def test_entities_match_catalog():
    """Entities.json work_centres must match catalog dim_work_centre.wc_id values (or distinct == 46)."""
    ent_wcs = set(ENTITIES.get("work_centres", {}).keys())
    dim_wc = (
        CAT.get("tables", {})
        .get("hrfin_silver.dim_work_centre", {})
        .get("columns", {})
        .get("wc_id", {})
    )
    if "values" in dim_wc and dim_wc["values"]:
        cat_wcs = set(dim_wc["values"])
        assert ent_wcs == cat_wcs, (
            f"Work centre codes mismatch:\n"
            f"In entities only: {ent_wcs - cat_wcs}\n"
            f"In catalog only: {cat_wcs - ent_wcs}"
        )
    else:
        assert dim_wc.get("distinct") == 46, (
            f"Expected distinct == 46, got {dim_wc.get('distinct')}"
        )
        assert len(ent_wcs) == 46, f"Expected 46 entities, got {len(ent_wcs)}"


def test_no_malformed_or_legacy_codes():
    """Codes like WC-N&H / WC-B&S / lower-case codes escape CODE_RE; scan for them separately (G4 B1 r1)."""
    pat = re.compile(r"\b(WC|DISC|FLD)-[A-Za-z0-9&]{2,}(?:-[A-Za-z]{3})?", re.I)
    known = set(ENTITIES["work_centres"]) | set(ENTITIES["disciplines"]) | set(ENTITIES["fields"])
    bad = []
    files = list((BACKEND / "app").rglob("*.py")) + [BACKEND / "certified/library.yaml",
                                                      BACKEND / "app/semantic/entity_aliases.yaml"]
    for f in files:
        for m in pat.finditer(f.read_text(encoding="utf-8")):
            if m.group(0) not in known and m.group(0).upper() not in known or m.group(0) != m.group(0).upper():
                bad.append(f"{f.name}: {m.group(0)}")
    assert not bad, sorted(set(bad))
