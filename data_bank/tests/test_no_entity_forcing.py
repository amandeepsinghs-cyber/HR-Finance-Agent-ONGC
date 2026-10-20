"""test_no_entity_forcing.py: Hardened static AST scanner enforcing Rule 5a and FULLY EMERGENT data generation.

Governing Policy (DELEGATION_PLAYBOOK.md § HARD RULES):
- FULLY EMERGENT (user decision, 2026-10-19). Story findings must come ONLY from general simulation rules:
  * FORBIDDEN: any condition, dictionary, loop count or index slice keyed on a specific entity ID
    (WC-/FLD-/PRJ-/CUST-/VEN-/EMP-) or story number that sets an amount, count, date, flag or selects records.
  * FORBIDDEN: numeric literals equal to story numbers in world_bible/story_register.yaml.
  * FORBIDDEN: slicing/range patterns tied to story counts (e.g. `[:260]`, `range(107)`).

Anti-Evasion Hardening (Lead Directives 2026-10-19):
  (a) Entity IDs: comparisons, membership tests (`in`, `.isin()`), dict keys, and allocation lists with entity ID literals.
  (b) Story Literals: numeric literals matching story numbers (unwhitelisted, >=2 non-zero digits or decimals, feeding output).
  (c) Slicing/Ranges: `range(N)`, `[:N]`, `idx < N` where N is an unwhitelisted story count.
  (d) String-Wrapped Numbers: `int()`, `float()`, `Decimal()`, `eval()`, `ast.literal_eval()`, `json.loads()` on string constants with digits.
  (e) Name-Based Entity Selection: entity names, short_names, cities, or field names (>=4 chars) from reference YAML used in
      comparisons, `.startswith()`, regex, or dict keys outside reference loading.
  (f) Name-Attribute Branching: branching on `.get("name")`, `["name"]`, `short_name`, `city`, `field_name` in conditionals.
  (g) Story-Number Arithmetic: binary operations involving story numbers or folded constant expressions matching story numbers.

Demo Persona Exemption (Lead Directive 2026-10-19):
- Demo-persona records are allowed to be specified exactly inside a single clearly delimited block:
  a function named `apply_demo_personas(...)` (or top-level `PERSONAS` dict/list whose keys/entries are only
  the 5 allowlisted EMP IDs: EMP-000001..3, EMP-102451, EMP-103892). Inside this delimited block, rules
  (b), (d), and (g) are exempted; everything outside it stays strict.
"""

import ast
import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
GENERATORS_DIR = DATA_BANK_ROOT / "generators"
WORLD_BIBLE_DIR = DATA_BANK_ROOT / "world_bible"
REF_DIR = WORLD_BIBLE_DIR / "reference"
WHITELIST_FILE = Path(__file__).resolve().parent / "entity_forcing_whitelist.yaml"

# Static checksum of entity_forcing_whitelist.yaml (editable ONLY by the lead)
WHITELIST_SHA256_RECORDED = "799ce970ca2dd8dcf3838ad4292b5d87cf57e7bf31fff683e64bb0b10ea4d526"

# -----------------------------------------------------------------------------
# 1. LOAD WORLD BIBLE EXPECTATIONS, CALIBRATION TARGETS & WHITELIST
# -----------------------------------------------------------------------------
STORY_REGISTER_FILE = WORLD_BIBLE_DIR / "story_register.yaml"
CALIBRATION_FILE = WORLD_BIBLE_DIR / "calibration_targets.yaml"

ENTITY_PATTERN = re.compile(
    r"^(WC-[A-Z0-9_-]+|FLD-[A-Z0-9_-]+|PRJ-[A-Z0-9_-]+|CUST-[A-Z0-9_-]+|VEN-[A-Z0-9_-]+|EMP-[0-9]{6})$"
)

# Reference entity names (work centres, fields, projects, customers, vendors)
ENTITY_NAMES: Set[str] = set()
STOP_WORDS = {
    "asset", "basin", "plant", "institute", "forward", "base", "headquarters", "corporate",
    "office", "services", "operations", "management", "division", "sector", "cluster",
    "limited", "company", "india", "drilling", "production", "refinery", "corporation",
    "block", "field", "project", "centre", "center", "scheme", "phase", "deep", "tight", "gas",
}


def load_configurations():
    """Load whitelist, story numbers, calibration targets, and reference entity names."""
    # 1. Read Whitelist YAML
    if not WHITELIST_FILE.exists():
        raise FileNotFoundError(f"Missing whitelist file: {WHITELIST_FILE}")
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        wl_data = yaml.safe_load(f)

    unit_cal_constants = set(wl_data.get("unit_and_calendar_constants", []))
    aging_buckets = set(wl_data.get("aging_buckets", []))
    allowed_personas = set(wl_data.get("allowed_personas", []))
    additional_wl = set(wl_data.get("additional_whitelisted_numbers", []))

    # 2. Read Story Numbers
    story_numbers: Dict[float, List[str]] = {}
    if STORY_REGISTER_FILE.exists():
        with open(STORY_REGISTER_FILE, "r", encoding="utf-8") as f:
            sreg = yaml.safe_load(f)
        for s in sreg.get("stories", []):
            sid = s.get("id")
            for k, v in (s.get("exact_numbers") or {}).items():
                val = v.get("value")
                if isinstance(val, (int, float)):
                    story_numbers.setdefault(float(val), []).append(f"{sid}:{k}")
                    if isinstance(val, float) and val.is_integer():
                        story_numbers.setdefault(int(val), []).append(f"{sid}:{k}")

    # 3. Read Public Calibration Numbers
    calib_numbers: Set[float] = set()
    if CALIBRATION_FILE.exists():
        with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
            ctarg = yaml.safe_load(f)
        for c in ctarg.get("calibration_targets", []):
            val = c.get("value")
            if isinstance(val, (int, float)):
                calib_numbers.add(float(val))
                if isinstance(val, float) and val.is_integer():
                    calib_numbers.add(int(val))

    # 4. Construct Whitelisted Numbers Set
    whitelisted_numbers: Set[float] = set()
    for n in unit_cal_constants | aging_buckets | additional_wl | calib_numbers:
        whitelisted_numbers.add(float(n))
        if isinstance(n, (int, float)) and float(n).is_integer():
            whitelisted_numbers.add(int(n))

    trivial = {0, 1, 2, 3, 4, 5, 10, 12, 100, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 12.0, 100.0}
    whitelisted_numbers.update(trivial)

    # 5. Load Reference Entity Names & Cities
    specific_files = ["work_centres.yaml", "fields.yaml", "projects.yaml", "customers.yaml"]
    for fname in specific_files:
        fpath = REF_DIR / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            for k, v in (data or {}).items():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            for field in ["name", "short_name", "city", "field_name"]:
                                val = item.get(field)
                                if val and isinstance(val, str):
                                    val_clean = val.strip()
                                    if len(val_clean) >= 4 and val_clean.lower() not in STOP_WORDS:
                                        ENTITY_NAMES.add(val_clean)
                                    for word in re.findall(r"[A-Z][a-z]{3,}", val_clean):
                                        if word.lower() not in STOP_WORDS:
                                            ENTITY_NAMES.add(word)

    return allowed_personas, whitelisted_numbers, story_numbers


ALLOWLIST_PERSONAS, WHITELISTED_NUMBERS, ALL_STORY_NUMBERS = load_configurations()


# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS FOR HARDENED AST DETECTION
# -----------------------------------------------------------------------------
def is_entity_id(val: Any) -> bool:
    """Check if value is a non-allowlisted entity ID literal (WC-, FLD-, PRJ-, CUST-, VEN-, EMP-)."""
    if not isinstance(val, str):
        return False
    if val in ALLOWLIST_PERSONAS:
        return False
    return bool(ENTITY_PATTERN.match(val))


def is_entity_name_string(s: Any) -> bool:
    """Check if string literal matches a reference entity name/city/field (Rule e)."""
    if not isinstance(s, str):
        return False
    s_clean = s.strip()
    if len(s_clean) < 4:
        return False
    return s_clean in ENTITY_NAMES


def extract_numeric_value(node: ast.AST) -> Any:
    """Extract numeric value from constant, or unwrap int("840") / float("18.5") calls."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Call):
        func_name = getattr(node.func, "id", getattr(node.func, "attr", ""))
        if func_name in ("int", "float", "Decimal") and node.args and isinstance(node.args[0], ast.Constant):
            try:
                if func_name == "int":
                    return int(node.args[0].value)
                if func_name in ("float", "Decimal"):
                    return float(node.args[0].value)
            except Exception:
                pass
    return None


def has_two_nonzero_digits_or_decimal(val: Any) -> bool:
    """Check if number has >= 2 significant non-zero digits or has decimals (Rule b.ii)."""
    s = str(val)
    if "." in s:
        parts = s.split(".")
        if len(parts) == 2 and parts[1] != "0":
            return True
    digits = [c for c in s.split(".")[0] if c.isdigit() and c != "0"]
    return len(digits) >= 2


def is_inside_print_or_docstring(node: ast.AST) -> bool:
    """Check if node is contained inside a print() call or docstring."""
    curr = node
    while hasattr(curr, "parent"):
        curr = curr.parent
        if isinstance(curr, ast.Call) and isinstance(curr.func, ast.Name) and curr.func.id == "print":
            return True
        if isinstance(curr, ast.Expr) and isinstance(curr.value, ast.Constant) and isinstance(curr.value.value, str):
            if hasattr(curr, "parent") and isinstance(curr.parent, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                return True
    return False


def is_reference_loading_context(node: ast.AST) -> bool:
    """Allow entity names and lookups inside legitimate reference data loading / normalization functions."""
    curr = node
    while hasattr(curr, "parent"):
        curr = curr.parent
        if isinstance(curr, ast.FunctionDef):
            fn = curr.name.lower()
            if any(term in fn for term in ("load", "reference", "clean_basin", "setup_geo")):
                return True
    return False


def is_time_or_calendar_context(node: ast.AST) -> bool:
    """Check if node is in a month/day arithmetic context (timedelta, monthrange, days=, hours=)."""
    curr = node
    while hasattr(curr, "parent"):
        parent = curr.parent
        if isinstance(parent, ast.Call):
            func_name = ""
            if isinstance(parent.func, ast.Name):
                func_name = parent.func.id
            elif isinstance(parent.func, ast.Attribute):
                func_name = parent.func.attr
            if func_name in ("timedelta", "monthrange"):
                return True
        if isinstance(parent, ast.keyword) and parent.arg in ("days", "months", "hours", "weeks"):
            return True
        curr = parent
    return False


def is_persona_dict(node: ast.AST) -> bool:
    """Check if AST Dict node defines an authorized demo persona record."""
    if not isinstance(node, ast.Dict):
        return False
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value in ("emp_id", "PERNR", "user_id"):
            if isinstance(v, ast.Constant) and v.value in ALLOWLIST_PERSONAS:
                return True
    return False


def is_inside_demo_personas_block(node: ast.AST) -> bool:
    """Check if AST node is contained within a delimited demo persona block (Rule exemption)."""
    curr = node
    while hasattr(curr, "parent"):
        curr = curr.parent
        # 1. Delimited function apply_demo_personas(...)
        if isinstance(curr, ast.FunctionDef) and ("demo_persona" in curr.name.lower() or curr.name == "apply_demo_personas"):
            return True
        # 2. Delimited top-level PERSONAS dict/list
        if isinstance(curr, ast.Assign):
            for target in curr.targets:
                if isinstance(target, ast.Name) and target.id.upper() in ("PERSONAS", "DEMO_PERSONAS"):
                    return True
        # 3. Individual persona dictionary
        if is_persona_dict(curr):
            return True
    return False


def get_entities_in_ast_node(node: ast.AST) -> List[str]:
    """Recursively collect non-allowlisted entity ID literals from an AST node."""
    if is_persona_dict(node):
        return []
    ents = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if is_entity_id(node.value):
            ents.append(node.value)
    for child in ast.iter_child_nodes(node):
        ents.extend(get_entities_in_ast_node(child))
    return ents


# -----------------------------------------------------------------------------
# 3. SCANNER ENGINE
# -----------------------------------------------------------------------------
def scan_generator_file(filepath: Path) -> List[Dict[str, Any]]:
    """Scan a generator python file for Rule 5a and FULLY EMERGENT violations."""
    with open(filepath, "r", encoding="utf-8") as f:
        src = f.read()

    lines = src.splitlines()
    tree = ast.parse(src, filename=str(filepath))

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent

    findings = []

    def add_finding(category: str, node: ast.AST, detail: str):
        if is_inside_print_or_docstring(node):
            return
        lineno = getattr(node, "lineno", 0)
        snippet = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
        findings.append({
            "category": category,
            "lineno": lineno,
            "snippet": snippet,
            "detail": detail,
        })

    for node in ast.walk(tree):
        in_persona = is_inside_demo_personas_block(node)

        # ---------------------------------------------------------------------
        # (d) String-Wrapped Numbers: int("840"), float("18.5"), eval("..."), etc.
        # (Exempt inside delimited demo persona blocks)
        # ---------------------------------------------------------------------
        if not in_persona and isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name in ("int", "float", "Decimal", "eval", "literal_eval", "loads"):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    if any(c.isdigit() for c in node.args[0].value):
                        add_finding(
                            "(d) string_wrapped_number",
                            node,
                            f"{func_name}(\"{node.args[0].value}\") wraps numeric literal in string conversion"
                        )

        # ---------------------------------------------------------------------
        # (e) Name-Based Entity Selection in Comparisons / in / Dict Keys / Regex
        # (Exempt inside reference loading and delimited demo persona blocks)
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Compare) and not is_reference_loading_context(node) and not in_persona:
            for op in [node.left] + node.comparators:
                if isinstance(op, ast.Constant) and is_entity_name_string(op.value):
                    add_finding(
                        "(e) name_based_entity_selection",
                        node,
                        f"String literal \"{op.value}\" matches entity name/city/field in comparison"
                    )
                elif isinstance(op, (ast.List, ast.Tuple, ast.Set)):
                    for elt in op.elts:
                        if isinstance(elt, ast.Constant) and is_entity_name_string(elt.value):
                            add_finding(
                                "(e) name_based_entity_selection",
                                node,
                                f"Collection contains entity name literal \"{elt.value}\" in comparison"
                            )
                            break

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and not is_reference_loading_context(node) and not in_persona:
            if node.func.attr in ("startswith", "endswith"):
                if node.args and isinstance(node.args[0], ast.Constant) and is_entity_name_string(node.args[0].value):
                    add_finding(
                        "(e) name_based_entity_selection",
                        node,
                        f".{node.func.attr}(\"{node.args[0].value}\") matches entity name/city"
                    )
            elif node.func.attr in ("search", "match"):
                if node.args and isinstance(node.args[0], ast.Constant) and is_entity_name_string(node.args[0].value):
                    add_finding(
                        "(e) name_based_entity_selection",
                        node,
                        f"Regex matches entity name/city \"{node.args[0].value}\""
                    )

        # ---------------------------------------------------------------------
        # (f) Branching on .get("name") / ["name"] / short_name / city
        # (Exempt inside reference loading and delimited demo persona blocks)
        # ---------------------------------------------------------------------
        if isinstance(node, (ast.If, ast.IfExp)) and not is_reference_loading_context(node) and not in_persona:
            test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
            if any(w in test_str for w in [
                ".get(\"name\"", "[\"name\"]", "short_name",
                ".get(\"city\"", "[\"city\"]", "name in", "in name"
            ]):
                add_finding(
                    "(f) name_attribute_branching",
                    node,
                    "Branching on entity name/city attribute in conditional test"
                )

        # ---------------------------------------------------------------------
        # (a) Comparisons and Membership Tests with Entity IDs
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Compare):
            operands = [node.left] + node.comparators
            for op in operands:
                if isinstance(op, ast.Constant) and is_entity_id(op.value):
                    add_finding(
                        "(a) entity_comparison",
                        node,
                        f"Comparison directly uses entity ID literal \"{op.value}\""
                    )
                elif isinstance(op, (ast.List, ast.Tuple, ast.Set)):
                    for elt in op.elts:
                        if isinstance(elt, ast.Constant) and is_entity_id(elt.value):
                            add_finding(
                                "(a) entity_in_membership_list",
                                node,
                                f"Membership test against collection containing entity ID literal \"{elt.value}\""
                            )
                            break

            # (c) Index comparison (idx < N or i < N) tied to story count
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Lt, ast.LtE)):
                comp = node.comparators[0]
                num_val = extract_numeric_value(comp)
                if num_val is not None and num_val in ALL_STORY_NUMBERS and num_val not in WHITELISTED_NUMBERS:
                    add_finding(
                        "(c) story_index_compare",
                        node,
                        f"Index threshold comparison (< {num_val}) matches story count for {ALL_STORY_NUMBERS[num_val]}"
                    )

        # ---------------------------------------------------------------------
        # (a) Dict Keys / (b) Dict Values (Dict values exempt in persona blocks)
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if k is not None and isinstance(k, ast.Constant):
                    if is_entity_id(k.value):
                        add_finding(
                            "(a) entity_dict_key",
                            node,
                            f"Dict key uses entity ID literal \"{k.value}\""
                        )
                    elif is_entity_name_string(k.value) and not is_reference_loading_context(node) and not in_persona:
                        add_finding(
                            "(e) name_based_entity_selection",
                            node,
                            f"Dict key uses entity name literal \"{k.value}\""
                        )
            if not in_persona:
                for v_node in node.values:
                    num_val = extract_numeric_value(v_node)
                    if num_val is not None:
                        if (num_val in ALL_STORY_NUMBERS and num_val not in WHITELISTED_NUMBERS
                                and has_two_nonzero_digits_or_decimal(num_val)
                                and not is_time_or_calendar_context(v_node)):
                            add_finding(
                                "(b) story_numeric_dict_value",
                                node,
                                f"Dict value {num_val} matches story number for {ALL_STORY_NUMBERS[num_val]}"
                            )

        # ---------------------------------------------------------------------
        # (a) Calls to .isin() with Entity IDs
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "isin":
            for arg in node.args:
                if isinstance(arg, (ast.List, ast.Tuple, ast.Set)):
                    for elt in arg.elts:
                        if isinstance(elt, ast.Constant) and is_entity_id(elt.value):
                            add_finding(
                                "(a) entity_isin_call",
                                node,
                                f".isin() called with collection containing entity ID literal \"{elt.value}\""
                            )
                            break

        # ---------------------------------------------------------------------
        # (a) Assignments of small entity lists/tuples / (b) Direct assignments
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Assign):
            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                ents = get_entities_in_ast_node(node.value)
                if ents and len(ents) <= 15:
                    add_finding(
                        "(a) entity_collection_assignment",
                        node,
                        f"Assignment of collection containing entity ID literals: {ents[:5]}"
                    )
            elif not in_persona:
                num_val = extract_numeric_value(node.value)
                if num_val is not None:
                    if (num_val in ALL_STORY_NUMBERS and num_val not in WHITELISTED_NUMBERS
                            and has_two_nonzero_digits_or_decimal(num_val)
                            and not is_time_or_calendar_context(node.value)):
                        add_finding(
                            "(b) story_numeric_literal_assign",
                            node,
                            f"Assignment of numeric literal {num_val} matching story {ALL_STORY_NUMBERS[num_val]}"
                        )

        # ---------------------------------------------------------------------
        # (g) Story Number Arithmetic: BinOp with story numbers or folded result
        # (Exempt inside delimited demo persona blocks)
        # ---------------------------------------------------------------------
        if not in_persona and isinstance(node, ast.BinOp):
            left_val = extract_numeric_value(node.left)
            right_val = extract_numeric_value(node.right)

            for v, operand in [(left_val, node.left), (right_val, node.right)]:
                if v is not None:
                    if (v in ALL_STORY_NUMBERS and v not in WHITELISTED_NUMBERS
                            and has_two_nonzero_digits_or_decimal(v)
                            and not is_time_or_calendar_context(operand)):
                        add_finding(
                            "(g) story_number_arithmetic",
                            node,
                            f"Arithmetic operand numeric literal {v} matches story {ALL_STORY_NUMBERS[v]}"
                        )

            if left_val is not None and right_val is not None and not is_time_or_calendar_context(node):
                try:
                    res = None
                    if isinstance(node.op, ast.Add): res = left_val + right_val
                    elif isinstance(node.op, ast.Sub): res = left_val - right_val
                    elif isinstance(node.op, ast.Mult): res = left_val * right_val
                    elif isinstance(node.op, ast.Div) and right_val != 0: res = left_val / right_val
                    if res is not None and res in ALL_STORY_NUMBERS and res not in WHITELISTED_NUMBERS and has_two_nonzero_digits_or_decimal(res):
                        add_finding(
                            "(g) story_number_arithmetic",
                            node,
                            f"Folded constant arithmetic result {res} matches story {ALL_STORY_NUMBERS[res]}"
                        )
                except Exception:
                    pass

        # ---------------------------------------------------------------------
        # (b) Ternary branches returning story number literals
        # (Exempt inside delimited demo persona blocks)
        # ---------------------------------------------------------------------
        if not in_persona and isinstance(node, ast.IfExp):
            for branch in [node.body, node.orelse]:
                num_val = extract_numeric_value(branch)
                if num_val is not None:
                    if (num_val in ALL_STORY_NUMBERS and num_val not in WHITELISTED_NUMBERS
                            and has_two_nonzero_digits_or_decimal(num_val)
                            and not is_time_or_calendar_context(branch)):
                        add_finding(
                            "(b) story_numeric_in_ternary",
                            node,
                            f"Ternary branch sets numeric literal {num_val} matching story {ALL_STORY_NUMBERS[num_val]}"
                        )

        # ---------------------------------------------------------------------
        # (c) range(N) where N is tied to unwhitelisted story count
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if node.args:
                num_val = extract_numeric_value(node.args[0])
                if num_val is not None and num_val in ALL_STORY_NUMBERS and num_val not in WHITELISTED_NUMBERS:
                    add_finding(
                        "(c) story_range_call",
                        node,
                        f"range({num_val}) matches story count for {ALL_STORY_NUMBERS[num_val]}"
                    )

        # ---------------------------------------------------------------------
        # (c) Slicing [:N] where N is tied to unwhitelisted story count
        # ---------------------------------------------------------------------
        if isinstance(node, ast.Slice):
            for bound in [node.lower, node.upper]:
                num_val = extract_numeric_value(bound)
                if num_val is not None and num_val in ALL_STORY_NUMBERS and num_val not in WHITELISTED_NUMBERS:
                    add_finding(
                        "(c) story_slice_bound",
                        node,
                        f"Slice bound {num_val} matches story count for {ALL_STORY_NUMBERS[num_val]}"
                    )

    return findings


# Discover all data generator scripts (excluding build/setup tools)
GENERATOR_FILES = sorted([
    p for p in GENERATORS_DIR.rglob("*.py")
    if not p.name.startswith("build_") and not p.name.startswith("__")
])


# -----------------------------------------------------------------------------
# 4. PYTEST TEST RUNNERS
# -----------------------------------------------------------------------------
def test_whitelist_integrity():
    """Verify that entity_forcing_whitelist.yaml has not been tampered with or modified."""
    assert WHITELIST_FILE.exists(), f"Missing {WHITELIST_FILE}"
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        actual_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
    assert actual_hash == WHITELIST_SHA256_RECORDED, (
        f"entity_forcing_whitelist.yaml checksum mismatch!\n"
        f"Recorded SHA-256: {WHITELIST_SHA256_RECORDED}\n"
        f"Actual SHA-256:   {actual_hash}\n"
        f"Only the lead may edit this whitelist."
    )


@pytest.mark.parametrize("generator_path", GENERATOR_FILES, ids=lambda p: p.name)
def test_no_entity_forcing(generator_path: Path):
    """Assert that generator adheres to Rule 5a and FULLY EMERGENT simulation rules."""
    findings = scan_generator_file(generator_path)
    if findings:
        report_lines = [
            f"\nFAILED Rule 5a & FULLY EMERGENT Scan: {generator_path.name} ({len(findings)} findings)"
        ]
        for f in findings:
            report_lines.append(
                f"  L{f['lineno']} [{f['category']}]: {f['detail']}\n    Snippet: {f['snippet']}"
            )
        error_msg = "\n".join(report_lines)
        pytest.fail(error_msg, pytrace=False)


# -----------------------------------------------------------------------------
# 5. STANDALONE CLI AUDIT REPORT RUNNER
# -----------------------------------------------------------------------------
def run_cli_audit():
    """Run audit and print full human-readable per-file report."""
    print("=" * 80)
    print("HARDENED AUDIT: ENFORCING RULE 5a & FULLY EMERGENT ARCHITECTURE")
    print("=" * 80)

    # Check whitelist hash
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        actual_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
    print(f"Whitelist Integrity SHA-256: {actual_hash}")
    if actual_hash != WHITELIST_SHA256_RECORDED:
        print(f"WARNING: Whitelist checksum does not match recorded value ({WHITELIST_SHA256_RECORDED})")

    total_findings_all = 0
    file_summary = []

    for gf in GENERATOR_FILES:
        rel_path = gf.relative_to(DATA_BANK_ROOT)
        findings = scan_generator_file(gf)
        total_findings_all += len(findings)

        counts_by_rule = {
            "(a)": 0, "(b)": 0, "(c)": 0, "(d)": 0, "(e)": 0, "(f)": 0, "(g)": 0
        }
        for r in findings:
            prefix = r["category"][:3]
            counts_by_rule[prefix] = counts_by_rule.get(prefix, 0) + 1

        file_summary.append({
            "file": str(rel_path),
            "name": gf.name,
            "total": len(findings),
            "breakdown": counts_by_rule,
            "findings": findings,
        })

    print(f"\nDiscovered {len(GENERATOR_FILES)} generator files under {GENERATORS_DIR.relative_to(DATA_BANK_ROOT)}/:\n")
    header = f"{'Generator File':<20} | {'(a) ID':<6} | {'(b) Lit':<7} | {'(c) Rng':<7} | {'(d) Wrap':<8} | {'(e) Name':<8} | {'(f) Br':<6} | {'(g) Arith':<9} | {'Total':<6}"
    print(header)
    print("-" * len(header))
    for s in file_summary:
        b = s["breakdown"]
        row = f"{s['name']:<20} | {b['(a)']:<6} | {b['(b)']:<7} | {b['(c)']:<7} | {b['(d)']:<8} | {b['(e)']:<8} | {b['(f)']:<6} | {b['(g)']:<9} | {s['total']:<6}"
        print(row)
    print("-" * len(header))
    print(f"{'TOTAL ACROSS ALL GENERATORS':<20} | {'':<6} | {'':<7} | {'':<7} | {'':<8} | {'':<8} | {'':<6} | {'':<9} | {total_findings_all:<6}\n")

    for s in file_summary:
        if s["findings"]:
            print(f"\n--- Violations in {s['file']} ({s['total']} findings) ---")
            for f in s["findings"][:15]:
                print(f"  Line {f['lineno']:<5} [{f['category']}]: {f['detail']}")
                print(f"         Snippet: {f['snippet']}")
            if len(s["findings"]) > 15:
                print(f"  ... and {len(s['findings']) - 15} additional violations in {s['name']}")

    print("\n" + "=" * 80)
    if total_findings_all > 0:
        print(f"RESULT: AUDIT FAILED with {total_findings_all} Rule 5a / FULLY EMERGENT violations.")
        sys.exit(1)
    else:
        print("RESULT: AUDIT PASSED. All generators are FULLY EMERGENT.")
        sys.exit(0)


if __name__ == "__main__":
    run_cli_audit()
