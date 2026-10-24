"""Safe arithmetic and logical expression evaluator (SPEC-08 §7.1, packet P2F.6).

Evaluates lever trigger and impact expressions over named inputs using Python's AST.
Strictly forbids attribute access, execution of unwhitelisted functions, and undeclared variables.
"""

from __future__ import annotations

import ast
import re
import statistics
from typing import Any, Callable, Dict, List, Optional, Set

WHITELIST_FUNCTIONS: Set[str] = {
    "abs",
    "min",
    "max",
    "prior",
    "yoy",
    "avg5",
    "median5",
}


class ExprError(ValueError):
    """Raised when an expression is malformed, forbidden, or contains unknown names."""
    pass


def _prev_fy(fy: str) -> str:
    """Compute previous fiscal year (e.g. 'FY26' -> 'FY25')."""
    fy_str = fy.strip()
    if fy_str.upper().startswith("FY") and fy_str[2:].isdigit():
        num = int(fy_str[2:])
        width = len(fy_str[2:])
        return f"FY{num - 1:0{width}d}"
    if fy_str.isdigit():
        return str(int(fy_str) - 1)
    return fy_str


def _get_5yr_window(fy: str) -> List[str]:
    """Return 5-year fiscal window ending in fy (e.g. ['FY22', 'FY23', 'FY24', 'FY25', 'FY26'])."""
    curr = fy
    window = [curr]
    for _ in range(4):
        curr = _prev_fy(curr)
        window.append(curr)
    return list(reversed(window))


def evaluate(
    expr_str: str,
    context: Optional[Dict[str, Any]] = None,
    history_fn: Optional[Callable[[str], Dict[str, float]]] = None,
    current_fy: Optional[str] = None,
    inputs: Optional[List[str]] = None,
) -> Any:
    """Safely evaluate an arithmetic/logical expression string.

    Args:
        expr_str: The expression to evaluate.
        context: Mapping of variable names to values for current_fy.
        history_fn: Optional callable (fy: str) -> Dict[str, float] for prior/yoy/avg5/median5.
        current_fy: The current fiscal year (e.g. 'FY26').
        inputs: Declared list of input names.

    Returns:
        The result of the evaluated expression (float, bool, or int).
    """
    if context is None:
        context = {}

    declared_names: Set[str] = set(context.keys())
    if inputs:
        declared_names.update(inputs)

    # Dotted identifiers (e.g. 'BS.INVENTORIES', 'PL.OPEX') in declared inputs
    # are rewritten to safe variable names before parsing to avoid becoming ast.Attribute.
    var_map: Dict[str, str] = {}
    rev_map: Dict[str, str] = {}

    clean_expr = expr_str.strip()
    # Sort by length descending so longer dotted names match first
    dotted_declared = sorted([name for name in declared_names if "." in name], key=len, reverse=True)
    for idx, orig_name in enumerate(dotted_declared):
        safe_id = f"_VAR_{idx}_"
        var_map[orig_name] = safe_id
        rev_map[safe_id] = orig_name
        clean_expr = re.sub(r"\b" + re.escape(orig_name) + r"\b", safe_id, clean_expr)

    try:
        tree = ast.parse(clean_expr, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"Syntax error in expression '{expr_str}': {e}") from e

    def _eval_ast(node: ast.AST, eval_fy: Optional[str]) -> Any:
        if isinstance(node, ast.Expression):
            return _eval_ast(node.body, eval_fy)

        elif isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            orig_name = rev_map.get(node.id, node.id)
            if orig_name in WHITELIST_FUNCTIONS:
                return orig_name

            # Look up in year context or base context
            if eval_fy and history_fn:
                year_ctx = history_fn(eval_fy)
                if orig_name in year_ctx:
                    return year_ctx[orig_name]

            if orig_name in context:
                return context[orig_name]

            raise ExprError(f"Unknown name in expression: '{orig_name}'")

        elif isinstance(node, ast.Attribute):
            # Explicitly reject all attribute access (e.g. obj.attr, os.system)
            raise ExprError(f"Attribute access is forbidden: {ast.dump(node)}")

        elif isinstance(node, ast.BinOp):
            left = _eval_ast(node.left, eval_fy)
            right = _eval_ast(node.right, eval_fy)
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    return 0.0
                return left / right
            elif isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    return 0.0
                return left // right
            elif isinstance(node.op, ast.Mod):
                if right == 0:
                    return 0.0
                return left % right
            else:
                raise ExprError(f"Unsupported binary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.UnaryOp):
            val = _eval_ast(node.operand, eval_fy)
            if isinstance(node.op, ast.UAdd):
                return +val
            elif isinstance(node.op, ast.USub):
                return -val
            elif isinstance(node.op, ast.Not):
                return not val
            else:
                raise ExprError(f"Unsupported unary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.Compare):
            left = _eval_ast(node.left, eval_fy)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval_ast(comparator, eval_fy)
                if isinstance(op, ast.Gt) and not (left > right):
                    return False
                elif isinstance(op, ast.GtE) and not (left >= right):
                    return False
                elif isinstance(op, ast.Lt) and not (left < right):
                    return False
                elif isinstance(op, ast.LtE) and not (left <= right):
                    return False
                elif isinstance(op, ast.Eq) and not (left == right):
                    return False
                elif isinstance(op, ast.NotEq) and not (left != right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(_eval_ast(val, eval_fy) for val in node.values)
            elif isinstance(node.op, ast.Or):
                return any(_eval_ast(val, eval_fy) for val in node.values)
            else:
                raise ExprError(f"Unsupported boolean operator: {type(node.op).__name__}")

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ExprError("Function call must be a simple identifier, not an attribute or complex expression")

            func_name = node.func.id
            if func_name not in WHITELIST_FUNCTIONS:
                raise ExprError(f"Function call outside whitelist is forbidden: '{func_name}'")

            # Standard math functions
            if func_name == "abs":
                if len(node.args) != 1:
                    raise ExprError("abs() takes exactly 1 argument")
                return abs(_eval_ast(node.args[0], eval_fy))
            elif func_name == "min":
                if not node.args:
                    raise ExprError("min() requires at least 1 argument")
                return min(_eval_ast(a, eval_fy) for a in node.args)
            elif func_name == "max":
                if not node.args:
                    raise ExprError("max() requires at least 1 argument")
                return max(_eval_ast(a, eval_fy) for a in node.args)

            # Historical / window functions
            target_fy = eval_fy or current_fy
            if not target_fy or not history_fn:
                # Fallback: if caller passed direct key in context
                arg_raw = clean_expr[node.args[0].col_offset : node.args[0].end_col_offset] if hasattr(node.args[0], "col_offset") else ""
                key_fallback = f"{func_name}({arg_raw})"
                if key_fallback in context:
                    return context[key_fallback]
                raise ExprError(f"Function '{func_name}' requires current_fy and history_fn")

            arg_node = node.args[0]
            if func_name == "prior":
                prior_year = _prev_fy(target_fy)
                return _eval_ast(arg_node, prior_year)

            elif func_name == "yoy":
                curr_val = _eval_ast(arg_node, target_fy)
                prior_year = _prev_fy(target_fy)
                prior_val = _eval_ast(arg_node, prior_year)
                if prior_val == 0:
                    return 0.0
                return (curr_val - prior_val) / prior_val

            elif func_name == "avg5":
                window_fys = _get_5yr_window(target_fy)
                vals = [_eval_ast(arg_node, y) for y in window_fys]
                return sum(vals) / len(vals)

            elif func_name == "median5":
                window_fys = _get_5yr_window(target_fy)
                vals = [_eval_ast(arg_node, y) for y in window_fys]
                return statistics.median(vals)

        else:
            raise ExprError(f"Forbidden AST node type: {type(node).__name__}")

    return _eval_ast(tree, current_fy)


eval_expr = evaluate
