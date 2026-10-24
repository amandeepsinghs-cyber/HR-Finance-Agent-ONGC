"""Top-5 action generator (SPEC-08 §7, packet P2F.6).

Evaluates the lever library against verified SSOT rows for a given FY,
scoring and ranking levers with owner diversity and persona-specific logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import pandas as pd
import yaml

from .expr import ExprError, evaluate, _prev_fy, _get_5yr_window


LEVER_VAR_ALIASES: Dict[str, List[str]] = {
    "OPEX.EXCH_LOSS": ["OPEX.EXCH_LOSS", "PL.EXCHANGE_LOSS_10YR", "PL.EXCHANGE_LOSS", "EXP.EXCHANGE_LOSS"],
    "OPEX.PROVISIONS": ["OPEX.PROVISIONS", "PL.PROVISIONS_WRITEOFF", "PL.PROVISIONS"],
    "EXPL.WELLS": ["EXPL.WELLS", "PL.EXPL_WELL"],
    "PL.OPEX": ["PL.OPEX", "PL.OPEX_10YR", "EXP.OPERATING"],
    "RATIO.DEBTOR_DAYS": ["RATIO.DEBTOR_DAYS", "RATIO.DEBTORS_TURNOVER_DAYS", "DEBTOR_DAYS"],
    "BS.INVENTORIES": ["BS.INVENTORIES", "BS.INVENTORY"],
    "PL.REV_OPS": ["PL.REV_OPS", "REV_OPS"],
    "PROD.TOTAL_BOE": ["PROD.TOTAL_BOE", "QTY.TOTAL_BOE"],
    "BS.CWIP_TOTAL": ["BS.CWIP_TOTAL", "BS.CWIP"],
    "CF.CAPEX": ["CF.CAPEX", "CAPEX.TOTAL", "OTH.CAPEX"],
    "PL.EMP_BENEFIT": ["PL.EMP_BENEFIT", "OTH.EMP_EXPENDITURE"],
    "BS.LEASE_LIAB_TOTAL": ["BS.LEASE_LIAB_TOTAL", "BS.LEASE_LIAB_TOTAL_10YR"],
    "PL.FIN_COST": ["PL.FIN_COST", "PL.FINANCE_COSTS"],
}


def _format_indian_num(val: Any) -> str:
    """Format numbers Indian-style with 1 decimal place or integer for small counts."""
    if isinstance(val, (int, float)):
        # If integer-like and small (e.g. days), format without decimals
        if abs(val - round(val)) < 1e-6 and abs(val) < 1000:
            return str(int(round(val)))
        return f"{val:,.1f}"
    return str(val)


def _is_e_level_persona(persona: str) -> bool:
    """Check if persona belongs to employee levels E1–E4."""
    p = persona.upper().strip()
    return any(p.startswith(prefix) for prefix in ("E1", "E2", "E3", "E4")) or "E1-E4" in p


def _lookup_cell(
    df: pd.DataFrame,
    var_name: str,
    fy: str,
    scope: str = "standalone",
) -> Tuple[Optional[float], Optional[Dict[str, str]]]:
    """Look up a variable in df for a specific fiscal year."""
    aliases = LEVER_VAR_ALIASES.get(var_name, [var_name])
    if var_name not in aliases:
        aliases = [var_name] + aliases

    sub = df
    if "scope" in sub.columns:
        sub = sub[sub["scope"] == scope]
    if "period_type" in sub.columns:
        sub = sub[sub["period_type"] == "annual"]
    if "verified" in sub.columns:
        sub = sub[sub["verified"] == True]
    if "is_latest_vintage" in sub.columns:
        sub = sub[sub["is_latest_vintage"] == True]

    fy_col = "fiscal_year" if "fiscal_year" in sub.columns else ("fy" if "fy" in sub.columns else None)
    if fy_col and not sub.empty:
        sub = sub[sub[fy_col].astype(str).str.upper() == fy.upper()]

    lc_col = "line_code" if "line_code" in sub.columns else None
    if not lc_col or sub.empty:
        return None, None

    for lc in aliases:
        match = sub[sub[lc_col] == lc]
        if not match.empty:
            row = match.iloc[0]
            val = None
            for col in ("value_inr_cr", "value", "value_native"):
                if col in row and pd.notna(row[col]):
                    val = float(row[col])
                    break
            if val is not None:
                doc = str(row.get("source_doc", "")).strip() if pd.notna(row.get("source_doc")) else ""
                page_raw = str(row.get("source_page_label", row.get("source_page", ""))).strip()
                page = page_raw if page_raw.startswith("p.") else (f"p.{page_raw}" if page_raw else "")
                lineage = {
                    "doc": doc,
                    "page": page,
                    "line_code": lc,
                    "fy": fy,
                    "val": val,
                }
                return val, lineage

    # Composite fallback syntheses when direct aliases are absent
    if var_name in ("BS.CWIP_TOTAL", "BS.CWIP"):
        cwip_components = ["BS.CWIP_DEV_WELLS", "BS.CWIP_OG_FACILITIES", "BS.CWIP_OTHER"]
        cwip_vals = []
        doc = ""
        page = ""
        for c_lc in cwip_components:
            match_c = sub[sub[lc_col] == c_lc]
            if not match_c.empty:
                r_c = match_c.iloc[0]
                for col in ("value_inr_cr", "value", "value_native"):
                    if col in r_c and pd.notna(r_c[col]):
                        cwip_vals.append(float(r_c[col]))
                        if not doc and pd.notna(r_c.get("source_doc")):
                            doc = str(r_c["source_doc"]).strip()
                        if not page:
                            page_raw = str(r_c.get("source_page_label", r_c.get("source_page", ""))).strip()
                            page = page_raw if page_raw.startswith("p.") else (f"p.{page_raw}" if page_raw else "")
                        break
        if cwip_vals:
            val = round(sum(cwip_vals), 1)
            lineage = {
                "doc": doc,
                "page": page,
                "line_code": var_name,
                "fy": fy,
                "val": val,
            }
            return val, lineage

    if var_name in ("PROD.TOTAL_BOE", "QTY.TOTAL_BOE"):
        prod_lines = ["PROD.CRUDE_ONGC", "PROD.GAS_ONGC", "PROD.CRUDE_JV", "PROD.GAS_JV"]
        prod_vals = []
        doc = ""
        page = ""
        for p_lc in prod_lines:
            match_p = sub[sub[lc_col] == p_lc]
            if not match_p.empty:
                r_p = match_p.iloc[0]
                for col in ("value_inr_cr", "value", "value_native"):
                    if col in r_p and pd.notna(r_p[col]):
                        prod_vals.append(float(r_p[col]))
                        if not doc and pd.notna(r_p.get("source_doc")):
                            doc = str(r_p["source_doc"]).strip()
                        if not page:
                            page_raw = str(r_p.get("source_page_label", r_p.get("source_page", ""))).strip()
                            page = page_raw if page_raw.startswith("p.") else (f"p.{page_raw}" if page_raw else "")
                        break
        if prod_vals:
            val = round(sum(prod_vals), 3)
            lineage = {
                "doc": doc,
                "page": page,
                "line_code": var_name,
                "fy": fy,
                "val": val,
            }
            return val, lineage

    return None, None


@dataclass
class _CandidateAction:
    lever_id: str
    title: str
    owner: str
    kpi: str
    horizon_days: int
    confidence: float
    score: float
    impact: Dict[str, Any]
    what_to_do: str
    ask: str
    evidence: List[Dict[str, str]]


def generate_actions(
    df: pd.DataFrame,
    fy: str,
    persona: str,
    levers_path: str | Path,
    ar_evidence_fn: Optional[Callable[[str, str], List[Any]]] = None,
    prior_fy: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate lever library against verified SSOT rows and return SPEC-08 §7.3 payload."""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    with open(levers_path, "r", encoding="utf-8") as f:
        levers_data = yaml.safe_load(f)

    levers_list = levers_data.get("levers", [])
    candidates: List[_CandidateAction] = []

    # Window of relevant fiscal years (up to 5 years ending in fy)
    window_fys = _get_5yr_window(fy)

    for lever in levers_list:
        lever_id = lever["id"]
        title = lever["title"]
        orig_owner = lever["owner"]
        kpi = lever["kpi"]
        horizon_days = int(lever.get("horizon_days", 90))
        lever_inputs = lever.get("trigger", {}).get("inputs", [])

        # Build data cache and lineage for all inputs across 5-year window
        history_data: Dict[str, Dict[str, float]] = {y: {} for y in window_fys}
        lineage_map: Dict[Tuple[str, str], Dict[str, str]] = {}

        missing_current_input = False
        for inp in lever_inputs:
            for y in window_fys:
                val, lin = _lookup_cell(df, inp, y)
                if val is not None:
                    history_data[y][inp] = val
                    if lin:
                        lineage_map[(inp, y)] = lin
                elif y == fy:
                    # Current year input is missing
                    missing_current_input = True

        if missing_current_input:
            continue

        current_ctx = history_data.get(fy, {})
        def history_fn(target_fy: str) -> Dict[str, float]:
            return history_data.get(target_fy, {})

        # Evaluate trigger expression
        trigger_expr = lever.get("trigger", {}).get("expr", "false")
        try:
            fired = evaluate(
                trigger_expr,
                context=current_ctx,
                history_fn=history_fn,
                current_fy=fy,
                inputs=lever_inputs,
            )
        except Exception:
            fired = False

        if not fired:
            continue

        # Evaluate impact range
        impact_spec = lever.get("impact", {})
        kind = impact_spec.get("kind", "annual")
        try:
            low_val = round(float(evaluate(
                impact_spec.get("low_expr", "0"),
                context=current_ctx,
                history_fn=history_fn,
                current_fy=fy,
                inputs=lever_inputs,
            )), 1)
            mid_val = round(float(evaluate(
                impact_spec.get("mid_expr", "0"),
                context=current_ctx,
                history_fn=history_fn,
                current_fy=fy,
                inputs=lever_inputs,
            )), 1)
            high_val = round(float(evaluate(
                impact_spec.get("high_expr", "0"),
                context=current_ctx,
                history_fn=history_fn,
                current_fy=fy,
                inputs=lever_inputs,
            )), 1)
        except Exception:
            continue

        # Calculate confidence: confidence_base * 0.7 if assumption * 0.5 if synthetic
        conf_base = float(lever.get("confidence_base", 1.0))
        if lever.get("uses_assumption", False):
            conf_base *= 0.7
        if lever.get("uses_synthetic", False):
            conf_base *= 0.5
        confidence = round(conf_base, 2)

        score = round(mid_val * confidence, 2)

        # Template renderer helper
        def _render_tmpl(tmpl: str) -> str:
            def _repl(m: re.Match) -> str:
                expr_str = m.group(1).strip()
                try:
                    res = evaluate(
                        expr_str,
                        context=current_ctx,
                        history_fn=history_fn,
                        current_fy=fy,
                        inputs=lever_inputs,
                    )
                    return _format_indian_num(res)
                except Exception:
                    return m.group(0)
            return re.sub(r"\{([^{}]+)\}", _repl, tmpl)

        what_to_do = _render_tmpl(lever.get("what_to_do_template", ""))
        ask = _render_tmpl(lever.get("ask_template", ""))

        # Build evidence items
        evidence: List[Dict[str, str]] = []
        prior_y = _prev_fy(fy)

        all_expr_text = " ".join([
            trigger_expr,
            impact_spec.get("low_expr", ""),
            impact_spec.get("mid_expr", ""),
            impact_spec.get("high_expr", ""),
            lever.get("what_to_do_template", ""),
            lever.get("ask_template", ""),
        ])

        used_years = [fy]
        if prior_y and ("prior" in all_expr_text or "yoy" in all_expr_text):
            if prior_y not in used_years:
                used_years.append(prior_y)
        if "avg5" in all_expr_text or "median5" in all_expr_text:
            for y in window_fys:
                if y not in used_years:
                    used_years.append(y)

        for y in used_years:
            for inp in lever_inputs:
                if (inp, y) in lineage_map:
                    lin = lineage_map[(inp, y)]
                    evidence.append({
                        "type": "data",
                        "ref": f"{inp} {y} = {_format_indian_num(lin['val'])} ({lin['doc']} {lin['page']})".strip(),
                    })

        # Inject AR evidence if available
        if ar_evidence_fn:
            try:
                ar_items = ar_evidence_fn(lever_id, fy)
                for item in ar_items:
                    ref_str = item.get("ref", "") if isinstance(item, dict) else str(item)
                    if ref_str:
                        evidence.append({"type": "ar", "ref": ref_str})
            except Exception:
                pass

        candidates.append(_CandidateAction(
            lever_id=lever_id,
            title=title,
            owner=orig_owner,
            kpi=kpi,
            horizon_days=horizon_days,
            confidence=confidence,
            score=score,
            impact={
                "low": low_val,
                "mid": mid_val,
                "high": high_val,
                "unit": "INR_cr",
                "kind": kind,
                "label": "Modelled estimate",
            },
            what_to_do=what_to_do,
            ask=ask,
            evidence=evidence,
        ))

    # Selection algorithm (SPEC-08 §7.2, Packet §5 requirement 2)
    # Sort candidates by score descending, tie-break by lever_id ascending
    candidates.sort(key=lambda c: (-c.score, c.lever_id))

    selected: List[_CandidateAction] = []
    owner_counts: Dict[str, int] = {}

    p_upper = persona.upper().strip()

    # Rule: If persona is DIR_HR, L07 is always included when it fires
    if p_upper == "DIR_HR":
        l07_candidate = next((c for c in candidates if c.lever_id == "L07"), None)
        if l07_candidate:
            selected.append(l07_candidate)
            owner_counts[l07_candidate.owner] = 1

    # Greedily select top candidates with max 3 per owner
    for cand in candidates:
        if any(s.lever_id == cand.lever_id for s in selected):
            continue
        if len(selected) >= 5:
            break
        if owner_counts.get(cand.owner, 0) < 3:
            selected.append(cand)
            owner_counts[cand.owner] = owner_counts.get(cand.owner, 0) + 1

    # Order the selected items per persona rules
    if p_upper == "DIR_HR":
        # DIR_HR levers first, then others sorted by score
        selected.sort(key=lambda c: (c.owner != "DIR_HR", -c.score, c.lever_id))
    elif p_upper == "DIR_FIN":
        # DIR_FIN levers first, then others sorted by score
        selected.sort(key=lambda c: (c.owner != "DIR_FIN", -c.score, c.lever_id))
    else:
        # Default: sorted by score
        selected.sort(key=lambda c: (-c.score, c.lever_id))

    is_e_level = _is_e_level_persona(persona)

    items: List[Dict[str, Any]] = []
    delegation_table: List[Dict[str, str]] = []

    for rank_idx, cand in enumerate(selected, 1):
        assigned_owner = "for discussion" if is_e_level else cand.owner

        items.append({
            "rank": rank_idx,
            "lever_id": cand.lever_id,
            "title": cand.title,
            "what_to_do": cand.what_to_do,
            "impact": cand.impact,
            "owner": assigned_owner,
            "horizon_days": cand.horizon_days,
            "kpi": cand.kpi,
            "evidence": cand.evidence,
            "confidence": cand.confidence,
        })

        primary_evidence = cand.evidence[0]["ref"] if cand.evidence else ""
        delegation_table.append({
            "owner": assigned_owner,
            "ask": cand.ask,
            "by_when": f"{cand.horizon_days} days",
            "kpi": cand.kpi,
            "evidence": primary_evidence,
        })

    result: Dict[str, Any] = {
        "fy": fy,
        "items": items,
        "delegation_table": delegation_table,
    }

    if len(items) < 5:
        result["note"] = f"Only {len(items)} levers are triggered by {fy} data"

    return result
